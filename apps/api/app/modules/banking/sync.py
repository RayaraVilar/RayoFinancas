from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.banking.models import BankConnection, BankConnectionStatus
from app.modules.banking.pluggy import BankProviderError
from app.modules.banking.ports import (
    BankProvider,
    CanonicalAccount,
    CanonicalAccountKind,
    CanonicalTransaction,
    CanonicalTransactionDirection,
)
from app.modules.identity.models import (
    AccountSource,
    AccountType,
    FinancialAccount,
    RecordStatus,
)
from app.modules.identity.service import record_audit_event
from app.modules.ledger.models import (
    CardInvoice,
    CreditCard,
    Transaction,
    TransactionKind,
    TransactionSource,
    TransactionStatus,
)
from app.modules.ledger.service import invoice_dates, match_category_rule

MAX_TRANSACTION_PAGES = 500


@dataclass(frozen=True)
class BankSyncResult:
    accounts: int
    transactions: int


def account_type(kind: CanonicalAccountKind) -> AccountType:
    return {
        CanonicalAccountKind.CHECKING: AccountType.CHECKING,
        CanonicalAccountKind.SAVINGS: AccountType.SAVINGS,
        CanonicalAccountKind.PAYMENT: AccountType.PAYMENT,
    }.get(kind, AccountType.OTHER)


def card_day(value: object, default: int) -> int:
    day = getattr(value, "day", default)
    return max(1, min(int(day), 28))


def is_transfer_like(item: CanonicalTransaction) -> bool:
    normalized = item.description.casefold()
    terms = (
        "pagamento de fatura",
        "pagamento fatura",
        "transferencia",
        "transferência",
        "pix enviado",
        "pix recebido",
    )
    return any(term in normalized for term in terms)


def transaction_kind(
    item: CanonicalTransaction,
    account_kind_value: CanonicalAccountKind,
) -> TransactionKind:
    if is_transfer_like(item):
        return TransactionKind.TRANSFER
    if account_kind_value == CanonicalAccountKind.CREDIT_CARD:
        return (
            TransactionKind.EXPENSE
            if item.direction == CanonicalTransactionDirection.DEBIT
            else TransactionKind.TRANSFER
        )
    return (
        TransactionKind.INCOME
        if item.direction == CanonicalTransactionDirection.CREDIT
        else TransactionKind.EXPENSE
    )


def transaction_status(provider_status: str) -> TransactionStatus:
    return (
        TransactionStatus.PENDING
        if provider_status.casefold() in {"pending", "in_progress"}
        else TransactionStatus.POSTED
    )


async def upsert_account(
    db: AsyncSession,
    connection: BankConnection,
    item: CanonicalAccount,
) -> FinancialAccount | CreditCard:
    if item.kind == CanonicalAccountKind.CREDIT_CARD:
        card = await db.scalar(
            select(CreditCard).where(
                CreditCard.bank_connection_id == connection.id,
                CreditCard.external_id == item.external_id,
            )
        )
        if card is None:
            card = CreditCard(
                user_id=connection.user_id,
                financial_profile_id=connection.financial_profile_id,
                bank_connection_id=connection.id,
                external_id=item.external_id,
                name=item.name[:100],
                closing_day=card_day(item.closing_date, 28),
                due_day=card_day(item.due_date, 10),
            )
            db.add(card)
        card.name = item.name[:100]
        card.institution_name = item.institution_name or connection.connector_name
        card.credit_limit = item.credit_limit or Decimal("0")
        card.currency = item.currency[:3]
        card.status = RecordStatus.ACTIVE
        await db.flush()
        return card

    account = await db.scalar(
        select(FinancialAccount).where(
            FinancialAccount.bank_connection_id == connection.id,
            FinancialAccount.external_id == item.external_id,
        )
    )
    if account is None:
        account = FinancialAccount(
            user_id=connection.user_id,
            financial_profile_id=connection.financial_profile_id,
            bank_connection_id=connection.id,
            external_id=item.external_id,
            name=item.name[:100],
            type=account_type(item.kind),
            source=AccountSource.BANK_PROVIDER,
        )
        db.add(account)
    account.name = item.name[:100]
    account.institution_name = item.institution_name or connection.connector_name
    account.type = account_type(item.kind)
    account.current_balance = item.balance
    account.currency = item.currency[:3]
    account.status = RecordStatus.ACTIVE
    await db.flush()
    return account


async def get_or_create_card_invoice(
    db: AsyncSession,
    connection: BankConnection,
    card: CreditCard,
    occurred_on: date,
) -> CardInvoice:
    competence, due_on = invoice_dates(occurred_on, card.closing_day, card.due_day)
    invoice = await db.scalar(
        select(CardInvoice).where(
            CardInvoice.credit_card_id == card.id,
            CardInvoice.competence_month == competence,
        )
    )
    if invoice is None:
        invoice = CardInvoice(
            user_id=connection.user_id,
            financial_profile_id=connection.financial_profile_id,
            credit_card_id=card.id,
            competence_month=competence,
            due_on=due_on,
        )
        db.add(invoice)
        await db.flush()
    return invoice


