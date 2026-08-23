from bot import router
from bot.keyboards.admin.main import admin_main_keyboard
from bot.router import Router
from config import ADMIN_IDS
from max_client import MaxBot


router = Router()


@router.message("/admin")
async def admin_handle_admin(
    bot: MaxBot,
    update: dict,
) -> None:
    message = update["message"]

    user_id = message["sender"]["user_id"]

    if user_id not in ADMIN_IDS:
        return

    await bot.send_message(
        user_id=user_id,
        text="Админ панель",
        attachments=[admin_main_keyboard()],
    )
