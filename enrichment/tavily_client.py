"""
HFIP – Tavily Research Client
Enriches tender context with recent web research.
Tavily API is designed specifically for AI retrieval workflows.
Docs: https://docs.tavily.com/
"""

from __future__ import annotations

import os
from typing import List, Optional

from loguru import logger
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential


# ─── Search Query Templates ──────────────────────────────────────────────────

def _build_queries(title: str, organization: str = "") -> List[str]:
    """Generate focused research queries from tender metadata."""
    queries = []
    # Primary: direct topic search
    queries.append(f"{title} funding healthcare AI")
    # Secondary: organization context
    if organization:
        queries.append(f"{organization} healthcare digital health projects")
    # Tertiary: market context
    queries.append(f"healthcare AI funding trends 2025 2026 Germany EU")
    return queries[:2]  # Limit to 2 queries to control cost


# ─── Client ──────────────────────────────────────────────────────────────────

class TavilyResearcher:
    """
    Uses Tavily Search API to gather market context and recent news
    that helps the Groq LLM make a better evaluation.

    Purpose: NOT primary tender collection – enrichment only.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_results: int = 5,
        search_depth: str = "advanced",
    ):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set – enrichment will be skipped.")
            self._client = None
        else:
            self._client = TavilyClient(api_key=self.api_key)
        self.max_results = max_results
        self.search_depth = search_depth

    def enrich(self, title: str, organization: str = "") -> str:
        """
        Search for context around a tender title.
        Returns a formatted string suitable for insertion into an LLM prompt.
        Returns empty string if Tavily is not configured.
        """
        if not self._client:
            return ""

        queries = _build_queries(title, organization)
        snippets: List[str] = []

        for query in queries:
            try:
                results = self._search(query)
                for r in results:
                    content = r.get("content", "").strip()
                    url = r.get("url", "")
                    if content:
                        snippets.append(f"• {content[:400]} ({url})")
            except Exception as exc:
                logger.warning(f"Tavily search failed for query '{query[:60]}': {exc}")
                continue

        if not snippets:
            return ""

        context = "\n".join(snippets[:6])  # Cap total context length
        logger.debug(f"Tavily enriched '{title[:50]}' with {len(snippets)} snippets")
        return context

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
    def _search(self, query: str) -> List[dict]:
        response = self._client.search(
            query=query,
            search_depth=self.search_depth,
            max_results=self.max_results,
            include_answer=True,
        )
        results = response.get("results", [])
        # Also include the synthesized answer if available
        answer = response.get("answer", "")
        if answer:
            results = [{"content": answer, "url": "tavily-answer"}] + results
        return results
