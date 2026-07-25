from __future__ import annotations

import base64
import calendar
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import Select, and_, case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.modules.identity.models import FinancialAccount, FinancialProfile, RecordStatus, User
from app.modules.identity.service import record_audit_event
from app.modules.ledger.models import (
    CardInvoice,
    CardInvoiceStatus,
    Category,
    CategoryKind,
    CategoryRule,
    CreditCard,
    Transaction,
    TransactionKind,
    TransactionSplit,
    TransactionStatus,
    TransferDirection,
)
from app.modules.ledger.schemas import (
    CardInvoicePaymentCreate,
    CategoryCreate,
    CategoryRuleCreate,
    CreditCardCreate,
    RefundCreate,
    TransactionCreate,
    TransactionSplitReplace,
    TransactionUpdate,
    TransferCreate,
)


def normalize_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.casefold().split())


def encode_cursor(item: Transaction) -> str:
    raw = f"{item.occurred_on.isoformat()}|{item.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(value: str) -> tuple[date, UUID]:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        occurred, transaction_id = raw.split("|", 1)
        return date.fromisoformat(occurred), UUID(transaction_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid pagination cursor.") from exc


async def list_categories(db: AsyncSession, user_id: UUID, profile_id: UUID) -> list[Category]:
    rows = await db.scalars(
        select(Category)
        .where(
            Category.is_active.is_(True),
            or_(
                Category.system_code.is_not(None),
                and_(
                    Category.user_id == user_id,
                    Category.financial_profile_id == profile_id,
                ),
            ),
        )
        .order_by(Category.kind, Category.name)
    )
    return list(rows)


async def create_category(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: CategoryCreate,
    correlation_id: str | None,
) -> Category:
    normalized = normalize_name(payload.name)
    existing = await db.scalar(
        select(Category).where(
            Category.financial_profile_id == profile.id,
            Category.normalized_name == normalized,
        )
    )
    if existing is not None:
        raise ValueError("A category with this name already exists.")
    category = Category(
        user_id=user.id,
        financial_profile_id=profile.id,
        name=payload.name,
        normalized_name=normalized,
        kind=payload.kind,
        color=payload.color.upper(),
        icon=payload.icon,
    )
    db.add(category)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="category.created",
        target_type="category",
        target_id=category.id,
        correlation_id=correlation_id,
    )
    return category


async def list_category_rules(
    db: AsyncSession, user_id: UUID, profile_id: UUID
) -> list[CategoryRule]:
    rows = await db.scalars(
        select(CategoryRule)
        .where(
            CategoryRule.user_id == user_id,
            CategoryRule.financial_profile_id == profile_id,
            CategoryRule.is_active.is_(True),
        )
        .order_by(CategoryRule.priority.desc(), CategoryRule.match_text)
    )
    return list(rows)


async def create_category_rule(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: CategoryRuleCreate,
    correlation_id: str | None,
) -> CategoryRule:
    await validate_category(
        db,
        user.id,
        profile.id,
        payload.category_id,
        TransactionKind.EXPENSE,
        allow_any_kind=True,
    )
    normalized = normalize_name(payload.match_text)
    existing = await db.scalar(
        select(CategoryRule).where(
            CategoryRule.financial_profile_id == profile.id,
            CategoryRule.normalized_match_text == normalized,
        )
    )
    if existing is not None:
        raise ValueError("A category rule with this text already exists.")
    rule = CategoryRule(
        user_id=user.id,
        financial_profile_id=profile.id,
        category_id=payload.category_id,
        match_text=payload.match_text,
        normalized_match_text=normalized,
        priority=payload.priority,
    )
    db.add(rule)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="category_rule.created",
        target_type="category_rule",
        target_id=rule.id,
        correlation_id=correlation_id,
    )
    return rule


async def get_owned_category_rule(
    db: AsyncSession, user_id: UUID, rule_id: UUID
) -> CategoryRule | None:
    return cast(
        CategoryRule | None,
        await db.scalar(
            select(CategoryRule).where(
                CategoryRule.id == rule_id,
                CategoryRule.user_id == user_id,
            )
        ),
    )


async def archive_category_rule(
    db: AsyncSession,
    user: User,
    rule: CategoryRule,
    correlation_id: str | None,
) -> None:
    rule.is_active = False
    await record_audit_event(
        db,
        user_id=user.id,
        action="category_rule.archived",
        target_type="category_rule",
        target_id=rule.id,
        correlation_id=correlation_id,
    )


