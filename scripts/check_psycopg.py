# scripts/check_psycopg.py

import asyncio

import psycopg

from config import DATABASE_URL


async def main() -> None:
    url = DATABASE_URL.replace(
        "postgresql+psycopg://",
        "postgresql://",
    )

    async with await psycopg.AsyncConnection.connect(
        url,
        connect_timeout=10,
    ) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT 1")

            result = await cursor.fetchone()

            print(result)


if __name__ == "__main__":
    asyncio.run(main())
