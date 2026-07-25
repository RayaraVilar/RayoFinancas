from __future__ import annotations

import hmac
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.modules.identity.demo import create_demo_user
from app.modules.identity.dependencies import (
    CsrfScope,
    CurrentScope,
    DatabaseSession,
    SelectedFinancialContext,
)
from app.modules.identity.google_oauth import (
    GoogleIdentityProvider,
    GoogleOAuthError,
)
from app.modules.identity.models import FinancialAccount
from app.modules.identity.privacy import export_user_data, request_user_deletion
from app.modules.identity.schemas import (
    AccountCreate,
    AccountResponse,
    AuthStatusResponse,
    ConsentCreate,
    ConsentResponse,
    DemoSessionResponse,
    FinancialProfileCreate,
    FinancialProfileResponse,
    OnboardingStateResponse,
    UserResponse,
)
from app.modules.identity.security import OAuthFlowCodec, new_oauth_flow
from app.modules.identity.service import (
    PRIVACY_CONSENT_TYPE,
    PRIVACY_CONSENT_VERSION,
    complete_onboarding,
    create_manual_account,
    create_profile,
    create_session,
    get_or_create_google_user,
    get_owned_profile,
    grant_consent,
    list_profiles,
    onboarding_state,
    record_audit_event,
)

router = APIRouter()
OAUTH_FLOW_COOKIE = "rayo_oauth_flow"
logger = logging.getLogger(__name__)


class FinancialContextResponse(BaseModel):
    mode: str
    profile_id: UUID | None
    profile_name: str | None


def get_google_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleIdentityProvider:
    try:
        return GoogleIdentityProvider(settings)
    except GoogleOAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is pending credentials.",
        ) from exc


