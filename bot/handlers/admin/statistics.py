from max_client import MaxBot
from config import ADMIN_IDS
from bot.router import Router


router = Router()


@router.callback("admin:statistics")
async def handle_statistics(
    bot: MaxBot,
    update: dict,
) -> None:
    callback = update.get("callback", {})

    user = callback.get(
        "user",
        callback.get("sender", {}),
    )

    user_id = int(user.get("user_id", 0))

    if user_id not in ADMIN_IDS:
        return

    callback_id = callback.get("callback_id")

    if not callback_id:
        return

    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": {
                "Статистика\n\nПользователей:0\n\nАктивных подписок:0\n\nВыручка:0\n\n"
            }
        },
    )
