from max_client import MaxBot

from bot.router import Router
from bot.keyboards.user.capabilities import capabilities_keyboard

router = Router()


@router.callback("user:capabilities")
async def handle_user_capabilities(
    bot: MaxBot,
    update: dict,
) -> None:
    callback = update.get("callback", {})

    message = update.get("message", {})

    callback_id = callback.get(
        "callback_id",
        "",
    )
    sender = callback.get(
        "user",
        callback.get("sender", {}),
    )
    user_id = int(sender.get("user_id", 0))
    recipient = message.get(
        "recipient",
        {},
    )
    chat_id = int(recipient.get("chat_id") or user_id)
    await bot.answer_callback(callback_id)
    await bot.send_message(
        user_id=chat_id,
        text=(
            "Вот с чем ко мне обычно приходят\n\n"
            "Выбери, что ближе - расскажу, как спросить"
            "И чем помогу."
        ),
        attachments=[capabilities_keyboard()],
    )
