from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile
from app.modules.payments.schemas import (
    PaymentCapabilityResponse,
    PaymentSimulationCreate,
    PaymentSimulationResponse,
)
from app.modules.payments.service import create_payment_simulation

router = APIRouter()


@router.get(
    "/payments/capabilities",
    response_model=PaymentCapabilityResponse,
    tags=["payments"],
)
async def get_payment_capabilities(scope: CurrentScope) -> PaymentCapabilityResponse:
    _ = scope
    settings = get_settings()
    return PaymentCapabilityResponse(
        initiation_enabled=settings.payment_initiation_enabled,
        kill_switch_active=settings.payment_kill_switch,
        provider_configured=bool(settings.payment_provider),
        implementation_status="SIMULATION_ONLY",
    )


@router.post(
    "/financial-profiles/{profile_id}/payment-simulations",
    response_model=PaymentSimulationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payments"],
)
async def post_payment_simulation(
    profile_id: UUID,
    payload: PaymentSimulationCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> PaymentSimulationResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        simulation = await create_payment_simulation(db, scope.user, profile, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    response = PaymentSimulationResponse.model_validate(simulation)
    return response.model_copy(
        update={
            "external_operations_count": len(simulation.bill_ids),
            "warning": (
                "Isto é apenas uma simulação. Nenhuma movimentação foi iniciada "
                "e a IA não pode executar pagamentos."
            ),
        }
    )


@router.post(
    "/payments/initiate",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    tags=["payments"],
)
async def post_payment_initiation(scope: CsrfScope) -> None:
    _ = scope
    settings = get_settings()
    if settings.payment_kill_switch or not settings.payment_initiation_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment initiation is disabled by product policy.",
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="No approved PaymentProvider is configured.",
    )
