from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.ledger.models import (
    CardInvoiceStatus,
    CategoryKind,
    TransactionKind,
    TransactionStatus,
    TransferDirection,
)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    kind: CategoryKind
    color: str = Field(default="#5E7A6E", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="tag", pattern=r"^[a-z0-9-]{2,32}$")

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: CategoryKind
    color: str
    icon: str
    system_code: str | None


class CategoryRuleCreate(BaseModel):
    match_text: str = Field(min_length=2, max_length=120)
    category_id: UUID
    priority: int = Field(default=100, ge=1, le=1000)

    @field_validator("match_text")
    @classmethod
    def clean_match_text(cls, value: str) -> str:
        return " ".join(value.split())


class CategoryRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    category_id: UUID
    match_text: str
    priority: int
    is_active: bool


class CreditCardCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    institution_name: str | None = Field(default=None, max_length=120)
    last_four: str | None = Field(default=None, pattern=r"^\d{4}$")
    closing_day: int = Field(ge=1, le=28)
    due_day: int = Field(ge=1, le=28)
    credit_limit: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        le=Decimal("99999999999999999.99"),
        decimal_places=2,
    )

    @field_validator("name", "institution_name")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class CreditCardResponse(BaseModel):
    id: UUID
    financial_profile_id: UUID
    name: str
    institution_name: str | None
    last_four: str | None
    closing_day: int
    due_day: int
    credit_limit: Decimal
    currency: str
    open_balance: Decimal


class CardInvoiceResponse(BaseModel):
    id: UUID
    credit_card_id: UUID
    card_name: str
    competence_month: date
    due_on: date
    status: CardInvoiceStatus
    total_amount: Decimal
    paid_on: date | None
    version: int


class CardInvoicePaymentCreate(BaseModel):
    account_id: UUID
    paid_on: date


class TransferCreate(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    description: str = Field(default="Transferência entre contas", min_length=2, max_length=160)
    amount: Decimal = Field(
        gt=Decimal("0"),
        le=Decimal("99999999999999999.99"),
        decimal_places=2,
    )
    occurred_on: date
    idempotency_key: UUID

    @model_validator(mode="after")
    def different_accounts(self) -> TransferCreate:
        if self.source_account_id == self.destination_account_id:
            raise ValueError("Source and destination accounts must be different.")
        self.description = " ".join(self.description.split())
        return self


class RefundCreate(BaseModel):
    occurred_on: date
    description: str | None = Field(default=None, min_length=2, max_length=160)

    @field_validator("description")
    @classmethod
    def clean_refund_description(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class TransactionCreate(BaseModel):
    account_id: UUID | None = None
    credit_card_id: UUID | None = None
    category_id: UUID | None = None
    kind: TransactionKind
    status: TransactionStatus = TransactionStatus.POSTED
    description: str = Field(min_length=2, max_length=160)
    amount: Decimal = Field(gt=Decimal("0"), le=Decimal("99999999999999999.99"), decimal_places=2)
    occurred_on: date
    competence_month: date | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @model_validator(mode="after")
    def normalize_competence(self) -> TransactionCreate:
        value = self.competence_month or self.occurred_on
        self.competence_month = value.replace(day=1)
        if (self.account_id is None) == (self.credit_card_id is None):
            raise ValueError("Choose either an account or a credit card.")
        if self.credit_card_id is not None and self.kind != TransactionKind.EXPENSE:
            raise ValueError("Credit card entries must be expenses.")
        if self.kind == TransactionKind.TRANSFER and self.category_id is not None:
            raise ValueError("Transfers cannot be categorized as income or expense.")
        return self


class TransactionUpdate(BaseModel):
    category_id: UUID | None = None
    description: str | None = Field(default=None, min_length=2, max_length=160)
    amount: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        le=Decimal("99999999999999999.99"),
        decimal_places=2,
    )
    occurred_on: date | None = None
    competence_month: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    status: TransactionStatus | None = None
    version: int = Field(ge=1)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @field_validator("competence_month")
    @classmethod
    def normalize_competence(cls, value: date | None) -> date | None:
        return value.replace(day=1) if value else None


class TransactionSplitItem(BaseModel):
    category_id: UUID
    amount: Decimal = Field(
        gt=Decimal("0"),
        le=Decimal("99999999999999999.99"),
        decimal_places=2,
    )
    description: str | None = Field(default=None, max_length=160)

    @field_validator("description")
    @classmethod
    def clean_split_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class TransactionSplitReplace(BaseModel):
    version: int = Field(ge=1)
    items: list[TransactionSplitItem] = Field(min_length=2, max_length=20)


class TransactionSplitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    category_id: UUID
    position: int
    description: str | None
    amount: Decimal


class TransactionSplitsResponse(BaseModel):
    transaction_id: UUID
    transaction_version: int
    items: list[TransactionSplitResponse]


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    financial_profile_id: UUID
    account_id: UUID | None
    credit_card_id: UUID | None
    card_invoice_id: UUID | None
    transfer_group_id: UUID | None
    transfer_direction: TransferDirection | None
    reversal_of_transaction_id: UUID | None
    category_id: UUID | None
    kind: TransactionKind
    status: TransactionStatus
    description: str
    amount: Decimal
    currency: str
    occurred_on: date
    competence_month: date
    notes: str | None
    version: int
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    next_cursor: str | None
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal


class TransferResponse(BaseModel):
    transfer_group_id: UUID
    outflow: TransactionResponse
    inflow: TransactionResponse
