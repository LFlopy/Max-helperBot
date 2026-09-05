from datetime import datetime

from bot.keyboards.admin.broadcasts import (
    broadcast_cancel_keyboard,
    broadcast_list_keyboard,
    broadcast_preview_keyboard,
    broadcast_status_keyboard,
    broadcasts_keyboard,
)
from bot.router import Router
from bot.states.fsm import fsm
from database.session import session_factory
from database.models import BroadcastStatus
from max_client import MaxBot
from services.admin import AdminBroadcastService, BroadcastSummary


router = Router()


def _date_time(value: datetime | None) -> str:
    return "—" if value is None else value.strftime("%d.%m.%Y %H:%M:%S")


def _summary_text(summary: BroadcastSummary) -> str:
    return "\n".join(
        [
            f"Рассылка #{summary.id}",
            "",
            f"Статус: {summary.status.value}",
            f"Всего: {summary.total}",
            f"Отправлено: {summary.sent}",
            f"Ошибок: {summary.failed}",
            f"Запущена: {_date_time(summary.started_at)}",
            f"Завершена: {_date_time(summary.finished_at)}",
        ]
    )


def _callback_context(update: dict) -> tuple[str, int] | None:
    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    user = callback.get("user", callback.get("sender", {}))
    if not isinstance(callback_id, str) or not callback_id:
        return None
    if not isinstance(user, dict):
        return None
    try:
        user_id = int(user.get("user_id", 0))
    except (TypeError, ValueError):
        return None
    return callback_id, user_id


@router.callback("admin:broadcasts")
async def broadcasts(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    callback_id, _ = context
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "Выберите вариант рассылки",
            "attachments": [broadcasts_keyboard()],
        },
    )


@router.callback("admin:broadcasts:all")
async def start_broadcast(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    callback_id, user_id = context
    await fsm.clear(user_id)
    await fsm.set_state(user_id, "admin:broadcast:compose")
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "Отправьте текст рассылки.",
            "attachments": [broadcast_cancel_keyboard()],
        },
    )


@router.callback("admin:broadcasts:status")
async def broadcast_statuses(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    callback_id, _ = context
    async with session_factory() as session:
        items = await AdminBroadcastService(session).list_recent()
    lines = ["Последние рассылки", ""]
    lines.extend(
        f"#{item.id}: {item.status.value} ({item.sent}/{item.total}, ошибок {item.failed})"
        for item in items
    )
    if not items:
        lines.append("Рассылок пока нет.")
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "\n".join(lines),
            "attachments": [
                broadcast_list_keyboard(tuple(item.id for item in items))
            ],
        },
    )


@router.callback_prefix("admin:broadcast:")
async def broadcast_status(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    callback_id, _ = context
    payload = update.get("callback", {}).get("payload")
    if not isinstance(payload, str):
        return
    parts = payload.split(":")
    try:
        broadcast_id = int(parts[2])
    except (IndexError, ValueError):
        return
    async with session_factory() as session:
        service = AdminBroadcastService(session)
        if len(parts) == 4 and parts[3] == "cancel":
            summary = await service.cancel(broadcast_id)
        elif len(parts) == 3:
            summary = await service.get_summary(broadcast_id)
        else:
            return
    text = "Рассылка не найдена." if summary is None else _summary_text(summary)
    can_cancel = summary is not None and summary.status in {
        BroadcastStatus.PENDING,
        BroadcastStatus.RUNNING,
    }
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": text,
            "attachments": [
                broadcast_status_keyboard(
                    None if summary is None else summary.id,
                    can_cancel,
                )
            ],
        },
    )


@router.state("admin:broadcast:compose")
async def compose_broadcast(
    bot: MaxBot,
    update: dict,
    _state: str,
) -> None:
    message = update.get("message", {})
    sender = message.get("sender", {})
    body = message.get("body", {})
    if not isinstance(sender, dict) or not isinstance(body, dict):
        return
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        return
    try:
        user_id = int(sender.get("user_id", 0))
    except (TypeError, ValueError):
        return

    async with session_factory() as session:
        recipient_count = await AdminBroadcastService(
            session
        ).get_recipient_count()
    await fsm.set_data(user_id, {"broadcast_text": text})
    await bot.send_message(
        user_id=user_id,
        text=f"Рассылка для {recipient_count} пользователей.\n\n{text}",
        attachments=[broadcast_preview_keyboard()],
    )


@router.callback("admin:broadcasts:confirm")
async def confirm_broadcast(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    callback_id, user_id = context
    data = await fsm.get_data(user_id)
    text = data.get("broadcast_text")
    if not isinstance(text, str):
        await bot.answer_callback(
            callback_id=callback_id,
            message={
                "text": "Черновик рассылки не найден.",
                "attachments": [broadcasts_keyboard()],
            },
        )
        return

    await fsm.clear(user_id)
    async with session_factory() as session:
        broadcast_id = await AdminBroadcastService(session).create(
            created_by_max_user_id=user_id,
            text=text,
        )
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": f"Рассылка #{broadcast_id} запущена.",
            "attachments": [broadcasts_keyboard()],
        },
    )
    async with session_factory() as session:
        result = await AdminBroadcastService(session).process(
            broadcast_id,
            bot,
        )
    await bot.send_message(
        user_id=user_id,
        text=(
            f"Рассылка #{broadcast_id} завершена.\n\n"
            f"Успешно: {result.successful}\n"
            f"Ошибок: {result.failed}"
        ),
        attachments=[broadcasts_keyboard()],
    )


@router.callback("admin:broadcasts:cancel")
async def cancel_broadcast(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    callback_id, user_id = context
    await fsm.clear(user_id)
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "Рассылка отменена.",
            "attachments": [broadcasts_keyboard()],
        },
    )
