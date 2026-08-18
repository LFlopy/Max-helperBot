import asyncio

from aiohttp import web

from config import MAX_BOT_TOKEN, WEBHOOK_SECRET
from max_client import MaxBot


async def webhook_handler(request: web.Request):
    secret = request.headers.get("X-max-Bot-Api-Secret")

    if secret != WEBHOOK_SECRET:
        return web.Response(status=403)

    update = await request.json()

    print(update)

    return web.Response(status=200)


async def main():
    bot = MaxBot(MAX_BOT_TOKEN)
    await bot.start()

    app = web.Application()

    app["bot"] = bot

    app.router.add_post(
        "/max-helper/webhook",
        webhook_handler,
    )

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host="127.0.0.1",
        port=8080,
    )

    await site.start()
    print("webhook server started")

    try:
        await asyncio.Event().wait()
    finally:
        await bot.close()
        await runner.cleanup()

    result = await bot.subscribe_webhook(
        "https://ovchuntonova.ru/max-helper/webhook",
        WEBHOOK_SECRET,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
