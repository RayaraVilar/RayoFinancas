from datetime import date

from app.modules.ledger.service import invoice_dates


def test_invoice_before_closing_is_due_in_same_month() -> None:
    assert invoice_dates(date(2026, 7, 8), closing_day=10, due_day=17) == (
        date(2026, 7, 1),
        date(2026, 7, 17),
    )


def test_invoice_after_closing_moves_to_next_month() -> None:
    assert invoice_dates(date(2026, 7, 11), closing_day=10, due_day=17) == (
        date(2026, 8, 1),
        date(2026, 8, 17),
    )


def test_due_day_before_closing_moves_due_date_forward() -> None:
    assert invoice_dates(date(2026, 12, 1), closing_day=20, due_day=5) == (
        date(2026, 12, 1),
        date(2027, 1, 5),
    )
