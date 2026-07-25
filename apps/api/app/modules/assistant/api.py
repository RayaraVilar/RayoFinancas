from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import Settings, get_settings
from app.modules.assistant.providers import AssistantProviderError
from app.modules.assistant.registry import assistant_tools
from app.modules.assistant.schemas import (
    AssistantCapabilityResponse,
    AssistantCredentialUpsert,
    AssistantMessageRequest,
    AssistantMessageResponse,
    AssistantSettingsResponse,
)
from app.modules.assistant.service import (
    answer_financial_question,
    credential_api_key,
    get_assistant_credential,
    save_assistant_credential,
)
from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
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
    credential = await get_assistant_credential(db, scope.user.id)
    configured = credential is not None and not scope.user.is_demo
    return AssistantCapabilityResponse(
        configured=configured,
        status="READY" if configured else "PENDING_CREDENTIAL",
        model=settings.assistant_model,
        tools=assistant_tools(),
        guarantees=[
            "Cálculos críticos vêm do backend determinístico, não do modelo.",
            "Toda ferramenta exige o contexto financeiro autorizado.",
            "Não existe ferramenta de execução ou iniciação de pagamento.",
            "Fatos, estimativas e simulações devem ser identificados separadamente.",
        ],
    )


@router.get(
    "/assistant/settings",
    response_model=AssistantSettingsResponse,
    tags=["assistant"],
)
async def get_assistant_settings(
    db: DatabaseSession,
    scope: CurrentScope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssistantSettingsResponse:
    credential = await get_assistant_credential(db, scope.user.id)
    return AssistantSettingsResponse(
        configured=credential is not None and not scope.user.is_demo,
        provider="gemini",
        model=settings.gemini_model,
        key_hint=credential.key_hint if credential and not scope.user.is_demo else None,
        storage="ENCRYPTED_PER_USER",
    )


@router.put(
    "/assistant/settings",
    response_model=AssistantSettingsResponse,
    tags=["assistant"],
)
async def put_assistant_settings(
    payload: AssistantCredentialUpsert,
    db: DatabaseSession,
    scope: CsrfScope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssistantSettingsResponse:
    if scope.user.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A conta de demonstração não aceita credenciais.",
        )
    credential = await save_assistant_credential(
        db,
        user_id=scope.user.id,
        api_key=payload.api_key,
        settings=settings,
    )
    await db.commit()
    return AssistantSettingsResponse(
        configured=True,
        provider="gemini",
        model=settings.gemini_model,
        key_hint=credential.key_hint,
        storage="ENCRYPTED_PER_USER",
    )


@router.delete(
    "/assistant/settings",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["assistant"],
)
async def delete_assistant_settings(
    db: DatabaseSession,
    scope: CsrfScope,
) -> Response:
    credential = await get_assistant_credential(db, scope.user.id)
    if credential:
        await db.delete(credential)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/financial-profiles/{profile_id}/assistant/messages",
    response_model=AssistantMessageResponse,
    tags=["assistant"],
)
async def post_assistant_message(
    profile_id: UUID,
    payload: AssistantMessageRequest,
    db: DatabaseSession,
    scope: CsrfScope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssistantMessageResponse:
    if await get_owned_profile(db, scope.user.id, profile_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    credential = await get_assistant_credential(db, scope.user.id)
    if credential is None or scope.user.is_demo:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O assistente ainda não foi configurado.",
        )
    try:
        return await answer_financial_question(
            db=db,
            user_id=scope.user.id,
            profile_id=profile_id,
            question=payload.message,
            settings=settings,
            api_key=credential_api_key(credential, settings),
            as_of=date.today(),
        )
    except AssistantProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
