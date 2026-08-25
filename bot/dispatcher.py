from max_client import MaxBot
from bot.router import Handler, Router, RouteMap, StateHandler
from bot.states.fsm import fsm


class Dispatcher:
    def __init__(self) -> None:
        self.routers: list[Router] = []
        self.message_handlers: dict[str, Handler] = {}
        self.callback_handlers: dict[str, Handler] = {}
        self.state_handlers: dict[str, StateHandler] = {}

    def include_router(self, router: Router) -> None:
        self._ensure_unique_routes(
            source=router.message_handlers,
            target=self.message_handlers,
            handler_type="message",
        )
        self._ensure_unique_routes(
            source=router.callback_handlers,
            target=self.callback_handlers,
            handler_type="callback",
        )
        self._ensure_unique_routes(
            source=router.state_handlers,
            target=self.state_handlers,
            handler_type="state",
        )

        self.routers.append(router)
        self.message_handlers.update(router.message_handlers)
        self.callback_handlers.update(router.callback_handlers)
        self.state_handlers.update(router.state_handlers)

    def include_routers(self, *routers: Router) -> None:
        for router in routers:
            self.include_router(router)

    @staticmethod
    def _ensure_unique_routes(
        source: RouteMap,
        target: RouteMap,
        handler_type: str,
    ) -> None:
        duplicate_routes = set(source) & set(target)

        if duplicate_routes:
            routes = ", ".join(sorted(duplicate_routes))
            raise ValueError(f"Duplicate {handler_type} routes: {routes}")

    async def dispatch(
        self,
        bot: MaxBot,
        update: dict,
    ) -> None:

        update_type = update.get("update_type")

        if update_type == "message_created":
            await self._dispatch_message(
                bot=bot,
                update=update,
            )
        elif update_type == "message_callback":
            await self._dispatch_callback(
                bot=bot,
                update=update,
            )

    async def _dispatch_message(
        self,
        bot: MaxBot,
        update: dict,
    ) -> None:
        message = update.get("message", {})
        body = message.get("body", {})
        sender = message.get("sender", {})

        text = body.get("text")
        user_id = int(sender.get("user_id", 0))

        if not text:
            return

        state = await fsm.get_state(user_id)

        if state is not None:
            state_namespace = state.split(
                ":",
                1,
            )[0]
            handler = self.state_handlers.get(
                state,
                self.state_handlers.get(state_namespace),
            )

            if handler is not None:
                await handler(
                    bot,
                    update,
                    state,
                )
                return

        handler = self.message_handlers.get(text)

        if handler is not None:
            await handler(bot, update)
            return

    async def _dispatch_callback(
        self,
        bot: MaxBot,
        update: dict,
    ) -> None:
        callback = update.get("callback", {})

        payload = callback.get("payload")

        if not payload:
            return

        handler = self.callback_handlers.get(payload)
        if handler is not None:
            await handler(bot, update)
            return
