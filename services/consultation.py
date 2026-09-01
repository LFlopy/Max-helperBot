import logging

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Message
from database.repositories import MessageRepository, UserRepository
from services.ai import AIClient, AIClientError, AIMessage, get_ai_client
from services.prompts import CONSULTATION_SYSTEM_PROMPT


logger = logging.getLogger(__name__)

AI_UNAVAILABLE_MESSAGE = (
    "Сейчас не получается подготовить ответ. "
    "Попробуй отправить сообщение немного позже."
)


class ConsultationService:
    def __init__(
        self,
        session: AsyncSession,
        ai_client: AIClient | None = None,
        history_limit: int = 20,
    ) -> None:
        if history_limit < 1:
            raise ValueError("history_limit must be positive")

        self.users = UserRepository(session)
        self.messages = MessageRepository(session)
        self.ai_client = ai_client or get_ai_client()
        self.history_limit = history_limit

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
            limit=self.history_limit,
        )

        context = [
            AIMessage(
                role="system",
                content=f"Текущая тема консультации: {topic}.",
            ),
            *self._to_ai_messages(history),
        ]
        try:
            response = await self.ai_client.generate(
                system_prompt=CONSULTATION_SYSTEM_PROMPT,
                messages=context,
            )
        except AIClientError:
            logger.exception(
                "AI consultation request failed",
                extra={"max_user_id": max_user_id},
            )
            return AI_UNAVAILABLE_MESSAGE

        await self.messages.create(
            user_id=user.id,
            role="assistant",
            content=response,
        )

        return response

    @staticmethod
    def _to_ai_messages(messages: list[Message]) -> list[AIMessage]:
        context: list[AIMessage] = []
        for message in messages:
            if message.role == "user":
                context.append(AIMessage(role="user", content=message.content))
            elif message.role == "assistant":
                context.append(
                    AIMessage(role="assistant", content=message.content)
                )
        return context
