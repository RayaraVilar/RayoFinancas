"""Per-user AI credentials and isolated demo users.

Revision ID: 20260725_0016
Revises: 20260724_0015
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260725_0016"
down_revision: str | Sequence[str] | None = "20260724_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "assistant_credentials",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("key_hint", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "ix_assistant_credentials_user_id",
        "assistant_credentials",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("assistant_credentials")
    op.drop_column("users", "is_demo")
