from max_client import MaxBot

from bot.router import Router
from bot.keyboards.user.back_to_capabilities import back

router = Router()


@router.state("consultation")
async def handle_consultation_message(
    bot: MaxBot,
    update: dict,
    state: str,
) -> None:
    message = update.get("message", {})
    body = message.get("body", {})
    sender = message.get("sender", {})

    user_id = int(sender.get("user_id", 0))
    text = body.get("text", "")

    await bot.send_message(
        user_id=user_id,
        text=(
            f"Тема: {state}\n\n"
            f"Получил сообщение:\n{text}"
        ),
        attachments=[
            back(),
        ],
    )
