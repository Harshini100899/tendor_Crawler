"""
HFIP – LLM Evaluator
Orchestrates Groq evaluation: builds prompt → calls LLM → parses JSON response.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from loguru import logger

from ai.groq_client import GroqClient
from ai.prompts import EVALUATOR_SYSTEM_PROMPT, build_user_prompt


# ─── Expected LLM output schema ──────────────────────────────────────────────

REQUIRED_FIELDS = {
    "relevant": bool,
    "score": int,
    "category": str,
    "summary": str,
    "required_skills": list,
    "proposal_effort": str,
    "consortium_required": bool,
}

VALID_CATEGORIES = {
    "Healthcare AI",
    "Digital Health",
    "Medical Imaging",
    "Health Data & Interoperability",
    "Biomedical Research",
    "Health Informatics",
    "Other Health",
    "Not Relevant",
}

VALID_EFFORTS = {"Low", "Medium", "High"}


# ─── Evaluator ───────────────────────────────────────────────────────────────

class TenderEvaluator:
    """
    Uses Groq LLM to perform deep evaluation of a tender.
    Returns a structured evaluation dict ready for database storage.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None):
        self._client = groq_client or GroqClient()

    def evaluate(self, tender: dict, tavily_context: str = "") -> dict:
        """
        Evaluate a single tender.
        Returns evaluation dict with keys matching the evaluations table schema.
        """
        deadline_str = ""
        if tender.get("deadline"):
            try:
                deadline_str = tender["deadline"].strftime("%d %B %Y")
            except Exception:
                deadline_str = str(tender["deadline"])

        user_prompt = build_user_prompt(
            title=tender.get("title", ""),
            source=tender.get("source", ""),
            organization=tender.get("organization", ""),
            country=tender.get("country", ""),
            deadline=deadline_str,
            description=tender.get("description", ""),
            tavily_context=tavily_context,
        )

        try:
            raw_response = self._client.chat(
                system_prompt=EVALUATOR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception as exc:
            logger.error(f"Groq evaluation failed for tender '{tender.get('title', '')[:50]}': {exc}")
            return self._fallback_evaluation(tender, error=str(exc))

        return self._parse_response(raw_response, tender)

    def _parse_response(self, raw: str, tender: dict) -> dict:
        """Parse and validate the LLM JSON response."""
        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?", "", raw).strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            # Attempt to repair: quote any unquoted string values after a JSON key
            # e.g.  "summary": Some text,  →  "summary": "Some text",
            repaired = re.sub(
                r'("(?:summary|category|proposal_effort)")\s*:\s*([^"\[{\d\n][^,}\n]*?)(\s*[,}])',
                lambda m: f'{m.group(1)}: "{m.group(2).strip()}"{m.group(3)}',
                clean,
            )
            try:
                data = json.loads(repaired)
            except json.JSONDecodeError as exc2:
                logger.warning(f"LLM returned invalid JSON: {exc2}\nRaw: {raw[:500]}")
                return self._fallback_evaluation(tender, error=f"JSON parse error: {exc2}", raw=raw)

        # Validate and sanitise fields
        result = {
            "tender_id": tender.get("id"),
            "relevant": bool(data.get("relevant", False)),
            "score": max(0, min(100, int(data.get("score", 0)))),
            "category": data.get("category", "Not Relevant"),
            "summary": str(data.get("summary", ""))[:1000],
            "required_skills": data.get("required_skills", []),
            "proposal_effort": data.get("proposal_effort", "Medium"),
            "consortium_required": bool(data.get("consortium_required", False)),
            "raw_response": raw,
            "model_used": self._client.get_model_name(),
        }

        # Sanitise category
        if result["category"] not in VALID_CATEGORIES:
            result["category"] = "Other Health"

        # Sanitise effort
        if result["proposal_effort"] not in VALID_EFFORTS:
            result["proposal_effort"] = "Medium"

        # Sanitise skills list
        if not isinstance(result["required_skills"], list):
            result["required_skills"] = []
        result["required_skills"] = [str(s) for s in result["required_skills"][:6]]

        logger.info(
            f"Evaluation complete: '{tender.get('title', '')[:50]}' → "
            f"score={result['score']} relevant={result['relevant']} "
            f"category={result['category']!r}"
        )
        return result

    @staticmethod
    def _fallback_evaluation(tender: dict, error: str = "", raw: str = "") -> dict:
        """Return a safe fallback when evaluation fails."""
        return {
            "tender_id": tender.get("id"),
            "relevant": False,
            "score": 0,
            "category": "Not Relevant",
            "summary": f"Evaluation failed: {error[:200]}",
            "required_skills": [],
            "proposal_effort": "Unknown",
            "consortium_required": False,
            "raw_response": raw or error,
            "model_used": "unknown",
        }
