"""Bank connections and idempotent webhook receipts.

Revision ID: 20260724_0006
Revises: 20260724_0005
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0006"
down_revision: str | Sequence[str] | None = "20260724_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "bank_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            enum("PLUGGY", "MOCK", name="bankprovidername"),
            nullable=False,
        ),
        sa.Column("external_item_id", sa.String(64), nullable=True),
        sa.Column("connector_id", sa.String(64), nullable=True),
        sa.Column("connector_name", sa.String(160), nullable=True),
        sa.Column(
            "status",
            enum(
                "PENDING",
                "SYNCING",
                "HEALTHY",
                "ERROR",
                "RECONNECT_REQUIRED",
                "REVOKED",
                name="bankconnectionstatus",
            ),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column(
            "consent_granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_connections_user_id", "bank_connections", ["user_id"])
    op.create_index(
        "ix_bank_connections_financial_profile_id",
        "bank_connections",
        ["financial_profile_id"],
    )
    op.create_index(
        "uq_bank_connections_provider_external",
        "bank_connections",
        ["provider", "external_item_id"],
        unique=True,
    )
    op.create_index(
        "ix_bank_connections_profile_status",
        "bank_connections",
        ["financial_profile_id", "status"],
    )

    op.create_table(
        "bank_webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=True),
        sa.Column(
            "provider",
            enum("PLUGGY", "MOCK", name="bankprovidername"),
            nullable=False,
        ),
        sa.Column("external_event_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column(
            "status",
            enum("RECEIVED", "PROCESSED", "FAILED", name="webhookprocessingstatus"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["bank_connections.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bank_webhook_events_connection_id",
        "bank_webhook_events",
        ["connection_id"],
    )
    op.create_index(
        "uq_bank_webhook_events_provider_event",
        "bank_webhook_events",
        ["provider", "external_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_bank_webhook_events_status_created",
        "bank_webhook_events",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("bank_webhook_events")
    op.drop_table("bank_connections")
