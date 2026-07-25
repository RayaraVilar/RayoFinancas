from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile
from app.modules.insights.schemas import (
    InsightFeedbackCreate,
    InsightResponse,
    InsightStateUpdate,
)
from app.modules.insights.service import (
    add_feedback,
    evaluate_insights,
    get_owned_insight,
)

router = APIRouter()


@router.get(
    "/financial-profiles/{profile_id}/insights",
    response_model=list[InsightResponse],
    tags=["insights"],
)
async def get_insights(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
    as_of: Annotated[date, Query(default_factory=date.today)],
    limit: Annotated[int, Query(ge=1, le=50)] = 3,
) -> list[InsightResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    items = await evaluate_insights(db, scope.user.id, profile.id, as_of)
    await db.commit()
    return [InsightResponse.model_validate(item) for item in items[:limit]]


@router.patch(
    "/insights/{insight_id}",
    response_model=InsightResponse,
    tags=["insights"],
)
async def patch_insight(
    insight_id: UUID,
    payload: InsightStateUpdate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> InsightResponse:
    insight = await get_owned_insight(db, scope.user.id, insight_id)
    if insight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found.")
    insight.state = payload.state
    await db.commit()
    return InsightResponse.model_validate(insight)


@router.post(
    "/insights/{insight_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["insights"],
)
async def post_insight_feedback(
    insight_id: UUID,
    payload: InsightFeedbackCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> None:
    insight = await get_owned_insight(db, scope.user.id, insight_id)
    if insight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found.")
    await add_feedback(db, scope.user.id, insight, payload)
    await db.commit()