async def match_category_rule(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    description: str,
    kind: TransactionKind,
) -> Category | None:
    normalized_description = normalize_name(description)
    rules = await list_category_rules(db, user_id, profile_id)
    rules.sort(
        key=lambda item: (item.priority, len(item.normalized_match_text)),
        reverse=True,
    )
    for rule in rules:
        if rule.normalized_match_text not in normalized_description:
            continue
        try:
            return await validate_category(
                db,
                user_id,
                profile_id,
                rule.category_id,
                kind,
            )
        except ValueError:
            continue
    return None


def next_month(value: date) -> date:
    return date(value.year + (value.month == 12), 1 if value.month == 12 else value.month + 1, 1)


def invoice_dates(occurred_on: date, closing_day: int, due_day: int) -> tuple[date, date]:
    invoice_month = occurred_on.replace(day=1)
    if occurred_on.day > closing_day:
        invoice_month = next_month(invoice_month)
    due_month = invoice_month if due_day > closing_day else next_month(invoice_month)
    due_on = due_month.replace(
        day=min(due_day, calendar.monthrange(due_month.year, due_month.month)[1])
    )
    return invoice_month, due_on


async def list_credit_cards(
    db: AsyncSession, user_id: UUID, profile_id: UUID
) -> list[tuple[CreditCard, Decimal]]:
    rows = await db.execute(
        select(
            CreditCard,
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.reversal_of_transaction_id.is_not(None),
                            -Transaction.amount,
                        ),
                        (
                            Transaction.kind == TransactionKind.EXPENSE,
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("open_balance"),
        )
        .outerjoin(
            Transaction,
            and_(
                Transaction.credit_card_id == CreditCard.id,
                Transaction.status == TransactionStatus.POSTED,
            ),
        )
        .outerjoin(CardInvoice, CardInvoice.id == Transaction.card_invoice_id)
        .where(
            CreditCard.user_id == user_id,
            CreditCard.financial_profile_id == profile_id,
            CreditCard.status == RecordStatus.ACTIVE,
            or_(
                CardInvoice.id.is_(None),
                CardInvoice.status != CardInvoiceStatus.PAID,
            ),
        )
        .group_by(CreditCard.id)
        .order_by(CreditCard.name)
    )
    return [(row[0], Decimal(row[1])) for row in rows.all()]


async def create_credit_card(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: CreditCardCreate,
    correlation_id: str | None,
) -> CreditCard:
    card = CreditCard(
        user_id=user.id,
        financial_profile_id=profile.id,
        name=payload.name,
        institution_name=payload.institution_name,
        last_four=payload.last_four,
        closing_day=payload.closing_day,
        due_day=payload.due_day,
        credit_limit=payload.credit_limit,
        currency=profile.currency,
    )
    db.add(card)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="credit_card.manual_created",
        target_type="credit_card",
        target_id=card.id,
        correlation_id=correlation_id,
    )
    return card


async def validate_credit_card(
    db: AsyncSession, user_id: UUID, profile_id: UUID, credit_card_id: UUID
) -> CreditCard:
    card = await db.scalar(
        select(CreditCard).where(
            CreditCard.id == credit_card_id,
            CreditCard.user_id == user_id,
            CreditCard.financial_profile_id == profile_id,
            CreditCard.status == RecordStatus.ACTIVE,
        )
    )
    if card is None:
        raise LookupError("Credit card not found.")
    return card


async def get_or_create_invoice(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    card: CreditCard,
    occurred_on: date,
) -> CardInvoice:
    competence_month, due_on = invoice_dates(occurred_on, card.closing_day, card.due_day)
    invoice = await db.scalar(
        select(CardInvoice).where(
            CardInvoice.credit_card_id == card.id,
            CardInvoice.competence_month == competence_month,
        )
    )
    if invoice is None:
        invoice = CardInvoice(
            user_id=user.id,
            financial_profile_id=profile.id,
            credit_card_id=card.id,
            competence_month=competence_month,
            due_on=due_on,
        )
        db.add(invoice)
        await db.flush()
    if invoice.status == CardInvoiceStatus.PAID:
        raise ValueError("This card invoice is already paid.")
    return invoice


