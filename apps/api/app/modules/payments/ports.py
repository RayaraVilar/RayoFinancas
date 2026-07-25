from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PaymentAuthorization:
    provider_payment_id: str
    authorization_url: str
    expires_in_seconds: int


@dataclass(frozen=True)
class ProviderPaymentState:
    provider_payment_id: str
    status: str
    amount: Decimal


class PaymentProvider(Protocol):
    async def create_authorization(
        self,
        *,
        amount: Decimal,
        idempotency_key: str,
        callback_url: str,
    ) -> PaymentAuthorization: ...

    async def get_payment(self, provider_payment_id: str) -> ProviderPaymentState: ...
