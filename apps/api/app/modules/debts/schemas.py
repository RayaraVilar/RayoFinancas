from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.debts.models import AmortizationSystem, DebtStatus


class DebtCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    original_principal: Decimal = Field(gt=0, decimal_places=2, max_digits=19)
    outstanding_balance: Decimal = Field(gt=0, decimal_places=2, max_digits=19)
    annual_interest_rate: Decimal | None = Field(default=None, ge=0, le=1000)
    annual_cet_rate: Decimal | None = Field(default=None, ge=0, le=1000)
    amortization_system: AmortizationSystem
    installments_remaining: int = Field(ge=1, le=600)
    monthly_payment: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    next_due_on: date | None = None

    @model_validator(mode="after")
    def validate_balance(self) -> DebtCreate:
        if self.outstanding_balance > self.original_principal * 10:
            raise ValueError("Outstanding balance is outside the supported range.")
        return self


class DebtResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    original_principal: Decimal
    outstanding_balance: Decimal
    annual_interest_rate: Decimal | None
    annual_cet_rate: Decimal | None
    amortization_system: AmortizationSystem
    installments_remaining: int
    monthly_payment: Decimal | None
    next_due_on: date | None
    status: DebtStatus
    data_quality: str
    version: int


class DebtSimulationRequest(BaseModel):
    one_time_extra: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    recurring_extra: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)


class DebtSimulationResult(BaseModel):
    debt_id: UUID
    system: AmortizationSystem
    exact: bool
    months: int
    total_interest: Decimal
    total_paid: Decimal
    months_saved: int
    interest_saved: Decimal
    assumptions: list[str]


class DebtStrategyResponse(BaseModel):
    strategy: str
    ordered_debt_ids: list[UUID]
    ordered_names: list[str]
    rationale: str
