"""
HFIP – Microsoft Teams Notification
Sends Adaptive Card alerts to a Teams channel via Incoming Webhook.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

import requests
from loguru import logger


class TeamsNotifier:
    """
    Sends rich Adaptive Card messages to a Microsoft Teams channel
    using an Incoming Webhook URL.
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL", "")
        if not self.webhook_url:
            logger.warning("TEAMS_WEBHOOK_URL not set – Teams notifications disabled.")

    def send(self, tender: dict, evaluation: dict) -> bool:
        """
        Send a Teams alert for a high-scoring tender.
        Returns True on success, False on failure.
        """
        if not self.webhook_url:
            logger.info("Teams webhook not configured – skipping notification.")
            return False

        payload = self._build_payload(tender, evaluation)
        try:
            resp = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=15,
            )
            resp.raise_for_status()
            logger.info(f"Teams alert sent for: {tender.get('title', '')[:60]}")
            return True
        except Exception as exc:
            logger.error(f"Teams alert failed: {exc}")
            return False

    def _build_payload(self, tender: dict, evaluation: dict) -> dict:
        """Build a Teams Adaptive Card payload."""
        title = tender.get("title", "Unknown")[:100]
        source = tender.get("source", "").upper()
        score = evaluation.get("score", 0)
        category = evaluation.get("category", "")
        summary = evaluation.get("summary", "")[:400]
        url = tender.get("url", "")
        deadline = tender.get("deadline")
        deadline_str = deadline.strftime("%d %B %Y") if isinstance(deadline, datetime) else str(deadline or "TBC")
        skills = evaluation.get("required_skills", [])
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except Exception:
                skills = [skills]
        skills_str = " · ".join(skills[:5]) if skills else "Not specified"
        effort = evaluation.get("proposal_effort", "Unknown")
        consortium = "Yes" if evaluation.get("consortium_required") else "No"

        # Score colour
        if score >= 90:
            score_color = "attention"   # Red (urgent/high)
        elif score >= 75:
            score_color = "warning"     # Yellow
        else:
            score_color = "good"        # Green

        # Teams MessageCard format (compatible with most webhook integrations)
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0078D4",
            "summary": f"🚨 New Healthcare AI Opportunity: {title}",
            "sections": [
                {
                    "activityTitle": f"🚨 **New Healthcare AI Opportunity**",
                    "activitySubtitle": f"Source: **{source}** | Score: **{score}/100** | Category: {category}",
                    "activityImage": "https://img.icons8.com/color/96/medical-heart.png",
                    "facts": [
                        {"name": "📋 Title", "value": title},
                        {"name": "🏢 Organization", "value": tender.get("organization", "Unknown")},
                        {"name": "🌍 Country", "value": tender.get("country", "Unknown")},
                        {"name": "📅 Deadline", "value": deadline_str},
                        {"name": "⭐ AI Score", "value": f"{score}/100"},
                        {"name": "🏷️ Category", "value": category},
                        {"name": "🔧 Required Skills", "value": skills_str},
                        {"name": "⚡ Proposal Effort", "value": effort},
                        {"name": "🤝 Consortium Required", "value": consortium},
                        {"name": "📝 Summary", "value": summary},
                    ],
                    "markdown": True,
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "View Tender",
                    "targets": [{"os": "default", "uri": url or "#"}],
                }
            ] if url else [],
        }
