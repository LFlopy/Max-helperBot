import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import time_ns
from typing import cast

from sqlalchemy import delete, select

from bot.dispatcher import Dispatcher
from bot.router import Router
from config import ADMIN_IDS
from database.models import (
    Broadcast,
    Message,
    Payment,
    PaymentStatus,
    Subscription,
    Tariff,
    User,
)
from database.repositories import (
    MessageRepository,
    PaymentRepository,
    TariffRepository,
    UserRepository,
)
from database.session import engine, session_factory
from max_client import MaxBot
from services.admin import (
    AdminBroadcastService,
    AdminStatisticsService,
    AdminSubscriptionService,
    AdminUserService,
    BroadcastSender,
)


class FakeSender:
    def __init__(self, failed_user_ids: set[int] | None = None) -> None:
        self.failed_user_ids = failed_user_ids or set()
        self.sent: list[tuple[int, str]] = []
        self.active = 0
        self.max_active = 0

    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> object:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0)
            if user_id in self.failed_user_ids:
                raise RuntimeError("Synthetic send failure")
            self.sent.append((user_id, text))
            return {}
        finally:
            self.active -= 1


class FakeBot:
    def __init__(self) -> None:
        self.callback_answers = 0

    async def answer_callback(self, callback_id: str, message: dict) -> dict:
        self.callback_answers += 1
        return {}


async def cleanup(
    max_user_ids: Sequence[int],
    tariff_codes: Sequence[str],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(Broadcast).where(
                Broadcast.created_by_max_user_id.in_(max_user_ids)
            )
        )
        user_ids = list(
            (
                await session.execute(
                    select(User.id).where(User.max_user_id.in_(max_user_ids))
                )
            ).scalars()
        )
        tariff_ids = list(
            (
                await session.execute(
                    select(Tariff.id).where(Tariff.code.in_(tariff_codes))
                )
            ).scalars()
        )
        if user_ids:
            await session.execute(delete(Message).where(Message.user_id.in_(user_ids)))
            await session.execute(delete(Payment).where(Payment.user_id.in_(user_ids)))
            await session.execute(
                delete(Subscription).where(Subscription.user_id.in_(user_ids))
            )
            await session.execute(delete(User).where(User.id.in_(user_ids)))
        if tariff_ids:
            await session.execute(delete(Tariff).where(Tariff.id.in_(tariff_ids)))
        await session.commit()


async def check_security() -> None:
    unauthorized_user_id = -1
    while unauthorized_user_id in ADMIN_IDS:
        unauthorized_user_id -= 1

    router = Router()

    @router.callback("admin:security-check")
    async def protected_handler(_bot: MaxBot, _update: dict) -> None:
        raise AssertionError("Unauthorized admin handler was called")

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    fake_bot = FakeBot()
    await dispatcher.dispatch(
        cast(MaxBot, fake_bot),
        {
            "update_type": "message_callback",
            "callback": {
                "payload": "admin:security-check",
                "callback_id": "security-check",
                "user": {"user_id": unauthorized_user_id},
            },
        },
    )
    assert fake_bot.callback_answers == 0


