import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
import logging
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdateIdentity:
    key: str
    update_type: str


def get_update_identity(update: dict[str, object]) -> UpdateIdentity | None:
    update_type = update.get("update_type")
    if not isinstance(update_type, str) or not update_type:
        raise ValueError("update_type must be a non-empty string")

    if update_type == "message_created":
        message = update.get("message")
        if not isinstance(message, dict):
            raise ValueError("message_created update has no message")
        body = message.get("body")
        if not isinstance(body, dict):
            raise ValueError("message_created update has no message body")
        message_id = body.get("mid")
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("message_created update has no message id")
        return UpdateIdentity(
            key=f"{update_type}:{message_id}",
            update_type=update_type,
        )

    if update_type == "message_callback":
        callback = update.get("callback")
        if not isinstance(callback, dict):
            raise ValueError("message_callback update has no callback")
        callback_id = callback.get("callback_id")
        if not isinstance(callback_id, str) or not callback_id:
            raise ValueError("message_callback update has no callback id")
        return UpdateIdentity(
            key=f"{update_type}:{callback_id}",
            update_type=update_type,
        )

    return None


class BackgroundTaskRegistry:
    def __init__(self, shutdown_timeout: float = 30.0) -> None:
        if shutdown_timeout <= 0:
            raise ValueError("shutdown_timeout must be positive")
        self.tasks: set[asyncio.Task[None]] = set()
        self.shutdown_timeout = shutdown_timeout
        self.accepting = True

    def schedule(self, coroutine: Coroutine[Any, Any, None]) -> None:
        if not self.accepting:
            coroutine.close()
            raise RuntimeError("Background task registry is shutting down")
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self._task_done)

    def _task_done(self, task: asyncio.Task[None]) -> None:
        self.tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Unhandled background task exception: %s",
                type(error).__name__,
                exc_info=(type(error), error, error.__traceback__),
            )

    async def close(self) -> None:
        self.accepting = False
        if not self.tasks:
            return

        _, pending = await asyncio.wait(
            tuple(self.tasks),
            timeout=self.shutdown_timeout,
        )
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
