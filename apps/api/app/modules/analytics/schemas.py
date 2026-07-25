from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class MetricValue(BaseModel):
    value: Decimal
    previous_equivalent: Decimal | None
    change_percent: Decimal | None


class CategoryExpense(BaseModel):
    category: str
    color: str
    amount: Decimal
    share_percent: Decimal


class RecurringExpense(BaseModel):
    description: str
    average_amount: Decimal
    occurrences: int


class AnalyticsCoverage(BaseModel):
    transaction_count: int
    categorized_percent: Decimal
    latest_sync_at: datetime | None
    freshness: str
    confidence: str


class DashboardAnalyticsResponse(BaseModel):
    contract_version: str = "2026-07-24.v1"
    period_start: date
    period_end: date
    equivalent_previous_start: date
    equivalent_previous_end: date
    income: MetricValue
    expense: MetricValue
    monthly_balance: MetricValue
    savings_rate_percent: Decimal | None
    net_worth: Decimal
    projected_month_expense: Decimal
    projected_month_balance: Decimal
    categories: list[CategoryExpense]
    recurring_expenses: list[RecurringExpense]
    coverage: AnalyticsCoverage
    calculation_notes: list[str]
