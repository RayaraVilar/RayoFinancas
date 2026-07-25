from datetime import date
from decimal import Decimal

from app.modules.analytics.service import (
    change_percent,
    month_bounds,
    percent,
    previous_equivalent_bounds,
    quantize_money,
)


def test_equivalent_period_clamps_short_previous_month() -> None:
    assert previous_equivalent_bounds(date(2026, 3, 31)) == (
        date(2026, 2, 1),
        date(2026, 2, 28),
    )
    assert previous_equivalent_bounds(date(2026, 7, 15)) == (
        date(2026, 6, 1),
        date(2026, 6, 15),
    )


def test_month_bounds_support_leap_year() -> None:
    assert month_bounds(date(2028, 2, 10)) == (
        date(2028, 2, 1),
        date(2028, 2, 29),
    )


def test_money_and_percent_round_half_up() -> None:
    assert quantize_money(Decimal("10.005")) == Decimal("10.01")
    assert percent(Decimal("1"), Decimal("3")) == Decimal("33.3")
    assert change_percent(Decimal("120"), Decimal("100")) == Decimal("20.0")


def test_zero_denominators_are_explicit() -> None:
    assert percent(Decimal("10"), Decimal("0")) == Decimal("0.0")
    assert change_percent(Decimal("10"), Decimal("0")) is None
