import asyncio

from config import MAX_BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_URL
from max_client import MaxBot


async def main():
    bot = MaxBot(MAX_BOT_TOKEN)

    await bot.start()

    try:
        result = await bot.subscribe_webhook(
            WEBHOOK_URL,
            WEBHOOK_SECRET,
        )

        print(result)

    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