async def validate_account(
    db: AsyncSession, user_id: UUID, profile_id: UUID, account_id: UUID
) -> FinancialAccount:
    account = await db.scalar(
        select(FinancialAccount).where(
            FinancialAccount.id == account_id,
            FinancialAccount.user_id == user_id,
            FinancialAccount.financial_profile_id == profile_id,
            FinancialAccount.status == RecordStatus.ACTIVE,
        )
    )
    if account is None:
        raise LookupError("Account not found.")
    return account


async def validate_category(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID,
    category_id: UUID | None,
    transaction_kind: TransactionKind,
    *,
    allow_any_kind: bool = False,
) -> Category | None:
    if category_id is None:
        return None
    category = await db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.is_active.is_(True),
            or_(
                Category.system_code.is_not(None),
                and_(
                    Category.user_id == user_id,
                    Category.financial_profile_id == profile_id,
                ),
            ),
        )
    )
    if category is None:
        raise LookupError("Category not found.")
    expected = (
        CategoryKind.INCOME if transaction_kind == TransactionKind.INCOME else CategoryKind.EXPENSE
    )
    if not allow_any_kind and category.kind not in {expected, CategoryKind.BOTH}:
        raise ValueError("Category is incompatible with the transaction kind.")
    return category


async def create_transaction(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: TransactionCreate,
    correlation_id: str | None,
) -> Transaction:
    account: FinancialAccount | None = None
    card: CreditCard | None = None
    invoice: CardInvoice | None = None
    if payload.account_id is not None:
        account = await validate_account(db, user.id, profile.id, payload.account_id)
    if payload.credit_card_id is not None:
        card = await validate_credit_card(db, user.id, profile.id, payload.credit_card_id)
        invoice = await get_or_create_invoice(db, user, profile, card, payload.occurred_on)
    category = await validate_category(db, user.id, profile.id, payload.category_id, payload.kind)
    if category is None and payload.kind != TransactionKind.TRANSFER:
        category = await match_category_rule(
            db,
            user.id,
            profile.id,
            payload.description,
            payload.kind,
        )
    transaction = Transaction(
        user_id=user.id,
        financial_profile_id=profile.id,
        account_id=account.id if account else None,
        credit_card_id=card.id if card else None,
        card_invoice_id=invoice.id if invoice else None,
        category_id=category.id if category else None,
        kind=payload.kind,
        status=payload.status,
        description=payload.description,
        amount=payload.amount,
        currency=(account.currency if account else card.currency if card else profile.currency),
        occurred_on=payload.occurred_on,
        competence_month=payload.competence_month,
        notes=payload.notes,
    )
    db.add(transaction)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="transaction.manual_created",
        target_type="transaction",
        target_id=transaction.id,
        correlation_id=correlation_id,
        safe_metadata={"kind": transaction.kind.value, "status": transaction.status.value},
    )
    return transaction


async def create_paired_transfer(
    db: AsyncSession,
    user: User,
    profile: FinancialProfile,
    payload: TransferCreate,
    correlation_id: str | None,
) -> tuple[Transaction, Transaction]:
    operation_key = str(payload.idempotency_key)
    existing = await db.scalar(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.operation_key == operation_key,
        )
    )
    if existing is not None:
        if existing.transfer_group_id is None:
            raise ValueError("Idempotency key is already used by another operation.")
        pair = await db.scalar(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.transfer_group_id == existing.transfer_group_id,
                Transaction.id != existing.id,
            )
        )
        if pair is None:
            raise ValueError("Transfer pair is incomplete.")
        return (
            (existing, pair)
            if existing.transfer_direction == TransferDirection.OUTFLOW
            else (pair, existing)
        )

    source = await validate_account(db, user.id, profile.id, payload.source_account_id)
    destination = await validate_account(db, user.id, profile.id, payload.destination_account_id)
    transfer_group_id = uuid4()
    common = {
        "user_id": user.id,
        "financial_profile_id": profile.id,
        "kind": TransactionKind.TRANSFER,
        "status": TransactionStatus.POSTED,
        "description": payload.description,
        "amount": payload.amount,
        "currency": profile.currency,
        "occurred_on": payload.occurred_on,
        "competence_month": payload.occurred_on.replace(day=1),
        "transfer_group_id": transfer_group_id,
    }
    outflow = Transaction(
        **common,
        account_id=source.id,
        transfer_direction=TransferDirection.OUTFLOW,
        operation_key=operation_key,
        notes=f"Transferência para {destination.name}.",
    )
    inflow = Transaction(
        **common,
        account_id=destination.id,
        transfer_direction=TransferDirection.INFLOW,
        notes=f"Transferência de {source.name}.",
    )
    db.add_all((outflow, inflow))
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="transfer.paired_created",
        target_type="transaction",
        target_id=outflow.id,
        correlation_id=correlation_id,
        safe_metadata={"accounting_treatment": "excluded_from_income_and_expense"},
    )
    return outflow, inflow


