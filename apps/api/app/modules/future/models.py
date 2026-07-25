from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"
    __table_args__ = (
        Index(
            "uq_net_worth_snapshots_profile_date",
            "financial_profile_id",
            "snapshot_on",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    snapshot_on: Mapped[date] = mapped_column(Date, index=True)
    assets: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    liabilities: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    algorithm_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HealthScoreSnapshot(Base):
    __tablename__ = "health_score_snapshots"
    __table_args__ = (
        Index(
            "uq_health_score_snapshots_profile_date_version",
            "financial_profile_id",
            "snapshot_on",
            "algorithm_version",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    snapshot_on: Mapped[date] = mapped_column(Date, index=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    confidence_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    subscores: Mapped[dict[str, object]] = mapped_column(JSON)
    algorithm_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
