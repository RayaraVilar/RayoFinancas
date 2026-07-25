from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.modules.business.models import (
    InboxCandidate,
    InboxReviewStatus,
    NotificationPreference,
    Receivable,
    ReceivableStatus,
    Subscription,
    SubscriptionStatus,
)
from app.modules.business.schemas import (
    BusinessCashflowResponse,
    GmailCapabilityResponse,
    InboxCandidateResponse,
    InboxReviewUpdate,
    NotificationPreferenceResponse,
    NotificationPreferenceUpsert,
    ReceivableCreate,
    ReceivableResponse,
    ReceivableTransition,
    SubscriptionCreate,
    SubscriptionResponse,
)
from app.modules.business.service import (
    business_cashflow,
    create_receivable,
    create_subscription_candidate,
    list_receivables,
    subscription_response,
)
from app.modules.identity.dependencies import CsrfScope, CurrentScope, DatabaseSession
from app.modules.identity.models import FinancialProfile, FinancialProfileType
from app.modules.identity.service import get_owned_profile

router = APIRouter()


async def require_business_profile(
    db: DatabaseSession,
    user_id: UUID,
    profile_id: UUID,
) -> FinancialProfile:
    profile = await get_owned_profile(db, user_id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    if profile.type != FinancialProfileType.BUSINESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This capability is available only in an Empresa profile.",
        )
    return profile


