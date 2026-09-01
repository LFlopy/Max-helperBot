"""add trial usage to users

Revision ID: d3f8a6c14b72
Revises: b7c4e12a9f30
Create Date: 2026-09-01 19:05:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d3f8a6c14b72"
down_revision: str | Sequence[str] | None = "b7c4e12a9f30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "trial_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "trial_used_at")
