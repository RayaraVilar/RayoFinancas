from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.planning.models import BillSource
from app.modules.planning.service import bill_dedupe_key


def test_bill_exact_dedupe_normalizes_description() -> None:
    profile_id = UUID("00000000-0000-0000-0000-000000000001")
    first = bill_dedupe_key(
        profile_id,
        BillSource.MANUAL,
        "  Energia Elétrica! ",
        Decimal("120.00"),
        date(2026, 7, 30),
    )
    second = bill_dedupe_key(
        profile_id,
        BillSource.MANUAL,
        "energia elétrica",
        Decimal("120"),
        date(2026, 7, 30),
    )
    assert first == second


def test_bill_dedupe_separates_profiles_and_sources() -> None:
    common = ("Conta", Decimal("50"), date(2026, 8, 1))
    personal = bill_dedupe_key(
        UUID("00000000-0000-0000-0000-000000000001"),
        BillSource.MANUAL,
        *common,
    )
    business = bill_dedupe_key(
        UUID("00000000-0000-0000-0000-000000000002"),
        BillSource.MANUAL,
        *common,
    )
    assert personal != business
