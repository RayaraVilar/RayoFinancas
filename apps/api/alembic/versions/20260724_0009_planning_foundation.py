"""Bills, budgets, and monthly plans.

Revision ID: 20260724_0009
Revises: 20260724_0008
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0009"
down_revision: str | Sequence[str] | None = "20260724_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def identity_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
    ]


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "bills",
        *identity_columns(),
        sa.Column(
            "source",
            enum("MANUAL", "CARD_INVOICE", "BANK_PROVIDER", "EMAIL", name="billsource"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(96)),
        sa.Column("dedupe_key", sa.String(64), nullable=False),
        sa.Column(
            "possible_duplicate_of_id",
            sa.Uuid(),
            sa.ForeignKey("bills.id", ondelete="SET NULL"),
        ),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column(
            "status",
            enum(
                "DRAFT",
                "REVIEW_REQUIRED",
                "CONFIRMED",
                "PAID",
                "DISMISSED",
                name="billstatus",
            ),
            nullable=False,
        ),
        sa.Column("paid_on", sa.Date()),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    for column in ("user_id", "financial_profile_id", "possible_duplicate_of_id", "due_on"):
        op.create_index(f"ix_bills_{column}", "bills", [column])
    op.create_index(
        "uq_bills_profile_dedupe",
        "bills",
        ["financial_profile_id", "dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_bills_profile_status_due",
        "bills",
        ["financial_profile_id", "status", "due_on"],
    )

    op.create_table(
        "monthly_budgets",
        *identity_columns(),
        sa.Column(
            "category_id",
            sa.Uuid(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
        ),
        sa.Column("competence_month", sa.Date(), nullable=False),
        sa.Column("limit_amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    for column in ("user_id", "financial_profile_id", "category_id", "competence_month"):
        op.create_index(f"ix_monthly_budgets_{column}", "monthly_budgets", [column])
    op.create_index(
        "uq_monthly_budgets_profile_category_month",
        "monthly_budgets",
        ["financial_profile_id", "category_id", "competence_month"],
        unique=True,
    )

    op.create_table(
        "monthly_plans",
        *identity_columns(),
        sa.Column("competence_month", sa.Date(), nullable=False),
        sa.Column("expected_income", sa.Numeric(19, 2), nullable=False),
        sa.Column("essential_commitment", sa.Numeric(19, 2), nullable=False),
        sa.Column("debt_commitment", sa.Numeric(19, 2), nullable=False),
        sa.Column("goal_contribution", sa.Numeric(19, 2), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    for column in ("user_id", "financial_profile_id", "competence_month"):
        op.create_index(f"ix_monthly_plans_{column}", "monthly_plans", [column])
    op.create_index(
        "uq_monthly_plans_profile_month",
        "monthly_plans",
        ["financial_profile_id", "competence_month"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("monthly_plans")
    op.drop_table("monthly_budgets")
    op.drop_table("bills")
