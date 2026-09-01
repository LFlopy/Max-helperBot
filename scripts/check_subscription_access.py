import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import time_ns

from database.repositories import (
    MessageRepository,
    SubscriptionRepository,
    TariffRepository,
    UserRepository,
)
from database.session import engine, session_factory
from services import ConsultationService, SubscriptionService
from services.ai import AIMessage


class FakeAIClient:
    def __init__(self) -> None:
        self.calls: list[list[AIMessage]] = []

    async def generate(
        self,
        system_prompt: str,
        messages: Sequence[AIMessage],
    ) -> str:
        self.calls.append(list(messages))
        return "Тестовый ответ"


async def cleanup(max_user_ids: tuple[int, ...], tariff_code: str) -> None:
    async with session_factory() as session:
        users = UserRepository(session)
        messages = MessageRepository(session)
        subscriptions = SubscriptionRepository(session)

        for max_user_id in max_user_ids:
            user = await users.get_by_max_user_id(max_user_id)
            if user is None:
                continue

            subscription = await subscriptions.get_latest_by_user(user.id)
            if subscription is not None:
                await session.delete(subscription)
            for message in await messages.get_recent_by_user(user.id, limit=100):
                await session.delete(message)
            await session.delete(user)

        tariff = await TariffRepository(session).get_by_code(tariff_code)
        if tariff is not None:
            await session.delete(tariff)
        await session.commit()


async def add_history(
    repository: MessageRepository,
    user_id: int,
    prefix: str,
    count: int,
) -> None:
    for index in range(count):
        await repository.create(
            user_id=user_id,
            role="user",
            content=f"{prefix} {index}",
        )


async def main() -> None:
    marker = time_ns()
    max_user_ids = (-marker, -marker - 1, -marker - 2)
    tariff_code = f"check-{marker}"
    now = datetime.now(timezone.utc)

    try:
        async with session_factory() as session:
            users = UserRepository(session)
            messages = MessageRepository(session)
            subscriptions = SubscriptionRepository(session)
            tariff = await TariffRepository(session).upsert(
                code=tariff_code,
                name="Integration check",
                price=Decimal("100.00"),
                duration_days=30,
                history_limit=5,
            )
            free_user = await users.get_or_create(max_user_ids[0])
            paid_user = await users.get_or_create(max_user_ids[1])
            expired_user = await users.get_or_create(max_user_ids[2])

            await subscriptions.create(
                user_id=paid_user.id,
                tariff_id=tariff.id,
                starts_at=now - timedelta(days=1),
                expires_at=now + timedelta(days=1),
            )
            await subscriptions.create(
                user_id=expired_user.id,
                tariff_id=tariff.id,
                starts_at=now - timedelta(days=2),
                expires_at=now - timedelta(days=1),
            )

            access_service = SubscriptionService(
                session,
                free_history_limit=3,
            )
            free_access = await access_service.get_user_access(free_user.id)
            paid_access = await access_service.get_user_access(paid_user.id)
            expired_access = await access_service.get_user_access(
                expired_user.id
            )

            assert not free_access.has_active_subscription
            assert free_access.history_limit == 3
            assert paid_access.has_active_subscription
            assert paid_access.history_limit == 5
            assert paid_access.tariff_code == tariff_code
            assert not expired_access.has_active_subscription
            assert expired_access.history_limit == 3

            await add_history(messages, free_user.id, "free", 4)
            await add_history(messages, paid_user.id, "paid", 6)

            free_ai = FakeAIClient()
            paid_ai = FakeAIClient()
            await ConsultationService(
                session,
                ai_client=free_ai,
                free_history_limit=3,
            ).process_message(
                max_user_id=free_user.max_user_id,
                content="free current",
                topic="consultation:check",
            )
            await ConsultationService(
                session,
                ai_client=paid_ai,
                free_history_limit=3,
            ).process_message(
                max_user_id=paid_user.max_user_id,
                content="paid current",
                topic="consultation:check",
            )

            assert len(free_ai.calls[0]) == 4
            assert [message.content for message in free_ai.calls[0][1:]] == [
                "free 2",
                "free 3",
                "free current",
            ]
            assert len(paid_ai.calls[0]) == 6
            assert [message.content for message in paid_ai.calls[0][1:]] == [
                "paid 2",
                "paid 3",
                "paid 4",
                "paid 5",
                "paid current",
            ]
    finally:
        await cleanup(max_user_ids, tariff_code)
        await engine.dispose()

    print("Subscription access check passed")


if __name__ == "__main__":
    asyncio.run(main())
