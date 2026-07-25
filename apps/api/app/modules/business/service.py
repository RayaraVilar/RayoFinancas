from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.business.models import (
    Receivable,
    ReceivableStatus,
    Subscription,
)
from app.modules.business.schemas import (
    BusinessCashflowResponse,
    CalendarDay,
    ReceivableCreate,
    SubscriptionCreate,
    SubscriptionResponse,
)
from app.modules.identity.models import FinancialAccount, FinancialProfile, RecordStatus, User
from app.modules.planning.models import Bill, BillStatus


def normalized_key(value: str) -> str:
    normalized = " ".join(re.sub(r"[^\w\s]", " ", value.casefold()).split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def receivable_dedupe(
    profile_id: UUID,
    description: str,
    amount: Decimal,
    due_on: date,
) -> str:
    raw = f"{profile_id}|{normalized_key(description)}|{amount:.2f}|{due_on.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_receivable(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: ReceivableCreate,
) -> Receivable:
    key = receivable_dedupe(
        profile.id,
        payload.description,
        payload.amount,
        payload.due_on,
    )
    existing = await db.scalar(
        select(Receivable).where(
            Receivable.financial_profile_id == profile.id,
            Receivable.dedupe_key == key,
        )
    )
    if existing:
        return existing
    item = Receivable(
        user_id=user.id,
        financial_profile_id=profile.id,
        source="MANUAL",
        dedupe_key=key,
        **payload.model_dump(),
    )
    db.add(item)
    await db.flush()
    return item


async def list_receivables(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
) -> list[Receivable]:
    return list(
        await db.scalars(
            select(Receivable)
            .where(
                Receivable.user_id == user_id,
                Receivable.financial_profile_id == profile_id,
                Receivable.status == ReceivableStatus.EXPECTED,
            )
            .order_by(Receivable.due_on)
        )
    )


def subscription_response(item: Subscription) -> SubscriptionResponse:
    annualized = item.amount * Decimal(12) / item.cadence_months
    return SubscriptionResponse(
        id=item.id,
        name=item.name,
        amount=item.amount,
        cadence_months=item.cadence_months,
        next_charge_on=item.next_charge_on,
        status=item.status,
        annualized_amount=annualized,
        version=item.version,
    )


async def create_subscription_candidate(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: SubscriptionCreate,
) -> Subscription:
    key = normalized_key(payload.name)
    existing = await db.scalar(
        select(Subscription).where(
            Subscription.financial_profile_id == profile.id,
            Subscription.merchant_key == key,
        )
    )
    if existing:
        return existing
    item = Subscription(
        user_id=user.id,
        financial_profile_id=profile.id,
        merchant_key=key,
        **payload.model_dump(),
    )
    db.add(item)
    await db.flush()
    return item


async def business_cashflow(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    start: date,
    end: date,
) -> BusinessCashflowResponse:
    accounts = await db.scalars(
        select(FinancialAccount).where(
            FinancialAccount.user_id == user_id,
            FinancialAccount.financial_profile_id == profile_id,
            FinancialAccount.status == RecordStatus.ACTIVE,
        )
    )
    opening = sum((item.current_balance for item in accounts), Decimal("0"))
    bills = list(
        await db.scalars(
            select(Bill).where(
                Bill.user_id == user_id,
                Bill.financial_profile_id == profile_id,
                Bill.status == BillStatus.CONFIRMED,
                Bill.due_on >= start,
                Bill.due_on <= end,
            )
        )
    )
    receivables = list(
        await db.scalars(
            select(Receivable).where(
                Receivable.user_id == user_id,
                Receivable.financial_profile_id == profile_id,
                Receivable.status == ReceivableStatus.EXPECTED,
                Receivable.confirmed.is_(True),
                Receivable.due_on >= start,
                Receivable.due_on <= end,
            )
        )
    )
    payable_by_day: dict[date, Decimal] = defaultdict(Decimal)
    receivable_by_day: dict[date, Decimal] = defaultdict(Decimal)
    for bill in bills:
        payable_by_day[bill.due_on] += bill.amount
    for receivable_item in receivables:
        receivable_by_day[receivable_item.due_on] += receivable_item.amount
    event_days = sorted(set(payable_by_day) | set(receivable_by_day))
    running = opening
    days = []
    for event_day in event_days:
        payable = payable_by_day[event_day]
        receivable = receivable_by_day[event_day]
        running += receivable - payable
        days.append(
            CalendarDay(
                date=event_day,
                payable=payable,
                receivable=receivable,
                projected_balance=running,
                confidence="CONFIRMED_INPUTS",
            )
        )
    total_payable = sum(payable_by_day.values(), Decimal("0"))
    total_receivable = sum(receivable_by_day.values(), Decimal("0"))
    return BusinessCashflowResponse(
        opening_balance=opening,
        total_payable=total_payable,
        total_receivable_confirmed=total_receivable,
        working_capital_at_horizon=opening + total_receivable - total_payable,
        days=days,
        notes=[
            "Somente recebíveis confirmados entram na projeção.",
            "O calendário não substitui contabilidade ou ERP.",
            "Itens de email jamais são aceitos automaticamente.",
        ],
    )
