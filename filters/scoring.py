"""
HFIP – Healthcare AI Scoring Engine
Pre-AI rule-based scoring to filter tenders before sending to Groq LLM.
This dramatically reduces API costs by only evaluating promising tenders.
"""

from __future__ import annotations

import json
import re
from typing import List, Optional, Tuple

from loguru import logger

from filters.cpv import score_cpv_codes
from filters.department import department_filter
from filters.keywords import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS


# ─── Thresholds ──────────────────────────────────────────────────────────────

SCORE_ARCHIVE = 50      # Below this: archive without AI evaluation
SCORE_AI_EVAL = 50      # At or above: send to Groq LLM
SCORE_ALERT = 80        # At or above: send Teams/email alert (post AI eval)


# ─── Scoring Engine ──────────────────────────────────────────────────────────

class HealthcareAIScorer:
    """
    Rule-based scorer that produces a keyword + CPV score for each tender.
    Runs BEFORE the Groq LLM to filter out irrelevant tenders cheaply.
    """

    def score(self, tender: dict) -> Tuple[int, List[str]]:
        """
        Score a tender dict (with 'title', 'description', 'cpv_codes').
        Returns (score, matched_terms).
        """
        text = self._build_text(tender)
        text_lower = text.lower()

        score = 0
        matched: List[str] = []

        # ── Positive keywords ─────────────────────────────────────────────
        for keyword, points in POSITIVE_KEYWORDS.items():
            if keyword.lower() in text_lower:
                score += points
                matched.append(f"+{points}: {keyword}")

        # ── Negative keywords ─────────────────────────────────────────────
        for keyword, penalty in NEGATIVE_KEYWORDS.items():
            if keyword.lower() in text_lower:
                score += penalty  # penalty is already negative
                matched.append(f"{penalty}: {keyword}")

        # ── CPV codes ─────────────────────────────────────────────────────
        cpv_codes = tender.get("cpv_codes", [])
        if isinstance(cpv_codes, str):
            try:
                cpv_codes = json.loads(cpv_codes)
            except Exception:
                cpv_codes = []
        cpv_score = score_cpv_codes(cpv_codes)
        if cpv_score != 0:
            score += cpv_score
            matched.append(f"CPV codes: +{cpv_score}")

        # ── Source bonus ──────────────────────────────────────────────
        source = tender.get("source", "")
        if source in ("gba", "bmftr"):
            score += 10  # These sources are specifically healthcare/research
            matched.append(f"Source bonus ({source}): +10")

        # ── Department topic filter ───────────────────────────────────
        topic_score, topics = department_filter.classify(tender)
        if topic_score != 0:
            score += topic_score
            if topics:
                matched.append(f"Department topics ({', '.join(topics[:2])}): +{topic_score}")
            else:
                matched.append(f"Department: no topic match: {topic_score}")

        logger.debug(
            f"Scored [{tender.get('source', '?')}] "
            f"{tender.get('title', '')[:60]} → {score}"
        )
        return score, matched

    def should_archive(self, score: int) -> bool:
        return score < SCORE_ARCHIVE

    def should_evaluate_with_ai(self, score: int) -> bool:
        return score >= SCORE_AI_EVAL

    def should_alert(self, ai_score: int) -> bool:
        return ai_score >= SCORE_ALERT

    def _build_text(self, tender: dict) -> str:
        parts = [
            tender.get("title", ""),
            tender.get("description", "") or "",
            tender.get("organization", "") or "",
        ]
        return " ".join(p for p in parts if p)


# ─── Convenience function ────────────────────────────────────────────────────

_scorer = HealthcareAIScorer()


def compute_keyword_score(tender: dict) -> Tuple[int, List[str]]:
    """Module-level convenience wrapper."""
    return _scorer.score(tender)
