from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import MessageRepository, UserRepository


class ConsultationService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.messages = MessageRepository(session)

    async def process_message(
        self,
        max_user_id: int,
        content: str,
        topic: str,
        first_name: str | None = None,
    ) -> str:
        user = await self.users.get_or_create(
            max_user_id=max_user_id,
            first_name=first_name,
        )
        await self.messages.create(
            user_id=user.id,
            role="user",
            content=content,
        )
        history = await self.messages.get_recent_by_user(
            user_id=user.id,
            limit=20,
        )

        response = (
            f"Тема: {topic}\n\n"
            f"Получил сообщение:\n{content}"
        )

        await self.messages.create(
            user_id=user.id,
            role="assistant",
            content=response,
        )

        return response