async def refund_transaction(
    db: AsyncSession,
    user: User,
    transaction: Transaction,
    payload: RefundCreate,
    correlation_id: str | None,
) -> Transaction:
    if transaction.kind == TransactionKind.TRANSFER:
        raise ValueError("Transfers cannot be refunded.")
    if transaction.status != TransactionStatus.POSTED:
        raise ValueError("Only posted transactions can be refunded.")
    if transaction.reversal_of_transaction_id is not None:
        raise ValueError("A refund cannot be refunded.")
    existing = await db.scalar(
        select(Transaction).where(
            Transaction.reversal_of_transaction_id == transaction.id,
            Transaction.user_id == user.id,
        )
    )
    if existing is not None:
        return existing

    if transaction.card_invoice_id is not None:
        invoice = await db.get(CardInvoice, transaction.card_invoice_id)
        if invoice is None or invoice.status == CardInvoiceStatus.PAID:
            raise ValueError("A paid card invoice cannot be refunded in this increment.")

    refund = Transaction(
        user_id=user.id,
        financial_profile_id=transaction.financial_profile_id,
        account_id=transaction.account_id,
        credit_card_id=transaction.credit_card_id,
        card_invoice_id=transaction.card_invoice_id,
        category_id=transaction.category_id,
        kind=(
            TransactionKind.INCOME
            if transaction.kind == TransactionKind.EXPENSE
            else TransactionKind.EXPENSE
        ),
        status=TransactionStatus.POSTED,
        description=payload.description or f"Estorno · {transaction.description}",
        amount=transaction.amount,
        currency=transaction.currency,
        occurred_on=payload.occurred_on,
        competence_month=(
            transaction.competence_month
            if transaction.card_invoice_id is not None
            else payload.occurred_on.replace(day=1)
        ),
        notes="Estorno vinculado à movimentação original.",
        reversal_of_transaction_id=transaction.id,
    )
    db.add(refund)
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="transaction.refunded",
        target_type="transaction",
        target_id=refund.id,
        correlation_id=correlation_id,
        safe_metadata={"original_kind": transaction.kind.value},
    )
    return refund


@dataclass(frozen=True)
class CardInvoiceListingItem:
    invoice: CardInvoice
    card_name: str
    total_amount: Decimal


async def list_card_invoices(
    db: AsyncSession, user_id: UUID, profile_id: UUID
) -> list[CardInvoiceListingItem]:
    rows = await db.execute(
        select(
            CardInvoice,
            CreditCard.name,
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.kind == TransactionKind.EXPENSE,
                                Transaction.status == TransactionStatus.POSTED,
                            ),
                            Transaction.amount,
                        ),
                        (
                            and_(
                                Transaction.reversal_of_transaction_id.is_not(None),
                                Transaction.status == TransactionStatus.POSTED,
                            ),
                            -Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .join(CreditCard, CreditCard.id == CardInvoice.credit_card_id)
        .outerjoin(Transaction, Transaction.card_invoice_id == CardInvoice.id)
        .where(
            CardInvoice.user_id == user_id,
            CardInvoice.financial_profile_id == profile_id,
        )
        .group_by(CardInvoice.id, CreditCard.name)
        .order_by(CardInvoice.due_on.desc(), CardInvoice.id.desc())
    )
    return [
        CardInvoiceListingItem(invoice=row[0], card_name=row[1], total_amount=Decimal(row[2]))
        for row in rows.all()
    ]


async def get_owned_invoice(
    db: AsyncSession, user_id: UUID, invoice_id: UUID
) -> CardInvoice | None:
    return cast(
        CardInvoice | None,
        await db.scalar(
            select(CardInvoice).where(
                CardInvoice.id == invoice_id,
                CardInvoice.user_id == user_id,
            )
        ),
    )


