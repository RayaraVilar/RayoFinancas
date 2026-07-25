from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.main import app
from app.modules.banking.models import (
    BankConnection,
    BankConnectionStatus,
    BankProviderName,
    BankWebhookEvent,
)
from app.modules.banking.ports import (
    CanonicalAccount,
    CanonicalAccountKind,
    CanonicalTransaction,
    CanonicalTransactionDirection,
    ConnectToken,
    ProviderItem,
    TransactionPage,
)
from app.modules.banking.sync import synchronize_bank_connection
from app.modules.business.models import (
    EmailIngestionConsent,
    InboxCandidate,
    InboxReviewStatus,
    NotificationPreference,
    Receivable,
    Subscription,
)
from app.modules.debts.models import Debt, DebtPayment
from app.modules.future.models import HealthScoreSnapshot, NetWorthSnapshot
from app.modules.goals.models import (
    Goal,
    GoalContribution,
    GoalPlanVersion,
    GoalScenario,
    PendingAction,
)
from app.modules.identity.models import (
    AuditEvent,
    FinancialAccount,
    FinancialProfile,
    OAuthIdentity,
    Session,
    User,
    UserConsent,
)
from app.modules.identity.service import create_session
from app.modules.insights.models import Insight, InsightFeedback
from app.modules.ledger.models import (
    CardInvoice,
    Category,
    CategoryRule,
    CreditCard,
    Transaction,
    TransactionSplit,
)
from app.modules.payments.models import Payment, PaymentItem, PaymentSimulation
from app.modules.planning.models import Bill, MonthlyBudget, MonthlyPlan


class SanitizedFixtureProvider:
    transaction_status = "PENDING"

    async def create_connect_token(self, *, client_user_id: str) -> ConnectToken:
        return ConnectToken(value="fixture-token", expires_in_seconds=1800)

    async def get_item(self, external_item_id: str) -> ProviderItem:
        return ProviderItem(
            external_id=external_item_id,
            client_user_id=None,
            connector_id="fixture",
            connector_name="Banco de testes",
            status="UPDATED",
            updated_at=None,
        )

    async def revoke_item(self, external_item_id: str) -> None:
        return None

    async def list_accounts(self, external_item_id: str) -> list[CanonicalAccount]:
        return [
            CanonicalAccount(
                external_id="account-fixture-1",
                item_external_id=external_item_id,
                kind=CanonicalAccountKind.CHECKING,
                name="Conta sanitizada",
                institution_name="Banco de testes",
                balance=Decimal("1500.25"),
                currency="BRL",
                credit_limit=None,
                closing_date=None,
                due_date=None,
            )
        ]

    async def list_transactions(
        self,
        external_account_id: str,
        *,
        account_kind: CanonicalAccountKind,
        cursor: str | None = None,
    ) -> TransactionPage:
        _ = account_kind, cursor
        return TransactionPage(
            items=[
                CanonicalTransaction(
                    external_id="transaction-fixture-1",
                    account_external_id=external_account_id,
                    description="Mercado sanitizado",
                    amount=Decimal("42.90"),
                    direction=CanonicalTransactionDirection.DEBIT,
                    occurred_at=datetime(2026, 7, 23, 12, tzinfo=UTC),
                    status=self.transaction_status,
                    currency="BRL",
                    provider_category_id=None,
                    provider_category_name="Alimentação",
                )
            ],
            next_cursor=None,
        )


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RAYO_RUN_INTEGRATION") != "1",
        reason="Set RAYO_RUN_INTEGRATION=1 to test PostgreSQL.",
    ),
]


