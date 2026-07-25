"""Identity, financial profiles, onboarding, and audit.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("avatar_url", sa.String(2048), nullable=True),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            enum("ACTIVE", "DISABLED", "DELETION_PENDING", name="userstatus"),
            nullable=False,
        ),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "oauth_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("email_at_login", sa.String(320), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_oauth_identities_provider_subject",
        "oauth_identities",
        ["provider", "subject"],
        unique=True,
    )
    op.create_index("ix_oauth_identities_user_id", "oauth_identities", ["user_id"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])

    op.create_table(
        "financial_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            enum("PERSONAL", "BUSINESS", name="financialprofiletype"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("document_last4", sa.String(4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column(
            "status",
            enum("ACTIVE", "ARCHIVED", name="recordstatus"),
            nullable=False,
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_profiles_user_id", "financial_profiles", ["user_id"])
    op.create_index(
        "ix_financial_profiles_user_status",
        "financial_profiles",
        ["user_id", "status"],
    )
    op.create_index(
        "uq_financial_profiles_active_personal",
        "financial_profiles",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("type = 'PERSONAL' AND status = 'ACTIVE'"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("institution_name", sa.String(120), nullable=True),
        sa.Column(
            "type",
            enum("CHECKING", "SAVINGS", "CASH", "PAYMENT", "OTHER", name="accounttype"),
            nullable=False,
        ),
        sa.Column(
            "source",
            enum("MANUAL", "BANK_PROVIDER", name="accountsource"),
            nullable=False,
        ),
        sa.Column("current_balance", sa.Numeric(19, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "status",
            enum("ACTIVE", "ARCHIVED", name="recordstatus"),
            nullable=False,
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"], ["financial_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])
    op.create_index("ix_accounts_financial_profile_id", "accounts", ["financial_profile_id"])
    op.create_index(
        "ix_accounts_profile_status",
        "accounts",
        ["financial_profile_id", "status"],
    )

    op.create_table(
        "user_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("financial_profile_id", sa.Uuid(), nullable=True),
        sa.Column("consent_type", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["financial_profile_id"], ["financial_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])
    op.create_index(
        "ix_user_consents_financial_profile_id",
        "user_consents",
        ["financial_profile_id"],
    )
    op.create_index(
        "ix_user_consents_user_type",
        "user_consents",
        ["user_id", "consent_type"],
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("safe_metadata", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index(
        "ix_audit_events_user_created",
        "audit_events",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("user_consents")
    op.drop_table("accounts")
    op.drop_table("financial_profiles")
    op.drop_table("sessions")
    op.drop_table("oauth_identities")
    op.drop_table("users")
