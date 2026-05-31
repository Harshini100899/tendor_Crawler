"""
HFIP – Bund.de RSS Connector
Monitors official German federal government RSS feeds for funding opportunities.
RSS feed docs: https://service.bund.de/Content/DE/Service/RSS/rss.html
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from urllib.parse import urljoin

import feedparser
import requests
from loguru import logger

from database.models import Tender


BUND_RSS_FEEDS = [
    {
        "url": "https://www.bund.de/SiteGlobals/Functions/RSSFeed/RSSFeed_Ausschreibungen/RSSFeed_Ausschreibungen_node.rss",
        "name": "Bund Ausschreibungen",
    },
    {
        "url": "https://www.bund.de/SiteGlobals/Functions/RSSFeed/RSSFeed_Foerderprogramme/RSSFeed_Foerderprogramme_node.rss",
        "name": "Bund Foerderprogramme",
    },
]

HEALTHCARE_KEYWORDS = [
    "gesundheit", "health", "medizin", "medical", "krankenhaus", "hospital",
    "klinik", "clinic", "pflege", "care", "arzneimittel", "pharma",
    "digital health", "digitale gesundheit", "ki", "artificial intelligence",
    "machine learning", "maschinelles lernen", "forschung", "research",
    "innovation", "ict", "informationstechnologie", "software",
]


class BundConnector:
    """
    Polls Bund.de RSS feeds and filters entries relevant to Healthcare AI.
    No authentication required – pure RSS parsing.
    """

    def __init__(self, feeds: Optional[List[dict]] = None):
        self.feeds = feeds or BUND_RSS_FEEDS
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "HFIP/1.0 (Healthcare Funding Intelligence)"})

    def fetch_recent(self) -> List[dict]:
        """Fetch all RSS entries, apply keyword filter, return normalized tenders."""
        all_tenders: List[dict] = []
        for feed_config in self.feeds:
            tenders = self._process_feed(feed_config)
            all_tenders.extend(tenders)
            time.sleep(1)
        logger.info(f"Bund RSS: collected {len(all_tenders)} relevant entries")
        return all_tenders

    def _process_feed(self, feed_config: dict) -> List[dict]:
        url = feed_config["url"]
        feed_name = feed_config["name"]
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            logger.error(f"Bund RSS fetch failed [{feed_name}]: {exc}")
            return []

        tenders = []
        for entry in feed.entries:
            if not self._is_relevant(entry):
                continue
            tender = self._parse_entry(entry, feed_name)
            if tender:
                tenders.append(tender)

        logger.info(f"Bund RSS [{feed_name}]: {len(tenders)} relevant out of {len(feed.entries)} entries")
        return tenders

    def _is_relevant(self, entry) -> bool:
        """Quickly decide if entry mentions healthcare/AI topics."""
        text = (
            getattr(entry, "title", "") + " " +
            getattr(entry, "summary", "") + " " +
            getattr(entry, "description", "")
        ).lower()
        return any(kw in text for kw in HEALTHCARE_KEYWORDS)

    def _parse_entry(self, entry, feed_name: str) -> Optional[dict]:
        try:
            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            # Strip HTML tags from summary
            summary = re.sub(r"<[^>]+>", " ", summary).strip()

            link = getattr(entry, "link", "") or ""

            # Parse published date
            published = None
            if hasattr(entry, "published"):
                try:
                    published = parsedate_to_datetime(entry.published).replace(tzinfo=None)
                except Exception:
                    pass
            if published is None and hasattr(entry, "updated"):
                try:
                    published = parsedate_to_datetime(entry.updated).replace(tzinfo=None)
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
                "deadline": None,  # RSS feeds rarely include deadlines
                "published_date": published,
                "url": link,
                "cpv_codes": [],
                "hash": Tender.compute_hash(title, link, "bund"),
            }
        except Exception as exc:
            logger.warning(f"Bund entry parse error: {exc}")
            return None
