"""Canonical bank account and transaction mappings.

Revision ID: 20260724_0007
Revises: 20260724_0006
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0007"
down_revision: str | Sequence[str] | None = "20260724_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def add_provider_columns(table: str) -> None:
    op.add_column(table, sa.Column("bank_connection_id", sa.Uuid(), nullable=True))
    op.add_column(table, sa.Column("external_id", sa.String(96), nullable=True))
    op.create_foreign_key(
        f"fk_{table}_bank_connection_id_bank_connections",
        table,
        "bank_connections",
        ["bank_connection_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        f"ix_{table}_bank_connection_id",
        table,
        ["bank_connection_id"],
    )


def upgrade() -> None:
    add_provider_columns("accounts")
    op.create_index(
        "uq_accounts_bank_connection_external",
        "accounts",
        ["bank_connection_id", "external_id"],
        unique=True,
    )
    add_provider_columns("credit_cards")
    op.create_index(
        "uq_credit_cards_bank_connection_external",
        "credit_cards",
        ["bank_connection_id", "external_id"],
        unique=True,
    )
    add_provider_columns("transactions")
    op.create_index(
        "uq_transactions_bank_connection_external",
        "transactions",
        ["bank_connection_id", "external_id"],
        unique=True,
    )


def drop_provider_columns(table: str, unique_index: str) -> None:
    op.drop_index(unique_index, table_name=table)
    op.drop_index(f"ix_{table}_bank_connection_id", table_name=table)
    op.drop_constraint(
        f"fk_{table}_bank_connection_id_bank_connections",
        table,
        type_="foreignkey",
    )
    op.drop_column(table, "external_id")
    op.drop_column(table, "bank_connection_id")


def downgrade() -> None:
    drop_provider_columns("transactions", "uq_transactions_bank_connection_external")
    drop_provider_columns("credit_cards", "uq_credit_cards_bank_connection_external")
    drop_provider_columns("accounts", "uq_accounts_bank_connection_external")
