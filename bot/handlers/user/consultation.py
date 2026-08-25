from max_client import MaxBot

from bot.router import Router
from bot.states.user.consultation import ConsultationState
from bot.keyboards.user.back_to_capabilities import back

router = Router()


@router.state(ConsultationState.SLEEP)
async def handle_sleep_consultation(
    bot: MaxBot,
    update: dict,
) -> None:
    message = update.get("message", {})
    body = message.get("body", {})
    sender = message.get("sender", {})

    user_id = int(sender.get("user_id", 0))
    text = body.get("text", "")

    await bot.send_message(
        user_id=user_id,
        text=(
            "Принял вопрос про сон:\n\n"
            f"{text}\n\n"
            "Сейчас разберу его в контексте сна."
        ),
        attachments=[
            back(),
        ],
    )
