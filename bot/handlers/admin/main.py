from bot.keyboards.admin.main import admin_main_keyboard
from bot.router import Router
from bot.states.fsm import fsm
from max_client import MaxBot


router = Router()


async def show_admin(
    bot: MaxBot,
    user_id: int,
) -> None:
    await fsm.clear(user_id)
    await bot.send_message(
        user_id=user_id,
        text="Админ панель",
        attachments=[
            admin_main_keyboard(),
        ],
    )


@router.message("/admin")
async def admin_handle_admin(
    bot: MaxBot,
    update: dict,
) -> None:
    message = update["message"]
    user_id = int(message["sender"]["user_id"])

    await show_admin(
        bot=bot,
        user_id=user_id,
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

    await show_admin(
        bot=bot,
        user_id=user_id,
    )
