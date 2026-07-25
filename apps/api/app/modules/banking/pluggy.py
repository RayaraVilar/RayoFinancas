from __future__ import annotations

import asyncio
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.modules.banking.ports import (
    CanonicalAccount,
    CanonicalAccountKind,
    CanonicalTransaction,
    CanonicalTransactionDirection,
    ConnectToken,
    ProviderItem,
    TransactionPage,
)


class BankProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_date(value: object) -> date | None:
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def account_kind(payload: dict[str, Any]) -> CanonicalAccountKind:
    if payload.get("type") == "CREDIT":
        return CanonicalAccountKind.CREDIT_CARD
    subtype = payload.get("subtype")
    if subtype == "CHECKING_ACCOUNT":
        return CanonicalAccountKind.CHECKING
    if subtype == "SAVINGS_ACCOUNT":
        return CanonicalAccountKind.SAVINGS
    return CanonicalAccountKind.OTHER


def transaction_direction(
    payload: dict[str, Any],
    kind: CanonicalAccountKind,
) -> CanonicalTransactionDirection:
    provider_type = payload.get("type")
    if provider_type == "CREDIT":
        return CanonicalTransactionDirection.CREDIT
    if provider_type == "DEBIT":
        return CanonicalTransactionDirection.DEBIT
    amount = Decimal(str(payload.get("amount", 0)))
    if kind == CanonicalAccountKind.CREDIT_CARD:
        return (
            CanonicalTransactionDirection.DEBIT
            if amount >= 0
            else CanonicalTransactionDirection.CREDIT
        )
    return (
        CanonicalTransactionDirection.CREDIT if amount >= 0 else CanonicalTransactionDirection.DEBIT
    )


class PluggyBankProvider:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        api_url: str = "https://api.pluggy.ai",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._api_url = api_url.rstrip("/")
        self._api_key: str | None = None
        self._api_key_expires_at = 0.0
        self._auth_lock = asyncio.Lock()

    async def _get_api_key(self) -> str:
        if self._api_key and time.monotonic() < self._api_key_expires_at:
            return self._api_key
        async with self._auth_lock:
            if self._api_key and time.monotonic() < self._api_key_expires_at:
                return self._api_key
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        f"{self._api_url}/auth",
                        json={
                            "clientId": self._client_id,
                            "clientSecret": self._client_secret,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise BankProviderError(
                    "authentication_failed",
                    "Provider authentication failed.",
                ) from exc
            api_key = payload.get("apiKey")
            if not isinstance(api_key, str) or not api_key:
                raise BankProviderError("invalid_auth_response", "Provider authentication failed.")
            self._api_key = api_key
            self._api_key_expires_at = time.monotonic() + (110 * 60)
            return api_key

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        api_key = await self._get_api_key()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method,
                    f"{self._api_url}{path}",
                    params=params,
                    json=json,
                    headers={"X-API-KEY": api_key},
                )
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                self._api_key = None
                self._api_key_expires_at = 0
            raise BankProviderError(
                f"http_{exc.response.status_code}",
                "Provider request failed.",
            ) from exc
        except httpx.HTTPError as exc:
            raise BankProviderError("provider_unavailable", "Provider is unavailable.") from exc

    async def create_connect_token(self, *, client_user_id: str) -> ConnectToken:
        response = await self._request(
            "POST",
            "/connect_token",
            json={
                "options": {
                    "clientUserId": client_user_id,
                    "avoidDuplicates": True,
                }
            },
        )
        payload = response.json()
        token = payload.get("accessToken") or payload.get("connectToken")
        if not isinstance(token, str) or not token:
            raise BankProviderError("invalid_connect_token", "Provider returned an invalid token.")
        return ConnectToken(value=token, expires_in_seconds=1800)

    async def get_item(self, external_item_id: str) -> ProviderItem:
        payload = (await self._request("GET", f"/items/{external_item_id}")).json()
        connector = payload.get("connector") if isinstance(payload.get("connector"), dict) else {}
        return ProviderItem(
            external_id=str(payload["id"]),
            client_user_id=(
                payload.get("clientUserId")
                if isinstance(payload.get("clientUserId"), str)
                else None
            ),
            connector_id=(str(connector.get("id")) if connector.get("id") is not None else None),
            connector_name=(
                connector.get("name") if isinstance(connector.get("name"), str) else None
            ),
            status=str(payload.get("status", "UNKNOWN")),
            updated_at=parse_datetime(payload.get("updatedAt")),
        )

    async def revoke_item(self, external_item_id: str) -> None:
        await self._request("DELETE", f"/items/{external_item_id}")

    async def list_accounts(self, external_item_id: str) -> list[CanonicalAccount]:
        payload = (
            await self._request(
                "GET",
                "/accounts",
                params={"itemId": external_item_id},
            )
        ).json()
        results = payload.get("results", [])
        accounts: list[CanonicalAccount] = []
        for item in results if isinstance(results, list) else []:
            if not isinstance(item, dict):
                continue
            credit_data = item.get("creditData")
            if not isinstance(credit_data, dict):
                credit_data = {}
            accounts.append(
                CanonicalAccount(
                    external_id=str(item["id"]),
                    item_external_id=external_item_id,
                    kind=account_kind(item),
                    name=str(item.get("marketingName") or item.get("name") or "Conta"),
                    institution_name=None,
                    balance=Decimal(str(item.get("balance", 0))),
                    currency=str(item.get("currencyCode") or "BRL"),
                    credit_limit=(
                        Decimal(str(credit_data["creditLimit"]))
                        if credit_data.get("creditLimit") is not None
                        else None
                    ),
                    closing_date=parse_date(credit_data.get("balanceCloseDate")),
                    due_date=parse_date(credit_data.get("balanceDueDate")),
                )
            )
        return accounts

    async def list_transactions(
        self,
        external_account_id: str,
        *,
        account_kind: CanonicalAccountKind,
        cursor: str | None = None,
    ) -> TransactionPage:
        params = {"accountId": external_account_id}
        if cursor:
            params["after"] = cursor
        payload = (await self._request("GET", "/v2/transactions", params=params)).json()
        results = payload.get("results", [])
        items: list[CanonicalTransaction] = []
        for item in results if isinstance(results, list) else []:
            if not isinstance(item, dict):
                continue
            occurred_at = parse_datetime(item.get("date"))
            if occurred_at is None:
                continue
            raw_amount = Decimal(str(item.get("amount", 0)))
            items.append(
                CanonicalTransaction(
                    external_id=str(item["id"]),
                    account_external_id=external_account_id,
                    description=str(item.get("description") or "Movimentação"),
                    amount=abs(raw_amount),
                    direction=transaction_direction(item, account_kind),
                    occurred_at=occurred_at,
                    status=str(item.get("status") or "POSTED"),
                    currency=str(item.get("currencyCode") or "BRL"),
                    provider_category_id=(
                        str(item["categoryId"]) if item.get("categoryId") is not None else None
                    ),
                    provider_category_name=(
                        item.get("category") if isinstance(item.get("category"), str) else None
                    ),
                )
            )
        next_cursor = None
        next_value = payload.get("next")
        if isinstance(next_value, str) and next_value:
            values = parse_qs(urlparse(next_value).query).get("after")
            next_cursor = values[0] if values else None
        return TransactionPage(items=items, next_cursor=next_cursor)
