import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    BROADCAST_MAX_ATTEMPTS,
    BROADCAST_RETRY_BACKOFF_SECONDS,
    BROADCAST_SEND_INTERVAL_SECONDS,
)
from database.models import Broadcast, BroadcastStatus
from database.repositories import (
    BroadcastDeliveryRepository,
    BroadcastRepository,
    UserRepository,
)
from max_client import MaxAPIError


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


@dataclass(frozen=True, slots=True)
class SendFailure:
    code: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class BroadcastSummary:
    id: int
    status: BroadcastStatus
    total: int
    sent: int
    failed: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class AdminBroadcastService:
    def __init__(
        self,
        session: AsyncSession,
        concurrency: int = 10,
        batch_size: int = 100,
        send_interval_seconds: float = BROADCAST_SEND_INTERVAL_SECONDS,
        max_attempts: int = BROADCAST_MAX_ATTEMPTS,
        retry_backoff_seconds: float = BROADCAST_RETRY_BACKOFF_SECONDS,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if send_interval_seconds < 0 or retry_backoff_seconds < 0:
            raise ValueError("broadcast timing cannot be negative")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.session = session
        self.broadcasts = BroadcastRepository(session)
        self.deliveries = BroadcastDeliveryRepository(session)
        self.users = UserRepository(session)
        self.concurrency = concurrency
        self.batch_size = batch_size
        self.send_interval_seconds = send_interval_seconds
        self.max_attempts = max_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self._send_lock = asyncio.Lock()
        self._next_send_at = 0.0

    async def get_recipient_count(self) -> int:
        return await self.users.count()

    async def list_recent(self, limit: int = 5) -> tuple[BroadcastSummary, ...]:
        broadcasts = await self.broadcasts.list_recent(limit)
        return tuple(self._summary(item) for item in broadcasts)

    async def get_summary(self, broadcast_id: int) -> BroadcastSummary | None:
        broadcast = await self.broadcasts.get_by_id(broadcast_id)
        return None if broadcast is None else self._summary(broadcast)

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
                max_attempts=self.max_attempts,
                limit=self.batch_size,
            )
            if not batch:
                break

            retry_pending = False
            for offset in range(0, len(batch), self.concurrency):
                delivery_batch = batch[offset : offset + self.concurrency]
                results = await asyncio.gather(
                    *(
                        self._send(sender, max_user_id, broadcast.text)
                        for _, max_user_id in delivery_batch
                    )
                )
                for (delivery, _), failure in zip(
                    delivery_batch,
                    results,
                    strict=True,
                ):
                    if failure is None:
                        await self.deliveries.mark_sent(
                            delivery,
                            datetime.now(timezone.utc),
                        )
                    else:
                        retry = (
                            failure.retryable
                            and delivery.attempts + 1 < self.max_attempts
                        )
                        await self.deliveries.mark_failed_attempt(
                            delivery,
                            failure.code,
                            retry=retry,
                        )
                        retry_pending = retry_pending or retry
                        if retry:
                            logger.warning(
                                "Retryable broadcast delivery error: "
                                "broadcast_id=%s attempt=%s error=%s",
                                broadcast.id,
                                delivery.attempts,
                                failure.code,
                            )

            await self._refresh_counters(broadcast)
            await self.session.commit()
            if retry_pending and self.retry_backoff_seconds:
                await asyncio.sleep(self.retry_backoff_seconds)

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

    async def _send(
        self,
        sender: BroadcastSender,
        user_id: int,
        text: str,
    ) -> SendFailure | None:
        await self._pace()
        try:
            await sender.send_message(user_id=user_id, text=text)
        except Exception as error:
            return SendFailure(
                code=(
                    f"http_{error.status_code}"
                    if isinstance(error, MaxAPIError)
                    else type(error).__name__
                ),
                retryable=(
                    isinstance(error, MaxAPIError)
                    and error.status_code == 429
                ),
            )
        return None

    async def _pace(self) -> None:
        if not self.send_interval_seconds:
            return
        async with self._send_lock:
            loop = asyncio.get_running_loop()
            delay = self._next_send_at - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_send_at = loop.time() + self.send_interval_seconds

    @staticmethod
    def _result(broadcast: Broadcast) -> BroadcastResult:
        return BroadcastResult(
            broadcast_id=broadcast.id,
            status=broadcast.status,
            total=broadcast.total_recipients,
            successful=broadcast.sent_count,
            failed=broadcast.failed_count,
        )

    @staticmethod
    def _summary(broadcast: Broadcast) -> BroadcastSummary:
        return BroadcastSummary(
            id=broadcast.id,
            status=broadcast.status,
            total=broadcast.total_recipients,
            sent=broadcast.sent_count,
            failed=broadcast.failed_count,
            created_at=broadcast.created_at,
            started_at=broadcast.started_at,
            finished_at=broadcast.finished_at,
        )
