from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.goals.models import GoalStatus, PendingActionStatus


class GoalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    target_amount: Decimal = Field(gt=0, decimal_places=2, max_digits=19)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    target_date: date
    monthly_contribution: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    priority: int = Field(default=100, ge=1, le=1000)


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    monthly_contribution: Decimal
    priority: int
    status: GoalStatus
    version: int
    progress_percent: Decimal
    remaining_amount: Decimal
    months_remaining: int
    required_monthly_contribution: Decimal
    pace_status: str


class ContributionCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2, max_digits=19)
    contributed_on: date
    idempotency_key: str = Field(min_length=8, max_length=64)


class GoalScenarioRequest(BaseModel):
    monthly_contribution: Decimal = Field(ge=0, decimal_places=2, max_digits=19)
    target_date: date
    idempotency_key: str = Field(min_length=8, max_length=64)


class ScenarioResult(BaseModel):
    name: str
    monthly_contribution: Decimal
    target_date: date
    months_to_target: int | None
    projected_amount_at_target: Decimal
    reaches_target: bool


class PendingActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_type: str
    target_id: UUID
    target_version: int
    status: PendingActionStatus
    before_state: dict[str, object]
    after_state: dict[str, object]
    expires_at: datetime


class GoalScenarioResponse(BaseModel):
    scenarios: list[ScenarioResult]
    pending_action: PendingActionResponse