async def clear_identity_tables() -> None:
    async with get_session_factory()() as db:
        for model in (
            AuditEvent,
            PaymentItem,
            Payment,
            PaymentSimulation,
            InboxCandidate,
            NotificationPreference,
            EmailIngestionConsent,
            Subscription,
            Receivable,
            InsightFeedback,
            Insight,
            BankWebhookEvent,
            BankConnection,
            UserConsent,
            PendingAction,
            HealthScoreSnapshot,
            NetWorthSnapshot,
            DebtPayment,
            Debt,
            GoalScenario,
            GoalPlanVersion,
            GoalContribution,
            Goal,
            Bill,
            MonthlyBudget,
            MonthlyPlan,
            TransactionSplit,
            Transaction,
            CardInvoice,
            CreditCard,
            CategoryRule,
            FinancialAccount,
            FinancialProfile,
            Session,
            OAuthIdentity,
            User,
        ):
            await db.execute(delete(model))
        await db.execute(delete(Category).where(Category.system_code.is_(None)))
        await db.commit()


@pytest.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    await clear_identity_tables()
    yield
    await clear_identity_tables()


async def authenticated_client(email: str) -> tuple[AsyncClient, User, str]:
    settings = get_settings()
    async with get_session_factory()() as db:
        user = User(email=email, display_name=email.split("@")[0].title())
        db.add(user)
        await db.flush()
        credentials = await create_session(db, user.id, settings)
        await db.commit()

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    client.cookies.set(settings.session_cookie_name, credentials.token)
    client.cookies.set(settings.csrf_cookie_name, credentials.csrf_token)
    return client, user, credentials.csrf_token


async def test_privacy_export_and_deletion_revoke_access() -> None:
    client, _, csrf_token = await authenticated_client("privacy@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Dados exportáveis"},
            headers=headers,
        )
        assert profile.status_code == 201

        exported = await client.get("/api/v1/privacy/export")
        assert exported.status_code == 200
        assert exported.headers["cache-control"] == "no-store"
        assert exported.json()["user"]["email"] == "privacy@example.com"
        assert exported.json()["datasets"]["financial_profiles"][0]["name"] == ("Dados exportáveis")

        deletion = await client.post("/api/v1/privacy/delete-account", headers=headers)
        assert deletion.status_code == 202
        assert deletion.json()["status"] == "DELETION_PENDING"
        assert "rayo_session=" in deletion.headers["set-cookie"]

        current_user = await client.get("/api/v1/auth/me")
        assert current_user.status_code == 401


async def test_business_inbox_receivables_subscriptions_and_notifications() -> None:
    client, user, csrf_token = await authenticated_client("empresa@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile_response = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "BUSINESS", "name": "Empresa"},
            headers=headers,
        )
        profile_id = profile_response.json()["id"]

        receivable = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/receivables",
            json={
                "description": "Projeto entregue",
                "counterparty": "Cliente",
                "amount": "1250.00",
                "due_on": "2026-08-05",
                "confirmed": True,
            },
            headers=headers,
        )
        assert receivable.status_code == 201
        transitioned = await client.post(
            f"/api/v1/receivables/{receivable.json()['id']}/transition",
            json={
                "target_status": "RECEIVED",
                "version": 1,
                "received_on": "2026-08-04",
            },
            headers=headers,
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "RECEIVED"

        subscription = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/subscriptions",
            json={
                "name": "Software contábil",
                "amount": "99.90",
                "cadence_months": 1,
                "next_charge_on": "2026-08-10",
            },
            headers=headers,
        )
        assert subscription.status_code == 201
        subscriptions = await client.get(f"/api/v1/financial-profiles/{profile_id}/subscriptions")
        assert [item["name"] for item in subscriptions.json()] == ["Software contábil"]

        async with get_session_factory()() as db:
            candidate = InboxCandidate(
                user_id=user.id,
                financial_profile_id=profile_id,
                source="EMAIL",
                dedupe_key="candidate-test-0001",
                sender_domain_hash="sanitized",
                extracted_fields={
                    "description": "Boleto candidato",
                    "amount": "310.00",
                },
                risk_flags=["UNTRUSTED_EXTERNAL_CONTENT"],
            )
            db.add(candidate)
            await db.commit()
            candidate_id = candidate.id

        inbox = await client.get(f"/api/v1/financial-profiles/{profile_id}/inbox-candidates")
        assert inbox.status_code == 200
        assert inbox.json()[0]["status"] == InboxReviewStatus.REVIEW_REQUIRED
        reviewed = await client.patch(
            f"/api/v1/inbox-candidates/{candidate_id}",
            json={"status": "REJECTED"},
            headers=headers,
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "REJECTED"

        preference = await client.put(
            "/api/v1/notification-preferences/EMAIL",
            json={
                "channel": "EMAIL",
                "enabled": True,
                "event_types": ["BILL_DUE", "LOW_BALANCE", "BILL_DUE"],
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
            },
            headers=headers,
        )
        assert preference.status_code == 200
        assert preference.json()["event_types"] == ["BILL_DUE", "LOW_BALANCE"]
        listed_preferences = await client.get("/api/v1/notification-preferences")
        assert listed_preferences.json()[0]["enabled"] is True


async def test_onboarding_requires_csrf_and_completes_vertical_flow() -> None:
    client, _, csrf_token = await authenticated_client("ana@example.com")
    async with client:
        rejected = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Vida pessoal"},
        )
        assert rejected.status_code == 403

        headers = {"X-CSRF-Token": csrf_token}
        profile_response = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Vida pessoal"},
            headers=headers,
        )
        assert profile_response.status_code == 201
        profile_id = profile_response.json()["id"]

        account_response = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/accounts",
            json={
                "name": "Conta principal",
                "institution_name": "Banco manual",
                "type": "CHECKING",
                "current_balance": "1200.50",
            },
            headers=headers,
        )
        assert account_response.status_code == 201

        consent_response = await client.post(
            "/api/v1/onboarding/privacy-consent",
            headers=headers,
        )
        assert consent_response.status_code == 201

        complete_response = await client.post(
            "/api/v1/onboarding/complete",
            headers=headers,
        )
        assert complete_response.status_code == 204

        state_response = await client.get("/api/v1/onboarding/state")
        assert state_response.json() == {
            "profile_count": 1,
            "account_count": 1,
            "privacy_consent_granted": True,
            "completed": True,
        }


