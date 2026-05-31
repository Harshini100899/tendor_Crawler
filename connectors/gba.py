"""
HFIP – G-BA Innovation Fund Connector
Monitors the Gemeinsamer Bundesausschuss (G-BA) Innovationsfonds
for current funding calls, including PDF extraction.
Source: https://www.g-ba-innovationsfonds.de/foerderung/aktuelle-ausschreibungen/
"""

from __future__ import annotations

import io
import re
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from database.models import Tender


GBA_BASE = "https://www.g-ba-innovationsfonds.de"
GBA_CALLS_URL = f"{GBA_BASE}/foerderung/aktuelle-ausschreibungen/"
GBA_DGA_URL = "https://www.g-ba.de/themen/methodenbewertung/digitale-gesundheitsanwendungen/"

DATE_PATTERNS = [
    r"(\d{2}\.\d{2}\.\d{4})",          # DD.MM.YYYY
    r"(\d{4}-\d{2}-\d{2})",            # YYYY-MM-DD
    r"(\d{1,2}\.\s+\w+\s+\d{4})",      # D. Month YYYY
]

DEADLINE_MARKERS = [
    "frist", "einreichungsfrist", "abgabefrist", "deadline", "antragsfrist",
    "bewerbungsfrist", "einsendeschluss"
]


class GBAConnector:
    """
    Scrapes G-BA Innovationsfonds funding calls.
    Handles both HTML listing pages and linked PDF attachments.
    """

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HFIP/1.0 (Healthcare Funding Intelligence Platform)"
        })

    def fetch_recent(self) -> List[dict]:
        tenders: List[dict] = []
        tenders.extend(self._scrape_innovation_calls())
        tenders.extend(self._scrape_dga_calls())
        logger.info(f"G-BA: collected {len(tenders)} funding calls")
        return tenders

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.warning(f"G-BA scrape failed [{url}]: {exc}")
            return None

    def _scrape_innovation_calls(self) -> List[dict]:
        soup = self._get_soup(GBA_CALLS_URL)
        if not soup:
            return []

        tenders = []
        # G-BA uses article/card-based layout for funding calls
        articles = soup.find_all(["article", "div"], class_=re.compile(r"(ausschreibung|foerderung|call|item|card)", re.I))
        if not articles:
            # Fallback: all anchor tags that look like call links
            articles = soup.find_all("a", href=re.compile(r"/foerderung/"))

        for article in articles:
            tender = self._parse_article(article, GBA_CALLS_URL, "gba_innovationsfonds")
            if tender:
                tenders.append(tender)
            time.sleep(self.delay)

        return tenders

    def _scrape_dga_calls(self) -> List[dict]:
        """Scrape G-BA DiGA (Digital Health Applications) page."""
        soup = self._get_soup(GBA_DGA_URL)
        if not soup:
            return []

        tenders = []
        links = soup.find_all("a", href=re.compile(r"\.(pdf|html)$", re.I))
        for link in links[:10]:  # Limit to avoid scraping the entire site
            href = link.get("href", "")
            full_url = urljoin(GBA_DGA_URL, href)
            title = link.get_text(strip=True)
            if len(title) < 10:
                continue
            tenders.append({
                "source": "gba",
                "title": title,
                "description": f"G-BA DiGA funding call: {title}",
                "organization": "Gemeinsamer Bundesausschuss (G-BA)",
                "country": "DE",
                "deadline": None,
                "published_date": datetime.utcnow(),
                "url": full_url,
                "cpv_codes": ["85000000", "72000000"],
                "hash": Tender.compute_hash(title, full_url, "gba"),
            })
        return tenders

    def _parse_article(self, element, base_url: str, sub_source: str) -> Optional[dict]:
        try:
            # Extract title
            heading = element.find(re.compile(r"^h[1-6]$"))
            if heading:
                title = heading.get_text(strip=True)
            else:
                title = element.get_text(separator=" ", strip=True)[:150]

            if len(title) < 10:
                return None

            # Extract link
            link_tag = element.find("a", href=True) if hasattr(element, "find") else element
            href = link_tag.get("href", "") if link_tag else ""
            url = urljoin(base_url, href) if href else base_url

            # Extract description text
            desc = element.get_text(separator=" ", strip=True)[:3000]

            # Try to find deadline in text
            deadline = self._extract_deadline(desc)

            return {
                "source": "gba",
                "title": title,
                "description": desc,
                "organization": "Gemeinsamer Bundesausschuss (G-BA) Innovationsfonds",
                "country": "DE",
                "deadline": deadline,
                "published_date": datetime.utcnow(),
                "url": url,
                "cpv_codes": ["85000000", "73000000"],
                "hash": Tender.compute_hash(title, url, "gba"),
            }
        except Exception as exc:
            logger.warning(f"G-BA article parse error: {exc}")
            return None

    def _extract_deadline(self, text: str) -> Optional[datetime]:
        """Heuristically find a deadline date near deadline-marker keywords."""
        text_lower = text.lower()
        for marker in DEADLINE_MARKERS:
            idx = text_lower.find(marker)
            if idx == -1:
                continue
            # Look in a 200-char window around the marker
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
