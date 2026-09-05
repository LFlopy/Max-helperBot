from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class BroadcastDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class BroadcastDelivery(Base):
    __tablename__ = "broadcast_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "broadcast_id",
            "user_id",
            name="uq_broadcast_deliveries_broadcast_user",
        ),
        Index(
            "ix_broadcast_deliveries_pending",
            "broadcast_id",
            "status",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("broadcasts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[BroadcastDeliveryStatus] = mapped_column(
        Enum(
            BroadcastDeliveryStatus,
            name="broadcast_delivery_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
