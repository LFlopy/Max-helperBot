import asyncio
from collections.abc import Sequence
from time import time_ns

from database.repositories import MessageRepository, UserRepository
from database.session import engine, session_factory
from services import ConsultationService
from services.ai import AIClientError, AIMessage
from services.consultation import AI_UNAVAILABLE_MESSAGE
from services.prompts import CONSULTATION_SYSTEM_PROMPT


class FakeAIClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, list[AIMessage]]] = []

    async def generate(
        self,
        system_prompt: str,
        messages: Sequence[AIMessage],
    ) -> str:
        self.calls.append((system_prompt, list(messages)))
        return self.responses.pop(0)


class FailingAIClient:
    async def generate(
        self,
        system_prompt: str,
        messages: Sequence[AIMessage],
    ) -> str:
        raise AIClientError("Expected check failure")


async def cleanup(max_user_id: int) -> None:
    async with session_factory() as session:
        users = UserRepository(session)
        user = await users.get_by_max_user_id(max_user_id)
        if user is None:
            return

        messages = MessageRepository(session)
        for message in await messages.get_recent_by_user(user.id, limit=100):
            await session.delete(message)
        await session.delete(user)
        await session.commit()


async def main() -> None:
    max_user_id = -time_ns()
    ai_client = FakeAIClient(["Первый AI-ответ", "Второй AI-ответ"])

    try:
        async with session_factory() as session:
            service = ConsultationService(
                session,
                ai_client=ai_client,
                history_limit=3,
            )
            first_response = await service.process_message(
                max_user_id=max_user_id,
                content="Первый вопрос",
                topic="consultation:food",
            )
            second_response = await service.process_message(
                max_user_id=max_user_id,
                content="Второй вопрос",
                topic="consultation:sleep",
            )

            assert first_response == "Первый AI-ответ"
            assert second_response == "Второй AI-ответ"
            assert len(ai_client.calls) == 2
            assert ai_client.calls[0][0] == CONSULTATION_SYSTEM_PROMPT
            assert [message.role for message in ai_client.calls[1][1]] == [
                "system",
                "user",
                "assistant",
                "user",
            ]
            assert [message.content for message in ai_client.calls[1][1][1:]] == [
                "Первый вопрос",
                "Первый AI-ответ",
                "Второй вопрос",
            ]

            user = await service.users.get_by_max_user_id(max_user_id)
            assert user is not None

            history = await service.messages.get_recent_by_user(user.id)
            assert [message.content for message in history] == [
                "Первый вопрос",
                "Первый AI-ответ",
                "Второй вопрос",
                "Второй AI-ответ",
            ]

            failing_service = ConsultationService(
                session,
                ai_client=FailingAIClient(),
            )
            fallback = await failing_service.process_message(
                max_user_id=max_user_id,
                content="Сообщение во время сбоя",
                topic="consultation:another",
            )
            assert fallback == AI_UNAVAILABLE_MESSAGE

            history = await service.messages.get_recent_by_user(user.id)
            assert history[-1].content == "Сообщение во время сбоя"
            assert all(
                message.content != AI_UNAVAILABLE_MESSAGE for message in history
            )
    finally:
        await cleanup(max_user_id)
        await engine.dispose()

    print("AI consultation check passed")


if __name__ == "__main__":
    asyncio.run(main())
