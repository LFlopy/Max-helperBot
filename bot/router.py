from collections.abc import Awaitable, Callable

from max_client import MaxBot


Handler = Callable[[MaxBot, dict], Awaitable[None]]


class Router:
    def __init__(self) -> None:
        self.message_handlers: dict[str, Handler] = {}

    def message(self, command: str):
        def decorator(handler: Handler) -> Handler:
            self.message_handlers[command] = handler
            return handler

        return decorator
