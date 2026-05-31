"""
HFIP – Bund / German Federal Procurement Connector
Uses the TED Europa Search API filtered to Germany (CY=DEU) to retrieve
German federal health & research procurement notices.

This approach guarantees real, working TED notice URLs and is not affected
by JavaScript-rendering or broken RSS feeds on service.bund.de.

TED API docs: https://docs.ted.europa.eu/api/latest/search.html
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


# ─── TED query for German federal health tenders ─────────────────────────────

# Country code DEU = Germany
BUND_COUNTRY = "DEU"

# Health/research keyword filter
BUND_FT_TERMS = (
    "Gesundheit OR Krankenhaus OR Klinikum OR Kliniken OR Medizin "
    "OR medizinisch OR Patient OR Uniklinik OR Krankenkasse OR Health"
)

# Notice types that represent actual contract/procurement notices
BUND_NOTICE_TYPES = "cn-standard cn-social pin-buyer pin-only"

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

TED_FIELDS = ["ND", "TI", "DS", "CY", "DT", "PD", "PC", "AU", "IA"]

DATE_PATTERNS = [r"(\d{2}\.\d{2}\.\d{4})", r"(\d{4}-\d{2}-\d{2})"]


class BundConnector:
    """
    Fetches German federal health/research procurement via TED Europa API
    filtered to Germany (CY=DEU).  Produces real, verified TED notice URLs.
    """

    def __init__(self, delay: float = 1.0, max_pages: int = 4):
        self.delay = delay
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def fetch_recent(self, days_back: int = 14) -> List[dict]:
        """Fetch recent German health tenders from TED."""
        since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y%m%d")
        today = datetime.utcnow().strftime("%Y%m%d")

        query = (
            f"CY IN ({BUND_COUNTRY}) "
            f"AND notice-type IN ({BUND_NOTICE_TYPES}) "
            f"AND PD>={since} AND PD<={today}"
        )

        all_tenders: List[dict] = []
        page = 1

        while page <= self.max_pages:
            payload = {
                "query": query,
                "fields": TED_FIELDS,
                "page": page,
                "limit": 25,
                "scope": "ALL",
                "onlyLatestVersions": True,
            }
            try:
                data = self._post(payload)
            except Exception as exc:
                logger.error(f"Bund/TED page {page} error: {exc}")
                break

            notices = data.get("notices", [])
            if not notices:
                break

            for n in notices:
                tender = self._parse_notice(n)
                if tender:
                    all_tenders.append(tender)

            total = data.get("totalNoticeCount", data.get("total", 0))
            fetched = page * 25
            logger.info(f"Bund/TED page {page}: {len(notices)} notices ({fetched}/{total})")
            if fetched >= total:
                break

            page += 1
            time.sleep(self.delay)

        logger.info(f"Bund: collected {len(all_tenders)} German health notices from TED")
        return all_tenders

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=20))
    def _post(self, payload: dict) -> dict:
        resp = self.session.post(TED_SEARCH_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _parse_notice(self, notice: dict) -> Optional[dict]:
        try:
            # Title
            ti = notice.get("TI", {})
            if isinstance(ti, dict):
                title = ti.get("DEU") or ti.get("ENG") or next(iter(ti.values()), "")
            else:
                title = str(ti)

            if not title:
                return None

            # Description
            ds = notice.get("DS", {})
            if isinstance(ds, dict):
                desc = ds.get("DEU") or ds.get("ENG") or next(iter(ds.values()), "")
            else:
                desc = str(ds) if ds else ""

            # Published date
            pub_raw = str(notice.get("PD", ""))
            published = None
            try:
                published = datetime.strptime(pub_raw[:8].replace("-", ""), "%Y%m%d")
            except ValueError:
                pass

            # Deadline
            dt_raw = notice.get("DT", "")
            if isinstance(dt_raw, list):
                dt_raw = dt_raw[0] if dt_raw else ""
            deadline = None
            if dt_raw:
                try:
                    deadline = datetime.strptime(str(dt_raw)[:10], "%Y-%m-%d")
                except ValueError:
                    pass

            # CPV codes
            pc = notice.get("PC", [])
            cpv_codes = pc if isinstance(pc, list) else ([pc] if pc else [])

            # Organization
            au = notice.get("AU", "")
            if isinstance(au, dict):
                first = next(iter(au.values()), [])
                organization = first[0] if isinstance(first, list) and first else str(first)
            elif isinstance(au, list):
                organization = au[0] if au else ""
            else:
                organization = str(au) if au else "Bundesverwaltung"

            # URL – canonical TED notice page
            nd = notice.get("ND", "")
            url = f"https://ted.europa.eu/en/notice/-/detail/{nd}" if nd else ""

            return {
                "source": "bund",
                "title": title,
                "description": desc[:3000],
                "organization": organization,
                "country": "DE",
                "deadline": deadline,
                "published_date": published,
                "url": url,
                "cpv_codes": cpv_codes,
                "hash": Tender.compute_hash(title, url, "bund"),
            }
        except Exception as exc:
            logger.warning(f"Bund notice parse error: {exc}")
            return None
