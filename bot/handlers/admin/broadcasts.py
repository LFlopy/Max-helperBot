from bot.keyboards.admin.broadcasts import broadcasts_keyboard
from bot.router import Router
from config import ADMIN_IDS
from max_client import MaxBot


router = Router()


@router.callback("admin:broadcasts")
async def broadcasts(
    bot: MaxBot,
    update: dict,
) -> None:
    callback = update.get("callback", {})

    user = callback.get("user", callback.get("sender", {}))

    user_id = int(user.get("user_id", 0))

    if user_id not in ADMIN_IDS:
        return

    callback_id = callback.get("callback_id")

    if not callback_id:
        return

    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": "Выберите вариант рассылки",
            "attachments": [
                broadcasts_keyboard(),
            ],
        },
    )
