"""
HFIP – BMFTR Connector
Scrapes the Federal Ministry for Research, Technology and Space (BMFTR)
Bekanntmachungsuche portal filtered to the Gesundheit theme.

Target URL (exactly as specified):
  https://www.bmftr.bund.de/SiteGlobals/Forms/Suche/Bekanntmachungsuche/
  Bekanntmachungsuche_Formular.html?cl2Categories_Themen=gesundheit
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlencode

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from database.models import Tender


# ─── URLs ─────────────────────────────────────────────────────────────────────

BMFTR_BASE = "https://www.bmftr.bund.de"
BMFTR_SEARCH_URL = (
    f"{BMFTR_BASE}/SiteGlobals/Forms/Suche/Bekanntmachungsuche/"
    "Bekanntmachungsuche_Formular.html"
)
# Fixed query parameter as required
BMFTR_SEARCH_PARAMS = {
    "cl2Categories_Themen": "gesundheit",
    "resultsPerPage": "20",
    "pageNumber": "1",
}

DATE_PATTERNS = [r"(\d{2}\.\d{2}\.\d{4})", r"(\d{4}-\d{2}-\d{2})"]
DEADLINE_MARKERS = ["frist", "einreichungsfrist", "deadline", "antragsfrist", "abgabefrist"]


class BMFTRConnector:
    """
    Scrapes BMFTR Bekanntmachungen filtered to the 'Gesundheit' theme.
    Paginates through all result pages.
    """

    def __init__(self, delay: float = 2.0, max_pages: int = 5):
        self.delay = delay
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HFIP/1.0 (Healthcare Funding Intelligence Platform)",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def fetch_recent(self) -> List[dict]:
        tenders: List[dict] = []
        for page_num in range(1, self.max_pages + 1):
            page_tenders = self._fetch_page(page_num)
            if not page_tenders:
                break
            tenders.extend(page_tenders)
            logger.info(f"BMFTR page {page_num}: {len(page_tenders)} results")
            time.sleep(self.delay)
        logger.info(f"BMFTR: collected {len(tenders)} Bekanntmachungen total")
        return tenders

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=20))
    def _fetch_page(self, page_num: int) -> List[dict]:
        params = {**BMFTR_SEARCH_PARAMS, "pageNumber": str(page_num)}
        try:
            resp = self.session.get(BMFTR_SEARCH_URL, params=params, timeout=25)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            return self._parse_results(soup)
        except Exception as exc:
            logger.warning(f"BMFTR page {page_num} failed: {exc}")
            return []

    def _parse_results(self, soup: BeautifulSoup) -> List[dict]:
        tenders = []

        # BMFTR uses a list of result items - try multiple CSS patterns
        items = (
            soup.find_all("div", class_=re.compile(r"(result|bekanntmachung|foerder|item|teaser|card)", re.I))
            or soup.find_all("article")
            or soup.find_all("li", class_=re.compile(r"(result|item|entry)", re.I))
        )

        # Deduplicate by href to avoid parsing the same link from wrapper+child divs
        seen_urls: set = set()

        for item in items:
            tender = self._parse_item(item)
            if tender and tender["url"] not in seen_urls:
                seen_urls.add(tender["url"])
                tenders.append(tender)

        if not tenders:
            logger.debug("BMFTR: no structured items found, trying link-based fallback")
            tenders = self._fallback_links(soup)

        return tenders

    def _parse_item(self, element) -> Optional[dict]:
        try:
            heading = element.find(re.compile(r"^h[1-6]$"))
            title = heading.get_text(strip=True) if heading else ""

            if not title:
                link_tag = element.find("a", href=True)
                if link_tag:
                    title = link_tag.get_text(strip=True)
            if len(title) < 10:
                return None

            link_tag = element.find("a", href=True)
            href = link_tag["href"] if link_tag else ""
            url = urljoin(BMFTR_BASE, href) if href else BMFTR_SEARCH_URL

            desc_tag = element.find("p")
            description = (
                desc_tag.get_text(strip=True) if desc_tag
                else element.get_text(separator=" ", strip=True)[:2000]
            )

            deadline = self._extract_deadline(description)

            return {
                "source": "bmftr",
                "title": title,
                "description": description[:3000],
                "organization": "Bundesministerium für Forschung, Technologie und Raumfahrt (BMFTR)",
                "country": "DE",
                "deadline": deadline,
                "published_date": datetime.utcnow(),
                "url": url,
                "cpv_codes": ["73000000", "72000000", "85000000"],
                "hash": Tender.compute_hash(title, url, "bmftr"),
            }
        except Exception as exc:
            logger.debug(f"BMFTR item parse error: {exc}")
            return None

    def _fallback_links(self, soup: BeautifulSoup) -> List[dict]:
        """Fallback: collect every anchor that looks like a Bekanntmachung detail link."""
        tenders = []
        seen: set = set()
        for a in soup.find_all("a", href=re.compile(r"bekanntmachung|foerder", re.I)):
            href = a.get("href", "")
            url = urljoin(BMFTR_BASE, href)
            title = a.get_text(strip=True)
            if len(title) < 10 or url in seen:
                continue
            seen.add(url)
            tenders.append({
                "source": "bmftr",
                "title": title,
                "description": title,
                "organization": "BMFTR",
                "country": "DE",
                "deadline": None,
                "published_date": datetime.utcnow(),
                "url": url,
                "cpv_codes": ["73000000"],
                "hash": Tender.compute_hash(title, url, "bmftr"),
            })
        return tenders

    def _extract_deadline(self, text: str) -> Optional[datetime]:
        text_lower = text.lower()
        for marker in DEADLINE_MARKERS:
            idx = text_lower.find(marker)
            if idx == -1:
                continue
            window = text[max(0, idx - 20): idx + 200]
            for pattern in DATE_PATTERNS:
                match = re.search(pattern, window)
                if match:
                    date_str = match.group(1)
                    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
        return None
