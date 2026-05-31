"""
HFIP – Database Repository
All database read/write operations (no raw SQL outside this module).
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from database.models import (
    Evaluation,
    Notification,
    Tender,
    create_all_tables,
    get_engine,
    get_session_factory,
)


# ─── Repository ──────────────────────────────────────────────────────────────

class TenderRepository:
    """Central data access object for all HFIP database operations."""

    def __init__(self, db_path: str = "data/hfip.db"):
        self.engine = get_engine(db_path)
        create_all_tables(self.engine)
        self._Session = get_session_factory(self.engine)
        logger.info(f"Database initialised at {db_path}")

    def close(self):
        """Dispose the engine connection pool (required on Windows before deleting DB files)."""
        self.engine.dispose()

    # ─── Context Manager ─────────────────────────────────────────────────────

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional database session."""
        sess: Session = self._Session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    # ─── Tenders ─────────────────────────────────────────────────────────────

    def upsert_tender(self, tender_data: dict) -> tuple[Tender, bool]:
        """
        Insert tender if hash is unique; otherwise skip.
        Returns (tender, created) where created=True when a new row was inserted.
        """
        with self.session() as sess:
            existing = sess.query(Tender).filter_by(hash=tender_data["hash"]).first()
            if existing:
                logger.debug(f"Duplicate tender skipped: {tender_data.get('title', '')[:60]}")
                return existing, False

            tender = Tender(
                source=tender_data.get("source", "unknown"),
                title=tender_data.get("title", ""),
                description=tender_data.get("description"),
                organization=tender_data.get("organization"),
                country=tender_data.get("country"),
                deadline=tender_data.get("deadline"),
                published_date=tender_data.get("published_date"),
                url=tender_data.get("url"),
                cpv_codes=json.dumps(tender_data.get("cpv_codes", [])),
                hash=tender_data["hash"],
                keyword_score=tender_data.get("keyword_score", 0),
                is_archived=tender_data.get("is_archived", False),
            )
            sess.add(tender)
            sess.flush()  # Get ID before commit
            sess.expunge(tender)
            logger.info(f"New tender saved: [{tender.source}] {tender.title[:60]}")
            return tender, True

    def get_tender_by_id(self, tender_id: int) -> Optional[Tender]:
        with self.session() as sess:
            return sess.query(Tender).filter_by(id=tender_id).first()

    def get_pending_evaluation(self) -> List[Tender]:
        """Tenders with keyword_score >= threshold but no evaluation yet."""
        with self.session() as sess:
            return (
                sess.query(Tender)
                .outerjoin(Evaluation, Tender.id == Evaluation.tender_id)
                .filter(
                    Tender.is_archived == False,
                    Evaluation.id == None,
                    Tender.keyword_score >= 50,
                )
                .order_by(Tender.created_at.desc())
                .all()
            )

    def get_all_tenders(
        self,
        source: Optional[str] = None,
        min_score: Optional[int] = None,
        keyword: Optional[str] = None,
        limit: int = 200,
    ) -> List[Tender]:
        with self.session() as sess:
            q = sess.query(Tender).filter(Tender.is_archived == False)
            if source:
                q = q.filter(Tender.source == source)
            if keyword:
                kw = f"%{keyword}%"
                q = q.filter(
                    Tender.title.ilike(kw) | Tender.description.ilike(kw) | Tender.organization.ilike(kw)
                )
            if min_score is not None:
                q = (
                    q.join(Evaluation, Tender.id == Evaluation.tender_id)
                    .filter(Evaluation.score >= min_score)
                )
            return q.order_by(Tender.created_at.desc()).limit(limit).all()

    def archive_tender(self, tender_id: int) -> None:
        with self.session() as sess:
            sess.query(Tender).filter_by(id=tender_id).update({"is_archived": True})

    # ─── Evaluations ─────────────────────────────────────────────────────────

    def save_evaluation(self, eval_data: dict) -> Evaluation:
        with self.session() as sess:
            # Remove existing evaluation if re-running
            sess.query(Evaluation).filter_by(tender_id=eval_data["tender_id"]).delete()
            evaluation = Evaluation(
                tender_id=eval_data["tender_id"],
                relevant=eval_data.get("relevant"),
                score=eval_data.get("score"),
                category=eval_data.get("category"),
                summary=eval_data.get("summary"),
                required_skills=json.dumps(eval_data.get("required_skills", [])),
                proposal_effort=eval_data.get("proposal_effort"),
                consortium_required=eval_data.get("consortium_required"),
                raw_response=eval_data.get("raw_response"),
                model_used=eval_data.get("model_used"),
                tavily_context=eval_data.get("tavily_context"),
            )
            sess.add(evaluation)
            logger.info(f"Evaluation saved: tender_id={eval_data['tender_id']} score={eval_data.get('score')}")
            return evaluation

    def get_evaluation_by_tender(self, tender_id: int) -> Optional[Evaluation]:
        with self.session() as sess:
            return sess.query(Evaluation).filter_by(tender_id=tender_id).first()

    # ─── Notifications ───────────────────────────────────────────────────────

    def save_notification(self, notif_data: dict) -> Notification:
        with self.session() as sess:
            notif = Notification(
                tender_id=notif_data["tender_id"],
                channel=notif_data["channel"],
                status=notif_data["status"],
                error_message=notif_data.get("error_message"),
            )
            sess.add(notif)
            return notif

    def notification_already_sent(self, tender_id: int, channel: str) -> bool:
        with self.session() as sess:
            return (
                sess.query(Notification)
                .filter_by(tender_id=tender_id, channel=channel, status="sent")
                .count()
                > 0
            )

    # ─── Analytics ───────────────────────────────────────────────────────────

    def count_tenders(self) -> dict:
        with self.session() as sess:
            total = sess.query(Tender).filter_by(is_archived=False).count()
            evaluated = sess.query(Evaluation).count()
            relevant = sess.query(Evaluation).filter(Evaluation.relevant == True).count()
            high_score = sess.query(Evaluation).filter(Evaluation.score >= 80).count()
            return {
                "total": total,
                "evaluated": evaluated,
                "relevant": relevant,
                "high_score": high_score,
            }

    def get_top_sources(self) -> List[dict]:
        with self.session() as sess:
            from sqlalchemy import func
            rows = (
                sess.query(Tender.source, func.count(Tender.id).label("count"))
                .filter(Tender.is_archived == False)
                .group_by(Tender.source)
                .order_by(func.count(Tender.id).desc())
                .all()
            )
            return [{"source": r.source, "count": r.count} for r in rows]

    def get_upcoming_deadlines(self, days: int = 30) -> List[Tender]:
        from datetime import timedelta
        cutoff = datetime.utcnow() + timedelta(days=days)
        with self.session() as sess:
            return (
                sess.query(Tender)
                .join(Evaluation, Tender.id == Evaluation.tender_id)
                .filter(
                    Tender.is_archived == False,
                    Tender.deadline != None,
                    Tender.deadline >= datetime.utcnow(),
                    Tender.deadline <= cutoff,
                    Evaluation.relevant == True,
                )
                .order_by(Tender.deadline.asc())
                .all()
            )
