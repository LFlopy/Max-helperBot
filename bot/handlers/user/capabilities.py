from max_client import MaxBot

from bot.router import Router
from bot.states.fsm import fsm
from bot.states.user.consultation import ConsultationState
from bot.keyboards.user.capabilities import capabilities_keyboard
from bot.keyboards.user.back_to_capabilities import back

router = Router()


@router.callback("user:capabilities")
async def handle_user_capabilities(
    bot: MaxBot,
    update: dict,
) -> None:
    callback = update.get("callback", {})

    message = update.get("message", {})

    callback_id = callback.get(
        "callback_id",
        "",
    )

    sender = callback.get(
        "user",
        callback.get("sender", {}),
    )
    user_id = int(sender.get("user_id", 0))
    recipient = message.get(
        "recipient",
        {},
    )
    chat_id = int(recipient.get("chat_id") or user_id)
    await fsm.clear(user_id)
    await bot.answer_callback(
    callback_id=callback_id,
    message={
        "text": (
            "Вот с чем ко мне обычно приходят 👇\n\n"
            "Выбери, что ближе — расскажу, как спросить "
            "и чем помогу."
        ),
        "attachments": [
            capabilities_keyboard()
        ],
    },
)


@router.callback("capabilities:sleep")
async def handle_sleep_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    callback = update.get("callback", {})

    callback_id = callback.get(
        "callback_id",
        "",
    )

    sender = callback.get(
        "user",
        callback.get("sender", {}),
    )
    user_id = int(sender.get("user_id", 0))

    await fsm.set_state(
        user_id,
        ConsultationState.SLEEP,
    )

    await bot.answer_callback(
    callback_id=callback_id,
    message={
        "text": (
            "Сон влияет на аппетит, стресс, восстановление "
            "и общее самочувствие.\n\n"
            "Напиши свой вопрос про сон: режим, засыпание, "
            "ночные пробуждения, утреннюю разбитость или "
            "другую ситуацию."
        ),
        "attachments": [
            back()
        ],
    },
)

