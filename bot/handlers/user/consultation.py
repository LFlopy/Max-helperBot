from max_client import MaxBot

from bot.router import Router
from bot.keyboards.user.back_to_capabilities import back
from database.session import session_factory
from services import ConsultationService

router = Router()


@router.state("consultation")
async def handle_consultation_message(
    bot: MaxBot,
    update: dict,
    state: str,
) -> None:
    message = update.get("message") or {}
    body = message.get("body") or {}
    sender = message.get("sender") or {}

    user_id = int(sender.get("user_id", 0))
    text = body.get("text")
    if not isinstance(text, str):
        return

    first_name = sender.get("first_name")
    if not isinstance(first_name, str):
        first_name = None

    async with session_factory() as session:
        service = ConsultationService(session)
        response = await service.process_message(
            max_user_id=user_id,
            content=text,
            topic=state,
            first_name=first_name,
        )

    await bot.send_message(
        user_id=user_id,
        text=response,
        attachments=[
            back(),
        ],
    )
