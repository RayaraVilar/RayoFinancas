from datetime import date
from decimal import Decimal

from app.modules.goals.service import months_between, required_monthly


def test_goal_months_and_required_contribution_are_deterministic() -> None:
    assert months_between(date(2026, 7, 24), date(2027, 1, 24)) == 6
    assert months_between(date(2026, 7, 24), date(2026, 8, 25)) == 2
    assert required_monthly(Decimal("1200"), Decimal("200"), 5) == Decimal("200.00")


def test_goal_due_now_exposes_full_remaining_amount() -> None:
    assert months_between(date(2026, 7, 24), date(2026, 7, 24)) == 0
    assert required_monthly(Decimal("1000"), Decimal("250"), 0) == Decimal("750")


def test_completed_goal_never_requires_negative_contribution() -> None:
    assert required_monthly(Decimal("1000"), Decimal("1200"), 4) == Decimal("0.00")
