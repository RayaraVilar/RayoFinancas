from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base, RecordStatus


class CategoryKind(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    BOTH = "BOTH"


class TransactionKind(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    VOIDED = "VOIDED"


class TransactionSource(StrEnum):
    MANUAL = "MANUAL"
    BANK_PROVIDER = "BANK_PROVIDER"


class TransferDirection(StrEnum):
    OUTFLOW = "OUTFLOW"
    INFLOW = "INFLOW"


class CardInvoiceStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PAID = "PAID"


class CreditCard(Base):
    __tablename__ = "credit_cards"
    __table_args__ = (
        CheckConstraint("closing_day BETWEEN 1 AND 28", name="closing_day_range"),
        CheckConstraint("due_day BETWEEN 1 AND 28", name="due_day_range"),
        CheckConstraint("credit_limit >= 0", name="credit_limit_non_negative"),
        Index("ix_credit_cards_profile_status", "financial_profile_id", "status"),
        Index(
            "uq_credit_cards_bank_connection_external",
            "bank_connection_id",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    bank_connection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("bank_connections.id", ondelete="SET NULL"), index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(96))
    name: Mapped[str] = mapped_column(String(100))
    institution_name: Mapped[str | None] = mapped_column(String(120))
    last_four: Mapped[str | None] = mapped_column(String(4))
    closing_day: Mapped[int] = mapped_column()
    due_day: Mapped[int] = mapped_column()
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False, create_constraint=True),
        default=RecordStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CardInvoice(Base):
    __tablename__ = "card_invoices"
    __table_args__ = (
        CheckConstraint(
            "competence_month = date_trunc('month', competence_month)::date",
            name="competence_first_day",
        ),
        Index(
            "uq_card_invoices_card_competence",
            "credit_card_id",
            "competence_month",
            unique=True,
        ),
        Index("ix_card_invoices_profile_status_due", "financial_profile_id", "status", "due_on"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    credit_card_id: Mapped[UUID] = mapped_column(
        ForeignKey("credit_cards.id", ondelete="CASCADE"), index=True
    )
    competence_month: Mapped[date] = mapped_column(Date, index=True)
    due_on: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[CardInvoiceStatus] = mapped_column(
        Enum(CardInvoiceStatus, native_enum=False, create_constraint=True),
        default=CardInvoiceStatus.OPEN,
    )
    paid_on: Mapped[date | None] = mapped_column(Date)
    paid_transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), index=True
    )
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index(
            "uq_categories_profile_normalized_name",
            "financial_profile_id",
            "normalized_name",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    financial_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    system_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    normalized_name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[CategoryKind] = mapped_column(
        Enum(CategoryKind, native_enum=False, create_constraint=True)
    )
    color: Mapped[str] = mapped_column(String(7))
    icon: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CategoryRule(Base):
    __tablename__ = "category_rules"
    __table_args__ = (
        Index(
            "uq_category_rules_profile_match",
            "financial_profile_id",
            "normalized_match_text",
            unique=True,
        ),
        Index(
            "ix_category_rules_profile_active_priority",
            "financial_profile_id",
            "is_active",
            "priority",
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
    match_text: Mapped[str] = mapped_column(String(120))
    normalized_match_text: Mapped[str] = mapped_column(String(120))
    priority: Mapped[int] = mapped_column(default=100)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "competence_month = date_trunc('month', competence_month)::date",
            name="competence_first_day",
        ),
        Index(
            "ix_transactions_user_profile_occurred",
            "user_id",
            "financial_profile_id",
            "occurred_on",
            "id",
        ),
        Index("ix_transactions_profile_status", "financial_profile_id", "status"),
        Index("uq_transactions_operation_key", "operation_key", unique=True),
        Index(
            "uq_transactions_reversal_of",
            "reversal_of_transaction_id",
            unique=True,
        ),
        Index(
            "uq_transactions_bank_connection_external",
            "bank_connection_id",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    bank_connection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("bank_connections.id", ondelete="SET NULL"), index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(96))
    account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True
    )
    credit_card_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("credit_cards.id", ondelete="RESTRICT"), index=True
    )
    card_invoice_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("card_invoices.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[TransactionKind] = mapped_column(
        Enum(TransactionKind, native_enum=False, create_constraint=True)
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, native_enum=False, create_constraint=True),
        default=TransactionStatus.POSTED,
    )
    source: Mapped[TransactionSource] = mapped_column(
        Enum(TransactionSource, native_enum=False, create_constraint=True),
        default=TransactionSource.MANUAL,
    )
    description: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    competence_month: Mapped[date] = mapped_column(Date, index=True)
    notes: Mapped[str | None] = mapped_column(String(500))
    transfer_group_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    transfer_direction: Mapped[TransferDirection | None] = mapped_column(
        Enum(TransferDirection, native_enum=False, create_constraint=True)
    )
    reversal_of_transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="RESTRICT"), index=True
    )
    operation_key: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TransactionSplit(Base):
    __tablename__ = "transaction_splits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index(
            "uq_transaction_splits_transaction_position",
            "transaction_id",
            "position",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    position: Mapped[int] = mapped_column()
    description: Mapped[str | None] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
