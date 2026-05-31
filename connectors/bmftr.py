"""
HFIP – BMFTR / Gesundheitsforschung Connector
Scrapes the official BMFTR health-research portal for funding calls.

Target: https://www.gesundheitsforschung-bmftr.de/de/bekanntmachungen-5786.php
        plus yearly sub-pages (2025, 2026 …).

All URLs produced are real, directly accessible pages on
www.gesundheitsforschung-bmftr.de.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from database.models import Tender


# ─── URLs ─────────────────────────────────────────────────────────────────────
BMFTR_BASE = "https://www.gesundheitsforschung-bmftr.de"
BMFTR_LISTING_URL = f"{BMFTR_BASE}/de/bekanntmachungen-5786.php"

# Year pages – add new ones as the site grows
BMFTR_YEAR_URLS = [
    f"{BMFTR_BASE}/de/bekanntmachungen-2026-18764.php",
    f"{BMFTR_BASE}/de/bekanntmachungen-2025-18217.php",
    f"{BMFTR_BASE}/de/bekanntmachungen-2024-16752.php",
]

DATE_PATTERNS = [r"(\d{2}\.\d{2}\.\d{4})", r"(\d{4}-\d{2}-\d{2})"]
DEADLINE_MARKERS = [
    "frist", "einreichungsfrist", "deadline", "antragsfrist", "abgabefrist",
    "bewerbungsfrist", "einsendeschluss",
]

# Individual call pages have pure-numeric filenames: /de/19679.php
# Navigation pages look like: /de/bekanntmachungen-2026-18764.php (word-word-N)
_CALL_PAGE_RE = re.compile(r"^/de/\d+\.php$")


class BMFTRConnector:
    """
    Scrapes Gesundheitsforschung-BMFTR year Bekanntmachung pages and follows
    each individual funding-call link to build a tender record.
    """

    def __init__(self, delay: float = 1.5, max_per_year: int = 30):
        self.delay = delay
        self.max_per_year = max_per_year
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HFIP/1.0 (Healthcare Funding Intelligence Platform)",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })

    def fetch_recent(self) -> List[dict]:
        tenders: List[dict] = []
        seen_urls: set = set()

        for year_url in BMFTR_YEAR_URLS:
            call_links = self._collect_call_links(year_url)
            logger.info(f"BMFTR {year_url[-25:]}: {len(call_links)} call links")
            for link in call_links[: self.max_per_year]:
                if link in seen_urls:
                    continue
                seen_urls.add(link)
                tender = self._fetch_call_page(link)
                if tender:
                    tenders.append(tender)
                time.sleep(self.delay * 0.4)

        logger.info(f"BMFTR: collected {len(tenders)} Förderbekanntmachungen total")
        return tenders

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=20))
    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.warning(f"BMFTR fetch failed [{url}]: {exc}")
            return None

    def _collect_call_links(self, year_url: str) -> List[str]:
        """Return individual call page URLs from a year listing page."""
        soup = self._get_soup(year_url)
        if not soup:
            return []
        links = []
        seen: set = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if _CALL_PAGE_RE.match(href):
                full_url = BMFTR_BASE + href
                if full_url not in seen:
                    seen.add(full_url)
                    links.append(full_url)
        return links

    def _fetch_call_page(self, url: str) -> Optional[dict]:
        soup = self._get_soup(url)
        if not soup:
            return None
        title_tag = soup.find("h1") or soup.find("h2")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title or len(title) < 10:
            return None
        main = soup.find("main") or soup.find(id="content") or soup.find("article")
        description = (main or soup).get_text(separator=" ", strip=True)[:3000]
        deadline = self._extract_deadline(description)
        return {
            "source": "bmftr",
            "title": title,
            "description": description,
            "organization": "Bundesministerium für Forschung, Technologie und Raumfahrt (BMFTR)",
            "country": "DE",
            "deadline": deadline,
            "published_date": datetime.utcnow(),
            "url": url,
            "cpv_codes": ["73000000", "72000000", "85000000"],
            "hash": Tender.compute_hash(title, url, "bmftr"),
        }

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
