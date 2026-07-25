from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.banking.models import BankConnectionStatus, BankProviderName


class BankIntegrationStatusResponse(BaseModel):
    provider: BankProviderName
    configured: bool
    mode: str


class BankConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    provider: BankProviderName
    connector_name: str | None
    status: BankConnectionStatus
    error_code: str | None
    consent_granted_at: datetime
    revoked_at: datetime | None
    last_synced_at: datetime | None
    sync_started_at: datetime | None
    sync_accounts_total: int
    sync_transactions_total: int
    consecutive_failures: int


class BankSyncAcceptedResponse(BaseModel):
    connection_id: UUID
    status: str = "QUEUED"


class BankOperationsResponse(BaseModel):
    profile_id: UUID
    healthy_connections: int
    degraded_connections: int
    pending_events: int
    failed_events: int
    dead_letter_events: int
    retry_limit: int = 5
    notes: list[str]


class ConnectTokenResponse(BaseModel):
    connection: BankConnectionResponse
    connect_token: str
    expires_in_seconds: int


class BankConnectionCallback(BaseModel):
    item_id: str = Field(min_length=8, max_length=64)


class PluggyWebhookPayload(BaseModel):
    event: str = Field(min_length=3, max_length=80)
    event_id: str = Field(alias="eventId", min_length=8, max_length=64)
    client_user_id: str | None = Field(default=None, alias="clientUserId")
    item_id: str | None = Field(default=None, alias="itemId")
