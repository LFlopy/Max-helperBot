import asyncio

from sqlalchemy import text

from database.session import engine


async def main() -> None:
    print("1. До engine.connect()")

    async with engine.connect() as connection:
        print("2. Соединение получено")

        print("3. До SELECT 1")

        result = await connection.execute(text("SELECT 1"))

        print("4. SELECT 1 выполнен")

        value = result.scalar()

        print("5. Результат:", value)

    print("6. Соединение закрыто")


if __name__ == "__main__":
    asyncio.run(main())
