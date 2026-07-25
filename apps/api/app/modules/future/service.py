from __future__ import annotations

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.service import calculate_dashboard_analytics
from app.modules.debts.models import Debt, DebtStatus
from app.modules.future.models import HealthScoreSnapshot, NetWorthSnapshot
from app.modules.future.schemas import (
    FutureResponse,
    HealthScoreResponse,
    HealthSubscore,
    ProjectionPoint,
)
from app.modules.goals.models import Goal, GoalStatus
from app.modules.identity.models import FinancialAccount, RecordStatus
from app.modules.planning.models import MonthlyBudget
from app.modules.planning.service import budget_progress

ALGORITHM_VERSION = "health-2026-07.v1"
PERCENT = Decimal("0.1")
CENT = Decimal("0.01")


def clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), value))


def cashflow_score(savings_rate: Decimal | None, balance: Decimal) -> Decimal | None:
    if savings_rate is None:
        return None
    if balance < 0:
        return Decimal("0")
    if savings_rate <= 10:
        return Decimal("30") + savings_rate * Decimal("3")
    if savings_rate <= 20:
        return Decimal("60") + (savings_rate - 10) * Decimal("2.5")
    return clamp(Decimal("85") + (savings_rate - 20) * Decimal("1.5"))


def reserve_score(months: Decimal | None) -> Decimal | None:
    if months is None:
        return None
    if months <= 1:
        return clamp(months * Decimal("35"))
    if months <= 3:
        return Decimal("35") + (months - 1) * Decimal("17.5")
    return clamp(Decimal("70") + (months - 3) * Decimal("10"))


def add_months(value: date, months: int) -> date:
    target_month = value.month - 1 + months
    year = value.year + target_month // 12
    month = target_month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def weighted_health_score(subscores: list[HealthSubscore]) -> HealthScoreResponse:
    available = [item for item in subscores if item.score is not None]
    available_weight = sum(item.weight for item in available)
    score = (
        sum(
            ((item.score or Decimal("0")) * item.weight for item in available),
            Decimal("0"),
        )
        / available_weight
        if available_weight
        else None
    )
    return HealthScoreResponse(
        algorithm_version=ALGORITHM_VERSION,
        score=score.quantize(PERCENT, rounding=ROUND_HALF_UP) if score is not None else None,
        confidence_percent=Decimal(available_weight).quantize(PERCENT),
        sufficient_data=available_weight >= 60,
        disclaimer=(
            "Índice educativo de hábitos e resiliência observáveis; "
            "não é score de crédito, diagnóstico ou recomendação de investimento."
        ),
        subscores=subscores,
    )


