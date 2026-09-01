from datetime import datetime

from bot.keyboards.admin.subscriptions import (
    active_subscriptions_keyboard,
    subscriptions_overview_keyboard,
    tariffs_keyboard,
)
from bot.router import Router
from database.session import session_factory
from max_client import MaxBot
from services.admin import (
    ActiveSubscriptionPage,
    AdminSubscriptionService,
)


router = Router()


def _callback_id(update: dict) -> str | None:
    callback_id = update.get("callback", {}).get("callback_id")
    if not isinstance(callback_id, str) or not callback_id:
        return None
    return callback_id


def _active_text(page: ActiveSubscriptionPage) -> str:
    lines = ["Активные подписки", ""]
    if not page.items:
        lines.append("Активных подписок пока нет.")
        return "\n".join(lines)
    for index, item in enumerate(page.items, start=1):
        lines.extend(
            [
                f"{index}. {item.first_name or 'Без имени'}",
                f"MAX ID: {item.max_user_id}",
                f"Тариф: {item.tariff_name}",
                f"До: {item.expires_at.strftime('%d.%m.%Y')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


async def _show_active(
    bot: MaxBot,
    callback_id: str,
    page_number: int,
) -> None:
    async with session_factory() as session:
        page = await AdminSubscriptionService(
            session
        ).list_active_subscriptions(page=page_number)
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": _active_text(page),
            "attachments": [active_subscriptions_keyboard(page)],
        },
    )


@router.callback("admin:subscriptions")
async def handle_subscriptions(bot: MaxBot, update: dict) -> None:
    callback_id = _callback_id(update)
    if callback_id is None:
        return
    async with session_factory() as session:
        overview = await AdminSubscriptionService(session).get_overview()
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": (
                "Подписки\n\n"
                f"Активных подписок: {overview.paid_count}\n"
                f"Trial: {overview.trial_count}\n"
                f"Free: {overview.free_count}"
            ),
            "attachments": [subscriptions_overview_keyboard()],
        },
    )


@router.callback("admin:subscriptions:active")
async def handle_active_subscriptions(bot: MaxBot, update: dict) -> None:
    callback_id = _callback_id(update)
    if callback_id is not None:
        await _show_active(bot, callback_id, page_number=1)


@router.callback_prefix("admin:subscriptions:active:page:")
async def handle_active_page(bot: MaxBot, update: dict) -> None:
    callback_id = _callback_id(update)
    payload = update.get("callback", {}).get("payload")
    if callback_id is None or not isinstance(payload, str):
        return
    try:
        page_number = max(1, int(payload.rsplit(":", 1)[1]))
    except (IndexError, ValueError):
        return
    await _show_active(bot, callback_id, page_number)


@router.callback("admin:subscriptions:tariffs")
async def handle_tariffs(bot: MaxBot, update: dict) -> None:
    callback_id = _callback_id(update)
    if callback_id is None:
        return
    async with session_factory() as session:
        tariffs = await AdminSubscriptionService(session).list_active_tariffs()
    lines = ["Активные тарифы", ""]
    for tariff in tariffs:
        lines.extend(
            [
                tariff.name,
                f"Code: {tariff.code}",
                f"Цена: {tariff.price} ₽",
                f"Период: {tariff.duration_days} дней",
                f"Лимит истории: {tariff.history_limit}",
                "",
            ]
        )
    if not tariffs:
        lines.append("Активных тарифов пока нет.")
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "\n".join(lines).rstrip(),
            "attachments": [tariffs_keyboard()],
        },
    )
