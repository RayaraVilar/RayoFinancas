from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import FinancialAccount, FinancialProfile, RecordStatus, User
from app.modules.identity.service import record_audit_event
from app.modules.ledger.models import (
    CardInvoice,
    CardInvoiceStatus,
    Category,
    Transaction,
    TransactionKind,
    TransactionStatus,
)
from app.modules.planning.models import (
    Bill,
    BillSource,
    BillStatus,
    MonthlyBudget,
    MonthlyPlan,
)
from app.modules.planning.schemas import (
    BillCreate,
    BillTransition,
    BudgetProgress,
    BudgetUpsert,
    FreeBalanceComponent,
    MonthlyPlanResponse,
    MonthlyPlanUpsert,
    PlanningSummaryResponse,
)

CENT = Decimal("0.01")


def bill_dedupe_key(
    profile_id: UUID,
    source: BillSource,
    description: str,
    amount: Decimal,
    due_on: date,
    external_id: str | None = None,
) -> str:
    normalized = " ".join(re.sub(r"[^\w\s]", " ", description.casefold()).split())
    identity = external_id or f"{normalized}|{amount.quantize(CENT)}|{due_on.isoformat()}"
    return hashlib.sha256(f"{profile_id}|{source.value}|{identity}".encode()).hexdigest()


async def list_bills(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    *,
    include_closed: bool = False,
) -> list[Bill]:
    filters = [Bill.user_id == user_id, Bill.financial_profile_id == profile_id]
    if not include_closed:
        filters.append(Bill.status.not_in({BillStatus.PAID, BillStatus.DISMISSED}))
    return list(await db.scalars(select(Bill).where(*filters).order_by(Bill.due_on, Bill.id)))


async def create_manual_bill(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: BillCreate,
    correlation_id: str | None,
) -> Bill:
    key = bill_dedupe_key(
        profile.id,
        BillSource.MANUAL,
        payload.description,
        payload.amount,
        payload.due_on,
    )
    existing = await db.scalar(
        select(Bill).where(
            Bill.financial_profile_id == profile.id,
            Bill.dedupe_key == key,
        )
    )
    if existing:
        return existing
    near = await db.scalar(
        select(Bill).where(
            Bill.financial_profile_id == profile.id,
            Bill.amount == payload.amount,
            Bill.due_on >= payload.due_on - timedelta(days=3),
            Bill.due_on <= payload.due_on + timedelta(days=3),
            Bill.status.not_in({BillStatus.DISMISSED}),
        )
    )
    bill = Bill(
        user_id=user.id,
        financial_profile_id=profile.id,
        source=BillSource.MANUAL,
        dedupe_key=key,
        possible_duplicate_of_id=near.id if near else None,
        description=payload.description,
        amount=payload.amount,
        due_on=payload.due_on,
        status=BillStatus.REVIEW_REQUIRED if near else BillStatus.DRAFT,
    )
    db.add(bill)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="bill.created",
        target_type="bill",
        target_id=bill.id,
        correlation_id=correlation_id,
        safe_metadata={"source": bill.source.value, "review": str(bool(near)).lower()},
    )
    return bill


async def transition_bill(
    db: AsyncSession,
    user: User,
    bill: Bill,
    payload: BillTransition,
    correlation_id: str | None,
) -> Bill:
    if bill.version != payload.version:
        raise ValueError("Bill changed; reload before confirming.")
    allowed = {
        BillStatus.DRAFT: {BillStatus.CONFIRMED, BillStatus.DISMISSED},
        BillStatus.REVIEW_REQUIRED: {BillStatus.CONFIRMED, BillStatus.DISMISSED},
        BillStatus.CONFIRMED: {BillStatus.PAID, BillStatus.DISMISSED},
        BillStatus.PAID: set(),
        BillStatus.DISMISSED: set(),
    }
    if payload.target_status not in allowed[bill.status]:
        raise ValueError("Invalid bill state transition.")
    if payload.target_status == BillStatus.PAID and payload.paid_on is None:
        raise ValueError("paid_on is required when marking a bill as paid.")
    bill.status = payload.target_status
    bill.paid_on = payload.paid_on if payload.target_status == BillStatus.PAID else None
    bill.version += 1
    await record_audit_event(
        db,
        user_id=user.id,
        action="bill.transitioned",
        target_type="bill",
        target_id=bill.id,
        correlation_id=correlation_id,
        safe_metadata={"status": bill.status.value},
    )
    return bill