@router.get(
    "/financial-profiles/{profile_id}/receivables",
    response_model=list[ReceivableResponse],
    tags=["business"],
)
async def get_receivables(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[ReceivableResponse]:
    profile = await require_business_profile(db, scope.user.id, profile_id)
    return [
        ReceivableResponse.model_validate(item)
        for item in await list_receivables(db, scope.user.id, profile.id)
    ]


@router.post(
    "/financial-profiles/{profile_id}/receivables",
    response_model=ReceivableResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["business"],
)
async def post_receivable(
    profile_id: UUID,
    payload: ReceivableCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> ReceivableResponse:
    profile = await require_business_profile(db, scope.user.id, profile_id)
    item = await create_receivable(db, scope.user, profile, payload)
    await db.commit()
    return ReceivableResponse.model_validate(item)


@router.post(
    "/receivables/{receivable_id}/transition",
    response_model=ReceivableResponse,
    tags=["business"],
)
async def post_receivable_transition(
    receivable_id: UUID,
    payload: ReceivableTransition,
    db: DatabaseSession,
    scope: CsrfScope,
) -> ReceivableResponse:
    item = await db.scalar(
        select(Receivable).where(
            Receivable.id == receivable_id,
            Receivable.user_id == scope.user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receivable not found.")
    if item.version != payload.version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale version.")
    allowed = {
        ReceivableStatus.EXPECTED: {
            ReceivableStatus.RECEIVED,
            ReceivableStatus.DISMISSED,
        },
        ReceivableStatus.RECEIVED: set(),
        ReceivableStatus.DISMISSED: set(),
    }
    if payload.target_status not in allowed[item.status]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid transition.")
    if payload.target_status == ReceivableStatus.RECEIVED and payload.received_on is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="received_on is required.",
        )
    item.status = payload.target_status
    item.received_on = payload.received_on
    item.version += 1
    await db.commit()
    return ReceivableResponse.model_validate(item)


@router.get(
    "/financial-profiles/{profile_id}/business-calendar",
    response_model=BusinessCashflowResponse,
    tags=["business"],
)
async def get_business_calendar(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
    start: Annotated[date, Query(default_factory=date.today)],
    days: Annotated[int, Query(ge=1, le=365)] = 90,
) -> BusinessCashflowResponse:
    profile = await require_business_profile(db, scope.user.id, profile_id)
    return await business_cashflow(
        db,
        scope.user.id,
        profile.id,
        start,
        start + timedelta(days=days),
    )


@router.post(
    "/financial-profiles/{profile_id}/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["business"],
)
async def post_subscription(
    profile_id: UUID,
    payload: SubscriptionCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> SubscriptionResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    item = await create_subscription_candidate(db, scope.user, profile, payload)
    await db.commit()
    return subscription_response(item)


@router.get(
    "/financial-profiles/{profile_id}/subscriptions",
    response_model=list[SubscriptionResponse],
    tags=["business"],
)
async def get_subscriptions(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[SubscriptionResponse]:
    if await get_owned_profile(db, scope.user.id, profile_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    items = await db.scalars(
        select(Subscription)
        .where(
            Subscription.user_id == scope.user.id,
            Subscription.financial_profile_id == profile_id,
        )
        .order_by(Subscription.next_charge_on, Subscription.name)
    )
    return [subscription_response(item) for item in items]


@router.post(
    "/subscriptions/{subscription_id}/confirm",
    response_model=SubscriptionResponse,
    tags=["business"],
)
async def post_subscription_confirmation(
    subscription_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> SubscriptionResponse:
    item = await db.scalar(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == scope.user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    if item.status == SubscriptionStatus.CANDIDATE:
        item.status = SubscriptionStatus.CONFIRMED
        item.version += 1
    await db.commit()
    return subscription_response(item)


@router.get(
    "/financial-profiles/{profile_id}/gmail-ingestion",
    response_model=GmailCapabilityResponse,
    tags=["business"],
)
async def get_gmail_ingestion_capability(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> GmailCapabilityResponse:
    if await get_owned_profile(db, scope.user.id, profile_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return GmailCapabilityResponse()


@router.get(
    "/financial-profiles/{profile_id}/inbox-candidates",
    response_model=list[InboxCandidateResponse],
    tags=["business"],
)
async def get_inbox_candidates(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[InboxCandidateResponse]:
    await require_business_profile(db, scope.user.id, profile_id)
    items = await db.scalars(
        select(InboxCandidate)
        .where(
            InboxCandidate.user_id == scope.user.id,
            InboxCandidate.financial_profile_id == profile_id,
        )
        .order_by(InboxCandidate.created_at.desc())
    )
    return [InboxCandidateResponse.model_validate(item) for item in items]


@router.patch(
    "/inbox-candidates/{candidate_id}",
    response_model=InboxCandidateResponse,
    tags=["business"],
)
async def patch_inbox_candidate(
    candidate_id: UUID,
    payload: InboxReviewUpdate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> InboxCandidateResponse:
    item = await db.scalar(
        select(InboxCandidate).where(
            InboxCandidate.id == candidate_id,
            InboxCandidate.user_id == scope.user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    if item.status != InboxReviewStatus.REVIEW_REQUIRED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already reviewed.")
    if payload.status == InboxReviewStatus.REVIEW_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose ACCEPTED or REJECTED.",
        )
    item.status = payload.status
    await db.commit()
    return InboxCandidateResponse.model_validate(item)


@router.get(
    "/notification-preferences",
    response_model=list[NotificationPreferenceResponse],
    tags=["notifications"],
)
async def get_notification_preferences(
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[NotificationPreferenceResponse]:
    items = await db.scalars(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == scope.user.id)
        .order_by(NotificationPreference.channel)
    )
    return [NotificationPreferenceResponse.model_validate(item) for item in items]


@router.put(
    "/notification-preferences/{channel}",
    response_model=NotificationPreferenceResponse,
    tags=["notifications"],
)
async def put_notification_preference(
    channel: str,
    payload: NotificationPreferenceUpsert,
    db: DatabaseSession,
    scope: CsrfScope,
) -> NotificationPreferenceResponse:
    if channel != payload.channel:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Channel path and payload must match.",
        )
    item = await db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == scope.user.id,
            NotificationPreference.channel == channel,
        )
    )
    if item is None:
        item = NotificationPreference(user_id=scope.user.id, channel=channel)
        db.add(item)
    item.enabled = payload.enabled
    item.event_types = sorted(set(payload.event_types))
    item.quiet_hours_start = payload.quiet_hours_start
    item.quiet_hours_end = payload.quiet_hours_end
    await db.commit()
    await db.refresh(item)
    return NotificationPreferenceResponse.model_validate(item)
