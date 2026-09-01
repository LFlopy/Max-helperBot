from bot.keyboards.admin.broadcasts import (
    broadcast_cancel_keyboard,
    broadcast_preview_keyboard,
    broadcasts_keyboard,
)
from bot.router import Router
from bot.states.fsm import fsm
from database.session import session_factory
from max_client import MaxBot
from services.admin import AdminBroadcastService


router = Router()


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
        recipients = await AdminBroadcastService(session).get_recipient_ids()
    await fsm.set_data(user_id, {"broadcast_text": text})
    await bot.send_message(
        user_id=user_id,
        text=f"Рассылка для {len(recipients)} пользователей.\n\n{text}",
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
        service = AdminBroadcastService(session)
        recipient_ids = await service.get_recipient_ids()
    result = await service.send_to_all(bot, recipient_ids, text)
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": (
                "Рассылка завершена.\n\n"
                f"Успешно: {result.successful}\n"
                f"Ошибок: {result.failed}"
            ),
            "attachments": [broadcasts_keyboard()],
        },
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
