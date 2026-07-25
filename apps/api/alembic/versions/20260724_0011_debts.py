"""Debt contracts and payments.

Revision ID: 20260724_0011
Revises: 20260724_0010
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0011"
down_revision: str | Sequence[str] | None = "20260724_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("original_principal", sa.Numeric(19, 2), nullable=False),
        sa.Column("outstanding_balance", sa.Numeric(19, 2), nullable=False),
        sa.Column("annual_interest_rate", sa.Numeric(9, 6)),
        sa.Column("annual_cet_rate", sa.Numeric(9, 6)),
        sa.Column(
            "amortization_system",
            sa.Enum(
                "PRICE",
                "SAC",
                "UNKNOWN",
                name="amortizationsystem",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("installments_remaining", sa.Integer(), nullable=False),
        sa.Column("monthly_payment", sa.Numeric(19, 2)),
        sa.Column("next_due_on", sa.Date()),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "PAID",
                "ARCHIVED",
                name="debtstatus",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("data_quality", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id"):
        op.create_index(f"ix_debts_{column}", "debts", [column])
    op.create_index("ix_debts_profile_status", "debts", ["financial_profile_id", "status"])
    op.create_table(
        "debt_payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("debt_id", sa.Uuid(), sa.ForeignKey("debts.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("principal_amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("interest_amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("debt_id", "user_id", "paid_on"):
        op.create_index(f"ix_debt_payments_{column}", "debt_payments", [column])


def downgrade() -> None:
    op.drop_table("debt_payments")
    op.drop_table("debts")