def set_session_cookies(
    response: Response,
    *,
    settings: Settings,
    token: str,
    csrf_token: str,
) -> None:
    max_age = settings.session_ttl_days * 24 * 60 * 60
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.get("/auth/status", response_model=AuthStatusResponse, tags=["auth"])
async def auth_status(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthStatusResponse:
    return AuthStatusResponse(
        google_configured=settings.google_oauth_configured,
        implementation_status=(
            "IMPLEMENTED_PENDING_CREDENTIAL"
            if not settings.google_oauth_configured
            else "CONFIGURED"
        ),
    )


@router.post("/auth/demo", response_model=DemoSessionResponse, tags=["auth"])
async def start_demo_session(
    request: Request,
    db: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    user, profile = await create_demo_user(db)
    credentials = await create_session(db, user.id, settings)
    await record_audit_event(
        db,
        user_id=user.id,
        action="auth.demo_started",
        target_type="session",
        target_id=credentials.session.id,
        correlation_id=request.headers.get("x-request-id"),
    )
    await db.commit()
    response = JSONResponse(
        content=jsonable_encoder(DemoSessionResponse(profile_id=profile.id)),
        status_code=status.HTTP_201_CREATED,
    )
    set_session_cookies(
        response,
        settings=settings,
        token=credentials.token,
        csrf_token=credentials.csrf_token,
    )
    return response


@router.get("/auth/google/start", tags=["auth"])
async def start_google_login(
    provider: Annotated[GoogleIdentityProvider, Depends(get_google_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    flow = new_oauth_flow()
    codec = OAuthFlowCodec(settings.secret_key.get_secret_value())
    response = RedirectResponse(provider.authorization_url(flow), status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        OAUTH_FLOW_COOKIE,
        codec.encode(flow),
        max_age=settings.oauth_flow_ttl_seconds,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/api/v1/auth/google",
    )
    return response


@router.get("/auth/google/callback", tags=["auth"])
async def finish_google_login(
    request: Request,
    db: DatabaseSession,
    provider: Annotated[GoogleIdentityProvider, Depends(get_google_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
    code: Annotated[str | None, Query(max_length=4096)] = None,
    state_value: Annotated[str | None, Query(alias="state", max_length=512)] = None,
    error: Annotated[str | None, Query(max_length=128)] = None,
) -> RedirectResponse:
    login_url = f"{settings.frontend_url.rstrip('/')}/entrar"
    failure_url = f"{login_url}?error=google"
    flow_cookie = request.cookies.get(OAUTH_FLOW_COOKIE)
    codec = OAuthFlowCodec(settings.secret_key.get_secret_value())
    flow = codec.decode(flow_cookie, settings.oauth_flow_ttl_seconds) if flow_cookie else None

    if error or not code or not state_value or flow is None:
        return RedirectResponse(failure_url, status_code=status.HTTP_303_SEE_OTHER)
    if not hmac.compare_digest(state_value, flow.state):
        return RedirectResponse(failure_url, status_code=status.HTTP_303_SEE_OTHER)

    try:
        claims = await provider.exchange_code(code, flow)
        user = await get_or_create_google_user(db, claims)
        credentials = await create_session(db, user.id, settings)
        await record_audit_event(
            db,
            user_id=user.id,
            action="auth.google_login",
            target_type="session",
            target_id=credentials.session.id,
            correlation_id=request.headers.get("x-request-id"),
        )
        await db.commit()
    except GoogleOAuthError as exc:
        logger.warning("Google OAuth failed: %s", exc.code)
        await db.rollback()
        await record_audit_event(
            db,
            user_id=None,
            action="auth.google_login",
            outcome="FAILED",
            correlation_id=request.headers.get("x-request-id"),
        )
        await db.commit()
        return RedirectResponse(
            f"{login_url}?error={exc.code}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError:
        logger.warning("Google OAuth failed while creating the local identity")
        await db.rollback()
        await record_audit_event(
            db,
            user_id=None,
            action="auth.google_login",
            outcome="FAILED",
            correlation_id=request.headers.get("x-request-id"),
        )
        await db.commit()
        return RedirectResponse(failure_url, status_code=status.HTTP_303_SEE_OTHER)

    destination = "/dashboard" if user.onboarding_completed_at else "/onboarding"
    response = RedirectResponse(
        f"{settings.frontend_url.rstrip('/')}{destination}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(OAUTH_FLOW_COOKIE, path="/api/v1/auth/google")
    set_session_cookies(
        response,
        settings=settings,
        token=credentials.token,
        csrf_token=credentials.csrf_token,
    )
    return response


@router.get("/auth/me", response_model=UserResponse, tags=["auth"])
async def current_user(scope: CurrentScope) -> UserResponse:
    return UserResponse.model_validate(scope.user)


@router.post("/auth/session/refresh", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def refresh_session(
    request: Request,
    db: DatabaseSession,
    scope: CsrfScope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    scope.session.revoked_at = datetime.now(UTC)
    credentials = await create_session(db, scope.user.id, settings)
    await record_audit_event(
        db,
        user_id=scope.user.id,
        action="session.rotated",
        target_type="session",
        target_id=credentials.session.id,
        correlation_id=request.headers.get("x-request-id"),
    )
    await db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_session_cookies(
        response,
        settings=settings,
        token=credentials.token,
        csrf_token=credentials.csrf_token,
    )
    return response


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def logout(
    request: Request,
    db: DatabaseSession,
    scope: CsrfScope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    is_demo = scope.user.is_demo
    scope.session.revoked_at = datetime.now(UTC)
    await record_audit_event(
        db,
        user_id=scope.user.id,
        action="auth.logout",
        target_type="session",
        target_id=scope.session.id,
        correlation_id=request.headers.get("x-request-id"),
    )
    if is_demo:
        await db.delete(scope.user)
    await db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookies(response, settings)
    return response


@router.get(
    "/financial-profiles",
    response_model=list[FinancialProfileResponse],
    tags=["financial profiles"],
)
async def get_profiles(db: DatabaseSession, scope: CurrentScope) -> list[FinancialProfileResponse]:
    profiles = await list_profiles(db, scope.user.id)
    return [FinancialProfileResponse.model_validate(profile) for profile in profiles]


@router.post(
    "/financial-profiles",
    response_model=FinancialProfileResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["financial profiles"],
)
async def post_profile(
    request: Request,
    payload: FinancialProfileCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> FinancialProfileResponse:
    try:
        profile = await create_profile(
            db,
            scope.user,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FinancialProfileResponse.model_validate(profile)


@router.post(
    "/financial-profiles/{profile_id}/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["accounts"],
)
async def post_manual_account(
    request: Request,
    profile_id: UUID,
    payload: AccountCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> AccountResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    account = await create_manual_account(
        db,
        scope.user,
        profile,
        payload,
        request.headers.get("x-request-id"),
    )
    await db.commit()
    return AccountResponse.model_validate(account)


@router.get(
    "/financial-profiles/{profile_id}/accounts",
    response_model=list[AccountResponse],
    tags=["accounts"],
)
async def get_profile_accounts(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[AccountResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    accounts = await db.scalars(
        select(FinancialAccount).where(
            FinancialAccount.user_id == scope.user.id,
            FinancialAccount.financial_profile_id == profile.id,
        )
    )
    return [AccountResponse.model_validate(account) for account in accounts]


@router.get(
    "/financial-context", response_model=FinancialContextResponse, tags=["financial profiles"]
)
async def financial_context(
    context: SelectedFinancialContext,
) -> FinancialContextResponse:
    return FinancialContextResponse(
        mode=context.mode,
        profile_id=context.profile.id if context.profile else None,
        profile_name=context.profile.name if context.profile else None,
    )


@router.post(
    "/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["consents"],
)
async def post_consent(
    request: Request,
    payload: ConsentCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> ConsentResponse:
    try:
        consent = await grant_consent(
            db,
            scope.user,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ConsentResponse.model_validate(consent)


@router.get("/onboarding/state", response_model=OnboardingStateResponse, tags=["onboarding"])
async def get_onboarding_state(
    db: DatabaseSession,
    scope: CurrentScope,
) -> OnboardingStateResponse:
    profile_count, account_count, consent_granted = await onboarding_state(db, scope.user)
    return OnboardingStateResponse(
        profile_count=profile_count,
        account_count=account_count,
        privacy_consent_granted=consent_granted,
        completed=scope.user.onboarding_completed_at is not None,
    )


@router.post(
    "/onboarding/privacy-consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["onboarding"],
)
async def grant_onboarding_privacy_consent(
    request: Request,
    db: DatabaseSession,
    scope: CsrfScope,
) -> ConsentResponse:
    consent = await grant_consent(
        db,
        scope.user,
        ConsentCreate(
            consent_type=PRIVACY_CONSENT_TYPE,
            version=PRIVACY_CONSENT_VERSION,
        ),
        request.headers.get("x-request-id"),
    )
    await db.commit()
    return ConsentResponse.model_validate(consent)


@router.post("/onboarding/complete", status_code=status.HTTP_204_NO_CONTENT, tags=["onboarding"])
async def finish_onboarding(
    request: Request,
    db: DatabaseSession,
    scope: CsrfScope,
) -> Response:
    try:
        await complete_onboarding(db, scope.user, request.headers.get("x-request-id"))
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/privacy/export", tags=["privacy"])
async def privacy_export(db: DatabaseSession, scope: CurrentScope) -> JSONResponse:
    export = await export_user_data(db, scope.user)
    return JSONResponse(
        content=jsonable_encoder(export),
        headers={
            "Content-Disposition": 'attachment; filename="rayo-export.json"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/privacy/delete-account",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["privacy"],
)
async def privacy_delete_account(
    request: Request,
    db: DatabaseSession,
    scope: CsrfScope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    requested_at = await request_user_deletion(db, scope.user)
    await record_audit_event(
        db,
        user_id=scope.user.id,
        action="privacy.deletion_requested",
        target_type="user",
        target_id=scope.user.id,
        correlation_id=request.headers.get("x-request-id"),
    )
    await db.commit()
    response = JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=jsonable_encoder(
            {
                "status": "DELETION_PENDING",
                "requested_at": requested_at,
                "message": (
                    "A conta foi bloqueada, as sessões e os consentimentos foram revogados. "
                    "A eliminação definitiva seguirá a política de retenção e auditoria."
                ),
            }
        ),
    )
    clear_session_cookies(response, settings)
    return response
