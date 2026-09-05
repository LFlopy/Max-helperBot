import asyncio
from datetime import timedelta
from decimal import Decimal
from time import perf_counter, time_ns
from typing import cast

from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import delete

from bot.dispatcher import Dispatcher
from bot.handlers.admin.broadcasts import router as broadcasts_router
from bot.handlers.admin.users import router as users_router
from bot.states.fsm import fsm
from config import ADMIN_IDS, WEBHOOK_SECRET
from database.models import ProcessedUpdate, Subscription, Tariff, User
from database.repositories import (
    SubscriptionRepository,
    TariffRepository,
    UserRepository,
)
from database.session import engine, session_factory
from main import BACKGROUND_TASKS_KEY, create_app
from max_client import MaxBot
from scripts.check_webhook_processing import wait_for_background_tasks


class FakeBot:
    def __init__(self) -> None:
        self.callback_messages: list[str] = []
        self.sent_messages: list[tuple[int, str]] = []
        self.broadcast_started = asyncio.Event()
        self.broadcast_release = asyncio.Event()

    async def answer_callback(
        self,
        callback_id: str,
        message: dict,
    ) -> dict[str, object]:
        text = message.get("text")
        if isinstance(text, str):
            self.callback_messages.append(text)
        return {}

    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> dict[str, object]:
        if text == "Callback broadcast check":
            self.broadcast_started.set()
            await self.broadcast_release.wait()
        self.sent_messages.append((user_id, text))
        return {}


def callback_update(
    callback_id: str,
    payload: str,
    admin_user_id: int,
) -> dict[str, object]:
    return {
        "update_type": "message_callback",
        "callback": {
            "callback_id": callback_id,
            "payload": payload,
            "user": {"user_id": admin_user_id},
        },
    }


async def post_twice(
    client: TestClient,
    update: dict[str, object],
) -> None:
    headers = {"X-Max-Bot-Api-Secret": WEBHOOK_SECRET}
    first = await client.post(
        "/max-helper/webhook",
        json=update,
        headers=headers,
    )
    second = await client.post(
        "/max-helper/webhook",
        json=update,
        headers=headers,
    )
    assert first.status == 200
    assert second.status == 200


async def cleanup(
    user_id: int,
    tariff_id: int,
    update_keys: tuple[str, ...],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(Subscription).where(Subscription.user_id == user_id)
        )
        await session.execute(delete(User).where(User.id == user_id))
        await session.execute(delete(Tariff).where(Tariff.id == tariff_id))
        await session.execute(
            delete(ProcessedUpdate).where(
                ProcessedUpdate.update_key.in_(update_keys)
            )
        )
        await session.commit()


async def main() -> None:
    marker = time_ns()
    max_user_id = -marker
    tariff_code = f"callback-{marker}"
    admin_user_id = next(iter(ADMIN_IDS))
    grant_callback_id = f"callback-grant-{marker}"
    cancel_callback_id = f"callback-cancel-{marker}"
    broadcast_callback_id = f"callback-broadcast-{marker}"
    update_keys = tuple(
        f"message_callback:{callback_id}"
        for callback_id in (
            grant_callback_id,
            cancel_callback_id,
            broadcast_callback_id,
        )
    )

    async with session_factory() as session:
        user = await UserRepository(session).get_or_create(max_user_id)
        tariff = await TariffRepository(session).upsert(
            code=tariff_code,
            name="Callback idempotency check",
            price=Decimal("1.00"),
            duration_days=1,
            history_limit=1,
        )
        user_id = user.id
        tariff_id = tariff.id

    fake_bot = FakeBot()
    dispatcher = Dispatcher()
    dispatcher.include_routers(users_router, broadcasts_router)
    app = create_app(cast(MaxBot, fake_bot), dispatcher)
    client = TestClient(TestServer(app))

    grant_payload = (
        f"admin:user:{user_id}:grant:tariff:{tariff_id}:confirm:page:1"
    )
    cancel_payload = f"admin:user:{user_id}:cancel:confirm:page:1"

    try:
        await client.start_server()
        registry = app[BACKGROUND_TASKS_KEY]

        await post_twice(
            client,
            callback_update(
                grant_callback_id,
                grant_payload,
                admin_user_id,
            ),
        )
        await wait_for_background_tasks(registry)

        async with session_factory() as session:
            subscription = await SubscriptionRepository(
                session
            ).get_active_by_user(user_id)
            assert subscription is not None
            assert subscription.expires_at - subscription.starts_at == timedelta(
                days=1
            )

        await post_twice(
            client,
            callback_update(
                cancel_callback_id,
                cancel_payload,
                admin_user_id,
            ),
        )
        await wait_for_background_tasks(registry)
        async with session_factory() as session:
            assert (
                await SubscriptionRepository(session).get_active_by_user(user_id)
                is None
            )

        await fsm.set_state(admin_user_id, "admin:broadcast:compose")
        await fsm.set_data(
            admin_user_id,
            {"broadcast_text": "Callback broadcast check"},
        )
        broadcast_update = callback_update(
            broadcast_callback_id,
            "admin:broadcasts:confirm",
            admin_user_id,
        )
        started_at = perf_counter()
        await post_twice(client, broadcast_update)
        elapsed = perf_counter() - started_at
        assert elapsed < 2.0
        await asyncio.wait_for(fake_bot.broadcast_started.wait(), timeout=2.0)
        assert fake_bot.callback_messages.count("Рассылка запущена.") == 1

        fake_bot.broadcast_release.set()
        await wait_for_background_tasks(registry)
        assert sum(
            text.startswith("Рассылка завершена.")
            for _, text in fake_bot.sent_messages
        ) == 1
    finally:
        fake_bot.broadcast_release.set()
        await client.close()
        await fsm.clear(admin_user_id)
        await cleanup(user_id, tariff_id, update_keys)
        await engine.dispose()

    print("Callback idempotency check passed")


if __name__ == "__main__":
    asyncio.run(main())
