"""Credit cards, invoices and card-aware transactions.

Revision ID: 20260724_0003
Revises: 20260724_0002
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0003"
down_revision: str | Sequence[str] | None = "20260724_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "credit_cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("institution_name", sa.String(120), nullable=True),
        sa.Column("last_four", sa.String(4), nullable=True),
        sa.Column("closing_day", sa.Integer(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("credit_limit", sa.Numeric(19, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            enum("ACTIVE", "ARCHIVED", name="recordstatus"),
            nullable=False,
        ),
        *timestamps(),
        sa.CheckConstraint(
            "closing_day BETWEEN 1 AND 28",
            name=op.f("ck_credit_cards_closing_day_range"),
        ),
        sa.CheckConstraint(
            "due_day BETWEEN 1 AND 28",
            name=op.f("ck_credit_cards_due_day_range"),
        ),
        sa.CheckConstraint(
            "credit_limit >= 0",
            name=op.f("ck_credit_cards_credit_limit_non_negative"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"],
            ["financial_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_cards_user_id", "credit_cards", ["user_id"])
    op.create_index(
        "ix_credit_cards_financial_profile_id",
        "credit_cards",
        ["financial_profile_id"],
    )
    op.create_index(
        "ix_credit_cards_profile_status",
        "credit_cards",
        ["financial_profile_id", "status"],
    )

    op.create_table(
        "card_invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=False),
        sa.Column("credit_card_id", sa.Uuid(), nullable=False),
        sa.Column("competence_month", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column(
            "status",
            enum("OPEN", "CLOSED", "PAID", name="cardinvoicestatus"),
            nullable=False,
        ),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column("paid_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "competence_month = date_trunc('month', competence_month)::date",
            name=op.f("ck_card_invoices_competence_first_day"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"],
            ["financial_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["credit_card_id"], ["credit_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["paid_transaction_id"],
            ["transactions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "user_id",
        "financial_profile_id",
        "credit_card_id",
        "competence_month",
        "due_on",
        "paid_transaction_id",
    ):
        op.create_index(f"ix_card_invoices_{column}", "card_invoices", [column])
    op.create_index(
        "uq_card_invoices_card_competence",
        "card_invoices",
        ["credit_card_id", "competence_month"],
        unique=True,
    )
    op.create_index(
        "ix_card_invoices_profile_status_due",
        "card_invoices",
        ["financial_profile_id", "status", "due_on"],
    )

    op.alter_column("transactions", "account_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("transactions", sa.Column("credit_card_id", sa.Uuid(), nullable=True))
    op.add_column("transactions", sa.Column("card_invoice_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_credit_card_id_credit_cards",
        "transactions",
        "credit_cards",
        ["credit_card_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_transactions_card_invoice_id_card_invoices",
        "transactions",
        "card_invoices",
        ["card_invoice_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_transactions_credit_card_id", "transactions", ["credit_card_id"])
    op.create_index("ix_transactions_card_invoice_id", "transactions", ["card_invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_card_invoice_id", table_name="transactions")
    op.drop_index("ix_transactions_credit_card_id", table_name="transactions")
    op.drop_constraint(
        "fk_transactions_card_invoice_id_card_invoices",
        "transactions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_transactions_credit_card_id_credit_cards",
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "card_invoice_id")
    op.drop_column("transactions", "credit_card_id")
    op.alter_column("transactions", "account_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_table("card_invoices")
    op.drop_table("credit_cards")
