from bot.keyboards.admin.main_menu import admin_main_menu
from bot.keyboards.user.main_menu import main_menu
from bot.router import Router
from bot.states.fsm import fsm
from config import ADMIN_IDS
from max_client import MaxBot


router = Router()


@router.callback("user:main")
async def handle_user_main(
    bot: MaxBot,
    update: dict,
) -> None:
    callback = update.get("callback", {})

    callback_id = callback.get("callback_id")

    if not callback_id:
        return

    user = callback.get(
        "user",
        callback.get("sender", {}),
    )

    user_id = int(user.get("user_id", 0))

    await fsm.clear(user_id)

    if user_id in ADMIN_IDS:
        keyboard = admin_main_menu()
    else:
        keyboard = main_menu()

    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "Главное меню",
            "attachments": [
                keyboard,
            ],
        },
    )
