from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Broadcast, BroadcastStatus


class BroadcastRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        created_by_max_user_id: int,
        text: str,
    ) -> Broadcast:
        broadcast = Broadcast(
            created_by_max_user_id=created_by_max_user_id,
            text=text,
            status=BroadcastStatus.PENDING,
            total_recipients=0,
            sent_count=0,
            failed_count=0,
        )
        self.session.add(broadcast)
        await self.session.flush()
        return broadcast

    async def get_by_id(
        self,
        broadcast_id: int,
        *,
        for_update: bool = False,
    ) -> Broadcast | None:
        return await self.session.get(
            Broadcast,
            broadcast_id,
            with_for_update=for_update,
        )

    async def list_unfinished(self) -> list[Broadcast]:
        result = await self.session.execute(
            select(Broadcast)
            .where(
                Broadcast.status.in_(
                    (BroadcastStatus.PENDING, BroadcastStatus.RUNNING)
                )
            )
            .order_by(Broadcast.id)
        )
        return list(result.scalars())

    async def list_recent(self, limit: int = 5) -> list[Broadcast]:
        result = await self.session.execute(
            select(Broadcast).order_by(Broadcast.id.desc()).limit(limit)
        )
        return list(result.scalars())

    async def set_running(
        self,
        broadcast: Broadcast,
        started_at: datetime,
    ) -> None:
        broadcast.status = BroadcastStatus.RUNNING
        if broadcast.started_at is None:
            broadcast.started_at = started_at
        broadcast.finished_at = None
        await self.session.flush()

    async def update_counters(
        self,
        broadcast: Broadcast,
        total: int,
        sent: int,
        failed: int,
    ) -> None:
        broadcast.total_recipients = total
        broadcast.sent_count = sent
        broadcast.failed_count = failed
        await self.session.flush()

    async def mark_completed(
        self,
        broadcast: Broadcast,
        finished_at: datetime,
    ) -> None:
        broadcast.status = BroadcastStatus.COMPLETED
        broadcast.finished_at = finished_at
        await self.session.flush()

    async def mark_failed(
        self,
        broadcast: Broadcast,
        finished_at: datetime,
    ) -> None:
        broadcast.status = BroadcastStatus.FAILED
        broadcast.finished_at = finished_at
        await self.session.flush()

    async def mark_cancelled(
        self,
        broadcast: Broadcast,
        finished_at: datetime,
    ) -> None:
        broadcast.status = BroadcastStatus.CANCELLED
        broadcast.finished_at = finished_at
        await self.session.flush()
