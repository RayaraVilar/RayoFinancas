from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.debts.models import AmortizationSystem, Debt
from app.modules.goals.models import Goal
from app.modules.identity.models import (
    AccountSource,
    AccountType,
    FinancialAccount,
    FinancialProfile,
    FinancialProfileType,
    User,
    UserConsent,
)
from app.modules.ledger.models import (
    Category,
    CreditCard,
    Transaction,
    TransactionKind,
    TransactionSource,
    TransactionStatus,
)
from app.modules.planning.models import Bill, BillSource, BillStatus, MonthlyPlan


def _month_start(value: date) -> date:
    return value.replace(day=1)


async def create_demo_user(db: AsyncSession) -> tuple[User, FinancialProfile]:
    today = date.today()
    await db.execute(
        delete(User).where(
            User.is_demo.is_(True),
            User.created_at < datetime.now(UTC) - timedelta(hours=24),
        )
    )
    demo_id = uuid4()
    user = User(
        id=demo_id,
        email=f"demo-{demo_id}@demo.rayo.local",
        display_name="Marina Demo",
        is_demo=True,
        onboarding_completed_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()
    personal = FinancialProfile(
        user_id=user.id,
        type=FinancialProfileType.PERSONAL,
        name="Minha vida",
    )
    business = FinancialProfile(
        user_id=user.id,
        type=FinancialProfileType.BUSINESS,
        name="Estúdio Aurora",
    )
    db.add_all([personal, business])
    await db.flush()

    personal_account = FinancialAccount(
        user_id=user.id,
        financial_profile_id=personal.id,
        name="Conta principal",
        institution_name="Banco demonstração",
        type=AccountType.CHECKING,
        source=AccountSource.MANUAL,
        current_balance=Decimal("4280.60"),
    )
    business_account = FinancialAccount(
        user_id=user.id,
        financial_profile_id=business.id,
        name="Conta da empresa",
        institution_name="Banco demonstração",
        type=AccountType.CHECKING,
        source=AccountSource.MANUAL,
        current_balance=Decimal("9350.00"),
    )
    categories = list(
        await db.scalars(select(Category).where(Category.system_code.is_not(None)))
    )
    db.add_all([personal_account, business_account])
    await db.flush()
    by_name = {item.name: item for item in categories}

    transaction_specs = [
        ("Salário", "Receitas", TransactionKind.INCOME, "7200.00", 2),
        ("Aluguel", "Moradia", TransactionKind.EXPENSE, "1850.00", 4),
        ("Supermercado", "Alimentação", TransactionKind.EXPENSE, "486.40", 7),
        ("Transporte", "Transporte", TransactionKind.EXPENSE, "238.90", 10),
        ("Cinema e jantar", "Lazer", TransactionKind.EXPENSE, "164.10", 13),
    ]
    transactions = []
    for description, category_name, kind, amount, day_offset in transaction_specs:
        occurred_on = max(_month_start(today), today - timedelta(days=day_offset))
        transactions.append(
            Transaction(
                user_id=user.id,
                financial_profile_id=personal.id,
                account_id=personal_account.id,
                category_id=by_name[category_name].id,
                kind=kind,
                status=TransactionStatus.POSTED,
                source=TransactionSource.MANUAL,
                description=description,
                amount=Decimal(amount),
                occurred_on=occurred_on,
                competence_month=_month_start(occurred_on),
            )
        )
    db.add_all(
        [
            *transactions,
            CreditCard(
                user_id=user.id,
                financial_profile_id=personal.id,
                name="Cartão principal",
                institution_name="Banco demonstração",
                last_four="2840",
                closing_day=18,
                due_day=25,
                credit_limit=Decimal("6500.00"),
            ),
            MonthlyPlan(
                user_id=user.id,
                financial_profile_id=personal.id,
                competence_month=_month_start(today),
                expected_income=Decimal("7200.00"),
                essential_commitment=Decimal("3100.00"),
                debt_commitment=Decimal("420.00"),
                goal_contribution=Decimal("700.00"),
            ),
            Bill(
                user_id=user.id,
                financial_profile_id=personal.id,
                source=BillSource.MANUAL,
                dedupe_key=hashlib.sha256(f"{demo_id}:energia".encode()).hexdigest(),
                description="Conta de energia",
                amount=Decimal("186.70"),
                due_on=today + timedelta(days=5),
                status=BillStatus.CONFIRMED,
            ),
            Goal(
                user_id=user.id,
                financial_profile_id=personal.id,
                name="Reserva de emergência",
                target_amount=Decimal("18000.00"),
                current_amount=Decimal("6300.00"),
                target_date=today + timedelta(days=420),
                monthly_contribution=Decimal("700.00"),
                priority=10,
            ),
            Debt(
                user_id=user.id,
                financial_profile_id=personal.id,
                name="Financiamento do notebook",
                original_principal=Decimal("5200.00"),
                outstanding_balance=Decimal("2180.00"),
                annual_interest_rate=Decimal("0.145000"),
                annual_cet_rate=Decimal("0.162000"),
                amortization_system=AmortizationSystem.PRICE,
                installments_remaining=6,
                monthly_payment=Decimal("420.00"),
                next_due_on=today + timedelta(days=12),
                data_quality="COMPLETE",
            ),
            UserConsent(
                user_id=user.id,
                financial_profile_id=None,
                consent_type="PRIVACY_POLICY",
                version="2026-07-24",
            ),
        ]
    )
    await db.flush()
    return user, personal
