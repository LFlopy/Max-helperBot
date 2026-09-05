import asyncio
from collections.abc import Sequence
from time import perf_counter, time_ns
from typing import cast

from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import delete

from bot.dispatcher import Dispatcher
from bot.router import Router
from config import WEBHOOK_SECRET
from database.models import Message, ProcessedUpdate, User
from database.repositories import MessageRepository, UserRepository
from database.session import engine, session_factory
from main import BACKGROUND_TASKS_KEY, create_app
from max_client import MaxBot
from services import ConsultationService
from services.ai import AIMessage
from services.update_processing import BackgroundTaskRegistry


class SlowAIClient:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        system_prompt: str,
        messages: Sequence[AIMessage],
    ) -> str:
        self.calls += 1
        await asyncio.sleep(3.1)
        return "Webhook integration response"


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> dict[str, object]:
        self.messages.append((user_id, text))
        return {}


async def wait_for_background_tasks(
    registry: BackgroundTaskRegistry,
    timeout: float = 10.0,
) -> None:
    async def wait_until_empty() -> None:
        while registry.tasks:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(wait_until_empty(), timeout=timeout)


async def cleanup(max_user_id: int, update_keys: tuple[str, ...]) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).get_by_max_user_id(max_user_id)
        if user is not None:
            await session.execute(delete(Message).where(Message.user_id == user.id))
            await session.delete(user)
        await session.execute(
            delete(ProcessedUpdate).where(
                ProcessedUpdate.update_key.in_(update_keys)
            )
        )
        await session.commit()


async def check_registry_shutdown() -> None:
    started = asyncio.Event()
    canceled = asyncio.Event()

    async def active_task() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            canceled.set()

    registry = BackgroundTaskRegistry(shutdown_timeout=0.01)
    registry.schedule(active_task())
    await started.wait()
    await registry.close()
    assert canceled.is_set()
    assert not registry.tasks


async def main() -> None:
    marker = time_ns()
    max_user_id = -marker
    message_mid = f"mid.{marker}"
    failing_mid = f"mid.{marker}-failure"
    update_keys = (
        f"message_created:{message_mid}",
        f"message_created:{failing_mid}",
    )
    ai_client = SlowAIClient()
    fake_bot = FakeBot()
    router = Router()

    @router.message("/webhook-check")
    async def consultation_handler(bot: MaxBot, update: dict) -> None:
        message = update["message"]
        sender = message["sender"]
        body = message["body"]
        async with session_factory() as session:
            response = await ConsultationService(
                session,
                ai_client=ai_client,
            ).process_message(
                max_user_id=int(sender["user_id"]),
                content=str(body["text"]),
                topic="consultation:another",
            )
        await bot.send_message(user_id=max_user_id, text=response)

    @router.message("/raise-check")
    async def failing_handler(_bot: MaxBot, _update: dict) -> None:
        raise RuntimeError("Expected webhook integration failure")

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    app = create_app(cast(MaxBot, fake_bot), dispatcher)
    client = TestClient(TestServer(app))
    headers = {"X-Max-Bot-Api-Secret": WEBHOOK_SECRET}

    message_update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": max_user_id},
            "body": {"mid": message_mid, "text": "/webhook-check"},
        },
    }

    try:
        await client.start_server()

        invalid_secret = await client.post(
            "/max-helper/webhook",
            json=message_update,
            headers={"X-Max-Bot-Api-Secret": "invalid"},
        )
        assert invalid_secret.status == 403

        malformed = await client.post(
            "/max-helper/webhook",
            data="{invalid",
            headers=headers,
        )
        assert malformed.status == 400

        started_at = perf_counter()
        accepted = await client.post(
            "/max-helper/webhook",
            json=message_update,
            headers=headers,
        )
        elapsed = perf_counter() - started_at
        assert accepted.status == 200
        assert elapsed < 2.0
        assert not fake_bot.messages

        duplicate = await client.post(
            "/max-helper/webhook",
            json=message_update,
            headers=headers,
        )
        assert duplicate.status == 200

        registry = app[BACKGROUND_TASKS_KEY]
        await wait_for_background_tasks(registry)
        assert ai_client.calls == 1
        assert fake_bot.messages == [
            (max_user_id, "Webhook integration response")
        ]

        async with session_factory() as session:
            user = await UserRepository(session).get_by_max_user_id(max_user_id)
            assert user is not None
            history = await MessageRepository(session).get_recent_by_user(user.id)
            assert [message.role for message in history] == ["user", "assistant"]

        failure_update = {
            "update_type": "message_created",
            "message": {
                "sender": {"user_id": max_user_id},
                "body": {"mid": failing_mid, "text": "/raise-check"},
            },
        }
        failed_handler = await client.post(
            "/max-helper/webhook",
            json=failure_update,
            headers=headers,
        )
        assert failed_handler.status == 200
        await wait_for_background_tasks(registry)
    finally:
        await client.close()
        await cleanup(max_user_id, update_keys)
        await check_registry_shutdown()
        await engine.dispose()

    print("Webhook processing check passed")


if __name__ == "__main__":
    asyncio.run(main())
