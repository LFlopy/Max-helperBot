from datetime import datetime

from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    BroadcastDelivery,
    BroadcastDeliveryStatus,
    User,
)


class BroadcastDeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_all_users(self, broadcast_id: int) -> int:
        await self.session.execute(
            insert(BroadcastDelivery)
            .from_select(
                ["broadcast_id", "user_id", "status", "attempts"],
                select(
                    literal(broadcast_id),
                    User.id,
                    literal(
                        BroadcastDeliveryStatus.PENDING,
                        type_=BroadcastDelivery.__table__.c.status.type,
                    ),
                    literal(0),
                ),
            )
            .on_conflict_do_nothing(
                constraint="uq_broadcast_deliveries_broadcast_user"
            )
        )
        return await self.count_total(broadcast_id)

    async def get_pending_batch(
        self,
        broadcast_id: int,
        max_attempts: int,
        limit: int,
    ) -> list[tuple[BroadcastDelivery, int]]:
        result = await self.session.execute(
            select(BroadcastDelivery, User.max_user_id)
            .join(User, User.id == BroadcastDelivery.user_id)
            .where(
                BroadcastDelivery.broadcast_id == broadcast_id,
                BroadcastDelivery.status == BroadcastDeliveryStatus.PENDING,
                BroadcastDelivery.attempts < max_attempts,
            )
            .order_by(BroadcastDelivery.id)
            .limit(limit)
            .with_for_update(skip_locked=True, of=BroadcastDelivery)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def mark_sent(
        self,
        delivery: BroadcastDelivery,
        sent_at: datetime,
    ) -> None:
        delivery.status = BroadcastDeliveryStatus.SENT
        delivery.attempts += 1
        delivery.last_error = None
        delivery.sent_at = sent_at
        await self.session.flush()

    async def mark_failed_attempt(
        self,
        delivery: BroadcastDelivery,
        error_code: str,
        retry: bool,
    ) -> None:
        delivery.attempts += 1
        delivery.last_error = error_code[:255]
        if not retry:
            delivery.status = BroadcastDeliveryStatus.FAILED
        await self.session.flush()

    async def count_total(self, broadcast_id: int) -> int:
        result = await self.session.execute(
            select(func.count(BroadcastDelivery.id)).where(
                BroadcastDelivery.broadcast_id == broadcast_id
            )
        )
        return result.scalar_one()

    async def get_counts(self, broadcast_id: int) -> tuple[int, int, int]:
        result = await self.session.execute(
            select(
                func.count(BroadcastDelivery.id),
                func.count(BroadcastDelivery.id).filter(
                    BroadcastDelivery.status == BroadcastDeliveryStatus.SENT
                ),
                func.count(BroadcastDelivery.id).filter(
                    BroadcastDelivery.status == BroadcastDeliveryStatus.FAILED
                ),
            ).where(BroadcastDelivery.broadcast_id == broadcast_id)
        )
        row = result.one()
        return row[0], row[1], row[2]
