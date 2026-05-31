"""
HFIP – BMBF/BMFTR Connector
Scrapes the German Federal Ministry of Education and Research (BMBF)
and the Förderportal Bund for healthcare & AI funding programmes.
Source: https://www.bmbf.de/bmbf/de/forschung/gesundheit/gesundheit.html
        https://www.foerderportal.bund.de
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


BMBF_BASE = "https://www.bmbf.de"
BMBF_HEALTH_URL = f"{BMBF_BASE}/bmbf/de/forschung/gesundheit/gesundheit.html"
BMBF_KI_URL = f"{BMBF_BASE}/bmbf/de/forschung/digitale-wirtschaft-und-gesellschaft/kuenstliche-intelligenz/kuenstliche-intelligenz.html"
FOERDERPORTAL_BASE = "https://foerderportal.bund.de"

SEARCH_KEYWORDS = [
    "Gesundheit", "KI", "Künstliche Intelligenz", "Digital Health",
    "Medizin", "Digitale Medizin", "eHealth", "Telemedizin",
    "Krankenhaus", "Pflege", "Medizinische Informatik",
]

DATE_PATTERNS = [r"(\d{2}\.\d{2}\.\d{4})", r"(\d{4}-\d{2}-\d{2})"]
DEADLINE_MARKERS = ["frist", "einreichungsfrist", "deadline", "antragsfrist", "abgabefrist"]


class BMFTRConnector:
    """
    Scrapes BMBF health & AI funding pages and the Förderportal Bund.
    Uses BeautifulSoup for static HTML and Playwright (optional) for JS pages.
    """

    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HFIP/1.0 (Healthcare Funding Intelligence Platform)",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })

    def fetch_recent(self) -> List[dict]:
        tenders: List[dict] = []
        tenders.extend(self._scrape_bmbf_health())
        time.sleep(self.delay)
        tenders.extend(self._scrape_bmbf_ki())
        time.sleep(self.delay)
        tenders.extend(self._scrape_foerderportal())
        logger.info(f"BMFTR: collected {len(tenders)} funding opportunities")
        return tenders

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=20))
    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            resp = self.session.get(url, timeout=25)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.warning(f"BMFTR scrape failed [{url}]: {exc}")
            return None

    def _scrape_bmbf_health(self) -> List[dict]:
        soup = self._get_soup(BMBF_HEALTH_URL)
        if not soup:
            return []
        return self._extract_news_items(soup, BMBF_HEALTH_URL, "bmbf_health")

    def _scrape_bmbf_ki(self) -> List[dict]:
        soup = self._get_soup(BMBF_KI_URL)
        if not soup:
            return []
        return self._extract_news_items(soup, BMBF_KI_URL, "bmbf_ki")

    def _scrape_foerderportal(self) -> List[dict]:
        """
        Search the Förderportal Bund for health/AI funding programmes.
        This portal lists all active federal funding programmes.
        """
        tenders = []
        for keyword in SEARCH_KEYWORDS[:3]:  # Limit to top keywords to avoid flooding
            time.sleep(self.delay)
            url = f"{FOERDERPORTAL_BASE}/foekat/jsp/SucheAction.do?action=searchlist&suchwort={keyword}&geberArt=B"
            soup = self._get_soup(url)
            if not soup:
                continue
            items = self._extract_foerderportal_items(soup, keyword)
            tenders.extend(items)
            logger.debug(f"Förderportal [{keyword}]: {len(items)} items")
        return tenders

    def _extract_news_items(self, soup: BeautifulSoup, base_url: str, sub: str) -> List[dict]:
        tenders = []
        # BMBF uses article tags and .c-teaser classes
        items = soup.find_all(["article", "div"], class_=re.compile(r"(teaser|news|meldung|aktuell|card)", re.I))
        if not items:
            items = soup.find_all("li", class_=re.compile(r"(teaser|news|item)", re.I))

        for item in items[:20]:
            title_tag = item.find(re.compile(r"^h[1-6]$"))
            if not title_tag:
                title_tag = item.find("a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            if len(title) < 10:
                continue

            link_tag = item.find("a", href=True)
            href = link_tag["href"] if link_tag else ""
            url = urljoin(base_url, href)

            desc_tag = item.find("p")
            description = desc_tag.get_text(strip=True) if desc_tag else item.get_text(separator=" ", strip=True)[:1000]

            deadline = self._extract_deadline(description)

            tenders.append({
                "source": "bmftr",
                "title": title,
                "description": description[:3000],
                "organization": "Bundesministerium für Bildung und Forschung (BMBF)",
                "country": "DE",
                "deadline": deadline,
                "published_date": datetime.utcnow(),
                "url": url,
                "cpv_codes": ["73000000", "72000000"],
                "hash": Tender.compute_hash(title, url, "bmftr"),
            })
        return tenders

    def _extract_foerderportal_items(self, soup: BeautifulSoup, keyword: str) -> List[dict]:
        tenders = []
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            title = cells[0].get_text(strip=True)
            if len(title) < 5:
                continue
            link_tag = cells[0].find("a", href=True)
            href = link_tag["href"] if link_tag else ""
            url = urljoin(FOERDERPORTAL_BASE, href)
            desc = " ".join(c.get_text(strip=True) for c in cells[1:])[:2000]
            deadline = self._extract_deadline(desc)
            tenders.append({
                "source": "bmftr",
                "title": title,
                "description": desc,
                "organization": "Förderportal Bund",
                "country": "DE",
                "deadline": deadline,
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
