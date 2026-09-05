from datetime import datetime

from bot.keyboards.user.subscriptions import (
    checkout_keyboard,
    profile_keyboard,
    tariff_details_keyboard,
    tariffs_keyboard,
)
from bot.router import Router
from database.session import session_factory
from max_client import MaxBot
from services.subscriptions import (
    AccessType,
    TrialAlreadyUsedError,
    TrialUnavailableError,
)
from services.user_subscriptions import UserProfile, UserSubscriptionService
from services.payments import PaymentProviderUnavailableError, PaymentServiceError


router = Router()


def _callback_context(update: dict) -> tuple[dict, str, int] | None:
    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    user = callback.get("user", callback.get("sender", {}))
    if not isinstance(callback, dict) or not isinstance(user, dict):
        return None
    if not isinstance(callback_id, str) or not callback_id:
        return None
    try:
        user_id = int(user.get("user_id", 0))
    except (TypeError, ValueError):
        return None
    return callback, callback_id, user_id


def _date(value: datetime | None) -> str:
    return "—" if value is None else value.strftime("%d.%m.%Y")


def _profile_text(profile: UserProfile) -> str:
    lines = [f"Профиль: {profile.first_name or 'Без имени'}", ""]
    if profile.access_type is AccessType.PAID:
        lines.extend(
            [
                "Доступ: подписка активна",
                f"Тариф: {profile.tariff_name or 'Подписка'}",
                f"Действует до: {_date(profile.expires_at)}",
            ]
        )
    elif profile.access_type is AccessType.TRIAL:
        lines.extend(
            [
                "Доступ: бесплатный пробный период",
                f"Действует до: {_date(profile.expires_at)}",
            ]
        )
    else:
        lines.append("Доступ: базовый бесплатный")
        if not profile.can_activate_trial:
            lines.append("Пробный период уже был использован.")
    return "\n".join(lines)


async def _show_profile(bot: MaxBot, callback_id: str, user_id: int) -> None:
    async with session_factory() as session:
        profile = await UserSubscriptionService(session).get_profile(user_id)
    if profile is None:
        await bot.answer_callback(
            callback_id=callback_id,
            message={"text": "Сначала запустите бота командой /start."},
        )
        return
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": _profile_text(profile),
            "attachments": [profile_keyboard(profile.can_activate_trial)],
        },
    )


@router.callback("user:profile")
async def handle_profile(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    _, callback_id, user_id = context
    await _show_profile(bot, callback_id, user_id)


@router.callback("user:trial:activate")
async def handle_trial_activation(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    _, callback_id, user_id = context
    try:
        async with session_factory() as session:
            trial = await UserSubscriptionService(session).activate_trial(user_id)
    except TrialAlreadyUsedError:
        text = "Пробный период уже был использован."
    except TrialUnavailableError:
        text = "У вас уже действует оплаченная подписка."
    except ValueError:
        text = "Сначала запустите бота командой /start."
    else:
        text = (
            "Пробный период активирован.\n"
            f"Бесплатный доступ действует до {_date(trial.expires_at)}."
        )
    async with session_factory() as session:
        profile = await UserSubscriptionService(session).get_profile(user_id)
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": text,
            "attachments": [
                profile_keyboard(
                    profile.can_activate_trial if profile is not None else False
                )
            ],
        },
    )


@router.callback("user:tariffs")
async def handle_tariffs(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    _, callback_id, _ = context
    async with session_factory() as session:
        tariffs = await UserSubscriptionService(session).list_tariffs()
    lines = ["Тарифы", ""]
    if tariffs:
        lines.extend(
            f"{tariff.name} — {tariff.price:.2f} ₽ на {tariff.duration_days} дней"
            for tariff in tariffs
        )
    else:
        lines.append("Сейчас нет доступных тарифов.")
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "\n".join(lines),
            "attachments": [
                tariffs_keyboard(
                    tuple((tariff.id, tariff.name) for tariff in tariffs)
                )
            ],
        },
    )


@router.callback_prefix("user:tariff:")
async def handle_tariff_details(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    callback, callback_id, user_id = context
    payload = callback.get("payload")
    if not isinstance(payload, str):
        return
    parts = payload.split(":")
    try:
        tariff_id = int(parts[2])
    except (IndexError, ValueError):
        return
    if len(parts) == 4 and parts[3] == "buy":
        try:
            async with session_factory() as session:
                checkout = await UserSubscriptionService(
                    session
                ).create_checkout(user_id, tariff_id)
        except PaymentProviderUnavailableError:
            await bot.answer_callback(
                callback_id=callback_id,
                message={
                    "text": "Онлайн-оплата пока недоступна.",
                    "attachments": [tariff_details_keyboard(tariff_id)],
                },
            )
            return
        except (PaymentServiceError, ValueError):
            await bot.answer_callback(
                callback_id=callback_id,
                message={"text": "Этот тариф сейчас недоступен."},
            )
            return
        label = "Тестовая оплата" if checkout.is_test else "Оплата"
        await bot.answer_callback(
            callback_id=callback_id,
            message={
                "text": (
                    f"{label} создана.\n\n"
                    "Это тестовая ссылка: она не списывает реальные деньги."
                    if checkout.is_test
                    else "Оплата создана. Перейдите по ссылке ниже."
                ),
                "attachments": [
                    checkout_keyboard(
                        checkout.payment_id,
                        checkout.checkout_url,
                    )
                ],
            },
        )
        return
    if len(parts) != 3:
        return
    async with session_factory() as session:
        tariff = await UserSubscriptionService(session).get_tariff(tariff_id)
    if tariff is None:
        await bot.answer_callback(
            callback_id=callback_id,
            message={
                "text": "Этот тариф сейчас недоступен.",
                "attachments": [tariffs_keyboard(())],
            },
        )
        return
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "\n".join(
                [
                    tariff.name,
                    "",
                    f"Стоимость: {tariff.price:.2f} ₽",
                    f"Срок доступа: {tariff.duration_days} дней",
                    "Доступ ко всем возможностям помощника на срок тарифа.",
                ]
            ),
            "attachments": [tariff_details_keyboard(tariff.id)],
        },
    )
