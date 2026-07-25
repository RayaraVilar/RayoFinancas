from decimal import Decimal

from app.modules.insights.service import analytics_candidates


def test_deficit_is_prioritized_and_reproducible() -> None:
    items = analytics_candidates(
        Decimal("-250"),
        Decimal("25"),
        Decimal("1000"),
        Decimal("90"),
        "CURRENT",
    )
    assert [item.rule_code for item in items] == ["PROJECTED_DEFICIT", "EXPENSE_SPIKE"]
    assert items[0].priority > items[1].priority
    assert items[0].evidence == {"projected_balance": "-250"}


def test_irrelevant_variations_do_not_create_noise() -> None:
    items = analytics_candidates(
        Decimal("500"),
        Decimal("19.9"),
        Decimal("99"),
        Decimal("100"),
        "CURRENT",
    )
    assert items == []


def test_stale_and_low_coverage_rules_expose_evidence() -> None:
    items = analytics_candidates(
        Decimal("100"),
        None,
        Decimal("500"),
        Decimal("40"),
        "OUTDATED",
    )
    assert {item.rule_code for item in items} == {
        "LOW_CATEGORY_COVERAGE",
        "STALE_BANK_DATA",
    }
