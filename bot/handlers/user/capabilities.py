from max_client import MaxBot

from bot.router import Router
from bot.keyboards.user.capabilities import capabilities_keyboard

router = Router()


@router.callback("user:capabilities")
async def handle_user_capabilities(
    bot: MaxBot,
    update: dict,
) -> None:
    print(update)
