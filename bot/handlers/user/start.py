from max_client import MaxBot

from bot.router import Router
from bot.keyboards.user.main import start_keyboard
from database.repositories import UserRepository
from database.session import session_factory

router = Router()


@router.message("/start")
async def handle_start(
    bot: MaxBot,
    update: dict,
) -> None:
    message = update["message"]
    sender = message["sender"]

    user_id = int(sender["user_id"])
    first_name = sender.get("first_name")
    if not isinstance(first_name, str):
        first_name = None

    async with session_factory() as session:
        repository = UserRepository(session)
        await repository.get_or_create(
            max_user_id=user_id,
            first_name=first_name,
        )

    await bot.send_message(
        user_id=user_id,
        text="Привет, помогу разобраться с ежедневным вопросами и образом жизни!",
        attachments=[start_keyboard()],
    )