async def calculate_future(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    as_of: date,
    assumed_monthly_savings: Decimal | None,
    custom_months: int | None,
) -> FutureResponse:
    analytics = await calculate_dashboard_analytics(
        db,
        user_id,
        profile_id,
        as_of,
    )
    accounts = list(
        await db.scalars(
            select(FinancialAccount).where(
                FinancialAccount.user_id == user_id,
                FinancialAccount.financial_profile_id == profile_id,
                FinancialAccount.status == RecordStatus.ACTIVE,
            )
        )
    )
    debts = list(
        await db.scalars(
            select(Debt).where(
                Debt.user_id == user_id,
                Debt.financial_profile_id == profile_id,
                Debt.status == DebtStatus.ACTIVE,
            )
        )
    )
    goals = list(
        await db.scalars(
            select(Goal).where(
                Goal.user_id == user_id,
                Goal.financial_profile_id == profile_id,
                Goal.status == GoalStatus.ACTIVE,
            )
        )
    )
    assets = sum((item.current_balance for item in accounts), Decimal("0"))
    liabilities = sum((item.outstanding_balance for item in debts), Decimal("0"))
    net_worth = assets - liabilities
    monthly_savings = (
        assumed_monthly_savings
        if assumed_monthly_savings is not None
        else analytics.projected_month_balance
    )
    horizons = [3, 6, 12, 24]
    if custom_months and custom_months not in horizons:
        horizons.append(custom_months)
    horizons.sort()

    reserve_months = assets / analytics.expense.value if analytics.expense.value > 0 else None
    budgets = list(
        await db.scalars(
            select(MonthlyBudget).where(
                MonthlyBudget.user_id == user_id,
                MonthlyBudget.financial_profile_id == profile_id,
                MonthlyBudget.competence_month == as_of.replace(day=1),
            )
        )
    )
    budget_rows = await budget_progress(db, user_id, profile_id, as_of)
    budget_score: Decimal | None = None
    if budgets and budget_rows:
        budget_total = sum(
            (
                clamp(Decimal("100") - max(Decimal("0"), item.consumed_percent - 100))
                for item in budget_rows
            ),
            Decimal("0"),
        )
        budget_score = budget_total / Decimal(len(budget_rows))
    if not debts:
        debt_score: Decimal | None = Decimal("100")
        debt_explanation = "Nenhuma dívida ativa cadastrada."
    elif analytics.income.value > 0:
        installments = sum(
            (item.monthly_payment or Decimal("0") for item in debts),
            Decimal("0"),
        )
        ratio = installments * 100 / analytics.income.value
        debt_score = clamp(Decimal("100") - ratio * Decimal("2"))
        debt_explanation = f"Parcelas representam {ratio.quantize(PERCENT)}% da renda observada."
    else:
        debt_score = None
        debt_explanation = "Renda insuficiente para medir comprometimento."
    goal_score = (
        Decimal(
            sum(
                1
                for item in goals
                if item.monthly_contribution
                >= max(
                    Decimal("0"),
                    (item.target_amount - item.current_amount)
                    / max(
                        1,
                        (item.target_date.year - as_of.year) * 12
                        + item.target_date.month
                        - as_of.month,
                    ),
                )
            )
        )
        * 100
        / Decimal(len(goals))
        if goals
        else None
    )
    freshness_score = {
        "HIGH": Decimal("100"),
        "MEDIUM": Decimal("60"),
        "LOW": Decimal("20"),
    }[analytics.coverage.confidence]
    subscores = [
        HealthSubscore(
            code="CASHFLOW",
            label="Fluxo de caixa",
            weight=25,
            score=cashflow_score(
                analytics.savings_rate_percent,
                analytics.monthly_balance.value,
            ),
            explanation="Usa resultado e taxa de economia do mês.",
        ),
        HealthSubscore(
            code="BUDGET",
            label="Aderência ao orçamento",
            weight=20,
            score=budget_score,
            explanation="Compara ritmo projetado e limites cadastrados.",
        ),
        HealthSubscore(
            code="RESERVE",
            label="Reserva",
            weight=20,
            score=reserve_score(reserve_months),
            explanation="Meses de despesas atuais cobertos pelo saldo reconhecido.",
        ),
        HealthSubscore(
            code="DEBT",
            label="Dívidas",
            weight=20,
            score=debt_score,
            explanation=debt_explanation,
        ),
        HealthSubscore(
            code="GOALS",
            label="Metas",
            weight=10,
            score=goal_score,
            explanation="Proporção de metas ativas no ritmo necessário.",
        ),
        HealthSubscore(
            code="DATA",
            label="Dados",
            weight=5,
            score=freshness_score,
            explanation="Cobertura de categorização e frescor das conexões.",
        ),
    ]
    return FutureResponse(
        algorithm_version=ALGORITHM_VERSION,
        as_of=as_of,
        assets=assets.quantize(CENT),
        liabilities=liabilities.quantize(CENT),
        net_worth=net_worth.quantize(CENT),
        assumed_monthly_savings=monthly_savings.quantize(CENT),
        projections=[
            ProjectionPoint(
                months=months,
                projected_on=add_months(as_of, months),
                net_worth=(net_worth + monthly_savings * months).quantize(CENT),
                assumption="Saldo atual + economia mensal constante; sem retorno de investimentos.",
            )
            for months in horizons
        ],
        health_score=weighted_health_score(subscores),
        calculation_notes=[
            "Passivos cadastrados reduzem o patrimônio.",
            "Premissas editadas valem apenas para esta simulação.",
            "Dados ausentes reduzem confiança em vez de receber nota artificial.",
        ],
    )


async def save_future_snapshot(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    result: FutureResponse,
) -> None:
    net_snapshot = await db.scalar(
        select(NetWorthSnapshot).where(
            NetWorthSnapshot.financial_profile_id == profile_id,
            NetWorthSnapshot.snapshot_on == result.as_of,
        )
    )
    if net_snapshot is None:
        db.add(
            NetWorthSnapshot(
                user_id=user_id,
                financial_profile_id=profile_id,
                snapshot_on=result.as_of,
                assets=result.assets,
                liabilities=result.liabilities,
                net_worth=result.net_worth,
                algorithm_version=result.algorithm_version,
            )
        )
    score_snapshot = await db.scalar(
        select(HealthScoreSnapshot).where(
            HealthScoreSnapshot.financial_profile_id == profile_id,
            HealthScoreSnapshot.snapshot_on == result.as_of,
            HealthScoreSnapshot.algorithm_version == result.algorithm_version,
        )
    )
    if score_snapshot is None:
        db.add(
            HealthScoreSnapshot(
                user_id=user_id,
                financial_profile_id=profile_id,
                snapshot_on=result.as_of,
                score=result.health_score.score,
                confidence_percent=result.health_score.confidence_percent,
                subscores={
                    item.code: item.model_dump(mode="json")
                    for item in result.health_score.subscores
                },
                algorithm_version=result.algorithm_version,
            )
        )
