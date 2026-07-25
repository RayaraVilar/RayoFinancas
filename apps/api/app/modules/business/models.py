from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class ReceivableStatus(StrEnum):
    EXPECTED = "EXPECTED"
    RECEIVED = "RECEIVED"
    DISMISSED = "DISMISSED"


class SubscriptionStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class InboxReviewStatus(StrEnum):
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Receivable(Base):
    __tablename__ = "receivables"
    __table_args__ = (
        Index("uq_receivables_profile_dedupe", "financial_profile_id", "dedupe_key", unique=True),
        Index("ix_receivables_profile_status_due", "financial_profile_id", "status", "due_on"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str | None] = mapped_column(String(96))
    dedupe_key: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(160))
    counterparty: Mapped[str | None] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    due_on: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[ReceivableStatus] = mapped_column(
        Enum(ReceivableStatus, native_enum=False, create_constraint=True),
        default=ReceivableStatus.EXPECTED,
    )
    confirmed: Mapped[bool] = mapped_column(default=True)
    received_on: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index(
            "uq_subscriptions_profile_merchant",
            "financial_profile_id",
            "merchant_key",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    merchant_key: Mapped[str] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 2))
    cadence_months: Mapped[int] = mapped_column(default=1)
    next_charge_on: Mapped[date] = mapped_column(Date)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, create_constraint=True),
        default=SubscriptionStatus.CANDIDATE,
    )
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmailIngestionConsent(Base):
    __tablename__ = "email_ingestion_consents"
    __table_args__ = (
        Index("uq_email_consents_user_profile", "user_id", "financial_profile_id", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    scope_version: Mapped[str] = mapped_column(String(32))
    mailbox_hash: Mapped[str | None] = mapped_column(String(64))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InboxCandidate(Base):
    __tablename__ = "inbox_candidates"
    __table_args__ = (
        Index(
            "uq_inbox_candidates_profile_dedupe",
            "financial_profile_id",
            "dedupe_key",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32))
    dedupe_key: Mapped[str] = mapped_column(String(64))
    sender_domain_hash: Mapped[str | None] = mapped_column(String(64))
    extracted_fields: Mapped[dict[str, object]] = mapped_column(JSON)
    risk_flags: Mapped[list[str]] = mapped_column(JSON)
    status: Mapped[InboxReviewStatus] = mapped_column(
        Enum(InboxReviewStatus, native_enum=False, create_constraint=True),
        default=InboxReviewStatus.REVIEW_REQUIRED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index("uq_notification_preferences_user_channel", "user_id", "channel", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(24))
    enabled: Mapped[bool] = mapped_column(default=False)
    event_types: Mapped[list[str]] = mapped_column(JSON)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5))
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