async def test_profile_context_is_isolated_between_users() -> None:
    first_client, _, first_csrf = await authenticated_client("first@example.com")
    second_client, _, second_csrf = await authenticated_client("second@example.com")
    async with first_client, second_client:
        first_profile = await first_client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Perfil A"},
            headers={"X-CSRF-Token": first_csrf},
        )
        second_profile = await second_client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Perfil B"},
            headers={"X-CSRF-Token": second_csrf},
        )
        assert first_profile.status_code == 201
        assert second_profile.status_code == 201
        second_profile_id = second_profile.json()["id"]

        accounts_response = await first_client.get(
            f"/api/v1/financial-profiles/{second_profile_id}/accounts"
        )
        assert accounts_response.status_code == 404

        context_response = await first_client.get(
            "/api/v1/financial-context",
            headers={"X-Financial-Profile-Id": second_profile_id},
        )
        assert context_response.status_code == 404


async def test_bank_sync_is_idempotent_and_promotes_pending_transaction() -> None:
    provider = SanitizedFixtureProvider()
    async with get_session_factory()() as db:
        user = User(email="sync@example.com", display_name="Sync")
        db.add(user)
        await db.flush()
        profile = FinancialProfile(
            user_id=user.id,
            type="PERSONAL",
            name="Perfil sincronizado",
        )
        db.add(profile)
        await db.flush()
        connection = BankConnection(
            user_id=user.id,
            financial_profile_id=profile.id,
            provider=BankProviderName.MOCK,
            external_item_id="item-fixture-1",
            connector_name="Banco de testes",
            status=BankConnectionStatus.HEALTHY,
        )
        db.add(connection)
        await db.flush()

        first = await synchronize_bank_connection(db, connection, provider)
        await db.commit()
        assert first.accounts == 1
        assert first.transactions == 1

        provider.transaction_status = "POSTED"
        second = await synchronize_bank_connection(db, connection, provider)
        await db.commit()
        assert second.accounts == 1
        assert second.transactions == 1

        accounts = (
            await db.scalars(
                select(FinancialAccount).where(FinancialAccount.bank_connection_id == connection.id)
            )
        ).all()
        transactions = (
            await db.scalars(
                select(Transaction).where(Transaction.bank_connection_id == connection.id)
            )
        ).all()
        assert len(accounts) == 1
        assert len(transactions) == 1
        assert transactions[0].status.value == "POSTED"
        assert transactions[0].version == 2


