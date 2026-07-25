"""Immutable payment simulations and disabled payment entities.

Revision ID: 20260724_0014
Revises: 20260724_0013
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260724_0014"
down_revision: str | Sequence[str] | None = "20260724_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "payment_simulations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("bill_ids", sa.JSON(), nullable=False),
        sa.Column("total_amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("account_options", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("risk_version", sa.String(32), nullable=False),
        sa.Column(
            "status",
            enum("ACTIVE", "EXPIRED", "INVALIDATED", name="paymentsimulationstatus"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id"):
        op.create_index(f"ix_payment_simulations_{column}", "payment_simulations", [column])
    op.create_index(
        "uq_payment_simulations_user_key",
        "payment_simulations",
        ["user_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_payment_simulations_status_expires",
        "payment_simulations",
        ["status", "expires_at"],
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column(
            "financial_profile_id",
            sa.Uuid(),
            sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "simulation_id",
            sa.Uuid(),
            sa.ForeignKey("payment_simulations.id", ondelete="RESTRICT"),
        ),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_payment_id", sa.String(96)),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column(
            "status",
            enum(
                "CREATED",
                "AUTHORIZATION_REQUIRED",
                "PROCESSING",
                "PARTIAL",
                "CONFIRMED",
                "FAILED",
                "UNKNOWN",
                "CANCELLED",
                name="paymentstatus",
            ),
            nullable=False,
        ),
        sa.Column("authorization_expires_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "financial_profile_id", "simulation_id"):
        op.create_index(f"ix_payments_{column}", "payments", [column])
    op.create_index(
        "uq_payments_user_key", "payments", ["user_id", "idempotency_key"], unique=True
    )
    op.create_table(
        "payment_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("payments.id", ondelete="CASCADE")),
        sa.Column("bill_id", sa.Uuid(), sa.ForeignKey("bills.id", ondelete="RESTRICT")),
        sa.Column("amount", sa.Numeric(19, 2), nullable=False),
        sa.Column("provider_idempotency_key", sa.String(96), nullable=False),
        sa.Column("provider_item_id", sa.String(96)),
        sa.Column(
            "status",
            enum(
                "PENDING",
                "PROCESSING",
                "CONFIRMED",
                "FAILED",
                "UNKNOWN",
                name="paymentitemstatus",
            ),
            nullable=False,
        ),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payment_items_payment_id", "payment_items", ["payment_id"])
    op.create_index("ix_payment_items_bill_id", "payment_items", ["bill_id"])
    op.create_index(
        "uq_payment_items_payment_bill",
        "payment_items",
        ["payment_id", "bill_id"],
        unique=True,
    )
    op.create_index(
        "uq_payment_items_provider_key",
        "payment_items",
        ["provider_idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("payment_items")
    op.drop_table("payments")
    op.drop_table("payment_simulations")
