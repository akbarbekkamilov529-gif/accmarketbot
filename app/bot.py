from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, CallbackQuery, ErrorEvent, Message

from app.config import Settings
from app.crypto import get_cipher
from app.database import dispose_engine, engine
from app.handlers import common, disputes, fallback, orders, profile, reviews, seller, buyer
from app.logging_config import get_logger, setup_logging
from app.middlewares import (
    DatabaseMiddleware,
    LanguageGateMiddleware,
    RateLimitMiddleware,
    UserMiddleware,
)
from app.models import Base
from app.scheduler import start_scheduler, stop_scheduler

logger = get_logger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start", description="Bosh menyu"),
    BotCommand(command="help", description="Yordam"),
]


async def build_storage(settings: Settings) -> BaseStorage:
    if settings.redis_url:
        from aiogram.fsm.storage.redis import RedisStorage

        logger.info("Using Redis FSM storage")
        return RedisStorage.from_url(settings.redis_url)
    logger.info("Using in-memory FSM storage")
    return MemoryStorage()


def build_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, protect_content=False),
    )


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(common.router)
    dp.include_router(profile.router)
    dp.include_router(seller.router)
    dp.include_router(buyer.router)
    dp.include_router(orders.router)
    dp.include_router(disputes.router)
    dp.include_router(reviews.router)
    dp.include_router(fallback.router)


def register_middlewares(dp: Dispatcher, settings: Settings) -> None:
    for observer in (dp.message, dp.callback_query):
        observer.middleware(DatabaseMiddleware())
        observer.middleware(UserMiddleware())
        observer.middleware(RateLimitMiddleware(settings.rate_limit_per_minute))
        observer.middleware(LanguageGateMiddleware())


def register_lifecycle(dp: Dispatcher, settings: Settings) -> None:
    @dp.startup()
    async def on_startup(bot: Bot) -> None:
        # Validate the encryption key early so credentials are never stored in plaintext.
        get_cipher()
        if settings.auto_create_tables:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created from metadata")
        start_scheduler()
        try:
            await bot.set_my_commands(BOT_COMMANDS)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to set bot commands")
        logger.info("Bot startup complete")

    @dp.shutdown()
    async def on_shutdown(bot: Bot) -> None:
        stop_scheduler()
        await dispose_engine()
        logger.info("Bot shutdown complete")


def register_error_handler(dp: Dispatcher) -> None:
    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        logger.exception("Unhandled handler error: %s", event.exception)
        update = event.update
        try:
            if update.callback_query is not None:
                await update.callback_query.answer(
                    "❌ Kutilmagan xatolik. Qayta urinib ko'ring.", show_alert=True
                )
            elif update.message is not None:
                await update.message.answer(
                    "❌ Kutilmagan xatolik yuz berdi. Iltimos, /start orqali qayta boshlang."
                )
        except Exception:  # noqa: BLE001
            pass
        return True


async def create_dispatcher(settings: Settings) -> Dispatcher:
    setup_logging(settings)
    storage = await build_storage(settings)
    dp = Dispatcher(storage=storage)
    register_middlewares(dp, settings)
    register_routers(dp)
    register_lifecycle(dp, settings)
    register_error_handler(dp)
    return dp
