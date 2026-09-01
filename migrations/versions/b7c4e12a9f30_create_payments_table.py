"""create payments table

Revision ID: b7c4e12a9f30
Revises: a91c3e6f2d47
Create Date: 2026-09-01 18:15:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b7c4e12a9f30"
down_revision: str | Sequence[str] | None = "a91c3e6f2d47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


payment_status = sa.Enum(
    "pending",
    "paid",
    "canceled",
    "failed",
    name="payment_status",
)


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("tariff_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column(
            "provider_payment_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_payment_id",
            name="uq_payments_provider_payment_id",
        ),
    )
    op.create_index(
        "ix_payments_status_created",
        "payments",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_payments_user_created",
        "payments",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payments_user_created", table_name="payments")
    op.drop_index("ix_payments_status_created", table_name="payments")
    op.drop_table("payments")
    payment_status.drop(op.get_bind(), checkfirst=False)
