from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class AmortizationSystem(StrEnum):
    PRICE = "PRICE"
    SAC = "SAC"
    UNKNOWN = "UNKNOWN"


class DebtStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    ARCHIVED = "ARCHIVED"


class Debt(Base):
    __tablename__ = "debts"
    __table_args__ = (Index("ix_debts_profile_status", "financial_profile_id", "status"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    original_principal: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    outstanding_balance: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    annual_interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    annual_cet_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    amortization_system: Mapped[AmortizationSystem] = mapped_column(
        Enum(AmortizationSystem, native_enum=False, create_constraint=True)
    )
    installments_remaining: Mapped[int] = mapped_column()
    monthly_payment: Mapped[Decimal | None] = mapped_column(Numeric(19, 2))
    next_due_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[DebtStatus] = mapped_column(
        Enum(DebtStatus, native_enum=False, create_constraint=True),
        default=DebtStatus.ACTIVE,
    )
    data_quality: Mapped[str] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    debt_id: Mapped[UUID] = mapped_column(ForeignKey("debts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    interest_amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    paid_on: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
