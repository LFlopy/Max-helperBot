"""create users table

Revision ID: c68ee833d79a
Revises:
Create Date: 2026-09-01 13:38:42.611673

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c68ee833d79a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("max_user_id"),
    )


def downgrade() -> None:
    op.drop_table("users")
