import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import DATABASE_URL


async def main() -> None:
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
    )

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))

            print(result.scalar())
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
