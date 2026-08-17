import asyncio

from config import MAX_BOT_TOKEN
from max_client import MaxBot


async def main():
    bot = MaxBot(MAX_BOT_TOKEN)

    await bot.start()

    try:
        me = await bot.get_me()
        print(me)

        # Здесь потом будет запуск polling/webhook

    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
