import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.repositories import BroadcastRepository
from max_client import MaxBot
from services.admin.broadcasts import AdminBroadcastService
from services.update_processing import BackgroundTaskRegistry


logger = logging.getLogger(__name__)


class BroadcastRecoveryManager:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        tasks: BackgroundTaskRegistry,
        bot: MaxBot,
    ) -> None:
        self.sessions = sessions
        self.tasks = tasks
        self.bot = bot
        self.active_ids: set[int] = set()

    async def resume_unfinished(self) -> int:
        async with self.sessions() as session:
            broadcasts = await BroadcastRepository(session).list_unfinished()
        for broadcast in broadcasts:
            self.schedule(broadcast.id)
        if broadcasts:
            logger.info(
                "Unfinished broadcasts scheduled: count=%s",
                len(broadcasts),
            )
        return len(broadcasts)

    def schedule(self, broadcast_id: int) -> bool:
        if broadcast_id in self.active_ids:
            return False
        self.active_ids.add(broadcast_id)
        try:
            self.tasks.schedule(self._process(broadcast_id))
        except Exception:
            self.active_ids.discard(broadcast_id)
            raise
        return True

    async def _process(self, broadcast_id: int) -> None:
        try:
            async with self.sessions() as session:
                broadcast = await BroadcastRepository(session).get_by_id(
                    broadcast_id
                )
                if broadcast is None:
                    return
                admin_id = broadcast.created_by_max_user_id
                result = await AdminBroadcastService(session).process(
                    broadcast_id,
                    self.bot,
                )
            await self.bot.send_message(
                user_id=admin_id,
                text=(
                    f"Рассылка #{broadcast_id} завершена после восстановления.\n\n"
                    f"Успешно: {result.successful}\n"
                    f"Ошибок: {result.failed}"
                ),
            )
        finally:
            self.active_ids.discard(broadcast_id)
