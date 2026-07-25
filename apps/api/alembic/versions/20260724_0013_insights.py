"""Versioned insights and feedback.

Revision ID: 20260724_0013
Revises: 20260724_0012
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0013"
down_revision: str | Sequence[str] | None = "20260724_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insights",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column("rule_code", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("cta_label", sa.String(80)),
        sa.Column("cta_path", sa.String(160)),
        sa.Column(
            "state",
            sa.Enum(
                "ACTIVE",
                "DISMISSED",
                "ACTED",
                name="insightstate",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id"):
        op.create_index(f"ix_insights_{column}", "insights", [column])
    op.create_index(
        "uq_insights_profile_dedupe",
        "insights",
        ["financial_profile_id", "dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_insights_profile_state_priority",
        "insights",
        ["financial_profile_id", "state", "priority"],
    )
    op.create_table(
        "insight_feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("insight_id", sa.Uuid(), sa.ForeignKey("insights.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("helpful", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_insight_feedback_insight_id", "insight_feedback", ["insight_id"])
    op.create_index("ix_insight_feedback_user_id", "insight_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_table("insight_feedback")
    op.drop_table("insights")
