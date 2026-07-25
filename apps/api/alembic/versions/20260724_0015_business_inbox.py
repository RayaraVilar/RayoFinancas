"""Business receivables, subscriptions, inbox, and notifications.

Revision ID: 20260724_0015
Revises: 20260724_0014
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0015"
down_revision: str | Sequence[str] | None = "20260724_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def base_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "receivables",
        *base_columns(),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(96)),
        sa.Column("dedupe_key", sa.String(64), nullable=False),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("counterparty", sa.String(120)),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column(
            "status",
            enum("EXPECTED", "RECEIVED", "DISMISSED", name="receivablestatus"),
            nullable=False,
        ),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("received_on", sa.Date()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id", "due_on"):
        op.create_index(f"ix_receivables_{column}", "receivables", [column])
    op.create_index(
        "uq_receivables_profile_dedupe",
        "receivables",
        ["financial_profile_id", "dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_receivables_profile_status_due",
        "receivables",
        ["financial_profile_id", "status", "due_on"],
    )

    op.create_table(
        "subscriptions",
        *base_columns(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("merchant_key", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("cadence_months", sa.Integer(), nullable=False),
        sa.Column("next_charge_on", sa.Date(), nullable=False),
        sa.Column(
            "status",
            enum("CANDIDATE", "CONFIRMED", "CANCELLED", name="subscriptionstatus"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id"):
        op.create_index(f"ix_subscriptions_{column}", "subscriptions", [column])
    op.create_index(
        "uq_subscriptions_profile_merchant",
        "subscriptions",
        ["financial_profile_id", "merchant_key"],
        unique=True,
    )

    op.create_table(
        "email_ingestion_consents",
        *base_columns(),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("scope_version", sa.String(32), nullable=False),
        sa.Column("mailbox_hash", sa.String(64)),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "uq_email_consents_user_profile",
        "email_ingestion_consents",
        ["user_id", "financial_profile_id"],
        unique=True,
    )

    op.create_table(
        "inbox_candidates",
        *base_columns(),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("dedupe_key", sa.String(64), nullable=False),
        sa.Column("sender_domain_hash", sa.String(64)),
        sa.Column("extracted_fields", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            enum(
                "REVIEW_REQUIRED",
                "ACCEPTED",
                "REJECTED",
                name="inboxreviewstatus",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id"):
        op.create_index(f"ix_inbox_candidates_{column}", "inbox_candidates", [column])
    op.create_index(
        "uq_inbox_candidates_profile_dedupe",
        "inbox_candidates",
        ["financial_profile_id", "dedupe_key"],
        unique=True,
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("channel", sa.String(24), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("quiet_hours_start", sa.String(5)),
        sa.Column("quiet_hours_end", sa.String(5)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])
    op.create_index(
        "uq_notification_preferences_user_channel",
        "notification_preferences",
        ["user_id", "channel"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("inbox_candidates")
    op.drop_table("email_ingestion_consents")
    op.drop_table("subscriptions")
    op.drop_table("receivables")
