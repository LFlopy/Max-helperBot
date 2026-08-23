import asyncio

from aiohttp import web

from bot import dispatcher
from bot.handlers.admin import broadcasts
from config import MAX_BOT_TOKEN, WEBHOOK_SECRET
from max_client import MaxBot
from bot.dispatcher import Dispatcher
from bot.handlers.user.start import router as start_router
from bot.handlers.user.capabilities import router as capabilities_router
from bot.handlers.admin.main import router as admin_main
from bot.handlers.admin.statistics import router as statistics_router
from bot.handlers.admin.broadcasts import router as broadcasts_router


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
    bot = MaxBot(MAX_BOT_TOKEN)
    await bot.start()

    dispatcher = Dispatcher()
    dispatcher.include_router(start_router)
    dispatcher.include_router(capabilities_router)
    dispatcher.include_router(admin_main)
    dispatcher.include_router(statistics_router)
    dispatcher.include_router(broadcasts_router)

    app = web.Application()

    app["bot"] = bot
    app["dispatcher"] = dispatcher

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
