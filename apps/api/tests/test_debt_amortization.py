from decimal import Decimal

from app.modules.debts.models import AmortizationSystem
from app.modules.debts.service import amortization_schedule, price_payment


def test_price_payment_golden_case() -> None:
    payment = price_payment(Decimal("10000"), Decimal("0.01"), 12)
    assert payment == Decimal("888.49")
    totals = amortization_schedule(
        Decimal("10000"),
        Decimal("12"),
        12,
        AmortizationSystem.PRICE,
    )
    assert totals.months == 12
    assert totals.interest == Decimal("661.85")


def test_sac_has_declining_interest_and_exact_term() -> None:
    totals = amortization_schedule(
        Decimal("12000"),
        Decimal("12"),
        12,
        AmortizationSystem.SAC,
    )
    assert totals.months == 12
    assert totals.interest == Decimal("780.00")
    assert totals.paid == Decimal("12780.00")


def test_extra_payment_reduces_price_term_and_interest() -> None:
    baseline = amortization_schedule(
        Decimal("10000"),
        Decimal("12"),
        24,
        AmortizationSystem.PRICE,
    )
    accelerated = amortization_schedule(
        Decimal("10000"),
        Decimal("12"),
        24,
        AmortizationSystem.PRICE,
        recurring_extra=Decimal("200"),
    )
    assert accelerated.months < baseline.months
    assert accelerated.interest < baseline.interest
