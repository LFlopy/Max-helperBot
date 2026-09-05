import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from time import time_ns
from typing import cast

from sqlalchemy import delete

from bot.dispatcher import Dispatcher
from bot.handlers.user.main_menu import router as main_menu_router
from bot.handlers.user.subscriptions import router as subscriptions_router
from config import ADMIN_IDS
from database.models import Payment, PaymentStatus, Subscription, Tariff, User
from database.repositories import (
    PaymentRepository,
    TariffRepository,
    UserRepository,
)
from database.session import engine, session_factory
from max_client import MaxBot
from services.payments import (
    PaymentConfirmation,
    PaymentService,
    get_payment_provider,
)
from services.subscriptions import SubscriptionService


class FakeBot:
    def __init__(self) -> None:
        self.answers: list[dict] = []

    async def answer_callback(self, callback_id: str, message: dict) -> dict:
        self.answers.append(message)
        return {}


def callback(payload: str, callback_id: str, user_id: int) -> dict:
    return {
        "update_type": "message_callback",
        "callback": {
            "payload": payload,
            "callback_id": callback_id,
            "user": {"user_id": user_id},
        },
    }


def callback_payloads(message: dict) -> set[str]:
    result: set[str] = set()
    for attachment in message.get("attachments", []):
        for row in attachment.get("payload", {}).get("buttons", []):
            for button in row:
                payload = button.get("payload")
                if isinstance(payload, str):
                    result.add(payload)
    return result


async def dispatch(
    dispatcher: Dispatcher,
    bot: FakeBot,
    payload: str,
    user_id: int,
    marker: str,
) -> dict:
    await dispatcher.dispatch(
        cast(MaxBot, bot),
        callback(payload, f"{marker}:{len(bot.answers)}", user_id),
    )
    return bot.answers[-1]


async def cleanup(
    max_user_ids: tuple[int, ...],
    tariff_codes: tuple[str, ...],
) -> None:
    async with session_factory() as session:
        users = await session.execute(
            User.__table__.select()
            .with_only_columns(User.id)
            .where(User.max_user_id.in_(max_user_ids))
        )
        user_ids = list(users.scalars())
        tariffs = await session.execute(
            Tariff.__table__.select()
            .with_only_columns(Tariff.id)
            .where(Tariff.code.in_(tariff_codes))
        )
        tariff_ids = list(tariffs.scalars())
        if user_ids:
            await session.execute(delete(Payment).where(Payment.user_id.in_(user_ids)))
            await session.execute(
                delete(Subscription).where(Subscription.user_id.in_(user_ids))
            )
            await session.execute(delete(User).where(User.id.in_(user_ids)))
        if tariff_ids:
            await session.execute(delete(Tariff).where(Tariff.id.in_(tariff_ids)))
        await session.commit()


