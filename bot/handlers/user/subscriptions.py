from datetime import datetime

from bot.keyboards.user.subscriptions import profile_keyboard
from bot.router import Router
from database.session import session_factory
from max_client import MaxBot
from services.subscriptions import AccessType
from services.user_subscriptions import UserProfile, UserSubscriptionService


router = Router()


def _callback_context(update: dict) -> tuple[dict, str, int] | None:
    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    user = callback.get("user", callback.get("sender", {}))
    if not isinstance(callback, dict) or not isinstance(user, dict):
        return None
    if not isinstance(callback_id, str) or not callback_id:
        return None
    try:
        user_id = int(user.get("user_id", 0))
    except (TypeError, ValueError):
        return None
    return callback, callback_id, user_id


def _date(value: datetime | None) -> str:
    return "—" if value is None else value.strftime("%d.%m.%Y")


def _profile_text(profile: UserProfile) -> str:
    lines = [f"Профиль: {profile.first_name or 'Без имени'}", ""]
    if profile.access_type is AccessType.PAID:
        lines.extend(
            [
                "Доступ: подписка активна",
                f"Тариф: {profile.tariff_name or 'Подписка'}",
                f"Действует до: {_date(profile.expires_at)}",
            ]
        )
    elif profile.access_type is AccessType.TRIAL:
        lines.extend(
            [
                "Доступ: бесплатный пробный период",
                f"Действует до: {_date(profile.expires_at)}",
            ]
        )
    else:
        lines.append("Доступ: базовый бесплатный")
        if not profile.can_activate_trial:
            lines.append("Пробный период уже был использован.")
    return "\n".join(lines)


async def _show_profile(bot: MaxBot, callback_id: str, user_id: int) -> None:
    async with session_factory() as session:
        profile = await UserSubscriptionService(session).get_profile(user_id)
    if profile is None:
        await bot.answer_callback(
            callback_id=callback_id,
            message={"text": "Сначала запустите бота командой /start."},
        )
        return
    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": _profile_text(profile),
            "attachments": [profile_keyboard(profile.can_activate_trial)],
        },
    )


@router.callback("user:profile")
async def handle_profile(bot: MaxBot, update: dict) -> None:
    context = _callback_context(update)
    if context is None:
        return
    _, callback_id, user_id = context
    await _show_profile(bot, callback_id, user_id)
