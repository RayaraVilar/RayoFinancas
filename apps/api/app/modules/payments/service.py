from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import FinancialAccount, FinancialProfile, RecordStatus, User
from app.modules.payments.models import PaymentSimulation, PaymentSimulationStatus
from app.modules.payments.schemas import AccountPaymentOption, PaymentSimulationCreate
from app.modules.planning.models import Bill, BillStatus, MonthlyPlan

RISK_VERSION = "payment-risk-2026-07.v1"


def simulation_hash(payload: object) -> str:
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def payment_risk(balance_after: Decimal, free_balance_after: Decimal) -> tuple[str, list[str]]:
    reasons = []
    if balance_after < 0:
        reasons.append("A conta ficaria com saldo negativo.")
    if free_balance_after < 0:
        reasons.append("O Saldo Livre ficaria negativo após compromissos.")
    if reasons:
        return "HIGH", reasons
    if free_balance_after < balance_after * Decimal("0.2"):
        return "MEDIUM", ["A margem restante ficaria abaixo de 20% do saldo pós-pagamento."]
    return "LOW", ["A simulação preserva saldo e compromissos conhecidos."]


async def create_payment_simulation(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: PaymentSimulationCreate,
) -> PaymentSimulation:
    existing = await db.scalar(
        select(PaymentSimulation).where(
            PaymentSimulation.user_id == user.id,
            PaymentSimulation.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        return existing
    unique_bill_ids = sorted(set(payload.bill_ids), key=str)
    bills = list(
        await db.scalars(
            select(Bill).where(
                Bill.user_id == user.id,
                Bill.financial_profile_id == profile.id,
                Bill.id.in_(unique_bill_ids),
                Bill.status == BillStatus.CONFIRMED,
            )
        )
    )
    if len(bills) != len(unique_bill_ids):
        raise ValueError("Every bill must be confirmed and belong to the selected profile.")
    accounts = list(
        await db.scalars(
            select(FinancialAccount).where(
                FinancialAccount.user_id == user.id,
                FinancialAccount.financial_profile_id == profile.id,
                FinancialAccount.status == RecordStatus.ACTIVE,
            )
        )
    )
    if not accounts:
        raise ValueError("No eligible payer account in this profile.")
    total = sum((item.amount for item in bills), Decimal("0"))
    as_of = datetime.now(UTC).date()
    month = as_of.replace(day=1)
    plan = await db.scalar(
        select(MonthlyPlan).where(
            MonthlyPlan.user_id == user.id,
            MonthlyPlan.financial_profile_id == profile.id,
            MonthlyPlan.competence_month == month,
        )
    )
    known_other_commitments = (
        plan.essential_commitment + plan.debt_commitment + plan.goal_contribution
        if plan
        else Decimal("0")
    )
    options = []
    for account in accounts:
        balance_after = account.current_balance - total
        free_after = balance_after - known_other_commitments
        risk, reasons = payment_risk(balance_after, free_after)
        options.append(
            AccountPaymentOption(
                account_id=account.id,
                account_name=account.name,
                balance_before=account.current_balance,
                payment_amount=total,
                balance_after=balance_after,
                free_balance_after=free_after,
                risk=risk,
                reasons=reasons,
            )
        )
    inputs = {
        "profile_id": str(profile.id),
        "bill_ids": [str(item) for item in unique_bill_ids],
        "idempotency_key": payload.idempotency_key,
    }
    snapshot = {
        "bills": [
            {"id": str(item.id), "amount": str(item.amount), "version": item.version}
            for item in sorted(bills, key=lambda item: str(item.id))
        ],
        "accounts": [
            {"id": str(item.id), "balance": str(item.current_balance)}
            for item in sorted(accounts, key=lambda item: str(item.id))
        ],
        "plan_version": plan.version if plan else None,
        "as_of": as_of.isoformat(),
    }
    simulation = PaymentSimulation(
        user_id=user.id,
        financial_profile_id=profile.id,
        idempotency_key=payload.idempotency_key,
        bill_ids=[str(item) for item in unique_bill_ids],
        total_amount=total,
        account_options=[item.model_dump(mode="json") for item in options],
        input_hash=simulation_hash(inputs),
        snapshot_hash=simulation_hash(snapshot),
        risk_version=RISK_VERSION,
        status=PaymentSimulationStatus.ACTIVE,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db.add(simulation)
    await db.flush()
    return simulation
