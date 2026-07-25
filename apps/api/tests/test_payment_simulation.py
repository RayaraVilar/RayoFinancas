from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.payments.service import payment_risk, simulation_hash


def test_payment_risk_is_versionable_and_deterministic() -> None:
    assert payment_risk(Decimal("-1"), Decimal("-20"))[0] == "HIGH"
    assert payment_risk(Decimal("1000"), Decimal("100"))[0] == "MEDIUM"
    assert payment_risk(Decimal("1000"), Decimal("500"))[0] == "LOW"
    assert simulation_hash({"b": 2, "a": 1}) == simulation_hash({"a": 1, "b": 2})


def test_production_cannot_enable_payment_initiation_from_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            secret_key="x" * 40,
            frontend_url="https://rayo.example",
            payment_initiation_enabled=True,
            payment_kill_switch=False,
            payment_provider="fixture",
        )
