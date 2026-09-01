import asyncio

from aiohttp import web

from bot.handlers import ROUTERS
from config import MAX_BOT_TOKEN, WEBHOOK_SECRET
from max_client import MaxBot
from bot.dispatcher import Dispatcher
from database.session import engine
from services.ai import configure_ai_client, shutdown_ai_client


async def close_database(_app: web.Application) -> None:
    await engine.dispose()


async def close_ai_client(_app: web.Application) -> None:
    await shutdown_ai_client()


async def webhook_handler(request: web.Request):
    secret = request.headers.get("X-max-Bot-Api-Secret")

    if secret != WEBHOOK_SECRET:
        return web.Response(status=403)

    update = await request.json()

    bot: MaxBot = request.app["bot"]
    dispatcher: Dispatcher = request.app["dispatcher"]

    await dispatcher.dispatch(
        bot=bot,
        update=update,
    )

    return web.Response(status=200)


async def main():
    configure_ai_client()

    bot = MaxBot(MAX_BOT_TOKEN)
    await bot.start()

    dispatcher = Dispatcher()
    dispatcher.include_routers(*ROUTERS)

    app = web.Application()

    app["bot"] = bot
    app["dispatcher"] = dispatcher
    app.on_cleanup.append(close_ai_client)
    app.on_cleanup.append(close_database)

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


if __name__ == "__main__":
    asyncio.run(main())
