"""Net worth and health score snapshots.

Revision ID: 20260724_0012
Revises: 20260724_0011
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0012"
down_revision: str | Sequence[str] | None = "20260724_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column("snapshot_on", sa.Date(), nullable=False),
        sa.Column("assets", sa.Numeric(19, 2), nullable=False),
        sa.Column("liabilities", sa.Numeric(19, 2), nullable=False),
        sa.Column("net_worth", sa.Numeric(19, 2), nullable=False),
        sa.Column("algorithm_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id", "snapshot_on"):
        op.create_index(f"ix_net_worth_snapshots_{column}", "net_worth_snapshots", [column])
    op.create_index(
        "uq_net_worth_snapshots_profile_date",
        "net_worth_snapshots",
        ["financial_profile_id", "snapshot_on"],
        unique=True,
    )
    op.create_table(
        "health_score_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column("snapshot_on", sa.Date(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("confidence_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("subscores", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id", "snapshot_on"):
        op.create_index(f"ix_health_score_snapshots_{column}", "health_score_snapshots", [column])
    op.create_index(
        "uq_health_score_snapshots_profile_date_version",
        "health_score_snapshots",
        ["financial_profile_id", "snapshot_on", "algorithm_version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("health_score_snapshots")
    op.drop_table("net_worth_snapshots")
