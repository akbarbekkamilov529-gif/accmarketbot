from __future__ import annotations

import asyncio
import signal

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.bot import build_bot, create_dispatcher
from app.config import get_settings
from app.database import dispose_engine
from app.logging_config import get_logger, setup_logging


async def _health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def run_webhook(bot: Bot, dp: Dispatcher, settings) -> None:
    app = web.Application()
    app.router.add_get("/health", _health)

    secret_token = settings.webhook_secret or None
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret_token,
    ).register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, host=settings.host, port=settings.port)
        await site.start()

        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=secret_token,
            drop_pending_updates=settings.webhook_drop_pending,
            allowed_updates=dp.resolve_used_update_types(),
        )

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except (NotImplementedError, RuntimeError):
                pass

        logger.info("Webhook server started on %s:%s", settings.host, settings.port)
        await stop_event.wait()
    finally:
        await runner.cleanup()


logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings)
    if not settings.bot_token:
        raise SystemExit(
            "BOT_TOKEN is not set. Copy .env.example to .env and fill in BOT_TOKEN."
        )

    bot = build_bot(settings)
    dp = await create_dispatcher(settings)
    try:
        if settings.use_webhook:
            await run_webhook(bot, dp, settings)
        else:
            await run_polling(bot, dp)
    finally:
        try:
            await bot.session.close()
        except Exception:  # noqa: BLE001
            pass
        await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
