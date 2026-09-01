from bot.keyboards.admin.statistics import back
from bot.router import Router
from database.session import session_factory
from max_client import MaxBot
from services.admin import AdminStatisticsService


router = Router()


@router.callback("admin:statistics")
async def handle_statistics(
    bot: MaxBot,
    update: dict,
) -> None:
    callback_id = update.get("callback", {}).get("callback_id")
    if not isinstance(callback_id, str) or not callback_id:
        return

    async with session_factory() as session:
        statistics = await AdminStatisticsService(session).get_statistics()

    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": (
                "Статистика\n\n"
                f"Пользователей: {statistics.users_count}\n"
                f"Новых за 24 часа: {statistics.new_users_24h}\n"
                f"Новых за 7 дней: {statistics.new_users_7d}\n\n"
                f"Активных paid подписок: {statistics.active_paid_count}\n"
                f"Активных trial: {statistics.active_trial_count}\n\n"
                f"Успешных платежей: {statistics.paid_payments_count}\n"
                f"Выручка: {statistics.revenue} ₽\n\n"
                f"Количество сообщений: {statistics.messages_count}\n"
                f"Сообщений за 24 часа: {statistics.messages_24h}"
            ),
            "attachments": [back()],
        },
    )
