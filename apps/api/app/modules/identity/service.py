from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.identity.google_oauth import GoogleIdentityClaims
from app.modules.identity.models import (
    AccountSource,
    AuditEvent,
    FinancialAccount,
    FinancialProfile,
    FinancialProfileType,
    OAuthIdentity,
    RecordStatus,
    Session,
    User,
    UserConsent,
    UserStatus,
)
from app.modules.identity.schemas import AccountCreate, ConsentCreate, FinancialProfileCreate
from app.modules.identity.security import generate_token, hash_secret

PRIVACY_CONSENT_TYPE = "PRIVACY_TERMS"
PRIVACY_CONSENT_VERSION = "2026-07-24"


@dataclass(frozen=True)
class SessionCredentials:
    token: str
    csrf_token: str
    session: Session


async def record_audit_event(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    outcome: str = "SUCCESS",
    target_type: str | None = None,
    target_id: UUID | None = None,
    correlation_id: str | None = None,
    safe_metadata: dict[str, str] | None = None,
) -> None:
    db.add(
        AuditEvent(
            user_id=user_id,
            action=action,
            outcome=outcome,
            target_type=target_type,
            target_id=target_id,
            correlation_id=correlation_id[:64] if correlation_id else None,
            safe_metadata=(
                json.dumps(safe_metadata, separators=(",", ":"), sort_keys=True)
                if safe_metadata
                else None
            ),
        )
    )


async def get_or_create_google_user(
    db: AsyncSession,
    claims: GoogleIdentityClaims,
) -> User:
    identity = await db.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == "google",
            OAuthIdentity.subject == claims.subject,
        )
    )
    if identity is not None:
        user = await db.get(User, identity.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise ValueError("User is not active.")
        return user

    normalized_email = claims.email.strip().casefold()
    user = await db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(
            email=normalized_email,
            display_name=claims.display_name.strip()[:120],
            avatar_url=claims.avatar_url,
        )
        db.add(user)
        await db.flush()
    elif user.status != UserStatus.ACTIVE:
        raise ValueError("User is not active.")

    db.add(
        OAuthIdentity(
            user_id=user.id,
            provider="google",
            subject=claims.subject,
            email_at_login=normalized_email,
        )
    )
    await db.flush()
    return user


async def create_session(
    db: AsyncSession,
    user_id: UUID,
    settings: Settings,
) -> SessionCredentials:
    raw_token = generate_token()
    csrf_token = generate_token()
    session = Session(
        user_id=user_id,
        token_hash=hash_secret(raw_token),
        csrf_hash=hash_secret(csrf_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.session_ttl_days),
    )
    db.add(session)
    await db.flush()
    return SessionCredentials(raw_token, csrf_token, session)


async def list_profiles(db: AsyncSession, user_id: UUID) -> list[FinancialProfile]:
    result = await db.scalars(
        select(FinancialProfile)
        .where(
            FinancialProfile.user_id == user_id,
            FinancialProfile.status == RecordStatus.ACTIVE,
        )
        .order_by(FinancialProfile.type, FinancialProfile.name)
    )
    return list(result)


async def get_owned_profile(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
) -> FinancialProfile | None:
    profile: FinancialProfile | None = await db.scalar(
        select(FinancialProfile).where(
            FinancialProfile.id == profile_id,
            FinancialProfile.user_id == user_id,
            FinancialProfile.status == RecordStatus.ACTIVE,
        )
    )
    return profile


async def create_profile(
    db: AsyncSession,
    user: User,
    payload: FinancialProfileCreate,
    correlation_id: str | None = None,
) -> FinancialProfile:
    if payload.type == FinancialProfileType.PERSONAL:
        existing_personal = await db.scalar(
            select(FinancialProfile).where(
                FinancialProfile.user_id == user.id,
                FinancialProfile.type == FinancialProfileType.PERSONAL,
                FinancialProfile.status == RecordStatus.ACTIVE,
            )
        )
        if existing_personal is not None:
            raise ValueError("An active personal profile already exists.")

    profile = FinancialProfile(
        user_id=user.id,
        type=payload.type,
        name=payload.name,
        document_last4=payload.document_last4,
        currency=user.base_currency,
        timezone=user.timezone,
    )
    db.add(profile)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="financial_profile.created",
        target_type="financial_profile",
        target_id=profile.id,
        correlation_id=correlation_id,
        safe_metadata={"profile_type": profile.type.value},
    )
    return profile


async def create_manual_account(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: AccountCreate,
    correlation_id: str | None = None,
) -> FinancialAccount:
    account = FinancialAccount(
        user_id=user.id,
        financial_profile_id=profile.id,
        name=payload.name,
        institution_name=payload.institution_name,
        type=payload.type,
        source=AccountSource.MANUAL,
        current_balance=payload.current_balance,
        currency=profile.currency,
    )
    db.add(account)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="account.manual_created",
        target_type="account",
        target_id=account.id,
        correlation_id=correlation_id,
        safe_metadata={"profile_type": profile.type.value},
    )
    return account


async def grant_consent(
    db: AsyncSession,
    user: User,
    payload: ConsentCreate,
    correlation_id: str | None = None,
) -> UserConsent:
    if payload.financial_profile_id is not None:
        profile = await get_owned_profile(db, user.id, payload.financial_profile_id)
        if profile is None:
            raise LookupError("Financial profile not found.")

    existing = await db.scalar(
        select(UserConsent).where(
            UserConsent.user_id == user.id,
            UserConsent.financial_profile_id == payload.financial_profile_id,
            UserConsent.consent_type == payload.consent_type,
            UserConsent.version == payload.version,
            UserConsent.revoked_at.is_(None),
        )
    )
    if existing is not None:
        return existing

    consent = UserConsent(
        user_id=user.id,
        financial_profile_id=payload.financial_profile_id,
        consent_type=payload.consent_type,
        version=payload.version,
    )
    db.add(consent)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="consent.granted",
        target_type="consent",
        target_id=consent.id,
        correlation_id=correlation_id,
        safe_metadata={"consent_type": payload.consent_type, "version": payload.version},
    )
    return consent


async def onboarding_state(
    db: AsyncSession,
    user: User,
) -> tuple[int, int, bool]:
    profile_count = await db.scalar(
        select(func.count())
        .select_from(FinancialProfile)
        .where(
            FinancialProfile.user_id == user.id,
            FinancialProfile.status == RecordStatus.ACTIVE,
        )
    )
    account_count = await db.scalar(
        select(func.count())
        .select_from(FinancialAccount)
        .where(
            FinancialAccount.user_id == user.id,
            FinancialAccount.status == RecordStatus.ACTIVE,
        )
    )
    consent = await db.scalar(
        select(UserConsent.id).where(
            UserConsent.user_id == user.id,
            UserConsent.consent_type == PRIVACY_CONSENT_TYPE,
            UserConsent.version == PRIVACY_CONSENT_VERSION,
            UserConsent.revoked_at.is_(None),
        )
    )
    return int(profile_count or 0), int(account_count or 0), consent is not None


async def complete_onboarding(
    db: AsyncSession,
    user: User,
    correlation_id: str | None = None,
) -> None:
    profile_count, account_count, consent_granted = await onboarding_state(db, user)
    if profile_count < 1 or account_count < 1 or not consent_granted:
        raise ValueError("Onboarding requirements are incomplete.")
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(UTC)
        await record_audit_event(
            db,
            user_id=user.id,
            action="onboarding.completed",
            target_type="user",
            target_id=user.id,
            correlation_id=correlation_id,
        )