async def main() -> None:
    if not ADMIN_IDS:
        raise RuntimeError("ADMIN_IDS must contain a test admin")
    marker = str(time_ns())
    admin_max_id = next(iter(ADMIN_IDS))
    regular_ids = tuple(-int(marker) - index for index in range(4))
    max_user_ids = regular_ids
    tariff_codes = (f"ui-active-{marker}", f"ui-inactive-{marker}")
    dispatcher = Dispatcher()
    dispatcher.include_routers(main_menu_router, subscriptions_router)
    bot = FakeBot()

    try:
        async with session_factory() as session:
            users = UserRepository(session)
            created = {}
            for index, max_user_id in enumerate(regular_ids):
                created[max_user_id] = await users.get_or_create(
                    max_user_id,
                    f"UI user {index}",
                )
            tariffs = TariffRepository(session)
            active = await tariffs.upsert(
                code=tariff_codes[0],
                name="Полный доступ",
                price=Decimal("990.00"),
                duration_days=30,
                history_limit=50,
            )
            inactive = await tariffs.upsert(
                code=tariff_codes[1],
                name="Скрытый тариф",
                price=Decimal("1.00"),
                duration_days=1,
                history_limit=1,
                is_active=False,
            )
            await SubscriptionService(session, free_history_limit=10).grant_paid_subscription(
                created[regular_ids[1]].id,
                active.id,
            )

        free_profile = await dispatch(
            dispatcher, bot, "user:profile", regular_ids[0], marker
        )
        assert "базовый бесплатный" in free_profile["text"]
        assert "user:trial:activate" in callback_payloads(free_profile)
        assert "user:tariffs" in callback_payloads(free_profile)
        assert "user:main" in callback_payloads(free_profile)

        activated = await dispatch(
            dispatcher, bot, "user:trial:activate", regular_ids[0], marker
        )
        assert "Пробный период активирован" in activated["text"]
        trial_profile = await dispatch(
            dispatcher, bot, "user:profile", regular_ids[0], marker
        )
        assert "бесплатный пробный период" in trial_profile["text"]
        assert "Действует до:" in trial_profile["text"]
        assert "user:trial:activate" not in callback_payloads(trial_profile)

        repeated_trial = await dispatch(
            dispatcher, bot, "user:trial:activate", regular_ids[0], marker
        )
        assert "уже был использован" in repeated_trial["text"]
        paid_trial = await dispatch(
            dispatcher, bot, "user:trial:activate", regular_ids[1], marker
        )
        assert "оплаченная подписка" in paid_trial["text"]

        paid_profile = await dispatch(
            dispatcher, bot, "user:profile", regular_ids[1], marker
        )
        assert "подписка активна" in paid_profile["text"]
        assert "Тариф: Полный доступ" in paid_profile["text"]

        tariffs_list = await dispatch(
            dispatcher, bot, "user:tariffs", regular_ids[2], marker
        )
        assert "Полный доступ" in tariffs_list["text"]
        assert "Скрытый тариф" not in tariffs_list["text"]
        assert f"user:tariff:{active.id}" in callback_payloads(tariffs_list)
        assert {"user:profile", "user:main"} <= callback_payloads(tariffs_list)

        tariff_details = await dispatch(
            dispatcher,
            bot,
            f"user:tariff:{active.id}",
            regular_ids[2],
            marker,
        )
        assert "Стоимость: 990.00 ₽" in tariff_details["text"]
        assert f"user:tariff:{active.id}:buy" in callback_payloads(
            tariff_details
        )
        assert {"user:tariffs", "user:main"} <= callback_payloads(
            tariff_details
        )
        inactive_details = await dispatch(
            dispatcher,
            bot,
            f"user:tariff:{inactive.id}",
            regular_ids[2],
            marker,
        )
        assert inactive_details["text"] == "Этот тариф сейчас недоступен."

        checkout = await dispatch(
            dispatcher,
            bot,
            f"user:tariff:{active.id}:buy",
            regular_ids[2],
            marker,
        )
        assert "Тестовая оплата" in checkout["text"]
        assert "не списывает реальные деньги" in checkout["text"]
        status_payload = next(
            payload
            for payload in callback_payloads(checkout)
            if payload.startswith("payment:status:")
        )
        payment_id = int(status_payload.rsplit(":", 1)[1])

        foreign_status = await dispatch(
            dispatcher, bot, status_payload, regular_ids[3], marker
        )
        assert foreign_status["text"] == "Платёж не найден."
        pending_status = await dispatch(
            dispatcher, bot, status_payload, regular_ids[2], marker
        )
        assert "Оплата ещё ожидается" in pending_status["text"]

        provider = get_payment_provider()
        async with session_factory() as session:
            payment = await PaymentRepository(session).get_by_id(payment_id)
            assert payment is not None
            await PaymentService(session, provider).process_successful_confirmation(
                PaymentConfirmation(
                    provider_payment_id=payment.provider_payment_id,
                    status=PaymentStatus.PAID,
                    paid_at=datetime.now(timezone.utc),
                )
            )

        paid_status = await dispatch(
            dispatcher, bot, status_payload, regular_ids[2], marker
        )
        assert "Оплата получена" in paid_status["text"]
        assert "Подписка действует до:" in paid_status["text"]
        assert "user:profile" in callback_payloads(paid_status)
        checkout_profile = await dispatch(
            dispatcher, bot, "user:profile", regular_ids[2], marker
        )
        assert "подписка активна" in checkout_profile["text"]

        regular_main = await dispatch(
            dispatcher, bot, "user:main", regular_ids[3], marker
        )
        assert "admin:main" not in callback_payloads(regular_main)
        assert {"user:profile", "user:tariffs"} <= callback_payloads(
            regular_main
        )
        admin_main = await dispatch(
            dispatcher, bot, "user:main", admin_max_id, marker
        )
        assert "admin:main" in callback_payloads(admin_main)
    finally:
        await cleanup(max_user_ids, tariff_codes)
        await engine.dispose()

    print("User subscription UI check passed")


if __name__ == "__main__":
    asyncio.run(main())
