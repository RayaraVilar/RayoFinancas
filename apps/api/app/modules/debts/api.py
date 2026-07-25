from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.modules.debts.schemas import (
    DebtCreate,
    DebtResponse,
    DebtSimulationRequest,
    DebtSimulationResult,
    DebtStrategyResponse,
)
from app.modules.debts.service import (
    create_debt,
    debt_strategy,
    get_owned_debt,
    list_debts,
    simulate_debt,
)
from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile

router = APIRouter()


@router.get(
    "/financial-profiles/{profile_id}/debts",
    response_model=list[DebtResponse],
    tags=["debts"],
)
async def get_debts(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[DebtResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return [
        DebtResponse.model_validate(item)
        for item in await list_debts(db, scope.user.id, profile.id)
    ]


@router.post(
    "/financial-profiles/{profile_id}/debts",
    response_model=DebtResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["debts"],
)
async def post_debt(
    profile_id: UUID,
    payload: DebtCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> DebtResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    debt = await create_debt(db, scope.user, profile, payload)
    await db.commit()
    return DebtResponse.model_validate(debt)


@router.post(
    "/debts/{debt_id}/simulate",
    response_model=DebtSimulationResult,
    tags=["debts"],
)
async def post_debt_simulation(
    debt_id: UUID,
    payload: DebtSimulationRequest,
    db: DatabaseSession,
    scope: CurrentScope,
) -> DebtSimulationResult:
    debt = await get_owned_debt(db, scope.user.id, debt_id)
    if debt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found.")
    try:
        return simulate_debt(debt, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get(
    "/financial-profiles/{profile_id}/debts/strategy",
    response_model=DebtStrategyResponse,
    tags=["debts"],
)
async def get_debt_strategy(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
    strategy: Annotated[
        Literal["SNOWBALL", "AVALANCHE"],
        Query(),
    ] = "AVALANCHE",
) -> DebtStrategyResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    debts = await list_debts(db, scope.user.id, profile.id)
    return debt_strategy(debts, strategy)
