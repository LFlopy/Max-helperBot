from bot.keyboards.user.back_to_capabilities import back
from bot.router import Router
from max_client import MaxBot
from services.content import content_service

router = Router()


async def show_capability(
    bot: MaxBot,
    update: dict,
    key: str,
) -> None:
    callback = update.get("callback", {})

    callback_id = callback.get("callback_id")

    if not callback_id:
        return

    text = await content_service.get_text(key)

    await bot.answer_callback(
        callback_id=callback_id,
        message={
            "text": text,
            "attachments": [
                back(),
            ],
        },
    )


@router.callback("capabilities:food")
async def capability_food(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:food",
    )


@router.callback("capabilities:weight")
async def capability_weight(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:weight",
    )


@router.callback("capabilities:sleep")
async def capability_sleep(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:sleep",
    )


@router.callback("capabilities:stress")
async def capability_stress(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:stress",
    )


@router.callback("capabilities:analyses")
async def capability_analyses(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:analyses",
    )


@router.callback("capabilities:hormones")
async def capability_hormones(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:hormones",
    )


@router.callback("capabilities:another")
async def capability_another(
    bot: MaxBot,
    update: dict,
) -> None:
    await show_capability(
        bot=bot,
        update=update,
        key="capabilities:another",
    )
