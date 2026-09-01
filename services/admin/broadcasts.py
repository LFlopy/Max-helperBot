import asyncio
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import UserRepository


class BroadcastSender(Protocol):
    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class BroadcastResult:
    successful: int
    failed: int


class AdminBroadcastService:
    def __init__(
        self,
        session: AsyncSession,
        concurrency: int = 10,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        self.users = UserRepository(session)
        self.concurrency = concurrency

    async def get_recipient_ids(self) -> list[int]:
        return await self.users.list_all_max_user_ids()

    async def send_to_all(
        self,
        sender: BroadcastSender,
        recipient_ids: list[int],
        text: str,
    ) -> BroadcastResult:
        successful = 0
        failed = 0
        for offset in range(0, len(recipient_ids), self.concurrency):
            batch = recipient_ids[offset : offset + self.concurrency]
            results = await asyncio.gather(
                *(self._send(sender, user_id, text) for user_id in batch)
            )
            successful_in_batch = sum(results)
            successful += successful_in_batch
            failed += len(results) - successful_in_batch
        return BroadcastResult(successful=successful, failed=failed)

    @staticmethod
    async def _send(
        sender: BroadcastSender,
        user_id: int,
        text: str,
    ) -> int:
        try:
            await sender.send_message(user_id=user_id, text=text)
        except Exception:
            return 0
        return 1