async def upsert_transaction(
    db: AsyncSession,
    connection: BankConnection,
    provider_account: CanonicalAccount,
    local_account: FinancialAccount | CreditCard,
    item: CanonicalTransaction,
) -> None:
    transaction = await db.scalar(
        select(Transaction).where(
            Transaction.bank_connection_id == connection.id,
            Transaction.external_id == item.external_id,
        )
    )
    kind = transaction_kind(item, provider_account.kind)
    occurred_on = item.occurred_at.date()
    card_invoice_id = None
    account_id = None
    credit_card_id = None
    if isinstance(local_account, CreditCard):
        credit_card_id = local_account.id
        if kind == TransactionKind.EXPENSE:
            invoice = await get_or_create_card_invoice(
                db,
                connection,
                local_account,
                occurred_on,
            )
            card_invoice_id = invoice.id
    else:
        account_id = local_account.id

    if transaction is None:
        category = (
            await match_category_rule(
                db,
                connection.user_id,
                connection.financial_profile_id,
                item.description,
                kind,
            )
            if kind != TransactionKind.TRANSFER
            else None
        )
        transaction = Transaction(
            user_id=connection.user_id,
            financial_profile_id=connection.financial_profile_id,
            bank_connection_id=connection.id,
            external_id=item.external_id,
            account_id=account_id,
            credit_card_id=credit_card_id,
            card_invoice_id=card_invoice_id,
            category_id=category.id if category else None,
            kind=kind,
            source=TransactionSource.BANK_PROVIDER,
            description=item.description[:160],
            amount=item.amount,
            currency=item.currency[:3],
            occurred_on=occurred_on,
            competence_month=occurred_on.replace(day=1),
            status=transaction_status(item.status),
        )
        db.add(transaction)
        return

    transaction.account_id = account_id
    transaction.credit_card_id = credit_card_id
    transaction.card_invoice_id = card_invoice_id
    transaction.kind = kind
    transaction.description = item.description[:160]
    transaction.amount = item.amount
    transaction.currency = item.currency[:3]
    transaction.occurred_on = occurred_on
    transaction.competence_month = occurred_on.replace(day=1)
    transaction.status = transaction_status(item.status)
    transaction.version += 1


async def synchronize_bank_connection(
    db: AsyncSession,
    connection: BankConnection,
    provider: BankProvider,
) -> BankSyncResult:
    if not connection.external_item_id:
        raise BankProviderError("missing_item", "Connection has no provider item.")
    if connection.status == BankConnectionStatus.REVOKED:
        raise BankProviderError("revoked", "Connection is revoked.")

    connection.status = BankConnectionStatus.SYNCING
    connection.sync_started_at = datetime.now(UTC)
    connection.error_code = None
    await db.flush()

    try:
        provider_accounts = await provider.list_accounts(connection.external_item_id)
        transaction_count = 0
        for provider_account in provider_accounts:
            local_account = await upsert_account(db, connection, provider_account)
            cursor: str | None = None
            seen_cursors: set[str] = set()
            for _ in range(MAX_TRANSACTION_PAGES):
                page = await provider.list_transactions(
                    provider_account.external_id,
                    account_kind=provider_account.kind,
                    cursor=cursor,
                )
                for item in page.items:
                    await upsert_transaction(
                        db,
                        connection,
                        provider_account,
                        local_account,
                        item,
                    )
                    transaction_count += 1
                if not page.next_cursor:
                    break
                if page.next_cursor in seen_cursors:
                    raise BankProviderError("cursor_loop", "Provider pagination did not advance.")
                seen_cursors.add(page.next_cursor)
                cursor = page.next_cursor
            else:
                raise BankProviderError("page_limit", "Provider pagination exceeded safety limit.")

        now = datetime.now(UTC)
        connection.status = BankConnectionStatus.HEALTHY
        connection.last_synced_at = now
        connection.sync_started_at = None
        connection.sync_accounts_total = len(provider_accounts)
        connection.sync_transactions_total = transaction_count
        connection.consecutive_failures = 0
        await record_audit_event(
            db,
            user_id=connection.user_id,
            action="bank_connection.synchronized",
            target_type="bank_connection",
            target_id=connection.id,
            correlation_id=None,
            safe_metadata={
                "accounts": str(len(provider_accounts)),
                "transactions": str(transaction_count),
            },
        )
        await db.flush()
        return BankSyncResult(
            accounts=len(provider_accounts),
            transactions=transaction_count,
        )
    except Exception as exc:
        connection.status = BankConnectionStatus.ERROR
        connection.error_code = exc.code if isinstance(exc, BankProviderError) else "sync_failed"
        connection.sync_started_at = None
        connection.consecutive_failures += 1
        await db.flush()
        raise
