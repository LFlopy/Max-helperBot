from max_client import MaxBot

from bot.router import Router
from bot.keyboards.user.main import start_keyboard

router = Router()


@router.message("/start")
async def handle_start(
    bot: MaxBot,
    update: dict,
) -> None:
    message = update["message"]

    user_id = message["sender"]["user_id"]

    await bot.send_message(
        user_id=user_id,
        text="Привет, помогу разобраться с ежедневным вопросами и образом жизни!",
        attachments=[start_keyboard()],
    )
