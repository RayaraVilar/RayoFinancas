from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import metadata


class Base(DeclarativeBase):
    metadata = metadata


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DELETION_PENDING = "DELETION_PENDING"


class FinancialProfileType(StrEnum):
    PERSONAL = "PERSONAL"
    BUSINESS = "BUSINESS"


class RecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class AccountType(StrEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CASH = "CASH"
    PAYMENT = "PAYMENT"
    OTHER = "OTHER"


class AccountSource(StrEnum):
    MANUAL = "MANUAL"
    BANK_PROVIDER = "BANK_PROVIDER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    locale: Mapped[str] = mapped_column(String(16), default="pt-BR")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    base_currency: Mapped[str] = mapped_column(String(3), default="BRL")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False, create_constraint=True),
        default=UserStatus.ACTIVE,
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OAuthIdentity(Base):
    __tablename__ = "oauth_identities"
    __table_args__ = (
        Index("uq_oauth_identities_provider_subject", "provider", "subject", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(255))
    email_at_login: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"
    __table_args__ = (
        Index(
            "uq_financial_profiles_active_personal",
            "user_id",
            unique=True,
            postgresql_where=text("type = 'PERSONAL' AND status = 'ACTIVE'"),
        ),
        Index("ix_financial_profiles_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[FinancialProfileType] = mapped_column(
        Enum(FinancialProfileType, native_enum=False, create_constraint=True)
    )
    name: Mapped[str] = mapped_column(String(100))
    document_last4: Mapped[str | None] = mapped_column(String(4))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False, create_constraint=True),
        default=RecordStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FinancialAccount(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_profile_status", "financial_profile_id", "status"),
        Index(
            "uq_accounts_bank_connection_external",
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
    name: Mapped[str] = mapped_column(String(100))
    institution_name: Mapped[str | None] = mapped_column(String(120))
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False, create_constraint=True)
    )
    source: Mapped[AccountSource] = mapped_column(
        Enum(AccountSource, native_enum=False, create_constraint=True),
        default=AccountSource.MANUAL,
    )
    bank_connection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("bank_connections.id", ondelete="SET NULL"), index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(96))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(19, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False, create_constraint=True),
        default=RecordStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserConsent(Base):
    __tablename__ = "user_consents"
    __table_args__ = (Index("ix_user_consents_user_type", "user_id", "consent_type"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    financial_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True
    )
    consent_type: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_user_created", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[UUID | None] = mapped_column(Uuid)
    outcome: Mapped[str] = mapped_column(String(32))
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    safe_metadata: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
