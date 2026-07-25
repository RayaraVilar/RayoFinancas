from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class PaymentSimulationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"


class PaymentStatus(StrEnum):
    CREATED = "CREATED"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    PROCESSING = "PROCESSING"
    PARTIAL = "PARTIAL"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class PaymentItemStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class PaymentSimulation(Base):
    __tablename__ = "payment_simulations"
    __table_args__ = (
        Index("uq_payment_simulations_user_key", "user_id", "idempotency_key", unique=True),
        Index("ix_payment_simulations_status_expires", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64))
    bill_ids: Mapped[list[str]] = mapped_column(JSON)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    account_options: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    input_hash: Mapped[str] = mapped_column(String(64))
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    risk_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[PaymentSimulationStatus] = mapped_column(
        Enum(PaymentSimulationStatus, native_enum=False, create_constraint=True),
        default=PaymentSimulationStatus.ACTIVE,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (Index("uq_payments_user_key", "user_id", "idempotency_key", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    simulation_id: Mapped[UUID] = mapped_column(
        ForeignKey("payment_simulations.id", ondelete="RESTRICT"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40))
    provider_payment_id: Mapped[str | None] = mapped_column(String(96))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, create_constraint=True)
    )
    authorization_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PaymentItem(Base):
    __tablename__ = "payment_items"
    __table_args__ = (
        Index("uq_payment_items_payment_bill", "payment_id", "bill_id", unique=True),
        Index("uq_payment_items_provider_key", "provider_idempotency_key", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), index=True
    )
    bill_id: Mapped[UUID] = mapped_column(ForeignKey("bills.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    provider_idempotency_key: Mapped[str] = mapped_column(String(96))
    provider_item_id: Mapped[str | None] = mapped_column(String(96))
    status: Mapped[PaymentItemStatus] = mapped_column(
        Enum(PaymentItemStatus, native_enum=False, create_constraint=True)
    )
    failure_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
