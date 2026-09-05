"""create broadcasts table

Revision ID: 8c7d4e2f1a63
Revises: f5e8b1c29a40
Create Date: 2026-09-05 14:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "8c7d4e2f1a63"
down_revision: str | Sequence[str] | None = "f5e8b1c29a40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


broadcast_status = sa.Enum(
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
    name="broadcast_status",
)


def upgrade() -> None:
    op.create_table(
        "broadcasts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_by_max_user_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", broadcast_status, nullable=False),
        sa.Column(
            "total_recipients", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("sent_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("broadcasts")
    broadcast_status.drop(op.get_bind(), checkfirst=False)
