from bot.keyboards.user.main_menu import main_menu
from max_client import MaxBot
from bot.router import Router


router = Router()


@router.callback("user:main")
async def handle_user_main(
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
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": ("Главное меню"),
            "attachments": [main_menu()],
        },
    )
