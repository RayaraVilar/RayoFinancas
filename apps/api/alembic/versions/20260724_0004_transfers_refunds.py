"""Paired transfers and idempotent refunds.

Revision ID: 20260724_0004
Revises: 20260724_0003
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0004"
down_revision: str | Sequence[str] | None = "20260724_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "transfer_direction",
            sa.Enum(
                "OUTFLOW",
                "INFLOW",
                name="transferdirection",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("reversal_of_transaction_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("operation_key", sa.String(64), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_reversal_of_transaction_id_transactions",
        "transactions",
        "transactions",
        ["reversal_of_transaction_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_transactions_reversal_of_transaction_id",
        "transactions",
        ["reversal_of_transaction_id"],
    )
    op.create_index(
        "uq_transactions_reversal_of",
        "transactions",
        ["reversal_of_transaction_id"],
        unique=True,
    )
    op.create_index(
        "uq_transactions_operation_key",
        "transactions",
        ["operation_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_transactions_operation_key", table_name="transactions")
    op.drop_index("uq_transactions_reversal_of", table_name="transactions")
    op.drop_index(
        "ix_transactions_reversal_of_transaction_id",
        table_name="transactions",
    )
    op.drop_constraint(
        "fk_transactions_reversal_of_transaction_id_transactions",
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "operation_key")
    op.drop_column("transactions", "reversal_of_transaction_id")
    op.drop_column("transactions", "transfer_direction")
