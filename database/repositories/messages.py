from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        role: str,
        content: str,
    ) -> Message:
        message = Message(
            user_id=user_id,
            role=role,
            content=content,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_recent_by_user(
        self,
        user_id: int,
        limit: int = 20,
    ) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.user_id == user_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        messages = list(result.scalars())
        messages.reverse()
        return messages
