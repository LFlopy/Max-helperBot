from collections.abc import Awaitable, Callable

from max_client import MaxBot


Handler = Callable[[MaxBot, dict], Awaitable[None]]


class Router:
    def __init__(self) -> None:
        self.message_handlers: dict[str, Handler] = {}
        self.callback_handlers: dict[str, Handler] = {}
        self.state_handlers: dict[str, Handler] = {}

    def message(self, command: str):
        def decorator(handler: Handler) -> Handler:
            self.message_handlers[command] = handler
            return handler

        return decorator

    def callback(self, payload: str):
        def decorator(handler: Handler) -> Handler:
            self.callback_handlers[payload] = handler
            return handler

        return decorator

    def state(self, state: str):
        def decorator(handler: Handler) -> Handler:
            self.state_handlers[state] = handler
            return handler

        return decorator
