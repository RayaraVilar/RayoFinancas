from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class BillSource(StrEnum):
    MANUAL = "MANUAL"
    CARD_INVOICE = "CARD_INVOICE"
    BANK_PROVIDER = "BANK_PROVIDER"
    EMAIL = "EMAIL"


class BillStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    DISMISSED = "DISMISSED"


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        Index("uq_bills_profile_dedupe", "financial_profile_id", "dedupe_key", unique=True),
        Index("ix_bills_profile_status_due", "financial_profile_id", "status", "due_on"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[BillSource] = mapped_column(
        Enum(BillSource, native_enum=False, create_constraint=True)
    )
    external_id: Mapped[str | None] = mapped_column(String(96))
    dedupe_key: Mapped[str] = mapped_column(String(64))
    possible_duplicate_of_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("bills.id", ondelete="SET NULL"), index=True
    )
    description: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    due_on: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus, native_enum=False, create_constraint=True),
        default=BillStatus.DRAFT,
    )
    paid_on: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MonthlyBudget(Base):
    __tablename__ = "monthly_budgets"
    __table_args__ = (
        Index(
            "uq_monthly_budgets_profile_category_month",
            "financial_profile_id",
            "category_id",
            "competence_month",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    competence_month: Mapped[date] = mapped_column(Date, index=True)
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MonthlyPlan(Base):
    __tablename__ = "monthly_plans"
    __table_args__ = (
        Index(
            "uq_monthly_plans_profile_month",
            "financial_profile_id",
            "competence_month",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    competence_month: Mapped[date] = mapped_column(Date, index=True)
    expected_income: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    essential_commitment: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    debt_commitment: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    goal_contribution: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
