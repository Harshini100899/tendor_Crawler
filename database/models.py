"""
HFIP – Database Models
SQLAlchemy ORM definitions for all tables.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


# ─── Base ────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─── Tenders ─────────────────────────────────────────────────────────────────

class Tender(Base):
    """Raw tender / funding opportunity collected from any source."""

    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)   # ted | bund | gba | bmftr
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    organization = Column(String(500), nullable=True)
    country = Column(String(10), nullable=True)
    deadline = Column(DateTime, nullable=True, index=True)
    published_date = Column(DateTime, nullable=True, index=True)
    url = Column(Text, nullable=True)
    cpv_codes = Column(Text, nullable=True)  # JSON array stored as string
    hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 dedup key
    keyword_score = Column(Integer, default=0)  # Pre-AI rule engine score
    is_archived = Column(Boolean, default=False)  # True if score < threshold
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    evaluation = relationship("Evaluation", back_populates="tender", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="tender", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tender id={self.id} source={self.source!r} title={self.title[:60]!r}>"

    @staticmethod
    def compute_hash(title: str, url: str, source: str) -> str:
        """Deterministic SHA-256 hash used for deduplication."""
        raw = f"{source}|{url}|{title}".lower().strip()
        return hashlib.sha256(raw.encode()).hexdigest()


# ─── Evaluations ─────────────────────────────────────────────────────────────

class Evaluation(Base):
    """Groq LLM evaluation result for a tender."""

    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    relevant = Column(Boolean, nullable=True)
    score = Column(Integer, nullable=True, index=True)       # 0–100
    category = Column(String(200), nullable=True)            # e.g. "Healthcare AI"
    summary = Column(Text, nullable=True)
    required_skills = Column(Text, nullable=True)            # JSON array
    proposal_effort = Column(String(20), nullable=True)      # Low | Medium | High
    consortium_required = Column(Boolean, nullable=True)
    raw_response = Column(Text, nullable=True)               # Full LLM JSON response
    model_used = Column(String(100), nullable=True)
    tavily_context = Column(Text, nullable=True)             # Research enrichment snippets
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tender = relationship("Tender", back_populates="evaluation")

    def __repr__(self) -> str:
        return f"<Evaluation tender_id={self.tender_id} score={self.score}>"


# ─── Notifications ───────────────────────────────────────────────────────────

class Notification(Base):
    """Record of every alert sent out."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)   # teams | email
    status = Column(String(20), nullable=False)    # sent | failed | skipped
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tender = relationship("Tender", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification tender_id={self.tender_id} channel={self.channel!r} status={self.status!r}>"


# ─── Engine / Session Factory ─────────────────────────────────────────────────

def get_engine(db_path: str = "data/hfip.db"):
    """Create SQLAlchemy engine (SQLite with WAL mode for concurrency)."""
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Enable WAL journal mode for better concurrent read performance
    @event.listens_for(engine, "connect")
    def set_wal_mode(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_all_tables(engine) -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(engine)


def get_session_factory(engine):
    """Return a SQLAlchemy session factory."""
    return sessionmaker(bind=engine, expire_on_commit=False)
