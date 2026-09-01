from datetime import datetime

from bot.keyboards.admin.users import (
    cancel_confirmation_keyboard,
    grant_confirmation_keyboard,
    subscription_management_keyboard,
    tariff_selection_keyboard,
    user_card_keyboard,
    users_keyboard,
)
from bot.router import Router
from database.session import session_factory
from max_client import MaxBot
from services.admin import (
    AdminTariffUnavailableError,
    AdminUserCard,
    AdminUserPage,
    AdminUserService,
)
from services.subscriptions import AccessType


router = Router()


def _callback(update: dict) -> tuple[dict, str] | None:
    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    if not isinstance(callback_id, str) or not callback_id:
        return None
    return callback, callback_id


def _date(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def _access_name(
    access_type: AccessType,
    tariff_name: str | None,
) -> str:
    if access_type is AccessType.PAID:
        return tariff_name or "Paid"
    if access_type is AccessType.TRIAL:
        return "Trial"
    return "Free"


def _users_text(page: AdminUserPage) -> str:
    lines = ["Пользователи", ""]
    if not page.items:
        lines.append("Пользователей пока нет.")
        return "\n".join(lines)

    for index, item in enumerate(page.items, start=1):
        lines.extend(
            [
                f"{index}. {item.first_name or 'Без имени'}",
                f"MAX ID: {item.max_user_id}",
                f"Внутренний ID: {item.id}",
                f"Доступ: {_access_name(item.access_type, item.tariff_name)}",
                f"До: {_date(item.access_expires_at)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _card_text(card: AdminUserCard) -> str:
    trial_status = (
        f"использован {_date(card.trial_used_at)}"
        if card.trial_used_at is not None
        else "не использован"
    )
    return "\n".join(
        [
            "Пользователь",
            "",
            f"Имя: {card.first_name or 'Без имени'}",
            f"MAX ID: {card.max_user_id}",
            f"Внутренний ID: {card.id}",
            f"Дата регистрации: {_date(card.created_at)}",
            "",
            f"Доступ: {card.access_type.value}",
            f"Тариф: {card.tariff_name or '—'}",
            f"Доступ до: {_date(card.access_expires_at)}",
            "",
            f"Trial: {trial_status}",
        ]
    )


async def _show_users(
    bot: MaxBot,
    callback_id: str,
    page_number: int,
) -> None:
    async with session_factory() as session:
        page = await AdminUserService(session).list_users(page=page_number)
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": _users_text(page),
            "attachments": [users_keyboard(page)],
        },
    )


async def _show_user_card(
    bot: MaxBot,
    callback_id: str,
    user_id: int,
    return_page: int,
) -> None:
    async with session_factory() as session:
        card = await AdminUserService(session).get_user_card(user_id)
    if card is None:
        await bot.answer_callback(
            callback_id=callback_id,
            message={"text": "Пользователь не найден."},
        )
        return
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": _card_text(card),
            "attachments": [user_card_keyboard(card, return_page)],
        },
    )


@router.callback("admin:users")
async def handle_users(bot: MaxBot, update: dict) -> None:
    context = _callback(update)
    if context is None:
        return
    _, callback_id = context
    await _show_users(bot, callback_id, page_number=1)


@router.callback_prefix("admin:users:page:")
async def handle_users_page(bot: MaxBot, update: dict) -> None:
    context = _callback(update)
    if context is None:
        return
    callback, callback_id = context
    payload = callback.get("payload")
    if not isinstance(payload, str):
        return
    try:
        page_number = int(payload.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    await _show_users(bot, callback_id, page_number=max(1, page_number))


@router.callback_prefix("admin:user:")
async def handle_user_card(bot: MaxBot, update: dict) -> None:
    context = _callback(update)
    if context is None:
        return
    callback, callback_id = context
    payload = callback.get("payload")
    if not isinstance(payload, str):
        return
    parts = payload.split(":")
    try:
        user_id = int(parts[2])
        return_page = max(1, int(parts[-1]))
    except (IndexError, ValueError):
        return

    if len(parts) == 5 and parts[3] == "page":
        await _show_user_card(bot, callback_id, user_id, return_page)
        return

    if len(parts) == 6 and parts[3:5] == ["subscriptions", "page"]:
        await bot.answer_callback(
            callback_id=callback_id,
            message={
                "text": "Управление подпиской",
                "attachments": [
                    subscription_management_keyboard(user_id, return_page)
                ],
            },
        )
        return

    if len(parts) == 6 and parts[3:5] == ["grant", "page"]:
        async with session_factory() as session:
            tariffs = await AdminUserService(session).list_active_tariffs()
        await bot.answer_callback(
            callback_id=callback_id,
            message={
                "text": "Выберите активный тариф",
                "attachments": [
                    tariff_selection_keyboard(user_id, tariffs, return_page)
                ],
            },
        )
        return

    if len(parts) == 8 and parts[3:5] == ["grant", "tariff"]:
        try:
            tariff_id = int(parts[5])
        except ValueError:
            return
        async with session_factory() as session:
            tariffs = await AdminUserService(session).list_active_tariffs()
        tariff = next((item for item in tariffs if item.id == tariff_id), None)
        if tariff is None:
            await bot.answer_callback(
                callback_id=callback_id,
                message={"text": "Тариф больше недоступен."},
            )
            return
        await bot.answer_callback(
            callback_id=callback_id,
            message={
                "text": (
                    f'Выдать пользователю тариф "{tariff.name}" '
                    f"на {tariff.duration_days} дней?"
                ),
                "attachments": [
                    grant_confirmation_keyboard(
                        user_id,
                        tariff.id,
                        return_page,
                    )
                ],
            },
        )
        return

    if (
        len(parts) == 9
        and parts[3:5] == ["grant", "tariff"]
        and parts[6:8] == ["confirm", "page"]
    ):
        try:
            tariff_id = int(parts[5])
        except ValueError:
            return
        try:
            async with session_factory() as session:
                await AdminUserService(session).grant_subscription(
                    user_id,
                    tariff_id,
                )
        except AdminTariffUnavailableError:
            await bot.answer_callback(
                callback_id=callback_id,
                message={"text": "Тариф больше недоступен."},
            )
            return
        await _show_user_card(bot, callback_id, user_id, return_page)
        return

    if len(parts) == 6 and parts[3:5] == ["cancel", "page"]:
        await bot.answer_callback(
            callback_id=callback_id,
            message={
                "text": "Отменить активную подписку пользователя?",
                "attachments": [
                    cancel_confirmation_keyboard(user_id, return_page)
                ],
            },
        )
        return

    if (
        len(parts) == 7
        and parts[3:5] == ["cancel", "confirm"]
        and parts[5] == "page"
    ):
        async with session_factory() as session:
            await AdminUserService(session).cancel_subscription(user_id)
        await _show_user_card(bot, callback_id, user_id, return_page)
