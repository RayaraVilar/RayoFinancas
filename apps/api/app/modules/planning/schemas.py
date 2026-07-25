from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.planning.models import BillSource, BillStatus


class BillCreate(BaseModel):
    description: str = Field(min_length=2, max_length=160)
    amount: Decimal = Field(gt=0, decimal_places=2, max_digits=19)
    due_on: date


class BillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    source: BillSource
    possible_duplicate_of_id: UUID | None
    description: str
    amount: Decimal
    due_on: date
    status: BillStatus
    paid_on: date | None
    version: int
    created_at: datetime


class BillTransition(BaseModel):
    target_status: BillStatus
    version: int = Field(ge=1)
    paid_on: date | None = None


class BudgetUpsert(BaseModel):
    category_id: UUID
    competence_month: date
    limit_amount: Decimal = Field(gt=0, decimal_places=2, max_digits=19)

    @model_validator(mode="after")
    def validate_month(self) -> BudgetUpsert:
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of the month.")
        return self


class BudgetProgress(BaseModel):
    id: UUID
    category_id: UUID
    category_name: str
    competence_month: date
    limit_amount: Decimal
    consumed_amount: Decimal
    projected_amount: Decimal
    consumed_percent: Decimal
    pace_status: str
    version: int


class MonthlyPlanUpsert(BaseModel):
    competence_month: date
    expected_income: Decimal = Field(ge=0, decimal_places=2, max_digits=19)
    essential_commitment: Decimal = Field(ge=0, decimal_places=2, max_digits=19)
    debt_commitment: Decimal = Field(ge=0, decimal_places=2, max_digits=19)
    goal_contribution: Decimal = Field(ge=0, decimal_places=2, max_digits=19)

    @model_validator(mode="after")
    def validate_month(self) -> MonthlyPlanUpsert:
        if self.competence_month.day != 1:
            raise ValueError("competence_month must be the first day of the month.")
        return self


class MonthlyPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    competence_month: date
    expected_income: Decimal
    essential_commitment: Decimal
    debt_commitment: Decimal
    goal_contribution: Decimal
    version: int


class FreeBalanceComponent(BaseModel):
    code: str
    label: str
    amount: Decimal


class PlanningSummaryResponse(BaseModel):
    contract_version: str = "2026-07-24.v1"
    as_of: date
    horizon_end: date
    account_balance: Decimal
    confirmed_bills: Decimal
    planned_commitments: Decimal
    free_balance: Decimal
    projected_deficit: bool
    components: list[FreeBalanceComponent]
    bills: list[BillResponse]
    budgets: list[BudgetProgress]
    plan: MonthlyPlanResponse | None
    calculation_notes: list[str]
