from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.modules.assistant.registry import assistant_tools
from app.modules.assistant.schemas import AssistantCapabilityResponse
from app.modules.identity.dependencies import CurrentScope, DatabaseSession
from app.modules.identity.service import get_owned_profile

router = APIRouter()


@router.get(
    "/financial-profiles/{profile_id}/assistant/capabilities",
    response_model=AssistantCapabilityResponse,
    tags=["assistant"],
)
async def get_assistant_capabilities(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssistantCapabilityResponse:
    if await get_owned_profile(db, scope.user.id, profile_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return AssistantCapabilityResponse(
        configured=settings.assistant_configured,
        status="READY" if settings.assistant_configured else "PENDING_CREDENTIAL",
        model=settings.assistant_model,
        tools=assistant_tools(),
        guarantees=[
            "Cálculos críticos vêm do backend determinístico, não do modelo.",
            "Toda ferramenta exige o contexto financeiro autorizado.",
            "Não existe ferramenta de execução ou iniciação de pagamento.",
            "Fatos, estimativas e simulações devem ser identificados separadamente.",
        ],
    )
