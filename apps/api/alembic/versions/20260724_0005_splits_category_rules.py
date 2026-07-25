"""Transaction splits and deterministic category rules.

Revision ID: 20260724_0005
Revises: 20260724_0004
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0005"
down_revision: str | Sequence[str] | None = "20260724_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "category_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("match_text", sa.String(120), nullable=False),
        sa.Column("normalized_match_text", sa.String(120), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"],
            ["financial_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_category_rules_user_id", "category_rules", ["user_id"])
    op.create_index(
        "ix_category_rules_financial_profile_id",
        "category_rules",
        ["financial_profile_id"],
    )
    op.create_index("ix_category_rules_category_id", "category_rules", ["category_id"])
    op.create_index(
        "uq_category_rules_profile_match",
        "category_rules",
        ["financial_profile_id", "normalized_match_text"],
        unique=True,
    )
    op.create_index(
        "ix_category_rules_profile_active_priority",
        "category_rules",
        ["financial_profile_id", "is_active", "priority"],
    )

    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(160), nullable=True),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount > 0",
            name=op.f("ck_transaction_splits_amount_positive"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"],
            ["financial_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "financial_profile_id", "transaction_id", "category_id"):
        op.create_index(f"ix_transaction_splits_{column}", "transaction_splits", [column])
    op.create_index(
        "uq_transaction_splits_transaction_position",
        "transaction_splits",
        ["transaction_id", "position"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("transaction_splits")
    op.drop_table("category_rules")