async def test_bills_free_balance_and_monthly_plan_are_explainable() -> None:
    client, _, csrf_token = await authenticated_client("planning@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile_response = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Planejamento"},
            headers=headers,
        )
        profile_id = profile_response.json()["id"]
        await client.post(
            f"/api/v1/financial-profiles/{profile_id}/accounts",
            json={
                "name": "Conta",
                "type": "CHECKING",
                "current_balance": "2000.00",
            },
            headers=headers,
        )
        bill_payload = {
            "description": "Energia",
            "amount": "200.00",
            "due_on": "2026-07-29",
        }
        first = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/bills",
            json=bill_payload,
            headers=headers,
        )
        repeated = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/bills",
            json=bill_payload,
            headers=headers,
        )
        assert first.status_code == 201
        assert repeated.json()["id"] == first.json()["id"]
        confirmed = await client.post(
            f"/api/v1/bills/{first.json()['id']}/transition",
            json={"target_status": "CONFIRMED", "version": 1},
            headers=headers,
        )
        assert confirmed.status_code == 200
        plan = await client.put(
            f"/api/v1/financial-profiles/{profile_id}/monthly-plan",
            json={
                "competence_month": "2026-07-01",
                "expected_income": "3000.00",
                "essential_commitment": "300.00",
                "debt_commitment": "100.00",
                "goal_contribution": "250.00",
            },
            headers=headers,
        )
        assert plan.status_code == 200
        summary = await client.get(
            f"/api/v1/financial-profiles/{profile_id}/planning/summary?as_of=2026-07-24"
        )
        assert summary.status_code == 200
        data = summary.json()
        assert data["confirmed_bills"] == "200.00"
        assert data["planned_commitments"] == "650.00"
        assert data["free_balance"] == "1350.00"
        assert data["projected_deficit"] is False


async def test_goal_scenario_only_mutates_after_structured_confirmation() -> None:
    client, _, csrf_token = await authenticated_client("goals@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile_response = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Metas"},
            headers=headers,
        )
        profile_id = profile_response.json()["id"]
        created = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/goals",
            json={
                "name": "Reserva",
                "target_amount": "12000.00",
                "current_amount": "2000.00",
                "target_date": "2027-07-24",
                "monthly_contribution": "500.00",
            },
            headers=headers,
        )
        assert created.status_code == 201
        goal_id = created.json()["id"]
        proposal = await client.post(
            f"/api/v1/goals/{goal_id}/scenarios",
            json={
                "monthly_contribution": "900.00",
                "target_date": "2027-07-24",
                "idempotency_key": "goal-scenario-0001",
            },
            headers=headers,
        )
        assert proposal.status_code == 201
        assert len(proposal.json()["scenarios"]) == 4
        before = await client.get(f"/api/v1/financial-profiles/{profile_id}/goals")
        assert before.json()[0]["monthly_contribution"] == "500.00"

        action_id = proposal.json()["pending_action"]["id"]
        confirmed = await client.post(
            f"/api/v1/pending-actions/{action_id}/confirm",
            headers=headers,
        )
        repeated = await client.post(
            f"/api/v1/pending-actions/{action_id}/confirm",
            headers=headers,
        )
        assert confirmed.status_code == 200
        assert repeated.status_code == 200
        assert confirmed.json()["monthly_contribution"] == "900.00"
        assert confirmed.json()["version"] == repeated.json()["version"] == 2


