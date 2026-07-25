from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.modules.identity.dependencies import (
    CsrfScope,
    CurrentScope,
    DatabaseSession,
    SelectedFinancialContext,
)
from app.modules.identity.service import get_owned_profile
from app.modules.ledger.models import TransactionKind, TransactionStatus
from app.modules.ledger.schemas import (
    CardInvoicePaymentCreate,
    CardInvoiceResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryRuleCreate,
    CategoryRuleResponse,
    CreditCardCreate,
    CreditCardResponse,
    RefundCreate,
    TransactionCreate,
    TransactionPage,
    TransactionResponse,
    TransactionSplitReplace,
    TransactionSplitResponse,
    TransactionSplitsResponse,
    TransactionUpdate,
    TransferCreate,
    TransferResponse,
)
from app.modules.ledger.service import (
    CardInvoiceListingItem,
    archive_category_rule,
    create_category,
    create_category_rule,
    create_credit_card,
    create_paired_transfer,
    create_transaction,
    get_owned_category_rule,
    get_owned_invoice,
    get_owned_transaction,
    list_card_invoices,
    list_categories,
    list_category_rules,
    list_credit_cards,
    list_transaction_splits,
    list_transactions,
    pay_card_invoice,
    refund_transaction,
    replace_transaction_splits,
    update_transaction,
    void_transaction,
)

router = APIRouter()


def invoice_response(item: CardInvoiceListingItem) -> CardInvoiceResponse:
    return CardInvoiceResponse(
        id=item.invoice.id,
        credit_card_id=item.invoice.credit_card_id,
        card_name=item.card_name,
        competence_month=item.invoice.competence_month,
        due_on=item.invoice.due_on,
        status=item.invoice.status,
        total_amount=item.total_amount,
        paid_on=item.invoice.paid_on,
        version=item.invoice.version,
    )


