from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.modules.identity.models import Base


class BankProviderName(StrEnum):
    PLUGGY = "PLUGGY"
    MOCK = "MOCK"


class BankConnectionStatus(StrEnum):
    PENDING = "PENDING"
    SYNCING = "SYNCING"
    HEALTHY = "HEALTHY"
    ERROR = "ERROR"
    RECONNECT_REQUIRED = "RECONNECT_REQUIRED"
    REVOKED = "REVOKED"


class WebhookProcessingStatus(StrEnum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class BankConnection(Base):
    __tablename__ = "bank_connections"
    __table_args__ = (
        Index(
            "uq_bank_connections_provider_external",
            "provider",
            "external_item_id",
            unique=True,
        ),
        Index(
            "ix_bank_connections_profile_status",
            "financial_profile_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[BankProviderName] = mapped_column(
        Enum(BankProviderName, native_enum=False, create_constraint=True)
    )
    external_item_id: Mapped[str | None] = mapped_column(String(64))
    connector_id: Mapped[str | None] = mapped_column(String(64))
    connector_name: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[BankConnectionStatus] = mapped_column(
        Enum(BankConnectionStatus, native_enum=False, create_constraint=True),
        default=BankConnectionStatus.PENDING,
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    consent_granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_accounts_total: Mapped[int] = mapped_column(default=0)
    sync_transactions_total: Mapped[int] = mapped_column(default=0)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BankWebhookEvent(Base):
    __tablename__ = "bank_webhook_events"
    __table_args__ = (
        Index(
            "uq_bank_webhook_events_provider_event",
            "provider",
            "external_event_id",
            unique=True,
        ),
        Index("ix_bank_webhook_events_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    connection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("bank_connections.id", ondelete="SET NULL"), index=True
    )
    provider: Mapped[BankProviderName] = mapped_column(
        Enum(BankProviderName, native_enum=False, create_constraint=True)
    )
    external_event_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[WebhookProcessingStatus] = mapped_column(
        Enum(WebhookProcessingStatus, native_enum=False, create_constraint=True),
        default=WebhookProcessingStatus.RECEIVED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
