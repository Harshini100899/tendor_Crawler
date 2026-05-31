"""
HFIP – Deduplication Engine
Prevents the same tender from being stored or processed twice
using SHA-256 content hashing and fuzzy title matching.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional

from loguru import logger

from database.models import Tender


# ─── Deduplication ───────────────────────────────────────────────────────────

class DeduplicationEngine:
    """
    Two-level deduplication:
    1. Exact hash match (SHA-256 of source + url + title) – handled by DB unique constraint.
    2. Fuzzy title similarity (Jaccard) – catches reposts with slightly different URLs.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold
        self._title_index: List[str] = []  # In-memory normalised title cache

    def compute_hash(self, title: str, url: str, source: str) -> str:
        """Deterministic SHA-256 dedup key."""
        return Tender.compute_hash(title, url, source)

    def is_duplicate_title(self, title: str, existing_titles: List[str]) -> bool:
        """
        Check fuzzy similarity between a new title and all known titles.
        Uses Jaccard similarity over word trigrams.
        """
        norm = self._normalize(title)
        new_grams = self._trigrams(norm)
        if not new_grams:
            return False
        for existing in existing_titles:
            existing_grams = self._trigrams(self._normalize(existing))
            sim = self._jaccard(new_grams, existing_grams)
            if sim >= self.threshold:
                logger.debug(f"Fuzzy duplicate detected (sim={sim:.2f}): {title[:60]}")
                return True
        return False

    def add_to_index(self, title: str) -> None:
        """Add a title to the in-memory fuzzy index after confirming it is unique."""
        self._title_index.append(title)

    def check_and_add(self, title: str) -> bool:
        """
        Returns True (duplicate) or False (new).
        Adds to index if new.
        """
        if self.is_duplicate_title(title, self._title_index):
            return True
        self.add_to_index(title)
        return False

    # ─── Utilities ───────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _trigrams(text: str) -> set:
        """Generate character trigrams from a string."""
        return {text[i:i+3] for i in range(len(text) - 2)} if len(text) >= 3 else set()

    @staticmethod
    def _jaccard(a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)
