from __future__ import annotations

import asyncio
import secrets
import signal

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from app.bot import build_bot, create_dispatcher
from app.config import Settings, get_settings
from app.database import dispose_engine
from app.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


async def _health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def _root(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "tg-account-marketplace-bot"})


def _register_common_routes(app: web.Application) -> None:
    app.router.add_get("/", _root)
    app.router.add_get("/health", _health)
    app.router.add_get("/healthz", _health)


def _resolve_webhook_secret(settings: Settings) -> str:
    if settings.webhook_secret:
        return settings.webhook_secret
    # Generated fallback keeps the bot deployable even if the operator forgot
    # to set WEBHOOK_SECRET. It still validates every incoming request.
    generated = secrets.token_urlsafe(32)
    logger.warning(
        "WEBHOOK_SECRET is not set. Generated an ephemeral secret; "
        "set WEBHOOK_SECRET in production to keep it stable across restarts."
    )
    return generated


async def _start_http_server(app: web.Application, settings: Settings) -> web.AppRunner:
    host = "0.0.0.0" if settings.is_render else settings.host
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=settings.port)
    await site.start()
    logger.info("HTTP server listening on %s:%s", host, settings.port)
    return runner


async def _set_webhook(
    bot: Bot, dp: Dispatcher, settings: Settings, secret_token: str
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            # setWebhook also terminates any active getUpdates session, so
            # polling and webhook delivery can never run at the same time.
            await bot.set_webhook(
                url=settings.webhook_url,
                secret_token=secret_token,
                drop_pending_updates=settings.webhook_drop_pending,
                allowed_updates=dp.resolve_used_update_types(),
            )
            logger.info("Telegram webhook registered: %s", settings.webhook_url)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            delay = min(2**attempt, 30)
            logger.exception(
                "Failed to set Telegram webhook (attempt %s/5), retrying in %ss",
                attempt,
                delay,
            )
            await asyncio.sleep(delay)
    raise RuntimeError("Unable to register Telegram webhook") from last_error


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError, ValueError):
            # Windows / restricted environments do not support signal handlers.
            pass


async def run_webhook(bot: Bot, dp: Dispatcher, settings: Settings) -> None:
    secret_token = _resolve_webhook_secret(settings)

    app = web.Application()
    _register_common_routes(app)
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret_token,
    ).register(app, path=settings.webhook_path)

    runner = await _start_http_server(app, settings)
    try:
        # Bind the port before any slow startup work (DB, Telegram API calls)
        # so Render's port scan always succeeds.
        await dp.emit_startup(bot=bot, dispatcher=dp, app=app)
        await _set_webhook(bot, dp, settings, secret_token)

        stop_event = asyncio.Event()
        _install_signal_handlers(stop_event)
        logger.info("Bot is running in webhook mode")
        await stop_event.wait()
    finally:
        try:
            await dp.emit_shutdown(bot=bot, dispatcher=dp, app=app)
        except Exception:  # noqa: BLE001
            logger.exception("Failed during dispatcher shutdown")
        await runner.cleanup()


async def run_polling(bot: Bot, dp: Dispatcher, settings: Settings) -> None:
    app = web.Application()
    _register_common_routes(app)
    runner = await _start_http_server(app, settings)
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            if not settings.polling_force:
                raise SystemExit(
                    "A Telegram webhook is already configured "
                    f"({webhook_info.url}). This is usually a running Render "
                    "deployment. Refusing to start polling so getUpdates and "
                    "webhook do not conflict. Stop the other service or set "
                    "POLLING_FORCE=true to replace the webhook."
                )
            logger.warning(
                "Replacing existing webhook %s because POLLING_FORCE=true",
                webhook_info.url,
            )
            # Remove the webhook before polling so getUpdates is the only method.
            await bot.delete_webhook(drop_pending_updates=settings.webhook_drop_pending)
        logger.info("Bot is running in long polling mode")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=True,
        )
    finally:
        await runner.cleanup()


async def main() -> None:
    settings = get_settings()
    setup_logging(settings)
    if not settings.bot_token:
        raise SystemExit(
            "BOT_TOKEN is not set. Copy .env.example to .env and fill in BOT_TOKEN."
        )

    logger.info(
        "Starting bot | environment=%s render=%s port=%s webhook=%s",
        settings.environment,
        settings.is_render,
        settings.port,
        settings.webhook_enabled,
    )

    bot = build_bot(settings)
    dp = await create_dispatcher(settings)
    use_webhook = settings.webhook_enabled and bool(settings.effective_webhook_base_url)

    if settings.webhook_enabled and not settings.effective_webhook_base_url:
        logger.warning(
            "Webhook mode was requested but neither WEBHOOK_BASE_URL nor "
            "RENDER_EXTERNAL_URL is available. Falling back to polling."
        )

    try:
        if use_webhook:
            await run_webhook(bot, dp, settings)
        else:
            await run_polling(bot, dp, settings)
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
