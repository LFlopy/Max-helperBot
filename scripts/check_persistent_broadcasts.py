import asyncio
from time import time_ns
from typing import cast

from sqlalchemy import delete, select

from bot.handlers.admin.broadcasts import broadcast_status
from database.models import Broadcast, BroadcastDelivery, User
from database.repositories import (
    BroadcastDeliveryRepository,
    BroadcastRepository,
    UserRepository,
)
from database.session import engine, session_factory
from max_client import MaxAPIError, MaxBot
from services.admin import AdminBroadcastService, BroadcastSender
from services.admin.broadcast_recovery import BroadcastRecoveryManager
from services.update_processing import BackgroundTaskRegistry


class FakeSender:
    def __init__(
        self,
        failed_ids: set[int] | None = None,
        rate_limited_id: int | None = None,
    ) -> None:
        self.failed_ids = failed_ids or set()
        self.rate_limited_id = rate_limited_id
        self.calls: dict[int, int] = {}
        self.messages: list[tuple[int, str]] = []
        self.callback_messages: list[str] = []

    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> dict[str, object]:
        self.calls[user_id] = self.calls.get(user_id, 0) + 1
        if user_id in self.failed_ids:
            raise RuntimeError("synthetic")
        if user_id == self.rate_limited_id and self.calls[user_id] < 3:
            raise MaxAPIError(429)
        self.messages.append((user_id, text))
        return {}

    async def answer_callback(
        self,
        callback_id: str,
        message: dict,
    ) -> dict[str, object]:
        self.callback_messages.append(str(message["text"]))
        return {}


class BlockingSender(FakeSender):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> dict[str, object]:
        self.started.set()
        await self.release.wait()
        return await super().send_message(user_id, text, attachments)


async def wait_for_tasks(registry: BackgroundTaskRegistry) -> None:
    async def empty() -> None:
        while registry.tasks:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(empty(), timeout=10)


async def cleanup(max_user_ids: tuple[int, ...], marker: str) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(Broadcast).where(Broadcast.text.like(f"broadcast-{marker}-%"))
        )
        await session.execute(
            delete(User).where(User.max_user_id.in_(max_user_ids))
        )
        await session.commit()


async def main() -> None:
    marker = str(time_ns())
    max_user_ids = tuple(-int(marker) - index for index in range(3))
    broadcast_ids: list[int] = []
    try:
        async with session_factory() as session:
            users = UserRepository(session)
            created = [
                await users.get_or_create(user_id, f"Broadcast check {index}")
                for index, user_id in enumerate(max_user_ids)
            ]

            service = AdminBroadcastService(
                session,
                send_interval_seconds=0,
                retry_backoff_seconds=0,
            )
            partial_id = await service.create(
                max_user_ids[0],
                f"broadcast-{marker}-partial",
            )
            broadcast_ids.append(partial_id)
            total = await service.deliveries.count_total(partial_id)
            assert await service.deliveries.create_for_all_users(partial_id) == total

            partial_sender = FakeSender({max_user_ids[1]})
            partial = await service.process(
                partial_id,
                cast(BroadcastSender, partial_sender),
            )
            assert partial.failed == 1
            assert partial.successful == partial.total - 1
            calls_after_first_run = dict(partial_sender.calls)
            repeated = await service.process(
                partial_id,
                cast(BroadcastSender, partial_sender),
            )
            assert repeated == partial
            assert partial_sender.calls == calls_after_first_run

            recovery_id = await service.create(
                max_user_ids[0],
                f"broadcast-{marker}-recovery",
            )
            broadcast_ids.append(recovery_id)
            first_delivery = (
                await session.execute(
                    select(BroadcastDelivery, User.max_user_id)
                    .join(User, User.id == BroadcastDelivery.user_id)
                    .where(BroadcastDelivery.broadcast_id == recovery_id)
                    .order_by(BroadcastDelivery.id)
                    .limit(1)
                )
            ).one()
            already_sent_max_id = first_delivery[1]
            await BroadcastDeliveryRepository(session).mark_sent(
                first_delivery[0],
                created[0].created_at,
            )
            await session.commit()

        recovery_sender = FakeSender()
        registry = BackgroundTaskRegistry()
        recovery = BroadcastRecoveryManager(
            session_factory,
            registry,
            cast(MaxBot, recovery_sender),
        )
        assert await recovery.resume_unfinished() >= 1
        await recovery.resume_unfinished()
        assert len(recovery.active_ids) == 1
        await wait_for_tasks(registry)
        assert (
            already_sent_max_id,
            f"broadcast-{marker}-recovery",
        ) not in recovery_sender.messages

        async with session_factory() as session:
            service = AdminBroadcastService(
                session,
                send_interval_seconds=0,
                retry_backoff_seconds=0,
                max_attempts=3,
            )
            retry_id = await service.create(
                max_user_ids[0],
                f"broadcast-{marker}-retry",
            )
            broadcast_ids.append(retry_id)
            retry_sender = FakeSender(rate_limited_id=max_user_ids[2])
            retry_result = await service.process(
                retry_id,
                cast(BroadcastSender, retry_sender),
            )
            assert retry_result.failed == 0
            assert retry_sender.calls[max_user_ids[2]] == 3

            cancel_id = await service.create(
                max_user_ids[0],
                f"broadcast-{marker}-cancel",
            )
            broadcast_ids.append(cancel_id)

        blocking = BlockingSender()

        async def process_cancelled() -> None:
            async with session_factory() as session:
                await AdminBroadcastService(
                    session,
                    concurrency=1,
                    batch_size=1,
                    send_interval_seconds=0,
                ).process(cancel_id, cast(BroadcastSender, blocking))

        processing = asyncio.create_task(process_cancelled())
        await asyncio.wait_for(blocking.started.wait(), timeout=2)
        async with session_factory() as session:
            cancelled = await AdminBroadcastService(session).cancel(cancel_id)
            assert cancelled is not None
            assert cancelled.status.value == "cancelled"
        blocking.release.set()
        await processing
        assert sum(blocking.calls.values()) == 1

        ui_bot = FakeSender()
        await broadcast_status(
            cast(MaxBot, ui_bot),
            {
                "callback": {
                    "callback_id": "broadcast-status-check",
                    "payload": f"admin:broadcast:{retry_id}",
                    "user": {"user_id": max_user_ids[0]},
                }
            },
        )
        assert len(ui_bot.callback_messages) == 1
        assert f"Рассылка #{retry_id}" in ui_bot.callback_messages[0]
        assert "Статус: completed" in ui_bot.callback_messages[0]

        async with session_factory() as session:
            recovered = await BroadcastRepository(session).get_by_id(recovery_id)
            assert recovered is not None
            assert recovered.status.value == "completed"
    finally:
        await cleanup(max_user_ids, marker)
        await engine.dispose()

    print("Persistent broadcasts check passed")


if __name__ == "__main__":
    asyncio.run(main())