async def pay_card_invoice(
    db: AsyncSession,
    user: User,
    invoice: CardInvoice,
    payload: CardInvoicePaymentCreate,
    correlation_id: str | None,
) -> CardInvoice:
    if invoice.status == CardInvoiceStatus.PAID:
        return invoice
    account = await validate_account(
        db,
        user.id,
        invoice.financial_profile_id,
        payload.account_id,
    )
    total = await db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            Transaction.reversal_of_transaction_id.is_not(None),
                            -Transaction.amount,
                        ),
                        (
                            Transaction.kind == TransactionKind.EXPENSE,
                            Transaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            )
        ).where(
            Transaction.card_invoice_id == invoice.id,
            Transaction.status == TransactionStatus.POSTED,
        )
    )
    amount = Decimal(total or 0)
    if amount <= 0:
        raise ValueError("A card invoice without expenses cannot be paid.")
    payment = Transaction(
        user_id=user.id,
        financial_profile_id=invoice.financial_profile_id,
        account_id=account.id,
        card_invoice_id=invoice.id,
        kind=TransactionKind.TRANSFER,
        status=TransactionStatus.POSTED,
        description="Pagamento de fatura",
        amount=amount,
        currency=account.currency,
        occurred_on=payload.paid_on,
        competence_month=payload.paid_on.replace(day=1),
        notes="Pagamento de cartão; não contabilizado novamente como despesa.",
    )
    db.add(payment)
    await db.flush()
    invoice.status = CardInvoiceStatus.PAID
    invoice.paid_on = payload.paid_on
    invoice.paid_transaction_id = payment.id
    invoice.version += 1
    await record_audit_event(
        db,
        user_id=user.id,
        action="card_invoice.paid",
        target_type="card_invoice",
        target_id=invoice.id,
        correlation_id=correlation_id,
        safe_metadata={"accounting_treatment": "transfer"},
    )
    return invoice


@dataclass(frozen=True)
class TransactionListing:
    items: list[Transaction]
    next_cursor: str | None
    income_total: Decimal
    expense_total: Decimal


def transaction_filters(
    user_id: UUID,
    profile_id: UUID | None,
    *,
    kind: TransactionKind | None,
    status: TransactionStatus | None,
    category_id: UUID | None,
    query: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [Transaction.user_id == user_id]
    if profile_id is not None:
        filters.append(Transaction.financial_profile_id == profile_id)
    if kind is not None:
        filters.append(Transaction.kind == kind)
    if status is not None:
        filters.append(Transaction.status == status)
    else:
        filters.append(Transaction.status != TransactionStatus.VOIDED)
    if category_id is not None:
        filters.append(Transaction.category_id == category_id)
    if query:
        filters.append(Transaction.description.ilike(f"%{query.strip()}%"))
    if date_from:
        filters.append(Transaction.occurred_on >= date_from)
    if date_to:
        filters.append(Transaction.occurred_on <= date_to)
    return filters


async def list_transactions(
    db: AsyncSession,
    user_id: UUID,
    profile_id: UUID | None,
    *,
    kind: TransactionKind | None,
    status: TransactionStatus | None,
    category_id: UUID | None,
    query: str | None,
    date_from: date | None,
    date_to: date | None,
    cursor: str | None,
    limit: int,
) -> TransactionListing:
    filters = transaction_filters(
        user_id,
        profile_id,
        kind=kind,
        status=status,
        category_id=category_id,
        query=query,
        date_from=date_from,
        date_to=date_to,
    )
    statement: Select[tuple[Transaction]] = select(Transaction).where(*filters)
    if cursor:
        cursor_date, cursor_id = decode_cursor(cursor)
        statement = statement.where(
            or_(
                Transaction.occurred_on < cursor_date,
                and_(Transaction.occurred_on == cursor_date, Transaction.id < cursor_id),
            )
        )
    rows = list(
        await db.scalars(
            statement.order_by(Transaction.occurred_on.desc(), Transaction.id.desc()).limit(
                limit + 1
            )
        )
    )
    has_more = len(rows) > limit
    items = rows[:limit]
    original = aliased(Transaction)
    totals = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Transaction.kind == TransactionKind.INCOME,
                                    Transaction.reversal_of_transaction_id.is_(None),
                                ),
                                Transaction.amount,
                            ),
                            (
                                and_(
                                    Transaction.reversal_of_transaction_id.is_not(None),
                                    original.kind == TransactionKind.INCOME,
                                ),
                                -Transaction.amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Transaction.kind == TransactionKind.EXPENSE,
                                    Transaction.reversal_of_transaction_id.is_(None),
                                ),
                                Transaction.amount,
                            ),
                            (
                                and_(
                                    Transaction.reversal_of_transaction_id.is_not(None),
                                    original.kind == TransactionKind.EXPENSE,
                                ),
                                -Transaction.amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .outerjoin(
                original,
                original.id == Transaction.reversal_of_transaction_id,
            )
            .where(*filters)
        )
    ).one()
    return TransactionListing(
        items=items,
        next_cursor=encode_cursor(items[-1]) if has_more and items else None,
        income_total=Decimal(totals[0]),
        expense_total=Decimal(totals[1]),
    )


