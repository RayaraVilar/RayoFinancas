from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class InsightState(StrEnum):
    ACTIVE = "ACTIVE"
    DISMISSED = "DISMISSED"
    ACTED = "ACTED"


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        Index("uq_insights_profile_dedupe", "financial_profile_id", "dedupe_key", unique=True),
        Index("ix_insights_profile_state_priority", "financial_profile_id", "state", "priority"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    rule_code: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[str] = mapped_column(String(32))
    dedupe_key: Mapped[str] = mapped_column(String(128))
    priority: Mapped[int] = mapped_column()
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, object]] = mapped_column(JSON)
    cta_label: Mapped[str | None] = mapped_column(String(80))
    cta_path: Mapped[str | None] = mapped_column(String(160))
    state: Mapped[InsightState] = mapped_column(
        Enum(InsightState, native_enum=False, create_constraint=True),
        default=InsightState.ACTIVE,
    )
    cooldown_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InsightFeedback(Base):
    __tablename__ = "insight_feedback"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    insight_id: Mapped[UUID] = mapped_column(
        ForeignKey("insights.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    helpful: Mapped[bool] = mapped_column()
    reason_code: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
