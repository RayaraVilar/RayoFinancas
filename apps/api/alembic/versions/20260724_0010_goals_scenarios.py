"""Goals, scenarios, plan history, and pending actions.

Revision ID: 20260724_0010
Revises: 20260724_0009
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0010"
down_revision: str | Sequence[str] | None = "20260724_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("target_amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("monthly_contribution", sa.Numeric(19, 2), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            enum("ACTIVE", "COMPLETED", "ARCHIVED", name="goalstatus"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id"):
        op.create_index(f"ix_goals_{column}", "goals", [column])
    op.create_index("ix_goals_profile_status", "goals", ["financial_profile_id", "status"])

    op.create_table(
        "goal_contributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("goal_id", sa.Uuid(), sa.ForeignKey("goals.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("contributed_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("goal_id", "user_id", "contributed_on"):
        op.create_index(f"ix_goal_contributions_{column}", "goal_contributions", [column])

    op.create_table(
        "goal_plan_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("goal_id", sa.Uuid(), sa.ForeignKey("goals.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_goal_plan_versions_goal_id", "goal_plan_versions", ["goal_id"])
    op.create_index("ix_goal_plan_versions_user_id", "goal_plan_versions", ["user_id"])
    op.create_index(
        "uq_goal_plan_versions_goal_version",
        "goal_plan_versions",
        ["goal_id", "version"],
        unique=True,
    )

    op.create_table(
        "goal_scenarios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("goal_id", sa.Uuid(), sa.ForeignKey("goals.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_goal_scenarios_goal_id", "goal_scenarios", ["goal_id"])
    op.create_index("ix_goal_scenarios_user_id", "goal_scenarios", ["user_id"])

    op.create_table(
        "pending_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("target_version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=False),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            enum("PENDING", "CONFIRMED", "EXPIRED", "CANCELLED", name="pendingactionstatus"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id"):
        op.create_index(f"ix_pending_actions_{column}", "pending_actions", [column])
    op.create_index(
        "uq_pending_actions_idempotency",
        "pending_actions",
        ["user_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_pending_actions_status_expires",
        "pending_actions",
        ["status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_table("pending_actions")
    op.drop_table("goal_scenarios")
    op.drop_table("goal_plan_versions")
    op.drop_table("goal_contributions")
    op.drop_table("goals")
