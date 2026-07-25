from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import dramatiq

from app.core.database import close_database, get_session_factory
from app.modules.banking.broker import broker as broker
from app.modules.banking.models import (
    BankConnection,
    BankWebhookEvent,
    WebhookProcessingStatus,
)
from app.modules.banking.service import get_bank_provider
from app.modules.banking.sync import synchronize_bank_connection


async def _synchronize(connection_id: UUID, event_id: UUID | None) -> None:
    try:
        async with get_session_factory()() as db:
            connection = await db.get(BankConnection, connection_id)
            if connection is None:
                return
            event = await db.get(BankWebhookEvent, event_id) if event_id is not None else None
            if event:
                event.attempts += 1
            try:
                await synchronize_bank_connection(db, connection, get_bank_provider())
            except Exception as exc:
                if event:
                    event.status = WebhookProcessingStatus.FAILED
                    event.last_error_code = getattr(exc, "code", "sync_failed")
                    event.processed_at = datetime.now(UTC)
                await db.commit()
                raise
            if event:
                event.status = WebhookProcessingStatus.PROCESSED
                event.last_error_code = None
                event.processed_at = datetime.now(UTC)
            await db.commit()
    finally:
        await close_database()


@dramatiq.actor(
    queue_name="bank-sync",
    max_retries=5,
    min_backoff=5_000,
    max_backoff=300_000,
    time_limit=300_000,
)
def synchronize_bank_connection_task(
    connection_id: str,
    event_id: str | None = None,
) -> None:
    asyncio.run(
        _synchronize(
            UUID(connection_id),
            UUID(event_id) if event_id else None,
        )
    )


def enqueue_bank_sync(connection_id: UUID, event_id: UUID | None = None) -> bool:
    try:
        synchronize_bank_connection_task.send(
            str(connection_id),
            str(event_id) if event_id else None,
        )
    except Exception:
        return False
    return True
