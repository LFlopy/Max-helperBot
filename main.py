import asyncio
import json

from aiohttp import web

from bot.handlers import ROUTERS
from config import MAX_BOT_TOKEN, WEBHOOK_SECRET
from max_client import MaxBot
from bot.dispatcher import Dispatcher
from database.session import engine, session_factory
from database.repositories import ProcessedUpdateRepository
from logging_config import configure_logging
from services.ai import configure_ai_client, shutdown_ai_client
from services.update_processing import (
    BackgroundTaskRegistry,
    MaxUpdateProcessor,
    get_update_identity,
)


BACKGROUND_TASKS_KEY = web.AppKey(
    "background_tasks",
    BackgroundTaskRegistry,
)
UPDATE_PROCESSOR_KEY = web.AppKey("update_processor", MaxUpdateProcessor)


async def close_background_tasks(app: web.Application) -> None:
    await app[BACKGROUND_TASKS_KEY].close()


async def close_database(_app: web.Application) -> None:
    await engine.dispose()


async def close_ai_client(_app: web.Application) -> None:
    await shutdown_ai_client()


async def webhook_handler(request: web.Request) -> web.Response:
    secret = request.headers.get("X-max-Bot-Api-Secret")

    if secret != WEBHOOK_SECRET:
        return web.Response(status=403)

    try:
        update = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return web.Response(status=400)
    if not isinstance(update, dict):
        return web.Response(status=400)

    try:
        identity = get_update_identity(update)
    except ValueError:
        return web.Response(status=400)
    if identity is None:
        return web.Response(status=200)

    async with session_factory() as session:
        registered = await ProcessedUpdateRepository(session).register(
            update_key=identity.key,
            update_type=identity.update_type,
        )
    if not registered:
        return web.Response(status=200)

    request.app[BACKGROUND_TASKS_KEY].schedule(
        request.app[UPDATE_PROCESSOR_KEY].process(update, identity)
    )

    return web.Response(status=200)


def create_app(
    bot: MaxBot,
    dispatcher: Dispatcher,
) -> web.Application:
    app = web.Application()
    app[BACKGROUND_TASKS_KEY] = BackgroundTaskRegistry()
    app[UPDATE_PROCESSOR_KEY] = MaxUpdateProcessor(bot, dispatcher)
    app.on_cleanup.append(close_background_tasks)
    app.on_cleanup.append(close_ai_client)
    app.on_cleanup.append(close_database)
    app.router.add_post("/max-helper/webhook", webhook_handler)
    return app


async def main() -> None:
    configure_logging()
    configure_ai_client()

    bot = MaxBot(MAX_BOT_TOKEN)
    await bot.start()

    dispatcher = Dispatcher()
    dispatcher.include_routers(*ROUTERS)

    app = create_app(bot, dispatcher)
    runner = web.AppRunner(app)

    try:
        await runner.setup()
        site = web.TCPSite(
            runner,
            host="0.0.0.0",
            port=8080,
        )
        await site.start()
        print("webhook server started")
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
