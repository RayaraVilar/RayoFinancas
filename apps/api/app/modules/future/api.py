from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.modules.future.schemas import FutureResponse
from app.modules.future.service import calculate_future, save_future_snapshot
from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile

router = APIRouter()


async def require_profile(db: DatabaseSession, user_id: UUID, profile_id: UUID) -> None:
    if await get_owned_profile(db, user_id, profile_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")


@router.get(
    "/financial-profiles/{profile_id}/future",
    response_model=FutureResponse,
    tags=["future"],
)
async def get_future(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
    as_of: Annotated[date, Query(default_factory=date.today)],
    monthly_savings: Annotated[Decimal | None, Query()] = None,
    custom_months: Annotated[int | None, Query(ge=1, le=120)] = None,
) -> FutureResponse:
    await require_profile(db, scope.user.id, profile_id)
    return await calculate_future(
        db,
        scope.user.id,
        profile_id,
        as_of,
        monthly_savings,
        custom_months,
    )


@router.post(
    "/financial-profiles/{profile_id}/future/snapshot",
    response_model=FutureResponse,
    tags=["future"],
)
async def post_future_snapshot(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> FutureResponse:
    await require_profile(db, scope.user.id, profile_id)
    result = await calculate_future(
        db,
        scope.user.id,
        profile_id,
        date.today(),
        None,
        None,
    )
    await save_future_snapshot(db, scope.user.id, profile_id, result)
    await db.commit()
    return result
