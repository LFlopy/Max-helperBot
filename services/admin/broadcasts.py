import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Broadcast, BroadcastStatus
from database.repositories import (
    BroadcastDeliveryRepository,
    BroadcastRepository,
    UserRepository,
)


logger = logging.getLogger(__name__)


class BroadcastSender(Protocol):
    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class BroadcastResult:
    broadcast_id: int
    status: BroadcastStatus
    total: int
    successful: int
    failed: int


class AdminBroadcastService:
    def __init__(
        self,
        session: AsyncSession,
        concurrency: int = 10,
        batch_size: int = 100,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.session = session
        self.broadcasts = BroadcastRepository(session)
        self.deliveries = BroadcastDeliveryRepository(session)
        self.users = UserRepository(session)
        self.concurrency = concurrency
        self.batch_size = batch_size

    async def get_recipient_count(self) -> int:
        return await self.users.count()

    async def create(
        self,
        created_by_max_user_id: int,
        text: str,
    ) -> int:
        try:
            broadcast = await self.broadcasts.create(
                created_by_max_user_id=created_by_max_user_id,
                text=text,
            )
            total = await self.deliveries.create_for_all_users(broadcast.id)
            await self.broadcasts.update_counters(broadcast, total, 0, 0)
            await self.session.commit()
            logger.info(
                "Broadcast created: id=%s total=%s",
                broadcast.id,
                total,
            )
            return broadcast.id
        except Exception:
            await self.session.rollback()
            raise

    async def process(
        self,
        broadcast_id: int,
        sender: BroadcastSender,
    ) -> BroadcastResult:
        broadcast = await self.broadcasts.get_by_id(
            broadcast_id,
            for_update=True,
        )
        if broadcast is None:
            raise ValueError("Broadcast not found")
        if broadcast.status in {
            BroadcastStatus.COMPLETED,
            BroadcastStatus.FAILED,
            BroadcastStatus.CANCELLED,
        }:
            return self._result(broadcast)

        await self.broadcasts.set_running(broadcast, datetime.now(timezone.utc))
        await self.session.commit()
        logger.info("Broadcast running: id=%s", broadcast.id)

        while True:
            await self.session.refresh(broadcast)
            if broadcast.status is BroadcastStatus.CANCELLED:
                return self._result(broadcast)

            batch = await self.deliveries.get_pending_batch(
                broadcast.id,
                max_attempts=1,
                limit=self.batch_size,
            )
            if not batch:
                break

            for offset in range(0, len(batch), self.concurrency):
                delivery_batch = batch[offset : offset + self.concurrency]
                results = await asyncio.gather(
                    *(
                        self._send(sender, max_user_id, broadcast.text)
                        for _, max_user_id in delivery_batch
                    )
                )
                for (delivery, _), error_code in zip(
                    delivery_batch,
                    results,
                    strict=True,
                ):
                    if error_code is None:
                        await self.deliveries.mark_sent(
                            delivery,
                            datetime.now(timezone.utc),
                        )
                    else:
                        await self.deliveries.mark_failed_attempt(
                            delivery,
                            error_code,
                            retry=False,
                        )

            await self._refresh_counters(broadcast)
            await self.session.commit()

        await self._refresh_counters(broadcast)
        finished_at = datetime.now(timezone.utc)
        if broadcast.failed_count:
            await self.broadcasts.mark_failed(broadcast, finished_at)
        else:
            await self.broadcasts.mark_completed(broadcast, finished_at)
        await self.session.commit()
        logger.info(
            "Broadcast finished: id=%s status=%s sent=%s failed=%s",
            broadcast.id,
            broadcast.status.value,
            broadcast.sent_count,
            broadcast.failed_count,
        )
        return self._result(broadcast)

    async def _refresh_counters(self, broadcast: Broadcast) -> None:
        total, sent, failed = await self.deliveries.get_counts(broadcast.id)
        await self.broadcasts.update_counters(broadcast, total, sent, failed)

    @staticmethod
    async def _send(
        sender: BroadcastSender,
        user_id: int,
        text: str,
    ) -> str | None:
        try:
            await sender.send_message(user_id=user_id, text=text)
        except Exception as error:
            return type(error).__name__
        return None

    @staticmethod
    def _result(broadcast: Broadcast) -> BroadcastResult:
        return BroadcastResult(
            broadcast_id=broadcast.id,
            status=broadcast.status,
            total=broadcast.total_recipients,
            successful=broadcast.sent_count,
            failed=broadcast.failed_count,
        )