@router.get(
    "/financial-profiles/{profile_id}/credit-cards",
    response_model=list[CreditCardResponse],
    tags=["credit-cards"],
)
async def get_credit_cards(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[CreditCardResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    cards = await list_credit_cards(db, scope.user.id, profile.id)
    return [
        CreditCardResponse(
            id=card.id,
            financial_profile_id=card.financial_profile_id,
            name=card.name,
            institution_name=card.institution_name,
            last_four=card.last_four,
            closing_day=card.closing_day,
            due_day=card.due_day,
            credit_limit=card.credit_limit,
            currency=card.currency,
            open_balance=open_balance,
        )
        for card, open_balance in cards
    ]


@router.post(
    "/financial-profiles/{profile_id}/credit-cards",
    response_model=CreditCardResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["credit-cards"],
)
async def post_credit_card(
    request: Request,
    profile_id: UUID,
    payload: CreditCardCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> CreditCardResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    card = await create_credit_card(
        db,
        scope.user,
        profile,
        payload,
        request.headers.get("x-request-id"),
    )
    await db.commit()
    return CreditCardResponse(
        id=card.id,
        financial_profile_id=card.financial_profile_id,
        name=card.name,
        institution_name=card.institution_name,
        last_four=card.last_four,
        closing_day=card.closing_day,
        due_day=card.due_day,
        credit_limit=card.credit_limit,
        currency=card.currency,
        open_balance=Decimal("0"),
    )


@router.get(
    "/financial-profiles/{profile_id}/card-invoices",
    response_model=list[CardInvoiceResponse],
    tags=["credit-cards"],
)
async def get_card_invoices(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[CardInvoiceResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return [
        invoice_response(item) for item in await list_card_invoices(db, scope.user.id, profile.id)
    ]


@router.post(
    "/card-invoices/{invoice_id}/pay",
    response_model=CardInvoiceResponse,
    tags=["credit-cards"],
)
async def post_card_invoice_payment(
    request: Request,
    invoice_id: UUID,
    payload: CardInvoicePaymentCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> CardInvoiceResponse:
    invoice = await get_owned_invoice(db, scope.user.id, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    try:
        await pay_card_invoice(
            db,
            scope.user,
            invoice,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    items = await list_card_invoices(db, scope.user.id, invoice.financial_profile_id)
    item = next(item for item in items if item.invoice.id == invoice.id)
    return invoice_response(item)


@router.get(
    "/financial-profiles/{profile_id}/categories",
    response_model=list[CategoryResponse],
    tags=["categories"],
)
async def get_categories(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[CategoryResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    categories = await list_categories(db, scope.user.id, profile.id)
    return [CategoryResponse.model_validate(category) for category in categories]


@router.post(
    "/financial-profiles/{profile_id}/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["categories"],
)
async def post_category(
    request: Request,
    profile_id: UUID,
    payload: CategoryCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> CategoryResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        category = await create_category(
            db,
            scope.user,
            profile,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CategoryResponse.model_validate(category)


@router.get(
    "/financial-profiles/{profile_id}/category-rules",
    response_model=list[CategoryRuleResponse],
    tags=["categories"],
)
async def get_category_rules(
    profile_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> list[CategoryRuleResponse]:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return [
        CategoryRuleResponse.model_validate(rule)
        for rule in await list_category_rules(db, scope.user.id, profile.id)
    ]


@router.post(
    "/financial-profiles/{profile_id}/category-rules",
    response_model=CategoryRuleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["categories"],
)
async def post_category_rule(
    request: Request,
    profile_id: UUID,
    payload: CategoryRuleCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> CategoryRuleResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        rule = await create_category_rule(
            db,
            scope.user,
            profile,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CategoryRuleResponse.model_validate(rule)


@router.delete(
    "/category-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["categories"],
)
async def delete_category_rule(
    request: Request,
    rule_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> Response:
    rule = await get_owned_category_rule(db, scope.user.id, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")
    await archive_category_rule(
        db,
        scope.user,
        rule,
        request.headers.get("x-request-id"),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/financial-profiles/{profile_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["transactions"],
)
async def post_transaction(
    request: Request,
    profile_id: UUID,
    payload: TransactionCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> TransactionResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        transaction = await create_transaction(
            db,
            scope.user,
            profile,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return TransactionResponse.model_validate(transaction)


@router.post(
    "/financial-profiles/{profile_id}/transfers",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["transactions"],
)
async def post_transfer(
    request: Request,
    profile_id: UUID,
    payload: TransferCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> TransferResponse:
    profile = await get_owned_profile(db, scope.user.id, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    try:
        outflow, inflow = await create_paired_transfer(
            db,
            scope.user,
            profile,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if outflow.transfer_group_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transfer group was not created.",
        )
    return TransferResponse(
        transfer_group_id=outflow.transfer_group_id,
        outflow=TransactionResponse.model_validate(outflow),
        inflow=TransactionResponse.model_validate(inflow),
    )


@router.get("/transactions", response_model=TransactionPage, tags=["transactions"])
async def get_transactions(
    db: DatabaseSession,
    scope: CurrentScope,
    context: SelectedFinancialContext,
    kind: TransactionKind | None = None,
    transaction_status: Annotated[
        TransactionStatus | None,
        Query(alias="status"),
    ] = None,
    category_id: UUID | None = None,
    query: Annotated[str | None, Query(max_length=100)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    cursor: Annotated[str | None, Query(max_length=256)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TransactionPage:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must not be after date_to.",
        )
    try:
        listing = await list_transactions(
            db,
            scope.user.id,
            context.profile.id if context.profile else None,
            kind=kind,
            status=transaction_status,
            category_id=category_id,
            query=query,
            date_from=date_from,
            date_to=date_to,
            cursor=cursor,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TransactionPage(
        items=[TransactionResponse.model_validate(transaction) for transaction in listing.items],
        next_cursor=listing.next_cursor,
        income_total=listing.income_total,
        expense_total=listing.expense_total,
        net_total=listing.income_total - listing.expense_total,
    )


@router.patch(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    tags=["transactions"],
)
async def patch_transaction(
    request: Request,
    transaction_id: UUID,
    payload: TransactionUpdate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> TransactionResponse:
    transaction = await get_owned_transaction(db, scope.user.id, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    try:
        updated = await update_transaction(
            db,
            scope.user,
            transaction,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TransactionResponse.model_validate(updated)


@router.get(
    "/transactions/{transaction_id}/splits",
    response_model=TransactionSplitsResponse,
    tags=["transactions"],
)
async def get_transaction_splits(
    transaction_id: UUID,
    db: DatabaseSession,
    scope: CurrentScope,
) -> TransactionSplitsResponse:
    transaction = await get_owned_transaction(db, scope.user.id, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    splits = await list_transaction_splits(db, scope.user.id, transaction.id)
    return TransactionSplitsResponse(
        transaction_id=transaction.id,
        transaction_version=transaction.version,
        items=[TransactionSplitResponse.model_validate(item) for item in splits],
    )


@router.put(
    "/transactions/{transaction_id}/splits",
    response_model=TransactionSplitsResponse,
    tags=["transactions"],
)
async def put_transaction_splits(
    request: Request,
    transaction_id: UUID,
    payload: TransactionSplitReplace,
    db: DatabaseSession,
    scope: CsrfScope,
) -> TransactionSplitsResponse:
    transaction = await get_owned_transaction(db, scope.user.id, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    try:
        splits = await replace_transaction_splits(
            db,
            scope.user,
            transaction,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return TransactionSplitsResponse(
        transaction_id=transaction.id,
        transaction_version=transaction.version,
        items=[TransactionSplitResponse.model_validate(item) for item in splits],
    )


@router.post(
    "/transactions/{transaction_id}/refund",
    response_model=TransactionResponse,
    tags=["transactions"],
)
async def post_transaction_refund(
    request: Request,
    transaction_id: UUID,
    payload: RefundCreate,
    db: DatabaseSession,
    scope: CsrfScope,
) -> TransactionResponse:
    transaction = await get_owned_transaction(db, scope.user.id, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    try:
        refund = await refund_transaction(
            db,
            scope.user,
            transaction,
            payload,
            request.headers.get("x-request-id"),
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return TransactionResponse.model_validate(refund)


@router.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["transactions"],
)
async def delete_transaction(
    request: Request,
    transaction_id: UUID,
    db: DatabaseSession,
    scope: CsrfScope,
) -> Response:
    transaction = await get_owned_transaction(db, scope.user.id, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    await void_transaction(
        db,
        scope.user,
        transaction,
        request.headers.get("x-request-id"),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
