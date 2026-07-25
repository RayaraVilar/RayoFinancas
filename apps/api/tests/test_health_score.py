from decimal import Decimal

from app.modules.future.schemas import HealthSubscore
from app.modules.future.service import (
    cashflow_score,
    reserve_score,
    weighted_health_score,
)


def test_cashflow_curve_has_documented_milestones() -> None:
    assert cashflow_score(Decimal("0"), Decimal("1")) == Decimal("30")
    assert cashflow_score(Decimal("10"), Decimal("1")) == Decimal("60")
    assert cashflow_score(Decimal("20"), Decimal("1")) == Decimal("85.0")
    assert cashflow_score(Decimal("30"), Decimal("1")) == Decimal("100")
    assert cashflow_score(Decimal("20"), Decimal("-1")) == Decimal("0")


def test_reserve_curve_has_one_three_and_six_month_milestones() -> None:
    assert reserve_score(Decimal("0")) == Decimal("0")
    assert reserve_score(Decimal("1")) == Decimal("35")
    assert reserve_score(Decimal("3")) == Decimal("70.0")
    assert reserve_score(Decimal("6")) == Decimal("100")


def test_missing_subscore_reduces_confidence_without_becoming_zero() -> None:
    result = weighted_health_score(
        [
            HealthSubscore(
                code="KNOWN",
                label="Conhecido",
                weight=60,
                score=Decimal("80"),
                explanation="fixture",
            ),
            HealthSubscore(
                code="MISSING",
                label="Ausente",
                weight=40,
                score=None,
                explanation="fixture",
            ),
        ]
    )
    assert result.score == Decimal("80.0")
    assert result.confidence_percent == Decimal("60.0")
    assert result.sufficient_data is True
