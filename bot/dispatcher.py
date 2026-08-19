from max_client import MaxBot
from bot.router import Router


class Dispatcher:
    def __init__(self) -> None:
        self.routers: list[Router] = []

    def include_router(self, router: Router) -> None:
        self.routers.append(router)

    async def dispatch(
        self,
        bot: MaxBot,
        update: dict,
    ) -> None:

        update_type = update.get("update_type")

        if update_type == "message_created":
            await self._dispach_message(
                bot=bot,
                update=update,
            )

    async def _dispach_message(
        self,
        bot: MaxBot,
        update: dict,
    ) -> None:
        message = update.get("message", {})
        body = message.get("body", {})

        text = body.get("text")

        if not text:
            return

        for router in self.routers:
            handler = router.message_handlers.get(text)

            if handler is not None:
                await handler(bot, update)
                return
