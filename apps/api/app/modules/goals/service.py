from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.goals.models import (
    Goal,
    GoalContribution,
    GoalPlanVersion,
    GoalScenario,
    GoalStatus,
    PendingAction,
    PendingActionStatus,
)
from app.modules.goals.schemas import (
    ContributionCreate,
    GoalCreate,
    GoalResponse,
    GoalScenarioRequest,
    GoalScenarioResponse,
    PendingActionResponse,
    ScenarioResult,
)
from app.modules.identity.models import FinancialProfile, User
from app.modules.identity.service import record_audit_event

CENT = Decimal("0.01")


def months_between(start: date, end: date) -> int:
    if end <= start:
        return 0
    months = (end.year - start.year) * 12 + end.month - start.month
    return max(1, months + (end.day > start.day))


def required_monthly(target: Decimal, current: Decimal, months: int) -> Decimal:
    remaining = max(Decimal("0"), target - current)
    if months <= 0:
        return remaining
    return (remaining / months).quantize(CENT, rounding=ROUND_HALF_UP)


def goal_response(goal: Goal, as_of: date | None = None) -> GoalResponse:
    as_of = as_of or date.today()
    remaining = max(Decimal("0"), goal.target_amount - goal.current_amount)
    months = months_between(as_of, goal.target_date)
    required = required_monthly(goal.target_amount, goal.current_amount, months)
    progress = min(
        Decimal("100"),
        goal.current_amount * 100 / goal.target_amount,
    ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return GoalResponse(
        id=goal.id,
        financial_profile_id=goal.financial_profile_id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        monthly_contribution=goal.monthly_contribution,
        priority=goal.priority,
        status=goal.status,
        version=goal.version,
        progress_percent=progress,
        remaining_amount=remaining,
        months_remaining=months,
        required_monthly_contribution=required,
        pace_status=(
            "COMPLETED"
            if remaining == 0
            else "ON_TRACK"
            if goal.monthly_contribution >= required
            else "BEHIND"
        ),
    )


def snapshot(goal: Goal) -> dict[str, object]:
    return {
        "name": goal.name,
        "target_amount": str(goal.target_amount),
        "current_amount": str(goal.current_amount),
        "target_date": goal.target_date.isoformat(),
        "monthly_contribution": str(goal.monthly_contribution),
        "status": goal.status.value,
    }


async def save_goal_version(db: AsyncSession, goal: Goal) -> None:
    db.add(
        GoalPlanVersion(
            goal_id=goal.id,
            user_id=goal.user_id,
            version=goal.version,
            snapshot=snapshot(goal),
        )
    )


async def create_goal(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: GoalCreate,
) -> Goal:
    if payload.target_date <= date.today():
        raise ValueError("Target date must be in the future.")
    if payload.current_amount > payload.target_amount:
        raise ValueError("Current amount cannot exceed target amount.")
    goal = Goal(
        user_id=user.id,
        financial_profile_id=profile.id,
        **payload.model_dump(),
    )
    db.add(goal)
    await db.flush()
    await save_goal_version(db, goal)
    return goal


async def list_goals(db: AsyncSession, user_id: UUID, profile_id: UUID) -> list[Goal]:
    return list(
        await db.scalars(
            select(Goal)
            .where(
                Goal.user_id == user_id,
                Goal.financial_profile_id == profile_id,
                Goal.status != GoalStatus.ARCHIVED,
            )
            .order_by(Goal.priority, Goal.target_date)
        )
    )


async def get_owned_goal(db: AsyncSession, user_id: UUID, goal_id: UUID) -> Goal | None:
    return cast(
        Goal | None,
        await db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)),
    )


