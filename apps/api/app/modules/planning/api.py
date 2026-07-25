from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile
from app.modules.planning.schemas import (
    BillCreate,
    BillResponse,
    BillTransition,
    BudgetProgress,
    BudgetUpsert,
    MonthlyPlanResponse,
    MonthlyPlanUpsert,
    PlanningSummaryResponse,
)
from app.modules.planning.service import (
    create_manual_bill,
    get_owned_bill,
    planning_summary,
    transition_bill,
    upsert_budget,
    upsert_monthly_plan,
)

router = APIRouter()


@router.get(
    "/financial-profiles/{profile_id}/planning/summary",
    response_model=PlanningSummaryResponse,
    tags=["planning"],
)
async def get_planning_summary(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
    as_of: Annotated[date, Query(default_factory=date.today)],
) -> PlanningSummaryResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    result = await planning_summary(db, scope.user.id, profile.id, as_of)
    await db.commit()
    return result


@router.post(
    "/financial-profiles/{profile_id}/bills",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["planning"],
)
async def post_bill(
    request: Request,
    profile_id: UUID,
    payload: BillCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> BillResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    bill = await create_manual_bill(
        db,
        scope.user,
        profile,
        payload,
        request.headers.get("x-request-id"),
    )
    await db.commit()
    return BillResponse.model_validate(bill)


@router.post(
    "/bills/{bill_id}/transition",
    response_model=BillResponse,
    tags=["planning"],
)
async def post_bill_transition(
    request: Request,
    bill_id: UUID,
    payload: BillTransition,
    db: DatabaseSession,
    scope: CsrfScope,
) -> BillResponse:
    bill = await get_owned_bill(db, scope.user.id, bill_id)
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found.")
    try:
        bill = await transition_bill(
            db,
            scope.user,
            bill,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return BillResponse.model_validate(bill)


@router.put(
    "/financial-profiles/{profile_id}/budgets",
    response_model=BudgetProgress,
    tags=["planning"],
)
async def put_budget(
    profile_id: UUID,
    payload: BudgetUpsert,
    db: DatabaseSession,
    scope: CsrfScope,
) -> BudgetProgress:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        await upsert_budget(db, scope.user, profile, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    summary = await planning_summary(
        db,
        scope.user.id,
        profile.id,
        payload.competence_month,
    )
    return next(item for item in summary.budgets if item.category_id == payload.category_id)


@router.put(
    "/financial-profiles/{profile_id}/monthly-plan",
    response_model=MonthlyPlanResponse,
    tags=["planning"],
)
async def put_monthly_plan(
    profile_id: UUID,
    payload: MonthlyPlanUpsert,
    db: DatabaseSession,
    scope: CsrfScope,
) -> MonthlyPlanResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    plan = await upsert_monthly_plan(db, scope.user, profile, payload)
    await db.commit()
    return MonthlyPlanResponse.model_validate(plan)
