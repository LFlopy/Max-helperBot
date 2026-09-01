"""create messages table

Revision ID: e2234b3649a2
Revises: c68ee833d79a
Create Date: 2026-09-01 13:47:18.735967

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e2234b3649a2"
down_revision: str | Sequence[str] | None = "c68ee833d79a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_user_id"),
        "messages",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_user_id"), table_name="messages")
    op.drop_table("messages")
