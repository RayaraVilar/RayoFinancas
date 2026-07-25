from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class CanonicalAccountKind(StrEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CREDIT_CARD = "CREDIT_CARD"
    PAYMENT = "PAYMENT"
    OTHER = "OTHER"


class CanonicalTransactionDirection(StrEnum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


@dataclass(frozen=True)
class ConnectToken:
    value: str
    expires_in_seconds: int


@dataclass(frozen=True)
class ProviderItem:
    external_id: str
    client_user_id: str | None
    connector_id: str | None
    connector_name: str | None
    status: str
    updated_at: datetime | None


@dataclass(frozen=True)
class CanonicalAccount:
    external_id: str
    item_external_id: str
    kind: CanonicalAccountKind
    name: str
    institution_name: str | None
    balance: Decimal
    currency: str
    credit_limit: Decimal | None
    closing_date: date | None
    due_date: date | None


@dataclass(frozen=True)
class CanonicalTransaction:
    external_id: str
    account_external_id: str
    description: str
    amount: Decimal
    direction: CanonicalTransactionDirection
    occurred_at: datetime
    status: str
    currency: str
    provider_category_id: str | None
    provider_category_name: str | None


@dataclass(frozen=True)
class TransactionPage:
    items: list[CanonicalTransaction]
    next_cursor: str | None


class BankProvider(Protocol):
    async def create_connect_token(self, *, client_user_id: str) -> ConnectToken: ...

    async def get_item(self, external_item_id: str) -> ProviderItem: ...

    async def revoke_item(self, external_item_id: str) -> None: ...

    async def list_accounts(self, external_item_id: str) -> list[CanonicalAccount]: ...

    async def list_transactions(
        self,
        external_account_id: str,
        *,
        account_kind: CanonicalAccountKind,
        cursor: str | None = None,
    ) -> TransactionPage: ...
