"""Bank synchronization progress and retry metadata.

Revision ID: 20260724_0008
Revises: 20260724_0007
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0008"
down_revision: str | Sequence[str] | None = "20260724_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bank_connections",
        sa.Column("sync_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "bank_connections",
        sa.Column("sync_accounts_total", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "bank_connections",
        sa.Column("sync_transactions_total", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "bank_connections",
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "bank_webhook_events",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "bank_webhook_events",
        sa.Column("last_error_code", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bank_webhook_events", "last_error_code")
    op.drop_column("bank_webhook_events", "attempts")
    op.drop_column("bank_connections", "consecutive_failures")
    op.drop_column("bank_connections", "sync_transactions_total")
    op.drop_column("bank_connections", "sync_accounts_total")
    op.drop_column("bank_connections", "sync_started_at")
