from max_client import MaxBot
from bot.router import (
    CallbackRouteMap,
    Handler,
    Router,
    RouteMap,
    StateHandler,
)
from bot.states.fsm import fsm
from config import ADMIN_IDS


class Dispatcher:
    def __init__(self) -> None:
        self.routers: list[Router] = []
        self.message_handlers: dict[str, Handler] = {}
        self.callback_handlers: dict[str, Handler] = {}
        self.callback_prefix_handlers: dict[str, Handler] = {}
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
            source=router.callback_prefix_handlers,
            target=self.callback_prefix_handlers,
            handler_type="callback prefix",
        )
        self._ensure_unique_routes(
            source=router.state_handlers,
            target=self.state_handlers,
            handler_type="state",
        )

        self.routers.append(router)
        self.message_handlers.update(router.message_handlers)
        self.callback_handlers.update(router.callback_handlers)
        self.callback_prefix_handlers.update(router.callback_prefix_handlers)
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
        message = update.get("message") or {}
        body = message.get("body") or {}
        sender = message.get("sender") or {}

        text = body.get("text")
        user_id = int(sender.get("user_id", 0))

        if text and text.startswith("/"):
            if text == "/admin" and user_id not in ADMIN_IDS:
                return
            handler = self.message_handlers.get(text)

            if handler is not None:
                await handler(bot, update)
                return

            return

        state = await fsm.get_state(user_id)

        if state is not None:
            if state.startswith("admin:") and user_id not in ADMIN_IDS:
                await fsm.clear(user_id)
                return
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

        if not text:
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

        if payload.startswith("admin:") and not self._is_admin_callback(
            callback
        ):
            return

        handler = self.callback_handlers.get(payload)
        if handler is None:
            handler = self._find_prefix_handler(
                payload,
                self.callback_prefix_handlers,
            )
        if handler is not None:
            await handler(bot, update)
            return

    @staticmethod
    def _find_prefix_handler(
        payload: str,
        handlers: CallbackRouteMap,
    ) -> Handler | None:
        matching_prefixes = [
            prefix for prefix in handlers if payload.startswith(prefix)
        ]
        if not matching_prefixes:
            return None
        prefix = max(matching_prefixes, key=len)
        return handlers[prefix]

    @staticmethod
    def _is_admin_callback(callback: dict) -> bool:
        user = callback.get("user", callback.get("sender", {}))
        if not isinstance(user, dict):
            return False
        try:
            user_id = int(user.get("user_id", 0))
        except (TypeError, ValueError):
            return False
        return user_id in ADMIN_IDS
