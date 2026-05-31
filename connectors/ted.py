"""
HFIP – TED Europa Connector
Fetches procurement notices via the official TED Search API v3.
API Docs: https://docs.ted.europa.eu/api/latest/search.html
NOTE: TED Search API is ANONYMOUS – no API key required.

Expert search criteria (exactly as specified):
  (classification-cpv IN (48180000 48200000 48800000 72110000 72200000 72300000
   73120000 73200000 73300000 85000000))
  AND (((FT ~ ("Gesundheit" OR "Health")) OR (FT ~ ("KHZG" OR "medical")))
       OR (FT ~ ("medizin" OR "patient")))
  AND contract-nature IN (9 services works Z)
  AND notice-type IN (brin-eeig brin-ecs cn-standard cn-social can-modif corr
   cn-desg can-desg pin-buyer qu-sy pin-cfc-social pin-cfc-standard pin-only
   pin-rtl subco veat)
  AND NOT (classification-cpv IN (core mior dese))
  SORT BY publication-number DESC
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from database.models import Tender


# ─── Constants ───────────────────────────────────────────────────────────────

TED_BASE_URL = "https://api.ted.europa.eu/v3"
SEARCH_ENDPOINT = "/notices/search"

# ── Exact CPV codes from expert search specification ──────────────────────────
TED_CPV_CODES = [
    "48180000",  # Medical software package
    "48200000",  # Networking, internet, intranet software
    "48800000",  # Information systems and servers
    "72110000",  # Computer consulting services
    "72200000",  # Software programming and consultancy services
    "72300000",  # Data services
    "73120000",  # Experimental development services
    "73200000",  # Research and development consultancy services
    "73300000",  # Design and execution of R&D
    "85000000",  # Health and social work services
]

# ── Notice types from expert search specification ─────────────────────────────
TED_NOTICE_TYPES = [
    "brin-eeig", "brin-ecs", "cn-standard", "cn-social", "can-modif",
    "corr", "cn-desg", "can-desg", "pin-buyer", "qu-sy",
    "pin-cfc-social", "pin-cfc-standard", "pin-only", "pin-rtl", "subco", "veat",
]

# ── Full-text keyword groups from expert search specification ─────────────────
TED_FT_KEYWORDS = [
    '"Gesundheit" OR "Health"',
    '"KHZG" OR "medical"',
    '"medizin" OR "patient"',
]

# ── Build the expert search query string ─────────────────────────────────────
_cpv_list = " ".join(TED_CPV_CODES)
_ft_clause = " OR ".join(f'FT ~ ({kw})' for kw in TED_FT_KEYWORDS)
_notice_types = " ".join(TED_NOTICE_TYPES)

TED_EXPERT_QUERY = (
    f"classification-cpv IN ({_cpv_list}) "
    f"AND ({_ft_clause}) "
    f"AND contract-nature IN (services works) "
    f"AND notice-type IN ({_notice_types}) "
    f"AND NOT (classification-cpv IN (core mior dese))"
)

# Fields to request from TED API
TED_FIELDS = [
    "ND",   # Notice number
    "TI",   # Title
    "DS",   # Description / short text
    "CY",   # Country
    "DT",   # Deadline
    "PD",   # Publication date
    "PC",   # CPV codes
    "AU",   # Authority name
    "IA",   # Internet address (buyer's website)
    "TD",   # Document type
    "publication-number",  # Canonical notice identifier for URL construction
]


class TEDConnector:
    """
    Pulls procurement notices from TED Europa.
    Uses the POST /v3/notices/search endpoint.
    NO API KEY required – TED Search API is openly accessible.
    """

    def __init__(self, api_key: Optional[str] = None):
        # api_key kept for interface compatibility but not needed for Search API
        self.api_key = api_key or os.getenv("TED_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
    def _post(self, payload: dict) -> dict:
        url = f"{TED_BASE_URL}{SEARCH_ENDPOINT}"
        resp = self.session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def fetch_recent(self, days_back: int = 7) -> List[dict]:
        """
        Fetch TED notices using the exact expert search query (CPV codes, FT
        keywords, notice types, contract nature) sorted by publication-number DESC.
        """
        since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y%m%d")
        today = datetime.utcnow().strftime("%Y%m%d")

        # Add date window on top of the expert search query
        dated_query = f"PD>={since} AND PD<={today} AND {TED_EXPERT_QUERY}"

        all_tenders: List[dict] = []
        page = 1

        while True:
            payload = {
                "query": dated_query,
                "fields": TED_FIELDS,
                "page": page,
                "limit": 25,
                "scope": "ALL",
                "onlyLatestVersions": True,
                "sort": [{"field": "publication-number", "order": "DESC"}],
            }

            try:
                data = self._post(payload)
            except Exception as exc:
                logger.error(f"TED API error page {page}: {exc}")
                break

            notices = data.get("notices", [])
            if not notices:
                break

            for notice in notices:
                tender = self._parse_notice(notice)
                if tender:
                    all_tenders.append(tender)

            total = data.get("totalNoticeCount", 0)
            fetched = page * 25
            logger.info(f"TED expert search: page {page} → {len(notices)} notices ({fetched}/{total})")

            if fetched >= total or page >= 8:  # Max 200 notices per run
                break

            page += 1
            time.sleep(1)

        logger.info(f"TED: collected {len(all_tenders)} notices total")
        return all_tenders

    def _parse_notice(self, notice: dict) -> Optional[dict]:
        """Map a TED API notice object to the HFIP normalized tender format."""
        try:
            title = notice.get("TI", {})
            if isinstance(title, dict):
                # TED returns multilingual: prefer English, then German, then first available
                title_str = (
                    title.get("EN")
                    or title.get("DE")
                    or next(iter(title.values()), "")
                )
            else:
                title_str = str(title)

            description = notice.get("DS", {})
            if isinstance(description, dict):
                desc_str = (
                    description.get("EN")
                    or description.get("DE")
                    or next(iter(description.values()), "")
                )
            else:
                desc_str = str(description)

            # Deadline – DT is a list of ISO datetime strings e.g. ['2026-06-22T10:00:00+02:00']
            deadline_raw = notice.get("DT", "")
            if isinstance(deadline_raw, list):
                deadline_raw = deadline_raw[0] if deadline_raw else ""
            deadline = None
            if deadline_raw:
                try:
                    # Strip timezone and parse ISO datetime
                    dt_clean = str(deadline_raw).split("+")[0].split("Z")[0].rstrip("Z")
                    deadline = datetime.strptime(dt_clean[:10], "%Y-%m-%d")
                except ValueError:
                    pass

            # Published date – TED returns "YYYY-MM-DD+HH:MM" format
            pub_raw = notice.get("PD", "")
            published = None
            if pub_raw:
                try:
                    # Strip timezone offset before parsing
                    pub_clean = str(pub_raw).split("+")[0].split("-")[0] if "+" in str(pub_raw) else str(pub_raw)[:10].replace("-", "")
                    # Handle both "20260531" and "2026-05-31" formats
                    pub_clean = str(pub_raw)[:10].replace("-", "")
                    published = datetime.strptime(pub_clean, "%Y%m%d")
                except ValueError:
                    pass

            # CPV codes
            cpv_raw = notice.get("PC", [])
            if isinstance(cpv_raw, str):
                cpv_codes = [cpv_raw]
            elif isinstance(cpv_raw, list):
                cpv_codes = cpv_raw
            else:
                cpv_codes = []

            # URL – canonical TED notice page (primary link shown to users)
            pub_number = notice.get("publication-number", "") or notice.get("ND", "")
            notice_id  = notice.get("ND", "")
            if pub_number:
                url = f"https://ted.europa.eu/en/notice/{pub_number}/general-information"
            elif notice_id:
                url = f"https://ted.europa.eu/en/notice/-/detail/{notice_id}"
            else:
                url = ""

            # Buyer/authority internet address (IA field) – stored as supplementary info
            buyer_url_raw = notice.get("IA", "")
            if isinstance(buyer_url_raw, list):
                buyer_url = buyer_url_raw[0] if buyer_url_raw else ""
            else:
                buyer_url = str(buyer_url_raw).strip() if buyer_url_raw else ""
            # Append buyer URL to description so it's surfaced in results
            if buyer_url and buyer_url.startswith("http"):
                desc_str = f"{desc_str}\n\nContracting authority: {buyer_url}".strip()

            # Organization – AU is a multilingual dict: {'deu': ['Name'], 'eng': ['Name']}
            org_raw = notice.get("AU", "")
            if isinstance(org_raw, str):
                organization = org_raw
            elif isinstance(org_raw, dict):
                first_val = next(iter(org_raw.values()), [])
                organization = first_val[0] if isinstance(first_val, list) and first_val else str(first_val)
            elif isinstance(org_raw, list):
                organization = org_raw[0] if org_raw else ""
            else:
                organization = ""

            # Country
            country_raw = notice.get("CY", "")
            if isinstance(country_raw, str):
                country = country_raw
            elif isinstance(country_raw, list):
                country = country_raw[0] if country_raw else ""
            else:
                country = str(country_raw) if country_raw else ""

            if not title_str:
                return None

            tender = {
                "source": "ted",
                "title": title_str,
                "description": desc_str,
                "organization": organization,
                "country": country,
                "deadline": deadline,
                "published_date": published,
                "url": url,
                "cpv_codes": cpv_codes,
                "hash": Tender.compute_hash(title_str, url, "ted"),
            }
            return tender

        except Exception as exc:
            logger.warning(f"TED notice parse error: {exc} | raw={str(notice)[:200]}")
            return None
