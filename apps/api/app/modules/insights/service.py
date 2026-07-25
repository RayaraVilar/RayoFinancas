from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.service import calculate_dashboard_analytics
from app.modules.goals.models import Goal, GoalStatus
from app.modules.goals.service import goal_response
from app.modules.insights.models import Insight, InsightFeedback, InsightState
from app.modules.insights.schemas import InsightFeedbackCreate

RULE_VERSION = "2026-07.v1"


@dataclass(frozen=True)
class InsightCandidate:
    rule_code: str
    priority: int
    severity: str
    title: str
    message: str
    evidence: dict[str, object]
    cta_label: str | None
    cta_path: str | None
    cooldown_days: int = 14


def analytics_candidates(
    projected_balance: Decimal,
    expense_change: Decimal | None,
    expense_value: Decimal,
    categorized_percent: Decimal,
    freshness: str,
) -> list[InsightCandidate]:
    candidates = []
    if projected_balance < 0:
        candidates.append(
            InsightCandidate(
                rule_code="PROJECTED_DEFICIT",
                priority=100,
                severity="HIGH",
                title="O mês tende a fechar no negativo",
                message=(
                    f"No ritmo atual, o fechamento estimado é {projected_balance:.2f}. "
                    "Revise compromissos antes de assumir novos gastos."
                ),
                evidence={"projected_balance": str(projected_balance)},
                cta_label="Revisar planejamento",
                cta_path="/dashboard#planning",
                cooldown_days=7,
            )
        )
    if expense_change is not None and expense_change >= 20 and expense_value >= 100:
        candidates.append(
            InsightCandidate(
                rule_code="EXPENSE_SPIKE",
                priority=80,
                severity="MEDIUM",
                title="Despesas acima do período equivalente",
                message=f"As despesas subiram {expense_change}% no recorte comparável.",
                evidence={
                    "expense_change_percent": str(expense_change),
                    "expense": str(expense_value),
                },
                cta_label="Ver categorias",
                cta_path="/dashboard#categories",
            )
        )
    if categorized_percent < 70 and expense_value > 0:
        candidates.append(
            InsightCandidate(
                rule_code="LOW_CATEGORY_COVERAGE",
                priority=55,
                severity="LOW",
                title="Categorizar melhora a leitura do mês",
                message=f"A cobertura atual é {categorized_percent}%.",
                evidence={"categorized_percent": str(categorized_percent)},
                cta_label="Revisar movimentações",
                cta_path="/dashboard#transactions",
                cooldown_days=21,
            )
        )
    if freshness in {"STALE", "OUTDATED"}:
        candidates.append(
            InsightCandidate(
                rule_code="STALE_BANK_DATA",
                priority=90,
                severity="HIGH" if freshness == "OUTDATED" else "MEDIUM",
                title="Dados bancários precisam de atualização",
                message="A última sincronização pode não refletir o saldo atual.",
                evidence={"freshness": freshness},
                cta_label="Sincronizar",
                cta_path="/dashboard#banking",
                cooldown_days=3,
            )
        )
    return candidates


async def evaluate_insights(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    as_of: date,
) -> list[Insight]:
    analytics = await calculate_dashboard_analytics(db, user_id, profile_id, as_of)
    candidates = analytics_candidates(
        analytics.projected_month_balance,
        analytics.expense.change_percent,
        analytics.expense.value,
        analytics.coverage.categorized_percent,
        analytics.coverage.freshness,
    )
    goals = await db.scalars(
        select(Goal).where(
            Goal.user_id == user_id,
            Goal.financial_profile_id == profile_id,
            Goal.status == GoalStatus.ACTIVE,
        )
    )
    behind = [goal_response(item, as_of) for item in goals]
    behind = [item for item in behind if item.pace_status == "BEHIND"]
    if behind:
        candidates.append(
            InsightCandidate(
                rule_code="GOAL_BEHIND",
                priority=65,
                severity="MEDIUM",
                title="Uma meta está fora do ritmo",
                message=f"{behind[0].name} precisa de ajuste no aporte ou na data.",
                evidence={
                    "goal_id": str(behind[0].id),
                    "required_monthly": str(behind[0].required_monthly_contribution),
                },
                cta_label="Simular meta",
                cta_path="/dashboard#goals",
            )
        )
    period_key = as_of.strftime("%Y-%m")
    now = datetime.now(UTC)
    for candidate in candidates:
        dedupe_key = f"{candidate.rule_code}:{RULE_VERSION}:{period_key}"
        existing = await db.scalar(
            select(Insight).where(
                Insight.financial_profile_id == profile_id,
                Insight.dedupe_key == dedupe_key,
            )
        )
        if existing:
            continue
        db.add(
            Insight(
                user_id=user_id,
                financial_profile_id=profile_id,
                rule_code=candidate.rule_code,
                rule_version=RULE_VERSION,
                dedupe_key=dedupe_key,
                priority=candidate.priority,
                severity=candidate.severity,
                title=candidate.title,
                message=candidate.message,
                evidence=candidate.evidence,
                cta_label=candidate.cta_label,
                cta_path=candidate.cta_path,
                cooldown_until=now + timedelta(days=candidate.cooldown_days),
            )
        )
    await db.flush()
    return list(
        await db.scalars(
            select(Insight)
            .where(
                Insight.user_id == user_id,
                Insight.financial_profile_id == profile_id,
                Insight.state == InsightState.ACTIVE,
            )
            .order_by(Insight.priority.desc(), Insight.created_at.desc())
        )
    )


async def get_owned_insight(
    db: AsyncSession,
    user_id: UUID,
    insight_id: UUID,
) -> Insight | None:
    return cast(
        Insight | None,
        await db.scalar(
            select(Insight).where(Insight.id == insight_id, Insight.user_id == user_id)
        ),
    )


async def add_feedback(
    db: AsyncSession,
    user_id: UUID,
    insight: Insight,
    payload: InsightFeedbackCreate,
) -> None:
    db.add(
        InsightFeedback(
            insight_id=insight.id,
            user_id=user_id,
            helpful=payload.helpful,
            reason_code=payload.reason_code,
        )
    )