async def add_contribution(
    db: AsyncSession,
    user: User,
    goal: Goal,
    payload: ContributionCreate,
) -> Goal:
    existing = await db.scalar(
        select(PendingAction).where(
            PendingAction.user_id == user.id,
            PendingAction.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        return goal
    before = snapshot(goal)
    goal.current_amount = min(goal.target_amount, goal.current_amount + payload.amount)
    goal.status = (
        GoalStatus.COMPLETED if goal.current_amount >= goal.target_amount else GoalStatus.ACTIVE
    )
    goal.version += 1
    db.add(
        GoalContribution(
            goal_id=goal.id,
            user_id=user.id,
            amount=payload.amount,
            contributed_on=payload.contributed_on,
        )
    )
    action = PendingAction(
        user_id=user.id,
        financial_profile_id=goal.financial_profile_id,
        action_type="GOAL_CONTRIBUTION",
        target_id=goal.id,
        target_version=goal.version - 1,
        idempotency_key=payload.idempotency_key,
        payload_hash=hashlib.sha256(payload.model_dump_json().encode()).hexdigest(),
        before_state=before,
        after_state=snapshot(goal),
        status=PendingActionStatus.CONFIRMED,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        confirmed_at=datetime.now(UTC),
    )
    db.add(action)
    await save_goal_version(db, goal)
    return goal


def scenario(
    name: str,
    goal: Goal,
    monthly: Decimal,
    target_date: date,
    as_of: date,
) -> ScenarioResult:
    months = months_between(as_of, target_date)
    projected = goal.current_amount + monthly * months
    remaining = max(Decimal("0"), goal.target_amount - goal.current_amount)
    months_to_target = (
        0 if remaining == 0 else math.ceil(remaining / monthly) if monthly > 0 else None
    )
    return ScenarioResult(
        name=name,
        monthly_contribution=monthly,
        target_date=target_date,
        months_to_target=months_to_target,
        projected_amount_at_target=projected.quantize(CENT, rounding=ROUND_HALF_UP),
        reaches_target=projected >= goal.target_amount,
    )


async def propose_goal_scenarios(
    db: AsyncSession,
    user: User,
    goal: Goal,
    payload: GoalScenarioRequest,
) -> GoalScenarioResponse:
    existing = await db.scalar(
        select(PendingAction).where(
            PendingAction.user_id == user.id,
            PendingAction.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        scenario_rows = await db.scalars(
            select(GoalScenario).where(
                GoalScenario.goal_id == goal.id,
                GoalScenario.user_id == user.id,
            )
        )
        latest = list(scenario_rows)[-4:]
        return GoalScenarioResponse(
            scenarios=[ScenarioResult.model_validate(item.results) for item in latest],
            pending_action=PendingActionResponse.model_validate(existing),
        )
    if payload.target_date <= date.today():
        raise ValueError("Target date must be in the future.")
    variants = [
        ("Atual", goal.monthly_contribution, goal.target_date),
        ("Conservador", payload.monthly_contribution * Decimal("0.75"), payload.target_date),
        ("Equilibrado", payload.monthly_contribution, payload.target_date),
        ("Agressivo", payload.monthly_contribution * Decimal("1.25"), payload.target_date),
    ]
    scenario_results = [
        scenario(name, goal, monthly, target_date, date.today())
        for name, monthly, target_date in variants
    ]
    for result in scenario_results:
        db.add(
            GoalScenario(
                goal_id=goal.id,
                user_id=user.id,
                name=result.name,
                inputs={
                    "monthly_contribution": str(result.monthly_contribution),
                    "target_date": result.target_date.isoformat(),
                },
                results=result.model_dump(mode="json"),
            )
        )
    before = snapshot(goal)
    after = {
        **before,
        "monthly_contribution": str(payload.monthly_contribution),
        "target_date": payload.target_date.isoformat(),
    }
    canonical = json.dumps(after, separators=(",", ":"), sort_keys=True)
    action = PendingAction(
        user_id=user.id,
        financial_profile_id=goal.financial_profile_id,
        action_type="UPDATE_GOAL_PLAN",
        target_id=goal.id,
        target_version=goal.version,
        idempotency_key=payload.idempotency_key,
        payload_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        before_state=before,
        after_state=after,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db.add(action)
    await db.flush()
    return GoalScenarioResponse(
        scenarios=scenario_results,
        pending_action=PendingActionResponse.model_validate(action),
    )


async def confirm_pending_action(
    db: AsyncSession,
    user: User,
    action: PendingAction,
    correlation_id: str | None,
) -> Goal:
    goal = await get_owned_goal(db, user.id, action.target_id)
    if goal is None:
        raise LookupError("Goal not found.")
    if action.status == PendingActionStatus.CONFIRMED:
        return goal
    if action.status != PendingActionStatus.PENDING:
        raise ValueError("Action is no longer pending.")
    if action.expires_at <= datetime.now(UTC):
        action.status = PendingActionStatus.EXPIRED
        raise ValueError("Action expired.")
    if goal.version != action.target_version:
        raise ValueError("Goal changed; create a new scenario.")
    goal.monthly_contribution = Decimal(str(action.after_state["monthly_contribution"]))
    goal.target_date = date.fromisoformat(str(action.after_state["target_date"]))
    goal.version += 1
    action.status = PendingActionStatus.CONFIRMED
    action.confirmed_at = datetime.now(UTC)
    await save_goal_version(db, goal)
    await record_audit_event(
        db,
        user_id=user.id,
        action="pending_action.confirmed",
        target_type="goal",
        target_id=goal.id,
        correlation_id=correlation_id,
        safe_metadata={"action_type": action.action_type},
    )
    return goal


async def get_owned_pending_action(
    db: AsyncSession,
    user_id: UUID,
    action_id: UUID,
) -> PendingAction | None:
    return cast(
        PendingAction | None,
        await db.scalar(
            select(PendingAction).where(
                PendingAction.id == action_id,
                PendingAction.user_id == user_id,
            )
        ),
    )
