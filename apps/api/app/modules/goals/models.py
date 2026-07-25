from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class GoalStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class PendingActionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (Index("ix_goals_profile_status", "financial_profile_id", "status"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    target_date: Mapped[date] = mapped_column(Date)
    monthly_contribution: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    priority: Mapped[int] = mapped_column(default=100)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, native_enum=False, create_constraint=True),
        default=GoalStatus.ACTIVE,
    )
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    contributed_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GoalPlanVersion(Base):
    __tablename__ = "goal_plan_versions"
    __table_args__ = (
        Index(
            "uq_goal_plan_versions_goal_version",
            "goal_id",
            "version",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column()
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GoalScenario(Base):
    __tablename__ = "goal_scenarios"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    inputs: Mapped[dict[str, object]] = mapped_column(JSON)
    results: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PendingAction(Base):
    __tablename__ = "pending_actions"
    __table_args__ = (
        Index("uq_pending_actions_idempotency", "user_id", "idempotency_key", unique=True),
        Index("ix_pending_actions_status_expires", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[UUID] = mapped_column(Uuid)
    target_version: Mapped[int] = mapped_column()
    idempotency_key: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    before_state: Mapped[dict[str, object]] = mapped_column(JSON)
    after_state: Mapped[dict[str, object]] = mapped_column(JSON)
    status: Mapped[PendingActionStatus] = mapped_column(
        Enum(PendingActionStatus, native_enum=False, create_constraint=True),
        default=PendingActionStatus.PENDING,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