async def test_manual_transactions_categories_totals_and_cursor() -> None:
    client, _, csrf_token = await authenticated_client("ledger@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile_response = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Meu dinheiro"},
            headers=headers,
        )
        profile_id = profile_response.json()["id"]
        account_response = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/accounts",
            json={
                "name": "Conta principal",
                "type": "CHECKING",
                "current_balance": "0",
            },
            headers=headers,
        )
        account_id = account_response.json()["id"]

        categories_response = await client.get(
            f"/api/v1/financial-profiles/{profile_id}/categories"
        )
        assert categories_response.status_code == 200
        categories = categories_response.json()
        assert len(categories) == 8
        income_category = next(item for item in categories if item["system_code"] == "income")
        food_category = next(item for item in categories if item["system_code"] == "food")

        for payload in (
            {
                "account_id": account_id,
                "category_id": income_category["id"],
                "kind": "INCOME",
                "description": "Salário",
                "amount": "5000.00",
                "occurred_on": "2026-07-05",
            },
            {
                "account_id": account_id,
                "category_id": food_category["id"],
                "kind": "EXPENSE",
                "description": "Supermercado",
                "amount": "350.25",
                "occurred_on": "2026-07-06",
            },
        ):
            response = await client.post(
                f"/api/v1/financial-profiles/{profile_id}/transactions",
                json=payload,
                headers=headers,
            )
            assert response.status_code == 201
            assert response.json()["competence_month"] == "2026-07-01"

        listing = await client.get(
            "/api/v1/transactions?limit=1",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        assert listing.status_code == 200
        page = listing.json()
        assert len(page["items"]) == 1
        assert page["next_cursor"] is not None
        assert page["income_total"] == "5000.00"
        assert page["expense_total"] == "350.25"
        assert page["net_total"] == "4649.75"

        analytics_response = await client.get(
            "/api/v1/analytics/dashboard?as_of=2026-07-06",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        assert analytics_response.status_code == 200
        analytics = analytics_response.json()
        assert analytics["income"]["value"] == "5000.00"
        assert analytics["expense"]["value"] == "350.25"
        assert analytics["monthly_balance"]["value"] == "4649.75"
        assert analytics["projected_month_expense"] == "1809.63"
        assert analytics["categories"][0]["category"] == food_category["name"]
        assert analytics["coverage"]["categorized_percent"] == "100.0"

        filtered = await client.get(
            "/api/v1/transactions?kind=EXPENSE&query=mercado",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        assert [item["description"] for item in filtered.json()["items"]] == ["Supermercado"]


async def test_transaction_update_void_and_user_isolation() -> None:
    first_client, _, first_csrf = await authenticated_client("owner@example.com")
    second_client, _, second_csrf = await authenticated_client("outsider@example.com")
    async with first_client, second_client:
        first_headers = {"X-CSRF-Token": first_csrf}
        profile_response = await first_client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Proprietário"},
            headers=first_headers,
        )
        profile_id = profile_response.json()["id"]
        account_response = await first_client.post(
            f"/api/v1/financial-profiles/{profile_id}/accounts",
            json={"name": "Carteira", "type": "CASH", "current_balance": "0"},
            headers=first_headers,
        )
        transaction_response = await first_client.post(
            f"/api/v1/financial-profiles/{profile_id}/transactions",
            json={
                "account_id": account_response.json()["id"],
                "kind": "EXPENSE",
                "description": "Café",
                "amount": "12.50",
                "occurred_on": "2026-07-24",
            },
            headers=first_headers,
        )
        transaction = transaction_response.json()

        forbidden_update = await second_client.patch(
            f"/api/v1/transactions/{transaction['id']}",
            json={"description": "Invasão", "version": 1},
            headers={"X-CSRF-Token": second_csrf},
        )
        assert forbidden_update.status_code == 404

        updated = await first_client.patch(
            f"/api/v1/transactions/{transaction['id']}",
            json={"description": "Café da manhã", "amount": "18.00", "version": 1},
            headers=first_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2

        stale = await first_client.patch(
            f"/api/v1/transactions/{transaction['id']}",
            json={"description": "Versão antiga", "version": 1},
            headers=first_headers,
        )
        assert stale.status_code == 409

        voided = await first_client.delete(
            f"/api/v1/transactions/{transaction['id']}",
            headers=first_headers,
        )
        assert voided.status_code == 204
        listing = await first_client.get(
            "/api/v1/transactions",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        assert listing.json()["items"] == []


async def test_credit_card_invoice_payment_does_not_duplicate_expense() -> None:
    client, _, csrf_token = await authenticated_client("cards@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile_response = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Cartões"},
            headers=headers,
        )
        profile_id = profile_response.json()["id"]
        account_response = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/accounts",
            json={"name": "Conta pagadora", "type": "CHECKING", "current_balance": "1000"},
            headers=headers,
        )
        account_id = account_response.json()["id"]
        card_response = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/credit-cards",
            json={
                "name": "Cartão principal",
                "last_four": "4242",
                "closing_day": 10,
                "due_day": 17,
                "credit_limit": "5000.00",
            },
            headers=headers,
        )
        assert card_response.status_code == 201
        card_id = card_response.json()["id"]
        categories = (
            await client.get(f"/api/v1/financial-profiles/{profile_id}/categories")
        ).json()
        food_category = next(item for item in categories if item["system_code"] == "food")

        purchase = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/transactions",
            json={
                "credit_card_id": card_id,
                "category_id": food_category["id"],
                "kind": "EXPENSE",
                "description": "Supermercado no cartão",
                "amount": "200.00",
                "occurred_on": "2026-07-08",
            },
            headers=headers,
        )
        assert purchase.status_code == 201
        assert purchase.json()["account_id"] is None
        assert purchase.json()["card_invoice_id"] is not None

        invoices = await client.get(f"/api/v1/financial-profiles/{profile_id}/card-invoices")
        assert invoices.status_code == 200
        invoice = invoices.json()[0]
        assert invoice["due_on"] == "2026-07-17"
        assert invoice["total_amount"] == "200.00"

        paid = await client.post(
            f"/api/v1/card-invoices/{invoice['id']}/pay",
            json={"account_id": account_id, "paid_on": "2026-07-17"},
            headers=headers,
        )
        assert paid.status_code == 200
        assert paid.json()["status"] == "PAID"

        repeated = await client.post(
            f"/api/v1/card-invoices/{invoice['id']}/pay",
            json={"account_id": account_id, "paid_on": "2026-07-17"},
            headers=headers,
        )
        assert repeated.status_code == 200

        listing = await client.get(
            "/api/v1/transactions",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        data = listing.json()
        assert data["expense_total"] == "200.00"
        assert Decimal(data["income_total"]) == Decimal("0.00")
        assert len(data["items"]) == 2
        assert {item["kind"] for item in data["items"]} == {"EXPENSE", "TRANSFER"}


async def test_paired_transfer_is_idempotent_and_excluded_from_totals() -> None:
    client, _, csrf_token = await authenticated_client("transfer@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Transferências"},
            headers=headers,
        )
        profile_id = profile.json()["id"]
        account_ids: list[str] = []
        for name in ("Conta A", "Conta B"):
            response = await client.post(
                f"/api/v1/financial-profiles/{profile_id}/accounts",
                json={"name": name, "type": "CHECKING", "current_balance": "0"},
                headers=headers,
            )
            account_ids.append(response.json()["id"])

        payload = {
            "source_account_id": account_ids[0],
            "destination_account_id": account_ids[1],
            "description": "Reserva mensal",
            "amount": "300.00",
            "occurred_on": "2026-07-24",
            "idempotency_key": "4dd60f8e-c79f-466e-8fd4-28dbfda07433",
        }
        created = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/transfers",
            json=payload,
            headers=headers,
        )
        assert created.status_code == 201
        transfer_group_id = created.json()["transfer_group_id"]
        assert created.json()["outflow"]["transfer_direction"] == "OUTFLOW"
        assert created.json()["inflow"]["transfer_direction"] == "INFLOW"

        repeated = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/transfers",
            json=payload,
            headers=headers,
        )
        assert repeated.status_code == 201
        assert repeated.json()["transfer_group_id"] == transfer_group_id

        listing = await client.get(
            "/api/v1/transactions",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        data = listing.json()
        assert Decimal(data["income_total"]) == Decimal("0")
        assert Decimal(data["expense_total"]) == Decimal("0")
        assert len(data["items"]) == 2


async def test_refund_is_idempotent_and_reduces_original_total() -> None:
    client, _, csrf_token = await authenticated_client("refund@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Estornos"},
            headers=headers,
        )
        profile_id = profile.json()["id"]
        account = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/accounts",
            json={"name": "Conta principal", "type": "CHECKING", "current_balance": "0"},
            headers=headers,
        )
        transaction = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/transactions",
            json={
                "account_id": account.json()["id"],
                "kind": "EXPENSE",
                "description": "Compra cancelada",
                "amount": "125.90",
                "occurred_on": "2026-07-20",
            },
            headers=headers,
        )
        transaction_id = transaction.json()["id"]
        payload = {"occurred_on": "2026-07-24"}

        refund = await client.post(
            f"/api/v1/transactions/{transaction_id}/refund",
            json=payload,
            headers=headers,
        )
        assert refund.status_code == 200
        assert refund.json()["reversal_of_transaction_id"] == transaction_id

        repeated = await client.post(
            f"/api/v1/transactions/{transaction_id}/refund",
            json=payload,
            headers=headers,
        )
        assert repeated.status_code == 200
        assert repeated.json()["id"] == refund.json()["id"]

        listing = await client.get(
            "/api/v1/transactions",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        data = listing.json()
        assert Decimal(data["expense_total"]) == Decimal("0")
        assert Decimal(data["income_total"]) == Decimal("0")
        assert len(data["items"]) == 2


async def test_category_rule_applies_and_split_reconciles_exact_amount() -> None:
    client, _, csrf_token = await authenticated_client("split@example.com")
    headers = {"X-CSRF-Token": csrf_token}
    async with client:
        profile = await client.post(
            "/api/v1/financial-profiles",
            json={"type": "PERSONAL", "name": "Organização"},
            headers=headers,
        )
        profile_id = profile.json()["id"]
        account = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/accounts",
            json={"name": "Conta principal", "type": "CHECKING", "current_balance": "0"},
            headers=headers,
        )
        categories = (
            await client.get(f"/api/v1/financial-profiles/{profile_id}/categories")
        ).json()
        transport = next(item for item in categories if item["system_code"] == "transport")
        leisure = next(item for item in categories if item["system_code"] == "leisure")

        rule = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/category-rules",
            json={"match_text": "  UBER  ", "category_id": transport["id"], "priority": 200},
            headers=headers,
        )
        assert rule.status_code == 201
        assert rule.json()["match_text"] == "UBER"

        transaction = await client.post(
            f"/api/v1/financial-profiles/{profile_id}/transactions",
            json={
                "account_id": account.json()["id"],
                "kind": "EXPENSE",
                "description": "Uber e passeio",
                "amount": "100.00",
                "occurred_on": "2026-07-24",
            },
            headers=headers,
        )
        assert transaction.status_code == 201
        assert transaction.json()["category_id"] == transport["id"]
        transaction_id = transaction.json()["id"]

        mismatch = await client.put(
            f"/api/v1/transactions/{transaction_id}/splits",
            json={
                "version": 1,
                "items": [
                    {"category_id": transport["id"], "amount": "40.00"},
                    {"category_id": leisure["id"], "amount": "50.00"},
                ],
            },
            headers=headers,
        )
        assert mismatch.status_code == 422

        split = await client.put(
            f"/api/v1/transactions/{transaction_id}/splits",
            json={
                "version": 1,
                "items": [
                    {
                        "category_id": transport["id"],
                        "amount": "40.00",
                        "description": "Transporte",
                    },
                    {
                        "category_id": leisure["id"],
                        "amount": "60.00",
                        "description": "Passeio",
                    },
                ],
            },
            headers=headers,
        )
        assert split.status_code == 200
        assert split.json()["transaction_version"] == 2
        assert sum(
            (Decimal(item["amount"]) for item in split.json()["items"]),
            Decimal("0"),
        ) == Decimal("100.00")

        listing = await client.get(
            "/api/v1/transactions",
            headers={"X-Financial-Profile-Id": profile_id},
        )
        assert Decimal(listing.json()["expense_total"]) == Decimal("100.00")
