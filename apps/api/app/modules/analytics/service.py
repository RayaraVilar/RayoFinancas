from __future__ import annotations

import calendar
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.schemas import (
    AnalyticsCoverage,
    CategoryExpense,
    DashboardAnalyticsResponse,
    MetricValue,
    RecurringExpense,
)
from app.modules.banking.models import BankConnection, BankConnectionStatus
from app.modules.identity.models import FinancialAccount, RecordStatus
from app.modules.ledger.models import (
    Category,
    Transaction,
    TransactionKind,
    TransactionSplit,
    TransactionStatus,
)

CENT = Decimal("0.01")
PERCENT = Decimal("0.1")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def percent(value: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0.0")
    return (value * 100 / total).quantize(PERCENT, rounding=ROUND_HALF_UP)


def month_bounds(as_of: date) -> tuple[date, date]:
    start = as_of.replace(day=1)
    end = as_of.replace(day=calendar.monthrange(as_of.year, as_of.month)[1])
    return start, end


def previous_equivalent_bounds(as_of: date) -> tuple[date, date]:
    current_start, _ = month_bounds(as_of)
    previous_month_end = current_start - timedelta(days=1)
    previous_start = previous_month_end.replace(day=1)
    elapsed_days = (as_of - current_start).days
    return previous_start, min(
        previous_start + timedelta(days=elapsed_days),
        previous_month_end,
    )


def change_percent(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return ((current - previous) * 100 / abs(previous)).quantize(
        PERCENT,
        rounding=ROUND_HALF_UP,
    )


def metric(current: Decimal, previous: Decimal) -> MetricValue:
    return MetricValue(
        value=quantize_money(current),
        previous_equivalent=quantize_money(previous),
        change_percent=change_percent(current, previous),
    )


def normalized_description(value: str) -> str:
    value = re.sub(r"\d+", "", value.casefold())
    return " ".join(value.split())[:80]


def effective_amount(
    transaction: Transaction,
    originals: dict[UUID, TransactionKind],
    target_kind: TransactionKind,
) -> Decimal:
    if transaction.kind == TransactionKind.TRANSFER:
        return Decimal("0")
    if transaction.reversal_of_transaction_id is None:
        return transaction.amount if transaction.kind == target_kind else Decimal("0")
    return (
        -transaction.amount
        if originals.get(transaction.reversal_of_transaction_id) == target_kind
        else Decimal("0")
    )


async def calculate_dashboard_analytics(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID | None,
    as_of: date,
) -> DashboardAnalyticsResponse:
    period_start, period_month_end = month_bounds(as_of)
    previous_start, previous_end = previous_equivalent_bounds(as_of)
    filters = [
        Transaction.user_id == user_id,
        Transaction.status == TransactionStatus.POSTED,
        Transaction.occurred_on >= previous_start,
        Transaction.occurred_on <= as_of,
    ]
    if profile_id:
        filters.append(Transaction.financial_profile_id == profile_id)
    transactions = list(await db.scalars(select(Transaction).where(*filters)))
    original_ids = [
        item.reversal_of_transaction_id
        for item in transactions
        if item.reversal_of_transaction_id is not None
    ]
    original_rows = (
        list(await db.scalars(select(Transaction).where(Transaction.id.in_(original_ids))))
        if original_ids
        else []
    )
    originals = {item.id: item.kind for item in original_rows}

    def totals(start: date, end: date) -> tuple[Decimal, Decimal]:
        rows = [item for item in transactions if start <= item.occurred_on <= end]
        income = sum(
            (effective_amount(item, originals, TransactionKind.INCOME) for item in rows),
            Decimal("0"),
        )
        expense = sum(
            (effective_amount(item, originals, TransactionKind.EXPENSE) for item in rows),
            Decimal("0"),
        )
        return income, expense

    income, expense = totals(period_start, as_of)
    previous_income, previous_expense = totals(previous_start, previous_end)
    monthly_balance = income - expense
    previous_balance = previous_income - previous_expense
    elapsed = max(1, (as_of - period_start).days + 1)
    days_in_month = period_month_end.day
    projected_expense = expense * Decimal(days_in_month) / Decimal(elapsed)
    projected_balance = income - projected_expense

    current_expenses = [
        item
        for item in transactions
        if period_start <= item.occurred_on <= as_of
        and effective_amount(item, originals, TransactionKind.EXPENSE) != 0
    ]
    transaction_ids = [item.id for item in current_expenses]
    split_rows = (
        list(
            await db.scalars(
                select(TransactionSplit).where(TransactionSplit.transaction_id.in_(transaction_ids))
            )
        )
        if transaction_ids
        else []
    )
    splits_by_transaction: dict[UUID, list[TransactionSplit]] = defaultdict(list)
    for split in split_rows:
        splits_by_transaction[split.transaction_id].append(split)
    category_ids = {split.category_id for split in split_rows} | {
        item.category_id for item in current_expenses if item.category_id
    }
    categories = (
        list(await db.scalars(select(Category).where(Category.id.in_(category_ids))))
        if category_ids
        else []
    )
    category_map = {item.id: item for item in categories}
    category_totals: dict[UUID | None, Decimal] = defaultdict(Decimal)
    for item in current_expenses:
        sign = Decimal("-1") if item.reversal_of_transaction_id else Decimal("1")
        if splits_by_transaction[item.id]:
            for split in splits_by_transaction[item.id]:
                category_totals[split.category_id] += sign * split.amount
        else:
            category_totals[item.category_id] += sign * item.amount
    category_items = []
    for category_id, amount in sorted(
        category_totals.items(),
        key=lambda row: row[1],
        reverse=True,
    ):
        category = category_map.get(category_id) if category_id else None
        category_items.append(
            CategoryExpense(
                category=category.name if category else "Sem categoria",
                color=category.color if category else "#A7B0AB",
                amount=quantize_money(amount),
                share_percent=percent(amount, expense),
            )
        )

    recurring_groups: dict[str, list[Transaction]] = defaultdict(list)
    recurring_start = period_start - timedelta(days=93)
    recurring_filters = [
        Transaction.user_id == user_id,
        Transaction.status == TransactionStatus.POSTED,
        Transaction.kind == TransactionKind.EXPENSE,
        Transaction.reversal_of_transaction_id.is_(None),
        Transaction.occurred_on >= recurring_start,
        Transaction.occurred_on <= as_of,
    ]
    if profile_id:
        recurring_filters.append(Transaction.financial_profile_id == profile_id)
    for item in await db.scalars(select(Transaction).where(*recurring_filters)):
        recurring_groups[normalized_description(item.description)].append(item)
    recurring = []
    for description, items in recurring_groups.items():
        distinct_months = {item.competence_month for item in items}
        if len(distinct_months) < 2:
            continue
        average = sum((item.amount for item in items), Decimal("0")) / len(items)
        recurring.append(
            RecurringExpense(
                description=description.title(),
                average_amount=quantize_money(average),
                occurrences=len(items),
            )
        )
    recurring.sort(key=lambda item: item.average_amount, reverse=True)

    account_filters = [
        FinancialAccount.user_id == user_id,
        FinancialAccount.status == RecordStatus.ACTIVE,
    ]
    if profile_id:
        account_filters.append(FinancialAccount.financial_profile_id == profile_id)
    balances = await db.scalars(select(FinancialAccount).where(*account_filters))
    net_worth = sum((item.current_balance for item in balances), Decimal("0"))

    connection_filters = [
        BankConnection.user_id == user_id,
        BankConnection.status != BankConnectionStatus.REVOKED,
    ]
    if profile_id:
        connection_filters.append(BankConnection.financial_profile_id == profile_id)
    connections = list(await db.scalars(select(BankConnection).where(*connection_filters)))
    latest_sync = max(
        (item.last_synced_at for item in connections if item.last_synced_at),
        default=None,
    )
    now = datetime.now(UTC)
    if latest_sync is None:
        freshness = "MANUAL_OR_UNKNOWN"
    elif now - latest_sync <= timedelta(hours=24):
        freshness = "CURRENT"
    elif now - latest_sync <= timedelta(days=7):
        freshness = "STALE"
    else:
        freshness = "OUTDATED"
    categorized_count = sum(
        1
        for item in current_expenses
        if item.category_id is not None or splits_by_transaction[item.id]
    )
    categorized = percent(Decimal(categorized_count), Decimal(len(current_expenses)))
    confidence = (
        "HIGH"
        if len(current_expenses) >= 10 and categorized >= 80 and freshness != "OUTDATED"
        else "MEDIUM"
        if transactions
        else "LOW"
    )

    return DashboardAnalyticsResponse(
        period_start=period_start,
        period_end=as_of,
        equivalent_previous_start=previous_start,
        equivalent_previous_end=previous_end,
        income=metric(income, previous_income),
        expense=metric(expense, previous_expense),
        monthly_balance=metric(monthly_balance, previous_balance),
        savings_rate_percent=percent(max(Decimal("0"), monthly_balance), income)
        if income > 0
        else None,
        net_worth=quantize_money(net_worth),
        projected_month_expense=quantize_money(projected_expense),
        projected_month_balance=quantize_money(projected_balance),
        categories=category_items[:8],
        recurring_expenses=recurring[:5],
        coverage=AnalyticsCoverage(
            transaction_count=len(current_expenses),
            categorized_percent=categorized,
            latest_sync_at=latest_sync,
            freshness=freshness,
            confidence=confidence,
        ),
        calculation_notes=[
            "Transferências próprias e pagamentos de fatura são excluídos.",
            "Estornos vinculados compensam o tipo da movimentação original.",
            "A projeção usa o ritmo diário realizado até a data selecionada.",
            "Comparações usam o mesmo número de dias do mês anterior.",
        ],
    )
