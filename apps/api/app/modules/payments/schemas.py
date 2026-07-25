from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.payments.models import PaymentSimulationStatus


class PaymentSimulationCreate(BaseModel):
    bill_ids: list[UUID] = Field(min_length=1, max_length=50)
    idempotency_key: str = Field(min_length=8, max_length=64)


class AccountPaymentOption(BaseModel):
    account_id: UUID
    account_name: str
    balance_before: Decimal
    payment_amount: Decimal
    balance_after: Decimal
    free_balance_after: Decimal
    risk: str
    reasons: list[str]


class PaymentSimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    bill_ids: list[str]
    total_amount: Decimal
    account_options: list[dict[str, object]]
    input_hash: str
    snapshot_hash: str
    risk_version: str
    status: PaymentSimulationStatus
    expires_at: datetime
    created_at: datetime
    external_operations_count: int = 0
    warning: str = "Esta é apenas uma simulação. Nenhum pagamento ou transferência foi iniciado."


class PaymentCapabilityResponse(BaseModel):
    initiation_enabled: bool
    kill_switch_active: bool
    provider_configured: bool
    implementation_status: str
