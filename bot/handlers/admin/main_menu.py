from bot.keyboards.admin.main_menu import admin_main_menu
from max_client import MaxBot
from config import ADMIN_IDS
from bot.router import Router


router = Router()


async def show_admin_main(
    bot: MaxBot,
    user_id: int,
) -> None:
    if user_id not in ADMIN_IDS:
        return

        await bot.send_message(
            user_id=user_id,
            text="Главное меню",
            attachments=[
                admin_main_menu(),
            ],
        )


@router.callback("admin:main")
async def admin_handle_main_callback(
    bot: MaxBot,
    update: dict,
) -> None:
    callback = update["callback"]

    user = callback.get(
        "user",
        callback.get("sender", {}),
    )

    user_id = int(user.get("user_id", 0))

    await show_admin_main(
        bot=bot,
        user_id=user_id,
    )
