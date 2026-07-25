from __future__ import annotations

import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.config import get_settings
from app.modules.banking.models import (
    BankConnection,
    BankConnectionStatus,
    BankProviderName,
    BankWebhookEvent,
    WebhookProcessingStatus,
)
from app.modules.banking.pluggy import BankProviderError
from app.modules.banking.schemas import (
    BankConnectionCallback,
    BankConnectionResponse,
    BankIntegrationStatusResponse,
    BankOperationsResponse,
    BankSyncAcceptedResponse,
    ConnectTokenResponse,
    PluggyWebhookPayload,
)
from app.modules.banking.service import (
    complete_bank_connection,
    get_owned_bank_connection,
    list_bank_connections,
    receive_pluggy_webhook,
    revoke_bank_connection,
    start_bank_connection,
)
from app.modules.banking.tasks import enqueue_bank_sync
from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile

router = APIRouter()


@router.get(
    "/banking/status",
    response_model=BankIntegrationStatusResponse,
    tags=["banking"],
)
async def get_banking_status(scope: CurrentScope) -> BankIntegrationStatusResponse:
    _ = scope
    settings = get_settings()
    return BankIntegrationStatusResponse(
        provider=BankProviderName.PLUGGY,
        configured=settings.pluggy_configured,
        mode="SANDBOX" if settings.pluggy_configured else "PENDING_CREDENTIALS",
    )


@router.get(
    "/financial-profiles/{profile_id}/bank-connections",
    response_model=list[BankConnectionResponse],
    tags=["banking"],
)
async def get_bank_connections(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[BankConnectionResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return [
        BankConnectionResponse.model_validate(connection)
        for connection in await list_bank_connections(db, scope.user.id, profile.id)
    ]


@router.get(
    "/financial-profiles/{profile_id}/banking/operations",
    response_model=BankOperationsResponse,
    tags=["banking"],
)
async def get_banking_operations(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> BankOperationsResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    connections = list(
        await db.scalars(
            select(BankConnection).where(
                BankConnection.user_id == scope.user.id,
                BankConnection.financial_profile_id == profile.id,
            )
        )
    )
    connection_ids = [connection.id for connection in connections]
    event_counts = {
        "pending": 0,
        "failed": 0,
        "dead": 0,
    }
    if connection_ids:
        event_counts["pending"] = int(
            await db.scalar(
                select(func.count())
                .select_from(BankWebhookEvent)
                .where(
                    BankWebhookEvent.connection_id.in_(connection_ids),
                    BankWebhookEvent.status == WebhookProcessingStatus.RECEIVED,
                )
            )
            or 0
        )
        event_counts["failed"] = int(
            await db.scalar(
                select(func.count())
                .select_from(BankWebhookEvent)
                .where(
                    BankWebhookEvent.connection_id.in_(connection_ids),
                    BankWebhookEvent.status == WebhookProcessingStatus.FAILED,
                )
            )
            or 0
        )
        event_counts["dead"] = int(
            await db.scalar(
                select(func.count())
                .select_from(BankWebhookEvent)
                .where(
                    BankWebhookEvent.connection_id.in_(connection_ids),
                    BankWebhookEvent.status == WebhookProcessingStatus.FAILED,
                    BankWebhookEvent.attempts >= 5,
                )
            )
            or 0
        )
    return BankOperationsResponse(
        profile_id=profile.id,
        healthy_connections=sum(
            connection.status == BankConnectionStatus.HEALTHY for connection in connections
        ),
        degraded_connections=sum(
            connection.status
            in {
                BankConnectionStatus.ERROR,
                BankConnectionStatus.RECONNECT_REQUIRED,
            }
            for connection in connections
        ),
        pending_events=event_counts["pending"],
        failed_events=event_counts["failed"],
        dead_letter_events=event_counts["dead"],
        notes=[
            "Eventos com cinco tentativas falhas entram na visão de dead-letter.",
            "Payloads e credenciais não são retornados nesta visão operacional.",
        ],
    )


@router.post(
    "/financial-profiles/{profile_id}/bank-connections/connect-token",
    response_model=ConnectTokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["banking"],
)
async def post_connect_token(
    request: Request,
    profile_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> ConnectTokenResponse:
    if scope.user.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A conta de demonstração não permite conexões externas.",
        )
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        connection, token = await start_bank_connection(
            db,
            scope.user,
            profile,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except BankProviderError as exc:
        await db.rollback()
        code = status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.code != "not_configured":
            code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return ConnectTokenResponse(
        connection=BankConnectionResponse.model_validate(connection),
        connect_token=token.value,
        expires_in_seconds=token.expires_in_seconds,
    )


@router.post(
    "/bank-connections/{connection_id}/complete",
    response_model=BankConnectionResponse,
    tags=["banking"],
)
async def post_bank_connection_complete(
    request: Request,
    connection_id: UUID,
    payload: BankConnectionCallback,
    db: DatabaseSession,
    scope: CsrfScope,
) -> BankConnectionResponse:
    connection = await get_owned_bank_connection(db, scope.user.id, connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    try:
        await complete_bank_connection(
            db,
            scope.user,
            connection,
            payload.item_id,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except BankProviderError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    enqueue_bank_sync(connection.id)
    return BankConnectionResponse.model_validate(connection)


@router.post(
    "/bank-connections/{connection_id}/sync",
    response_model=BankSyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["banking"],
)
async def post_bank_connection_sync(
    connection_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> BankSyncAcceptedResponse:
    connection = await get_owned_bank_connection(db, scope.user.id, connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    if not connection.external_item_id or connection.status.value == "REVOKED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Connection is not ready for synchronization.",
        )
    if not enqueue_bank_sync(connection.id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Synchronization queue is unavailable.",
        )
    return BankSyncAcceptedResponse(connection_id=connection.id)


@router.delete(
    "/bank-connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["banking"],
)
async def delete_bank_connection(
    request: Request,
    connection_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> Response:
    connection = await get_owned_bank_connection(db, scope.user.id, connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    try:
        await revoke_bank_connection(
            db,
            scope.user,
            connection,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except BankProviderError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/webhooks/pluggy",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["webhooks"],
)
async def post_pluggy_webhook(
    request: Request,
    db: DatabaseSession,
    webhook_secret: Annotated[str | None, Header(alias="X-Rayo-Webhook-Secret")] = None,
) -> dict[str, str]:
    settings = get_settings()
    expected = (
        settings.pluggy_webhook_secret.get_secret_value() if settings.pluggy_webhook_secret else ""
    )
    if not expected or not webhook_secret or not hmac.compare_digest(webhook_secret, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook.")
    raw_payload = await request.json()
    if not isinstance(raw_payload, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    try:
        payload = PluggyWebhookPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid webhook payload.",
        ) from exc
    event = await receive_pluggy_webhook(db, payload, raw_payload)
    await db.commit()
    if event.connection_id and payload.event in {"item/created", "item/updated"}:
        queued = enqueue_bank_sync(event.connection_id, event.id)
        return {"status": "accepted" if queued else "stored"}
    return {"status": "accepted"}
