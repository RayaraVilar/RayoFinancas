from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.modules.goals.schemas import (
    ContributionCreate,
    GoalCreate,
    GoalResponse,
    GoalScenarioRequest,
    GoalScenarioResponse,
)
from app.modules.goals.service import (
    add_contribution,
    confirm_pending_action,
    create_goal,
    get_owned_goal,
    get_owned_pending_action,
    goal_response,
    list_goals,
    propose_goal_scenarios,
)
from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile

router = APIRouter()


@router.get(
    "/financial-profiles/{profile_id}/goals",
    response_model=list[GoalResponse],
    tags=["goals"],
)
async def get_goals(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[GoalResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return [goal_response(item) for item in await list_goals(db, scope.user.id, profile.id)]


@router.post(
    "/financial-profiles/{profile_id}/goals",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["goals"],
)
async def post_goal(
    profile_id: UUID,
    payload: GoalCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> GoalResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        goal = await create_goal(db, scope.user, profile, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return goal_response(goal)


@router.post(
    "/goals/{goal_id}/contributions",
    response_model=GoalResponse,
    tags=["goals"],
)
async def post_goal_contribution(
    goal_id: UUID,
    payload: ContributionCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> GoalResponse:
    goal = await get_owned_goal(db, scope.user.id, goal_id)
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    goal = await add_contribution(db, scope.user, goal, payload)
    await db.commit()
    return goal_response(goal, payload.contributed_on)


@router.post(
    "/goals/{goal_id}/scenarios",
    response_model=GoalScenarioResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["goals"],
)
async def post_goal_scenarios(
    goal_id: UUID,
    payload: GoalScenarioRequest,
    db: DatabaseSession,
    scope: CsrfScope,
) -> GoalScenarioResponse:
    goal = await get_owned_goal(db, scope.user.id, goal_id)
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    try:
        result = await propose_goal_scenarios(db, scope.user, goal, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return result


@router.post(
    "/pending-actions/{action_id}/confirm",
    response_model=GoalResponse,
    tags=["pending-actions"],
)
async def post_pending_action_confirmation(
    request: Request,
    action_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> GoalResponse:
    action = await get_owned_pending_action(db, scope.user.id, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")
    try:
        goal = await confirm_pending_action(
            db,
            scope.user,
            action,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return goal_response(goal, date.today())