async def get_owned_transaction(
    db: AsyncSession, user_id: UUID, transaction_id: UUID
) -> Transaction | None:
    transaction: Transaction | None = await db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    return transaction


async def list_transaction_splits(
    db: AsyncSession, user_id: UUID, transaction_id: UUID
) -> list[TransactionSplit]:
    rows = await db.scalars(
        select(TransactionSplit)
        .where(
            TransactionSplit.user_id == user_id,
            TransactionSplit.transaction_id == transaction_id,
        )
        .order_by(TransactionSplit.position)
    )
    return list(rows)


async def replace_transaction_splits(
    db: AsyncSession,
    user: User,
    transaction: Transaction,
    payload: TransactionSplitReplace,
    correlation_id: str | None,
) -> list[TransactionSplit]:
    if transaction.version != payload.version:
        raise ValueError("Transaction was changed. Refresh and try again.")
    if transaction.kind == TransactionKind.TRANSFER:
        raise ValueError("Transfers cannot be split.")
    if transaction.status != TransactionStatus.POSTED:
        raise ValueError("Only posted transactions can be split.")
    if transaction.reversal_of_transaction_id is not None:
        raise ValueError("Refunds cannot be split.")
    total = sum((item.amount for item in payload.items), Decimal("0"))
    if total != transaction.amount:
        raise ValueError("Split amounts must equal the transaction amount.")

    for item in payload.items:
        await validate_category(
            db,
            user.id,
            transaction.financial_profile_id,
            item.category_id,
            transaction.kind,
        )
    await db.execute(
        delete(TransactionSplit).where(
            TransactionSplit.transaction_id == transaction.id,
            TransactionSplit.user_id == user.id,
        )
    )
    splits = [
        TransactionSplit(
            user_id=user.id,
            financial_profile_id=transaction.financial_profile_id,
            transaction_id=transaction.id,
            category_id=item.category_id,
            position=position,
            description=item.description,
            amount=item.amount,
        )
        for position, item in enumerate(payload.items, start=1)
    ]
    db.add_all(splits)
    transaction.category_id = None
    transaction.version += 1
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="transaction.splits_replaced",
        target_type="transaction",
        target_id=transaction.id,
        correlation_id=correlation_id,
        safe_metadata={"split_count": str(len(splits))},
    )
    return splits


async def update_transaction(
    db: AsyncSession,
    user: User,
    transaction: Transaction,
    payload: TransactionUpdate,
    correlation_id: str | None,
) -> Transaction:
    if transaction.version != payload.version:
        raise ValueError("Transaction was changed. Refresh and try again.")
    if payload.category_id is not None:
        await validate_category(
            db,
            user.id,
            transaction.financial_profile_id,
            payload.category_id,
            transaction.kind,
        )
    for field in (
        "category_id",
        "description",
        "amount",
        "occurred_on",
        "competence_month",
        "notes",
        "status",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(transaction, field, value)
    transaction.version += 1
    await db.flush()
    await record_audit_event(
        db,
        user_id=user.id,
        action="transaction.updated",
        target_type="transaction",
        target_id=transaction.id,
        correlation_id=correlation_id,
    )
    return transaction


async def void_transaction(
    db: AsyncSession,
    user: User,
    transaction: Transaction,
    correlation_id: str | None,
) -> None:
    transaction.status = TransactionStatus.VOIDED
    transaction.version += 1
    await record_audit_event(
        db,
        user_id=user.id,
        action="transaction.voided",
        target_type="transaction",
        target_id=transaction.id,
        correlation_id=correlation_id,
    )
