from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.banking.models import BankConnection, BankConnectionStatus
from app.modules.business.models import (
    EmailIngestionConsent,
    InboxCandidate,
    NotificationPreference,
    Receivable,
    Subscription,
)
from app.modules.debts.models import Debt, DebtPayment
from app.modules.future.models import HealthScoreSnapshot, NetWorthSnapshot
from app.modules.goals.models import Goal, GoalContribution, GoalPlanVersion, GoalScenario
from app.modules.identity.models import (
    FinancialAccount,
    FinancialProfile,
    OAuthIdentity,
    Session,
    User,
    UserConsent,
    UserStatus,
)
from app.modules.insights.models import Insight, InsightFeedback
from app.modules.ledger.models import (
    CardInvoice,
    CategoryRule,
    CreditCard,
    Transaction,
    TransactionSplit,
)
from app.modules.payments.models import Payment, PaymentItem, PaymentSimulation
from app.modules.planning.models import Bill, MonthlyBudget, MonthlyPlan

EXPORT_MODELS = (
    OAuthIdentity,
    FinancialProfile,
    FinancialAccount,
    UserConsent,
    CreditCard,
    CardInvoice,
    Transaction,
    TransactionSplit,
    CategoryRule,
    Bill,
    MonthlyBudget,
    MonthlyPlan,
    Goal,
    GoalContribution,
    GoalPlanVersion,
    GoalScenario,
    Debt,
    DebtPayment,
    NetWorthSnapshot,
    HealthScoreSnapshot,
    Insight,
    InsightFeedback,
    PaymentSimulation,
    Payment,
    PaymentItem,
    Receivable,
    Subscription,
    InboxCandidate,
    NotificationPreference,
    BankConnection,
)


def _serialize_row(row: Any) -> dict[str, Any]:
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
        if column.name not in {"access_token", "refresh_token", "token_hash", "csrf_hash"}
    }


async def export_user_data(db: AsyncSession, user: User) -> dict[str, Any]:
    datasets: dict[str, list[dict[str, Any]]] = {}
    for model in EXPORT_MODELS:
        if not hasattr(model, "user_id"):
            continue
        rows = list(await db.scalars(select(model).where(model.user_id == user.id)))
        datasets[model.__tablename__] = [_serialize_row(row) for row in rows]

    email_consents = list(
        await db.scalars(
            select(EmailIngestionConsent).where(EmailIngestionConsent.user_id == user.id)
        )
    )
    datasets[EmailIngestionConsent.__tablename__] = [_serialize_row(row) for row in email_consents]
    return {
        "export_version": "2026-07.v1",
        "generated_at": datetime.now(UTC),
        "user": _serialize_row(user),
        "datasets": datasets,
    }


async def request_user_deletion(db: AsyncSession, user: User) -> datetime:
    requested_at = datetime.now(UTC)
    user.status = UserStatus.DELETION_PENDING
    await db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.revoked_at.is_(None))
        .values(revoked_at=requested_at)
    )
    await db.execute(
        update(UserConsent)
        .where(UserConsent.user_id == user.id, UserConsent.revoked_at.is_(None))
        .values(revoked_at=requested_at)
    )
    await db.execute(
        update(EmailIngestionConsent)
        .where(
            EmailIngestionConsent.user_id == user.id,
            EmailIngestionConsent.revoked_at.is_(None),
        )
        .values(revoked_at=requested_at)
    )
    await db.execute(
        update(BankConnection)
        .where(BankConnection.user_id == user.id)
        .values(status=BankConnectionStatus.REVOKED, revoked_at=requested_at)
    )
    return requested_at
