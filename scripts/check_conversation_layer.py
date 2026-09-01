import asyncio
from time import time_ns

from database.repositories import MessageRepository, UserRepository
from database.session import engine, session_factory
from services import ConsultationService


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

    try:
        async with session_factory() as session:
            service = ConsultationService(session)
            first_response = await service.process_message(
                max_user_id=max_user_id,
                content="Первый вопрос",
                topic="consultation:food",
                first_name="Conversation check",
            )
            second_response = await service.process_message(
                max_user_id=max_user_id,
                content="Второй вопрос",
                topic="consultation:sleep",
            )

            user = await service.users.get_by_max_user_id(max_user_id)
            assert user is not None

            history = await service.messages.get_recent_by_user(user.id)
            assert [message.role for message in history] == [
                "user",
                "assistant",
                "user",
                "assistant",
            ]
            assert history[0].content == "Первый вопрос"
            assert history[1].content == first_response
            assert history[2].content == "Второй вопрос"
            assert history[3].content == second_response

            recent = await service.messages.get_recent_by_user(user.id, limit=2)
            assert [message.content for message in recent] == [
                "Второй вопрос",
                second_response,
            ]
    finally:
        await cleanup(max_user_id)
        await engine.dispose()

    print("Conversation layer check passed")


if __name__ == "__main__":
    asyncio.run(main())
