from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.debts.models import AmortizationSystem, Debt, DebtStatus
from app.modules.debts.schemas import (
    DebtCreate,
    DebtSimulationRequest,
    DebtSimulationResult,
    DebtStrategyResponse,
)
from app.modules.identity.models import FinancialProfile, User

CENT = Decimal("0.01")
MAX_MONTHS = 600


@dataclass(frozen=True)
class ScheduleTotals:
    months: int
    interest: Decimal
    paid: Decimal


def price_payment(principal: Decimal, monthly_rate: Decimal, months: int) -> Decimal:
    if months <= 0:
        return principal
    if monthly_rate == 0:
        return (principal / months).quantize(CENT, rounding=ROUND_HALF_UP)
    factor = (Decimal("1") + monthly_rate) ** months
    return (principal * monthly_rate * factor / (factor - Decimal("1"))).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def amortization_schedule(
    principal: Decimal,
    annual_rate_percent: Decimal | None,
    months: int,
    system: AmortizationSystem,
    *,
    monthly_payment: Decimal | None = None,
    one_time_extra: Decimal = Decimal("0"),
    recurring_extra: Decimal = Decimal("0"),
) -> ScheduleTotals:
    balance = principal
    monthly_rate = (annual_rate_percent or Decimal("0")) / Decimal("1200")
    fixed_payment = (
        monthly_payment or price_payment(principal, monthly_rate, months)
        if system != AmortizationSystem.SAC
        else None
    )
    sac_principal = principal / months
    total_interest = Decimal("0")
    total_paid = Decimal("0")
    count = 0
    while balance > Decimal("0.005") and count < MAX_MONTHS:
        count += 1
        interest = balance * monthly_rate
        if system == AmortizationSystem.SAC:
            regular_principal = min(balance, sac_principal)
        else:
            payment = fixed_payment or balance
            regular_principal = max(Decimal("0"), payment - interest)
            if regular_principal <= 0:
                raise ValueError("Monthly payment does not cover interest.")
            regular_principal = min(balance, regular_principal)
        extra = recurring_extra + (one_time_extra if count == 1 else Decimal("0"))
        principal_paid = min(balance, regular_principal + extra)
        paid = interest + principal_paid
        balance -= principal_paid
        total_interest += interest
        total_paid += paid
    if balance > Decimal("0.005"):
        raise ValueError("Debt does not amortize within the supported horizon.")
    return ScheduleTotals(
        months=count,
        interest=total_interest.quantize(CENT, rounding=ROUND_HALF_UP),
        paid=total_paid.quantize(CENT, rounding=ROUND_HALF_UP),
    )


async def create_debt(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: DebtCreate,
) -> Debt:
    quality = (
        "COMPLETE"
        if payload.annual_interest_rate is not None
        and payload.amortization_system != AmortizationSystem.UNKNOWN
        else "ESTIMATED"
    )
    debt = Debt(
        user_id=user.id,
        financial_profile_id=profile.id,
        data_quality=quality,
        **payload.model_dump(),
    )
    db.add(debt)
    await db.flush()
    return debt


async def list_debts(db: AsyncSession, user_id: UUID, profile_id: UUID) -> list[Debt]:
    return list(
        await db.scalars(
            select(Debt)
            .where(
                Debt.user_id == user_id,
                Debt.financial_profile_id == profile_id,
                Debt.status == DebtStatus.ACTIVE,
            )
            .order_by(Debt.outstanding_balance)
        )
    )


async def get_owned_debt(db: AsyncSession, user_id: UUID, debt_id: UUID) -> Debt | None:
    return cast(
        Debt | None,
        await db.scalar(select(Debt).where(Debt.id == debt_id, Debt.user_id == user_id)),
    )


def simulate_debt(debt: Debt, payload: DebtSimulationRequest) -> DebtSimulationResult:
    baseline = amortization_schedule(
        debt.outstanding_balance,
        debt.annual_interest_rate,
        debt.installments_remaining,
        debt.amortization_system,
        monthly_payment=debt.monthly_payment,
    )
    proposed = amortization_schedule(
        debt.outstanding_balance,
        debt.annual_interest_rate,
        debt.installments_remaining,
        debt.amortization_system,
        monthly_payment=debt.monthly_payment,
        one_time_extra=payload.one_time_extra,
        recurring_extra=payload.recurring_extra,
    )
    exact = (
        debt.annual_interest_rate is not None
        and debt.amortization_system != AmortizationSystem.UNKNOWN
    )
    assumptions = []
    if debt.annual_interest_rate is None:
        assumptions.append("Taxa ausente: cálculo usa 0% e é apenas ilustrativo.")
    if debt.amortization_system == AmortizationSystem.UNKNOWN:
        assumptions.append("Sistema desconhecido: aproximação por parcela constante.")
    if debt.annual_cet_rate is None:
        assumptions.append("CET não informado; seguros e tarifas podem não estar incluídos.")
    return DebtSimulationResult(
        debt_id=debt.id,
        system=debt.amortization_system,
        exact=exact,
        months=proposed.months,
        total_interest=proposed.interest,
        total_paid=proposed.paid,
        months_saved=max(0, baseline.months - proposed.months),
        interest_saved=max(Decimal("0"), baseline.interest - proposed.interest),
        assumptions=assumptions,
    )


def debt_strategy(debts: list[Debt], strategy: str) -> DebtStrategyResponse:
    if strategy == "SNOWBALL":
        ordered = sorted(debts, key=lambda item: (item.outstanding_balance, item.name))
        rationale = "Menores saldos primeiro para acelerar quitações visíveis."
    elif strategy == "AVALANCHE":
        ordered = sorted(
            debts,
            key=lambda item: (
                item.annual_interest_rate is None,
                -(item.annual_interest_rate or Decimal("0")),
                item.outstanding_balance,
            ),
        )
        rationale = (
            "Maiores taxas conhecidas primeiro para reduzir juros; taxas ausentes ficam ao final."
        )
    else:
        raise ValueError("Unknown debt strategy.")
    return DebtStrategyResponse(
        strategy=strategy,
        ordered_debt_ids=[item.id for item in ordered],
        ordered_names=[item.name for item in ordered],
        rationale=rationale,
    )
