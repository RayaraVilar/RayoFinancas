from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.modules.identity.models import FinancialProfile, Session, User, UserStatus
from app.modules.identity.security import hash_secret
from app.modules.identity.service import get_owned_profile

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@dataclass(frozen=True)
class UserScope:
    user: User
    session: Session


@dataclass(frozen=True)
class FinancialContext:
    mode: Literal["all", "profile"]
    profile: FinancialProfile | None


async def get_current_scope(
    request: Request,
    db: DatabaseSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserScope:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    row = (
        await db.execute(
            select(Session, User)
            .join(User, User.id == Session.user_id)
            .where(
                Session.token_hash == hash_secret(raw_token),
                Session.revoked_at.is_(None),
                Session.expires_at > datetime.now(UTC),
                User.status == UserStatus.ACTIVE,
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    session, user = row
    return UserScope(user=user, session=session)


CurrentScope = Annotated[UserScope, Depends(get_current_scope)]


async def require_csrf(
    request: Request,
    scope: CurrentScope,
    settings: Annotated[Settings, Depends(get_settings)],
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> UserScope:
    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    if not csrf_cookie or not csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    if not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    if not hmac.compare_digest(hash_secret(csrf_header), scope.session.csrf_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    return scope


CsrfScope = Annotated[UserScope, Depends(require_csrf)]


async def get_financial_context(
    db: DatabaseSession,
    scope: CurrentScope,
    selected_profile: Annotated[
        str | None,
        Header(alias="X-Financial-Profile-Id"),
    ] = None,
) -> FinancialContext:
    if selected_profile is None or selected_profile.casefold() == "all":
        return FinancialContext(mode="all", profile=None)
    try:
        profile_id = UUID(selected_profile)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid financial profile context.",
        ) from exc

    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context not found.")
    return FinancialContext(mode="profile", profile=profile)


SelectedFinancialContext = Annotated[FinancialContext, Depends(get_financial_context)]