async def main() -> None:
    marker = time_ns()
    max_user_ids = tuple(-marker - offset for offset in range(7))
    tariff_codes = (f"admin-{marker}", f"admin-inactive-{marker}")
    created_user_ids: list[int] = []

    try:
        async with session_factory() as session:
            baseline = await AdminStatisticsService(session).get_statistics()
            baseline_overview = await AdminSubscriptionService(
                session
            ).get_overview()

            tariffs = TariffRepository(session)
            tariff = await tariffs.upsert(
                code=tariff_codes[0],
                name="Admin integration tariff",
                price=Decimal("100.00"),
                duration_days=30,
                history_limit=40,
            )
            tariff_id = tariff.id
            tariff_code = tariff.code
            await tariffs.upsert(
                code=tariff_codes[1],
                name="Inactive admin tariff",
                price=Decimal("1.00"),
                duration_days=1,
                history_limit=1,
                is_active=False,
            )

            users = UserRepository(session)
            for index, max_user_id in enumerate(max_user_ids):
                user = await users.get_or_create(
                    max_user_id=max_user_id,
                    first_name=f"Admin check {index}",
                )
                created_user_ids.append(user.id)

            first_repository_page = await users.list_page(offset=0, limit=2)
            second_repository_page = await users.list_page(offset=2, limit=2)
            assert len(first_repository_page) == 2
            assert len(second_repository_page) == 2
            assert {item.id for item in first_repository_page}.isdisjoint(
                item.id for item in second_repository_page
            )

            admin_users = AdminUserService(session)
            user_page = await admin_users.list_users(page=1, page_size=3)
            assert user_page.total == baseline.users_count + len(max_user_ids)
            assert len(user_page.items) == 3
            assert user_page.page_count >= 3

            free_card = await admin_users.get_user_card(created_user_ids[0])
            assert free_card is not None
            assert free_card.max_user_id == max_user_ids[0]

            await admin_users.grant_subscription(created_user_ids[0], tariff_id)
            first_grant = await admin_users.get_user_card(created_user_ids[0])
            assert first_grant is not None
            assert first_grant.access_expires_at is not None
            first_expiry = first_grant.access_expires_at

            await admin_users.grant_subscription(created_user_ids[0], tariff_id)
            renewed = await admin_users.get_user_card(created_user_ids[0])
            assert renewed is not None
            assert renewed.access_expires_at == first_expiry + timedelta(days=30)

            assert await admin_users.cancel_subscription(created_user_ids[0])
            canceled = await admin_users.get_user_card(created_user_ids[0])
            assert canceled is not None
            assert canceled.access_type.value == "free"

            await admin_users.grant_subscription(created_user_ids[1], tariff_id)
            trial_service = admin_users.subscriptions
            await trial_service.activate_trial(created_user_ids[2])

            tariffs_view = await AdminSubscriptionService(
                session
            ).list_active_tariffs()
            assert any(item.code == tariff_code for item in tariffs_view)
            assert all(item.code != tariff_codes[1] for item in tariffs_view)

            active_page = await AdminSubscriptionService(
                session
            ).list_active_subscriptions(page=1, page_size=baseline.users_count + 20)
            assert any(
                item.user_id == created_user_ids[1] for item in active_page.items
            )

            payment_repository = PaymentRepository(session)
            payment = await payment_repository.create(
                user_id=created_user_ids[1],
                tariff_id=tariff_id,
                provider="admin-check",
                provider_payment_id=f"admin-check-{marker}",
                amount=Decimal("100.00"),
                currency="RUB",
            )
            await payment_repository.mark_paid(
                payment,
                paid_at=datetime.now(timezone.utc),
            )
            await session.commit()
            await MessageRepository(session).create(
                user_id=created_user_ids[1],
                role="user",
                content="Admin statistics integration check",
            )

            overview = await AdminSubscriptionService(session).get_overview()
            assert overview.paid_count == baseline_overview.paid_count + 1
            assert overview.trial_count == baseline_overview.trial_count + 1
            assert overview.free_count == baseline_overview.free_count + 5

            statistics = await AdminStatisticsService(session).get_statistics()
            assert statistics.users_count == baseline.users_count + 7
            assert statistics.new_users_24h == baseline.new_users_24h + 7
            assert statistics.new_users_7d == baseline.new_users_7d + 7
            assert statistics.active_paid_count == baseline.active_paid_count + 1
            assert statistics.active_trial_count == baseline.active_trial_count + 1
            assert statistics.paid_payments_count == baseline.paid_payments_count + 1
            assert statistics.revenue == baseline.revenue + Decimal("100.00")
            assert statistics.messages_count == baseline.messages_count + 1
            assert statistics.messages_24h == baseline.messages_24h + 1

            broadcast = AdminBroadcastService(session, concurrency=3)
            fake_sender = FakeSender({max_user_ids[1], max_user_ids[4]})
            broadcast_id = await broadcast.create(
                max_user_ids[0],
                "Admin broadcast check",
            )
            result = await broadcast.process(
                broadcast_id,
                cast(BroadcastSender, fake_sender),
            )
            assert result.successful == result.total - 2
            assert result.failed == 2
            assert fake_sender.max_active <= 3

        await check_security()
    finally:
        await cleanup(max_user_ids, tariff_codes)
        await engine.dispose()

    print("Admin panel check passed")


if __name__ == "__main__":
    asyncio.run(main())