async def get_owned_bill(
    db: AsyncSession,
    user_id: UUID,
    bill_id: UUID,
) -> Bill | None:
    return cast(
        Bill | None,
        await db.scalar(select(Bill).where(Bill.id == bill_id, Bill.user_id == user_id)),
    )


async def synchronize_invoice_bills(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
) -> None:
    invoices = await db.scalars(
        select(CardInvoice).where(
            CardInvoice.user_id == user_id,
            CardInvoice.financial_profile_id == profile_id,
            CardInvoice.status.in_({CardInvoiceStatus.OPEN, CardInvoiceStatus.CLOSED}),
        )
    )
    for invoice in invoices:
        transaction_amounts = await db.scalars(
            select(Transaction.amount).where(
                Transaction.card_invoice_id == invoice.id,
                Transaction.status == TransactionStatus.POSTED,
                Transaction.kind == TransactionKind.EXPENSE,
            )
        )
        amount = sum(transaction_amounts, Decimal("0"))
        if amount <= 0:
            continue
        external_id = str(invoice.id)
        key = bill_dedupe_key(
            profile_id,
            BillSource.CARD_INVOICE,
            "Fatura de cartão",
            amount,
            invoice.due_on,
            external_id,
        )
        bill = await db.scalar(
            select(Bill).where(
                Bill.financial_profile_id == profile_id,
                Bill.dedupe_key == key,
            )
        )
        if bill is None:
            bill = Bill(
                user_id=user_id,
                financial_profile_id=profile_id,
                source=BillSource.CARD_INVOICE,
                external_id=external_id,
                dedupe_key=key,
                description="Fatura de cartão",
                amount=amount,
                due_on=invoice.due_on,
                status=BillStatus.CONFIRMED,
            )
            db.add(bill)
        else:
            bill.amount = amount
            bill.due_on = invoice.due_on


async def upsert_budget(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: BudgetUpsert,
) -> MonthlyBudget:
    category = await db.scalar(
        select(Category).where(
            Category.id == payload.category_id,
            (Category.financial_profile_id == profile.id)
            | (Category.financial_profile_id.is_(None)),
        )
    )
    if category is None:
        raise ValueError("Category not found.")
    budget = await db.scalar(
        select(MonthlyBudget).where(
            MonthlyBudget.financial_profile_id == profile.id,
            MonthlyBudget.category_id == payload.category_id,
            MonthlyBudget.competence_month == payload.competence_month,
        )
    )
    if budget is None:
        budget = MonthlyBudget(
            user_id=user.id,
            financial_profile_id=profile.id,
            category_id=payload.category_id,
            competence_month=payload.competence_month,
            limit_amount=payload.limit_amount,
        )
        db.add(budget)
    else:
        budget.limit_amount = payload.limit_amount
        budget.version += 1
    await db.flush()
    return budget


async def upsert_monthly_plan(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: MonthlyPlanUpsert,
) -> MonthlyPlan:
    plan = await db.scalar(
        select(MonthlyPlan).where(
            MonthlyPlan.financial_profile_id == profile.id,
            MonthlyPlan.competence_month == payload.competence_month,
        )
    )
    values = payload.model_dump()
    if plan is None:
        plan = MonthlyPlan(
            user_id=user.id,
            financial_profile_id=profile.id,
            **values,
        )
        db.add(plan)
    else:
        for key, value in values.items():
            setattr(plan, key, value)
        plan.version += 1
    await db.flush()
    return plan


