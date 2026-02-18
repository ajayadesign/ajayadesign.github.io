"""
AjayaDesign Automation — SQLAlchemy ORM models for builds.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    SmallInteger,
    String,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return uuid.uuid4().hex[:8]


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    short_id: Mapped[str] = mapped_column(String(8), unique=True, default=_new_uuid)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    niche: Mapped[str] = mapped_column(String(255), nullable=False)
    goals: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Firebase link
    firebase_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, unique=True
    )
    source: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="form"
    )

    # Enhanced client details (Task 1)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    existing_website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    brand_colors: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitor_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rebuild: Mapped[bool] = mapped_column(Boolean, default=False)
    protected: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Result
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    repo_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repo_full: Mapped[str | None] = mapped_column(String(255), nullable=True)
    live_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pages_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Structured data (JSON for SQLite compat, JSONB in Postgres)
    blueprint: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    design_system: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    phases: Mapped[list["BuildPhase"]] = relationship(
        back_populates="build", cascade="all, delete-orphan", order_by="BuildPhase.phase_number"
    )
    logs: Mapped[list["BuildLog"]] = relationship(
        back_populates="build", cascade="all, delete-orphan", order_by="BuildLog.sequence"
    )
    pages: Mapped[list["BuildPage"]] = relationship(
        back_populates="build", cascade="all, delete-orphan"
    )

    @property
    def duration_secs(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "short_id": self.short_id,
            "client_name": self.client_name,
            "niche": self.niche,
            "goals": self.goals,
            "email": self.email,
            "status": self.status,
            "repo_name": self.repo_name,
            "repo_full": self.repo_full,
            "live_url": self.live_url,
            "pages_count": self.pages_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_secs": self.duration_secs,
            "error_message": self.error_message,
            "protected": self.protected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BuildPhase(Base):
    __tablename__ = "build_phases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    build_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("builds.id", ondelete="CASCADE"), nullable=False
    )
    phase_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    phase_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    ai_calls: Mapped[int] = mapped_column(Integer, default=0)
    ai_tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    ai_tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    build: Mapped["Build"] = relationship(back_populates="phases")

    __table_args__ = (
        Index("ix_build_phases_build_phase", "build_id", "phase_number", unique=True),
    )


class BuildLog(Base):
    __tablename__ = "build_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    build_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("builds.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(10), default="info")
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    build: Mapped["Build"] = relationship(back_populates="logs")

    __table_args__ = (
        Index("ix_build_logs_build_seq", "build_id", "sequence"),
    )


class BuildPage(Base):
    __tablename__ = "build_pages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    build_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("builds.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    main_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    fix_attempts: Mapped[int] = mapped_column(Integer, default=0)
    test_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    axe_violations: Mapped[int] = mapped_column(Integer, default=0)

    h1_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    build: Mapped["Build"] = relationship(back_populates="pages")

    __table_args__ = (
        Index("ix_build_pages_build", "build_id"),
    )
