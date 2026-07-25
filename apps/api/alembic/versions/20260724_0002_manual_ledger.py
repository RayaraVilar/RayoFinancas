"""Manual categories and transactions.

Revision ID: 20260724_0002
Revises: 20260724_0001
Create Date: 2026-07-24
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0002"
down_revision: str | Sequence[str] | None = "20260724_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_CATEGORIES = (
    ("10000000-0000-4000-8000-000000000001", "income", "Receitas", "INCOME", "#4E9A6D", "wallet"),
    ("10000000-0000-4000-8000-000000000002", "housing", "Moradia", "EXPENSE", "#315D4F", "house"),
    (
        "10000000-0000-4000-8000-000000000003",
        "food",
        "Alimentação",
        "EXPENSE",
        "#82A94C",
        "utensils",
    ),
    (
        "10000000-0000-4000-8000-000000000004",
        "transport",
        "Transporte",
        "EXPENSE",
        "#C3A65A",
        "car",
    ),
    ("10000000-0000-4000-8000-000000000005", "health", "Saúde", "EXPENSE", "#5B8FA8", "heart"),
    ("10000000-0000-4000-8000-000000000006", "education", "Educação", "EXPENSE", "#7567A8", "book"),
    ("10000000-0000-4000-8000-000000000007", "leisure", "Lazer", "EXPENSE", "#C26E72", "sparkles"),
    ("10000000-0000-4000-8000-000000000008", "other", "Outros", "BOTH", "#7A8982", "tag"),
)


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
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=True),
        sa.Column("system_code", sa.String(40), nullable=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("normalized_name", sa.String(80), nullable=False),
        sa.Column(
            "kind",
            enum("INCOME", "EXPENSE", "BOTH", name="categorykind"),
            nullable=False,
        ),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("icon", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"],
            ["financial_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("system_code"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_index(
        "ix_categories_financial_profile_id",
        "categories",
        ["financial_profile_id"],
    )
    op.create_index(
        "uq_categories_profile_normalized_name",
        "categories",
        ["financial_profile_id", "normalized_name"],
        unique=True,
    )
    categories = sa.table(
        "categories",
        sa.column("id", sa.Uuid()),
        sa.column("system_code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("normalized_name", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("color", sa.String()),
        sa.column("icon", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        categories,
        [
            {
                "id": UUID(category_id),
                "system_code": code,
                "name": name,
                "normalized_name": code,
                "kind": kind,
                "color": color,
                "icon": icon,
                "is_active": True,
            }
            for category_id, code, name, kind, color, icon in DEFAULT_CATEGORIES
        ],
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column(
            "kind",
            enum("INCOME", "EXPENSE", "TRANSFER", name="transactionkind"),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum("PENDING", "POSTED", "VOIDED", name="transactionstatus"),
            nullable=False,
        ),
        sa.Column(
            "source",
            enum("MANUAL", "BANK_PROVIDER", name="transactionsource"),
            nullable=False,
        ),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("competence_month", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("transfer_group_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint(
            "competence_month = date_trunc('month', competence_month)::date",
            name="ck_transactions_competence_first_day",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"],
            ["financial_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "user_id",
        "financial_profile_id",
        "account_id",
        "category_id",
        "occurred_on",
        "competence_month",
        "transfer_group_id",
    ):
        op.create_index(f"ix_transactions_{column}", "transactions", [column])
    op.create_index(
        "ix_transactions_user_profile_occurred",
        "transactions",
        ["user_id", "financial_profile_id", "occurred_on", "id"],
    )
    op.create_index(
        "ix_transactions_profile_status",
        "transactions",
        ["financial_profile_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("categories")