async def budget_progress(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    as_of: date,
) -> list[BudgetProgress]:
    month = as_of.replace(day=1)
    rows = (
        await db.execute(
            select(MonthlyBudget, Category)
            .join(Category, Category.id == MonthlyBudget.category_id)
            .where(
                MonthlyBudget.user_id == user_id,
                MonthlyBudget.financial_profile_id == profile_id,
                MonthlyBudget.competence_month == month,
            )
        )
    ).all()
    result = []
    for budget, category in rows:
        amounts = await db.scalars(
            select(Transaction.amount).where(
                Transaction.user_id == user_id,
                Transaction.financial_profile_id == profile_id,
                Transaction.category_id == budget.category_id,
                Transaction.kind == TransactionKind.EXPENSE,
                Transaction.status == TransactionStatus.POSTED,
                Transaction.reversal_of_transaction_id.is_(None),
                Transaction.occurred_on >= month,
                Transaction.occurred_on <= as_of,
            )
        )
        consumed = sum(amounts, Decimal("0"))
        elapsed = max(1, as_of.day)
        next_month = month.replace(
            month=month.month % 12 + 1,
            year=month.year + (month.month == 12),
        )
        days = (next_month - month).days
        projected = consumed * Decimal(days) / Decimal(elapsed)
        consumed_percent = consumed * 100 / budget.limit_amount
        result.append(
            BudgetProgress(
                id=budget.id,
                category_id=budget.category_id,
                category_name=category.name,
                competence_month=month,
                limit_amount=budget.limit_amount,
                consumed_amount=consumed.quantize(CENT, rounding=ROUND_HALF_UP),
                projected_amount=projected.quantize(CENT, rounding=ROUND_HALF_UP),
                consumed_percent=consumed_percent.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
                pace_status="OVER" if projected > budget.limit_amount else "ON_TRACK",
                version=budget.version,
            )
        )
    return result


async def planning_summary(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    as_of: date,
) -> PlanningSummaryResponse:
    horizon_end = (as_of.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    await synchronize_invoice_bills(db, user_id, profile_id)
    bills = await list_bills(db, user_id, profile_id)
    accounts = await db.scalars(
        select(FinancialAccount).where(
            FinancialAccount.user_id == user_id,
            FinancialAccount.financial_profile_id == profile_id,
            FinancialAccount.status == RecordStatus.ACTIVE,
        )
    )
    account_balance = sum((item.current_balance for item in accounts), Decimal("0"))
    confirmed = sum(
        (
            item.amount
            for item in bills
            if item.status == BillStatus.CONFIRMED and as_of <= item.due_on <= horizon_end
        ),
        Decimal("0"),
    )
    month = as_of.replace(day=1)
    plan = await db.scalar(
        select(MonthlyPlan).where(
            MonthlyPlan.user_id == user_id,
            MonthlyPlan.financial_profile_id == profile_id,
            MonthlyPlan.competence_month == month,
        )
    )
    planned_base = plan.essential_commitment + plan.debt_commitment if plan else Decimal("0")
    goal = plan.goal_contribution if plan else Decimal("0")
    planned_commitments = max(confirmed, planned_base) + goal
    free_balance = account_balance - planned_commitments
    budgets = await budget_progress(db, user_id, profile_id, as_of)
    return PlanningSummaryResponse(
        as_of=as_of,
        horizon_end=horizon_end,
        account_balance=account_balance,
        confirmed_bills=confirmed,
        planned_commitments=planned_commitments,
        free_balance=free_balance,
        projected_deficit=free_balance < 0,
        components=[
            FreeBalanceComponent(code="BALANCE", label="Saldo em contas", amount=account_balance),
            FreeBalanceComponent(code="BILLS", label="Compromissos confirmados", amount=-confirmed),
            FreeBalanceComponent(code="GOALS", label="Aporte planejado", amount=-goal),
        ],
        bills=bills,
        budgets=budgets,
        plan=MonthlyPlanResponse.model_validate(plan) if plan else None,
        calculation_notes=[
            "Limite de crédito e renda apenas prevista não entram no Saldo Livre.",
            "Entre plano e contas confirmadas, usamos o maior valor para evitar dupla contagem.",
            "O horizonte termina no último dia do mês selecionado.",
        ],
    )
