"""
HFIP – Scheduler
APScheduler-based job runner that orchestrates the full pipeline:
  Collect → Normalise → Score → Deduplicate → Evaluate → Alert
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

# Add project root to path so all imports resolve
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from ai.evaluator import TenderEvaluator
from ai.groq_client import GroqClient
from connectors.bmftr import BMFTRConnector
from connectors.bund import BundConnector
from connectors.gba import GBAConnector
from connectors.ted import TEDConnector
from database.repository import TenderRepository
from filters.dedup import DeduplicationEngine
from filters.scoring import HealthcareAIScorer
from notifications.email import EmailNotifier
from notifications.teams import TeamsNotifier
from enrichment.tavily_client import TavilyResearcher


# ─── Pipeline ────────────────────────────────────────────────────────────────

class HFIPPipeline:
    """
    Full pipeline orchestrator.
    Each method corresponds to one pipeline stage.
    """

    def __init__(self, db_path: str = "data/hfip.db"):
        self.repo = TenderRepository(db_path=db_path)
        self.scorer = HealthcareAIScorer()
        self.dedup = DeduplicationEngine()
        self.researcher = TavilyResearcher()
        self.notifier_teams = TeamsNotifier()
        self.notifier_email = EmailNotifier()

        # Lazy-init LLM (requires API key)
        self._evaluator: Optional[TenderEvaluator] = None

    @property
    def evaluator(self) -> TenderEvaluator:
        if self._evaluator is None:
            self._evaluator = TenderEvaluator(GroqClient())
        return self._evaluator

    # ─── Collection Jobs ─────────────────────────────────────────────────────

    def run_ted(self) -> None:
        """Collect from TED Europa API."""
        logger.info("=== TED Collection Started ===")
        connector = TEDConnector()
        tenders = connector.fetch_recent(days_back=1)
        self._ingest(tenders, "TED")

    def run_bund(self) -> None:
        """Collect from Bund.de RSS feeds."""
        logger.info("=== Bund RSS Collection Started ===")
        connector = BundConnector()
        tenders = connector.fetch_recent()
        self._ingest(tenders, "Bund")

    def run_gba(self) -> None:
        """Collect from G-BA Innovation Fund."""
        logger.info("=== G-BA Collection Started ===")
        connector = GBAConnector()
        tenders = connector.fetch_recent()
        self._ingest(tenders, "G-BA")

    def run_bmftr(self) -> None:
        """Collect from BMBF/BMFTR funding portal."""
        logger.info("=== BMFTR Collection Started ===")
        connector = BMFTRConnector()
        tenders = connector.fetch_recent()
        self._ingest(tenders, "BMFTR")

    def run_all_connectors(self) -> None:
        """Run all collectors sequentially."""
        self.run_ted()
        self.run_bund()
        self.run_gba()
        self.run_bmftr()

    # ─── Ingest + Score ──────────────────────────────────────────────────────

    def _ingest(self, raw_tenders: list, source_name: str) -> None:
        """Score, filter, deduplicate, and store a batch of raw tenders."""
        saved = 0
        archived = 0

        for tender_data in raw_tenders:
            # 1. Keyword + CPV scoring
            score, matches = self.scorer.score(tender_data)
            tender_data["keyword_score"] = score

            if self.scorer.should_archive(score):
                tender_data["is_archived"] = True
                archived += 1
            else:
                tender_data["is_archived"] = False

            # 2. Store (DB unique constraint handles exact hash dedup)
            _, created = self.repo.upsert_tender(tender_data)
            if created:
                saved += 1

        logger.info(f"{source_name}: {saved} new, {archived} archived out of {len(raw_tenders)} collected")

    # ─── AI Evaluation Job ───────────────────────────────────────────────────

    def run_evaluation(self) -> None:
        """
        Evaluate all pending tenders with Groq LLM.
        Only tenders with keyword_score >= 50 are evaluated.
        """
        logger.info("=== AI Evaluation Started ===")
        pending = self.repo.get_pending_evaluation()
        logger.info(f"Pending evaluation: {len(pending)} tenders")

        for tender in pending:
            tender_dict = {
                "id": tender.id,
                "title": tender.title,
                "description": tender.description,
                "organization": tender.organization,
                "country": tender.country,
                "deadline": tender.deadline,
                "source": tender.source,
                "url": tender.url,
            }

            # Tavily enrichment
            tavily_context = ""
            if tender.keyword_score >= 50:
                tavily_context = self.researcher.enrich(
                    title=tender.title,
                    organization=tender.organization or "",
                )

            # Groq evaluation
            evaluation = self.evaluator.evaluate(tender_dict, tavily_context=tavily_context)
            evaluation["tavily_context"] = tavily_context

            # Save evaluation
            self.repo.save_evaluation(evaluation)

            # Send alert if score is high enough
            if self.scorer.should_alert(evaluation.get("score", 0)):
                self._send_alerts(tender_dict, evaluation)

        logger.info("=== AI Evaluation Complete ===")

    # ─── Notifications ───────────────────────────────────────────────────────

    def _send_alerts(self, tender: dict, evaluation: dict) -> None:
        tender_id = tender.get("id")
        if not tender_id:
            return

        # Teams alert
        if not self.repo.notification_already_sent(tender_id, "teams"):
            success = self.notifier_teams.send(tender, evaluation)
            self.repo.save_notification({
                "tender_id": tender_id,
                "channel": "teams",
                "status": "sent" if success else "failed",
            })

        # Email alert
        if not self.repo.notification_already_sent(tender_id, "email"):
            success = self.notifier_email.send(tender, evaluation)
            self.repo.save_notification({
                "tender_id": tender_id,
                "channel": "email",
                "status": "sent" if success else "failed",
            })


# ─── Scheduler Setup ─────────────────────────────────────────────────────────

class HFIPScheduler:
    """APScheduler wrapper that registers all HFIP cron jobs."""

    def __init__(self, db_path: str = "data/hfip.db", timezone: str = "Europe/Berlin"):
        self.pipeline = HFIPPipeline(db_path=db_path)
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self._register_jobs()

    def _register_jobs(self) -> None:
        # Daily TED collection at 06:00
        self.scheduler.add_job(
            self.pipeline.run_ted,
            CronTrigger(hour=6, minute=0),
            id="ted_collection",
            name="TED Europa Collection",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Daily Bund RSS at 07:00
        self.scheduler.add_job(
            self.pipeline.run_bund,
            CronTrigger(hour=7, minute=0),
            id="bund_collection",
            name="Bund RSS Collection",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Weekly G-BA Monday at 08:00
        self.scheduler.add_job(
            self.pipeline.run_gba,
            CronTrigger(day_of_week="mon", hour=8, minute=0),
            id="gba_collection",
            name="G-BA Innovation Fund Collection",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Weekly BMFTR Monday at 09:00
        self.scheduler.add_job(
            self.pipeline.run_bmftr,
            CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="bmftr_collection",
            name="BMFTR Collection",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Daily AI evaluation at 10:00
        self.scheduler.add_job(
            self.pipeline.run_evaluation,
            CronTrigger(hour=10, minute=0),
            id="ai_evaluation",
            name="Groq AI Evaluation",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("All scheduler jobs registered.")

    def start(self) -> None:
        self.scheduler.start()
        logger.info("HFIP Scheduler started.")

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("HFIP Scheduler stopped.")

    def run_now(self) -> None:
        """Immediately run the full pipeline (useful for initial setup / testing)."""
        logger.info("Running full pipeline immediately...")
        self.pipeline.run_all_connectors()
        self.pipeline.run_evaluation()
