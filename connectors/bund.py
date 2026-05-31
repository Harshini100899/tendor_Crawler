"""
HFIP – Bund.de / service.bund.de Connector
Uses the official service.bund.de procurement search with the exact query
string specified by the department:

  Gesundheit* OR Uniklinik* OR Medizin OR Medizinisch OR Patient* OR
  Krankenhaus* OR Krankenkasse OR Health OR Klinikum OR Kliniken
  NOT Bauleistungen

Source: https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from urllib.parse import urljoin, urlencode, quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup
from loguru import logger

from database.models import Tender


# ─── service.bund.de search configuration ────────────────────────────────────

BUND_SEARCH_BASE = "https://www.service.bund.de"
BUND_SEARCH_FORM_URL = (
    f"{BUND_SEARCH_BASE}/Content/DE/Ausschreibungen/Suche/Formular.html"
)

# Exact search terms as specified in requirements
# Wildcards (*) and NOT operator preserved
BUND_SEARCH_QUERY = (
    "Gesundheit* OR Uniklinik* OR Medizin OR Medizinisch OR Patient* "
    "OR Krankenhaus* OR Krankenkasse OR Health OR Klinikum OR Kliniken "
    "NOT Bauleistungen"
)

# Terms that must NOT appear (mirrors the "NOT Bauleistungen" exclusion)
BUND_EXCLUDE_TERMS = ["bauleistung", "bauleistungen", "straßenbau", "tiefbau", "hochbau"]

# Positive inclusion terms (all must match at least one for post-filter)
BUND_INCLUDE_TERMS = [
    "gesundheit", "uniklinik", "medizin", "medizinisch", "patient",
    "krankenhaus", "krankenkasse", "health", "klinikum", "kliniken",
    "klinik",
]

# RSS fallback – Bund Ausschreibungen generic feed (used if search form fails)
BUND_RSS_URL = (
    "https://www.bund.de/SiteGlobals/Functions/RSSFeed/RSSFeed_Ausschreibungen/"
    "RSSFeed_Ausschreibungen_node.rss"
)
BUND_RSS_FOERDER_URL = (
    "https://www.bund.de/SiteGlobals/Functions/RSSFeed/RSSFeed_Foerderprogramme/"
    "RSSFeed_Foerderprogramme_node.rss"
)


class BundConnector:
    """
    Fetches German federal procurement/funding entries matching the exact
    department search terms from service.bund.de, with RSS fallback.
    Applies "NOT Bauleistungen" post-filter to exclude construction.
    """

    def __init__(self, delay: float = 2.0, max_pages: int = 5):
        self.delay = delay
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HFIP/1.0 (Healthcare Funding Intelligence)",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def fetch_recent(self) -> List[dict]:
        """Try service.bund.de search form first; fall back to filtered RSS."""
        tenders = self._fetch_search_form()
        if tenders:
            logger.info(f"Bund search form: {len(tenders)} relevant entries")
            return tenders

        logger.warning("Bund search form returned nothing – falling back to RSS + keyword filter")
        tenders = self._fetch_rss_filtered()
        logger.info(f"Bund RSS fallback: {len(tenders)} relevant entries")
        return tenders

    # ── Primary: service.bund.de search form ─────────────────────────────────

    def _fetch_search_form(self) -> List[dict]:
        """
        Submit the search query to service.bund.de and paginate through results.
        The form accepts GET parameters including 'searchString' (or 'suche').
        """
        all_tenders: List[dict] = []
        for page_num in range(1, self.max_pages + 1):
            page_tenders = self._search_page(page_num)
            if not page_tenders:
                break
            all_tenders.extend(page_tenders)
            time.sleep(self.delay)
        return all_tenders

    def _search_page(self, page_num: int) -> List[dict]:
        """Fetch one page of search results from service.bund.de."""
        params = {
            "view": "processForm",
            "resultsPerPage": "20",
            "pageNumber": str(page_num),
            "searchText": BUND_SEARCH_QUERY,
            "noFilterForClosedPublication": "true",
        }
        try:
            resp = self.session.get(
                BUND_SEARCH_FORM_URL, params=params, timeout=25
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            return self._parse_search_results(soup)
        except Exception as exc:
            logger.warning(f"Bund search page {page_num} failed: {exc}")
            return []

    def _parse_search_results(self, soup: BeautifulSoup) -> List[dict]:
        tenders = []
        # service.bund.de result list uses divs/articles with result classes
        items = (
            soup.find_all("div", class_=re.compile(r"(result|treffer|item|entry|ausschreibung)", re.I))
            or soup.find_all("article")
            or soup.find_all("li", class_=re.compile(r"(result|item|entry)", re.I))
        )
        seen: set = set()
        for item in items:
            tender = self._parse_result_item(item)
            if tender and tender["url"] not in seen:
                if self._passes_filter(tender):
                    seen.add(tender["url"])
                    tenders.append(tender)
        return tenders

    def _parse_result_item(self, element) -> Optional[dict]:
        try:
            heading = element.find(re.compile(r"^h[1-6]$"))
            title = heading.get_text(strip=True) if heading else ""
            if not title:
                a = element.find("a", href=True)
                title = a.get_text(strip=True) if a else ""
            if len(title) < 8:
                return None

            link_tag = element.find("a", href=True)
            href = link_tag["href"] if link_tag else ""
            url = urljoin(BUND_SEARCH_BASE, href) if href else BUND_SEARCH_FORM_URL

            desc_tag = element.find("p")
            description = (
                desc_tag.get_text(strip=True) if desc_tag
                else element.get_text(separator=" ", strip=True)[:2000]
            )

            return {
                "source": "bund",
                "title": title,
                "description": description[:5000],
                "organization": "Bundesverwaltung",
                "country": "DE",
                "deadline": None,
                "published_date": datetime.utcnow(),
                "url": url,
                "cpv_codes": [],
                "hash": Tender.compute_hash(title, url, "bund"),
            }
        except Exception as exc:
            logger.debug(f"Bund item parse error: {exc}")
            return None

    # ── RSS fallback ──────────────────────────────────────────────────────────

    def _fetch_rss_filtered(self) -> List[dict]:
        """Parse Bund RSS feeds and apply the exact department keyword filter."""
        all_tenders: List[dict] = []
        for feed_url in [BUND_RSS_URL, BUND_RSS_FOERDER_URL]:
            try:
                resp = self.session.get(feed_url, timeout=20)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
            except Exception as exc:
                logger.error(f"Bund RSS fetch failed [{feed_url}]: {exc}")
                continue

            for entry in feed.entries:
                tender = self._parse_rss_entry(entry)
                if tender and self._passes_filter(tender):
                    all_tenders.append(tender)
            time.sleep(1)
        return all_tenders

    def _parse_rss_entry(self, entry) -> Optional[dict]:
        try:
            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = re.sub(r"<[^>]+>", " ", summary).strip()
            link = getattr(entry, "link", "") or ""

            published = None
            for attr in ("published", "updated"):
                if hasattr(entry, attr):
                    try:
                        published = parsedate_to_datetime(getattr(entry, attr)).replace(tzinfo=None)
                        break
                    except Exception:
                        pass

            if not title:
                return None

            return {
                "source": "bund",
                "title": title,
                "description": summary[:5000],
                "organization": "Bundesverwaltung",
                "country": "DE",
                "deadline": None,
                "published_date": published,
                "url": link,
                "cpv_codes": [],
                "hash": Tender.compute_hash(title, link, "bund"),
            }
        except Exception as exc:
            logger.warning(f"Bund RSS entry parse error: {exc}")
            return None

    # ── Department filter ─────────────────────────────────────────────────────

    def _passes_filter(self, tender: dict) -> bool:
        """
        Apply the department search logic:
          INCLUDE if text matches any BUND_INCLUDE_TERMS
          EXCLUDE if text matches any BUND_EXCLUDE_TERMS  (NOT Bauleistungen etc.)
        """
        text = (tender.get("title", "") + " " + tender.get("description", "")).lower()

        # Exclusion takes priority
        if any(term in text for term in BUND_EXCLUDE_TERMS):
            return False

        # Must match at least one inclusion term
        return any(term in text for term in BUND_INCLUDE_TERMS)

