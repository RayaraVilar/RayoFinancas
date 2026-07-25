from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.banking.models import (
    BankConnection,
    BankConnectionStatus,
    BankProviderName,
    BankWebhookEvent,
)
from app.modules.banking.pluggy import BankProviderError, PluggyBankProvider
from app.modules.banking.ports import BankProvider, ConnectToken
from app.modules.banking.schemas import PluggyWebhookPayload
from app.modules.identity.models import FinancialProfile, User, UserConsent
from app.modules.identity.service import record_audit_event

BANK_DATA_CONSENT_TYPE = "BANK_DATA_ACCESS"
BANK_DATA_CONSENT_VERSION = "2026-07-24"


@lru_cache
def get_bank_provider() -> BankProvider:
    settings = get_settings()
    if not settings.pluggy_configured:
        raise BankProviderError("not_configured", "Bank provider is not configured.")
    return PluggyBankProvider(
        client_id=settings.pluggy_client_id or "",
        client_secret=(
            settings.pluggy_client_secret.get_secret_value()
            if settings.pluggy_client_secret
            else ""
        ),
        api_url=settings.pluggy_api_url,
    )


async def list_bank_connections(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
) -> list[BankConnection]:
    rows = await db.scalars(
        select(BankConnection)
        .where(
            BankConnection.user_id == user_id,
            BankConnection.financial_profile_id == profile_id,
        )
        .order_by(BankConnection.created_at.desc())
    )
    return list(rows)


async def get_owned_bank_connection(
    db: AsyncSession,
    user_id: UUID,
    connection_id: UUID,
) -> BankConnection | None:
    return cast(
        BankConnection | None,
        await db.scalar(
            select(BankConnection).where(
                BankConnection.id == connection_id,
                BankConnection.user_id == user_id,
            )
        ),
    )


async def start_bank_connection(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    correlation_id: str | None,
) -> tuple[BankConnection, ConnectToken]:
    connection = BankConnection(
        user_id=user.id,
        financial_profile_id=profile.id,
        provider=BankProviderName.PLUGGY,
        status=BankConnectionStatus.PENDING,
    )
    db.add(connection)
    await db.flush()
    token = await get_bank_provider().create_connect_token(client_user_id=str(connection.id))
    db.add(
        UserConsent(
            user_id=user.id,
            financial_profile_id=profile.id,
            consent_type=BANK_DATA_CONSENT_TYPE,
            version=BANK_DATA_CONSENT_VERSION,
        )
    )
    await record_audit_event(
        db,
        user_id=user.id,
        action="bank_connection.started",
        target_type="bank_connection",
        target_id=connection.id,
        correlation_id=correlation_id,
        safe_metadata={"provider": connection.provider.value},
    )
    return connection, token


async def complete_bank_connection(
    db: AsyncSession,
    user: User,
    connection: BankConnection,
    external_item_id: str,
    correlation_id: str | None,
) -> BankConnection:
    item = await get_bank_provider().get_item(external_item_id)
    if item.client_user_id != str(connection.id):
        raise ValueError("Provider item does not belong to this connection.")
    connection.external_item_id = item.external_id
    connection.connector_id = item.connector_id
    connection.connector_name = item.connector_name
    connection.status = (
        BankConnectionStatus.HEALTHY
        if item.status in {"UPDATED", "SUCCESS", "LOGIN_MFA", "WAITING_USER_INPUT"}
        else BankConnectionStatus.SYNCING
    )
    connection.error_code = None
    await record_audit_event(
        db,
        user_id=user.id,
        action="bank_connection.completed",
        target_type="bank_connection",
        target_id=connection.id,
        correlation_id=correlation_id,
        safe_metadata={"provider_status": item.status[:40]},
    )
    return connection


async def revoke_bank_connection(
    db: AsyncSession,
    user: User,
    connection: BankConnection,
    correlation_id: str | None,
) -> None:
    if connection.status == BankConnectionStatus.REVOKED:
        return
    if connection.external_item_id:
        await get_bank_provider().revoke_item(connection.external_item_id)
    connection.status = BankConnectionStatus.REVOKED
    connection.revoked_at = datetime.now(UTC)
    active_consents = await db.scalars(
        select(UserConsent).where(
            UserConsent.user_id == user.id,
            UserConsent.financial_profile_id == connection.financial_profile_id,
            UserConsent.consent_type == BANK_DATA_CONSENT_TYPE,
            UserConsent.revoked_at.is_(None),
        )
    )
    for consent in active_consents:
        consent.revoked_at = datetime.now(UTC)
    await record_audit_event(
        db,
        user_id=user.id,
        action="bank_connection.revoked",
        target_type="bank_connection",
        target_id=connection.id,
        correlation_id=correlation_id,
    )


def webhook_payload_hash(raw_payload: dict[str, object]) -> str:
    canonical = json.dumps(raw_payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


async def receive_pluggy_webhook(
    db: AsyncSession,
    payload: PluggyWebhookPayload,
    raw_payload: dict[str, object],
) -> BankWebhookEvent:
    existing = await db.scalar(
        select(BankWebhookEvent).where(
            BankWebhookEvent.provider == BankProviderName.PLUGGY,
            BankWebhookEvent.external_event_id == payload.event_id,
        )
    )
    if existing is not None:
        return existing

    connection: BankConnection | None = None
    if payload.client_user_id:
        try:
            connection_id = UUID(payload.client_user_id)
        except ValueError:
            connection_id = None
        if connection_id:
            connection = await db.get(BankConnection, connection_id)
    if connection is None and payload.item_id:
        connection = await db.scalar(
            select(BankConnection).where(
                BankConnection.provider == BankProviderName.PLUGGY,
                BankConnection.external_item_id == payload.item_id,
            )
        )

    event = BankWebhookEvent(
        connection_id=connection.id if connection else None,
        provider=BankProviderName.PLUGGY,
        external_event_id=payload.event_id,
        event_type=payload.event,
        payload_hash=webhook_payload_hash(raw_payload),
    )
    db.add(event)
    if connection:
        if payload.item_id and connection.external_item_id is None:
            connection.external_item_id = payload.item_id
        if payload.event in {"item/created", "item/updated"}:
            connection.status = BankConnectionStatus.SYNCING
            connection.error_code = None
        elif payload.event == "item/error":
            connection.status = BankConnectionStatus.RECONNECT_REQUIRED
            connection.error_code = "provider_item_error"
        elif payload.event == "item/deleted":
            connection.status = BankConnectionStatus.REVOKED
            connection.revoked_at = datetime.now(UTC)
    await db.flush()
    return event
