from max_client import MaxBot

from bot.router import Router
from bot.states.fsm import fsm
from bot.states.user.consultation import ConsultationState
from bot.keyboards.user.capabilities import capabilities_keyboard
from bot.keyboards.user.back_to_capabilities import back

router = Router()


CAPABILITY_TEXTS = {
    "capabilities:food": (
        ConsultationState.FOOD,
        "Питание связано с энергией, насыщением, привычками "
        "и самочувствием в течение дня.\n\n"
        "Напиши свой вопрос про питание: рацион, режим, тягу к сладкому, "
        "переедание, перекусы или другую ситуацию."
    ),
    "capabilities:weight": (
        ConsultationState.WEIGHT,
        "Вес зависит от питания, активности, сна, стресса "
        "и состояния здоровья.\n\n"
        "Напиши свой вопрос про вес: снижение, набор, плато, отеки "
        "или другую ситуацию."
    ),
    "capabilities:sleep": (
        ConsultationState.SLEEP,
        "Сон влияет на аппетит, стресс, восстановление "
        "и общее самочувствие.\n\n"
        "Напиши свой вопрос про сон: режим, засыпание, "
        "ночные пробуждения, утреннюю разбитость или "
        "другую ситуацию."
    ),
    "capabilities:stress": (
        ConsultationState.STRESS,
        "Стресс влияет на аппетит, сон, энергию "
        "и восстановление.\n\n"
        "Напиши свой вопрос про стресс: тревожность, усталость, "
        "заедание, напряжение или другую ситуацию."
    ),
    "capabilities:analyses": (
        ConsultationState.ANALYSES,
        "Анализы помогают увидеть возможные причины самочувствия "
        "и понять, что стоит обсудить со специалистом.\n\n"
        "Напиши свой вопрос про анализы: показатели, подготовку, "
        "динамику или другую ситуацию."
    ),
    "capabilities:hormones": (
        ConsultationState.HORMONES,
        "Гормоны и цикл могут влиять на вес, аппетит, настроение, "
        "сон и энергию.\n\n"
        "Напиши свой вопрос про гормоны, цикл, ПМС, задержки "
        "или другую ситуацию."
    ),
    "capabilities:another": (
        ConsultationState.ANOTHER,
        "Можно разобрать и другой вопрос, связанный с образом жизни "
        "и самочувствием.\n\n"
        "Напиши, что тебя беспокоит или что хочешь уточнить."
    ),
}


async def show_capability(
    bot: MaxBot,
    update: dict,
    key: str,
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

    state, text = CAPABILITY_TEXTS[key]

    await fsm.set_state(
        user_id,
        state,
    )

    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": text,
            "attachments": [
                back()
            ],
        },
    )


@router.callback("user:capabilities")
async def handle_user_capabilities(
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


@router.callback("capabilities:food")
async def handle_food_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:food",
    )


@router.callback("capabilities:weight")
async def handle_weight_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:weight",
    )


@router.callback("capabilities:sleep")
async def handle_sleep_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:sleep",
    )


@router.callback("capabilities:stress")
async def handle_stress_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:stress",
    )


@router.callback("capabilities:analyses")
async def handle_analyses_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:analyses",
    )


@router.callback("capabilities:hormones")
async def handle_hormones_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:hormones",
    )


@router.callback("capabilities:another")
async def handle_another_capability(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:another",
    )
