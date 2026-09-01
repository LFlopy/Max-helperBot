import asyncio
from time import time_ns

from database.repositories import UserRepository
from database.session import engine, session_factory


async def main() -> None:
    max_user_id = -time_ns()

    try:
        async with session_factory() as session:
            repository = UserRepository(session)
            created_user = await repository.get_or_create(
                max_user_id=max_user_id,
                first_name="Repository check",
            )
            existing_user = await repository.get_or_create(
                max_user_id=max_user_id,
                first_name="Ignored duplicate",
            )

            assert created_user.id == existing_user.id

            await session.delete(created_user)
            await session.commit()
    finally:
        await engine.dispose()

    print("UserRepository check passed")


if __name__ == "__main__":
    asyncio.run(main())
