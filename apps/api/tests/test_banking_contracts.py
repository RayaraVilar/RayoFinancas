from datetime import UTC, datetime
from decimal import Decimal

from app.core.config import Settings
from app.modules.banking.pluggy import account_kind, transaction_direction
from app.modules.banking.ports import (
    CanonicalAccountKind,
    CanonicalTransaction,
    CanonicalTransactionDirection,
)
from app.modules.banking.service import webhook_payload_hash
from app.modules.banking.sync import transaction_kind, transaction_status
from app.modules.ledger.models import TransactionKind, TransactionStatus


def test_pluggy_account_types_are_normalized() -> None:
    assert (
        account_kind({"type": "BANK", "subtype": "CHECKING_ACCOUNT"})
        == CanonicalAccountKind.CHECKING
    )
    assert (
        account_kind({"type": "BANK", "subtype": "SAVINGS_ACCOUNT"}) == CanonicalAccountKind.SAVINGS
    )
    assert account_kind({"type": "CREDIT"}) == CanonicalAccountKind.CREDIT_CARD


def test_credit_card_sign_convention_is_normalized() -> None:
    assert (
        transaction_direction(
            {"amount": Decimal("50")},
            CanonicalAccountKind.CREDIT_CARD,
        )
        == CanonicalTransactionDirection.DEBIT
    )
    assert (
        transaction_direction(
            {"amount": Decimal("-50")},
            CanonicalAccountKind.CREDIT_CARD,
        )
        == CanonicalTransactionDirection.CREDIT
    )


def test_webhook_hash_is_order_independent() -> None:
    assert webhook_payload_hash({"event": "item/created", "eventId": "abc"}) == (
        webhook_payload_hash({"eventId": "abc", "event": "item/created"})
    )


def test_pluggy_requires_enablement_and_all_secrets() -> None:
    disabled = Settings(
        pluggy_enabled=False,
        pluggy_client_id="client",
        pluggy_client_secret="secret",
        pluggy_webhook_secret="webhook",
    )
    assert disabled.pluggy_configured is False
    enabled = Settings(
        pluggy_enabled=True,
        pluggy_client_id="client",
        pluggy_client_secret="secret",
        pluggy_webhook_secret="webhook",
    )
    assert enabled.pluggy_configured is True


def canonical_transaction(
    *,
    description: str = "Compra sanitizada",
    direction: CanonicalTransactionDirection = CanonicalTransactionDirection.DEBIT,
    status: str = "POSTED",
) -> CanonicalTransaction:
    return CanonicalTransaction(
        external_id="transaction-fixture",
        account_external_id="account-fixture",
        description=description,
        amount=Decimal("10.00"),
        direction=direction,
        occurred_at=datetime(2026, 7, 24, tzinfo=UTC),
        status=status,
        currency="BRL",
        provider_category_id=None,
        provider_category_name=None,
    )


def test_sync_classifies_card_purchase_and_avoids_double_counting_payment() -> None:
    purchase = canonical_transaction()
    payment = canonical_transaction(description="Pagamento de fatura")
    assert transaction_kind(purchase, CanonicalAccountKind.CREDIT_CARD) == TransactionKind.EXPENSE
    assert transaction_kind(payment, CanonicalAccountKind.CHECKING) == TransactionKind.TRANSFER


def test_sync_maps_pending_and_posted_statuses() -> None:
    assert transaction_status("PENDING") == TransactionStatus.PENDING
    assert transaction_status("POSTED") == TransactionStatus.POSTED
