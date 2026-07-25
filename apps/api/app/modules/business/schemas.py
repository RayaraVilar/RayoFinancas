from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.business.models import (
    InboxReviewStatus,
    ReceivableStatus,
    SubscriptionStatus,
)


class ReceivableCreate(BaseModel):
    description: str = Field(min_length=2, max_length=160)
    counterparty: str | None = Field(default=None, max_length=120)
    amount: Decimal = Field(gt=0, decimal_places=2, max_digits=19)
    due_on: date
    confirmed: bool = True


class ReceivableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    counterparty: str | None
    amount: Decimal
    due_on: date
    status: ReceivableStatus
    confirmed: bool
    received_on: date | None
    version: int


class ReceivableTransition(BaseModel):
    target_status: ReceivableStatus
    version: int = Field(ge=1)
    received_on: date | None = None


class SubscriptionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    amount: Decimal = Field(gt=0, decimal_places=2)
    cadence_months: int = Field(default=1, ge=1, le=12)
    next_charge_on: date


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    amount: Decimal
    cadence_months: int
    next_charge_on: date
    status: SubscriptionStatus
    annualized_amount: Decimal
    version: int


class CalendarDay(BaseModel):
    date: date
    payable: Decimal
    receivable: Decimal
    projected_balance: Decimal
    confidence: str


class BusinessCashflowResponse(BaseModel):
    opening_balance: Decimal
    total_payable: Decimal
    total_receivable_confirmed: Decimal
    working_capital_at_horizon: Decimal
    days: list[CalendarDay]
    notes: list[str]


class GmailCapabilityResponse(BaseModel):
    configured: bool = False
    consent_separate: bool = True
    ingestion_enabled: bool = False
    status: str = "DESIGN_ONLY"
    warning: str = "Conteúdo de email é não confiável e sempre exigirá revisão humana."


class InboxCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    source: str
    extracted_fields: dict[str, object]
    risk_flags: list[str]
    status: InboxReviewStatus
    created_at: datetime


class InboxReviewUpdate(BaseModel):
    status: InboxReviewStatus


class NotificationPreferenceUpsert(BaseModel):
    channel: str = Field(min_length=2, max_length=24)
    enabled: bool
    event_types: list[str] = Field(max_length=20)
    quiet_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: str
    enabled: bool
    event_types: list[str]
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    updated_at: datetime
