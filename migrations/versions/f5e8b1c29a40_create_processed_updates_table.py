"""create processed updates table

Revision ID: f5e8b1c29a40
Revises: d3f8a6c14b72
Create Date: 2026-09-05 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f5e8b1c29a40"
down_revision: str | Sequence[str] | None = "d3f8a6c14b72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processed_updates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("update_key", sa.String(length=320), nullable=False),
        sa.Column("update_type", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("update_key"),
    )


def downgrade() -> None:
    op.drop_table("processed_updates")
