"""create broadcast deliveries table

Revision ID: 2d9a6b4c8e71
Revises: 8c7d4e2f1a63
Create Date: 2026-09-05 14:15:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2d9a6b4c8e71"
down_revision: str | Sequence[str] | None = "8c7d4e2f1a63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


delivery_status = sa.Enum(
    "pending",
    "sent",
    "failed",
    name="broadcast_delivery_status",
)


def upgrade() -> None:
    op.create_table(
        "broadcast_deliveries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("broadcast_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", delivery_status, nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["broadcast_id"],
            ["broadcasts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "broadcast_id",
            "user_id",
            name="uq_broadcast_deliveries_broadcast_user",
        ),
    )
    op.create_index(
        "ix_broadcast_deliveries_pending",
        "broadcast_deliveries",
        ["broadcast_id", "status", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_broadcast_deliveries_pending",
        table_name="broadcast_deliveries",
    )
    op.drop_table("broadcast_deliveries")
    delivery_status.drop(op.get_bind(), checkfirst=False)
