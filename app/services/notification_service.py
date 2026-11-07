from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models import Notification, User

logger = get_logger(__name__)


async def notify(
    session: AsyncSession,
    bot: Bot | None,
    user: User,
    text: str,
    *,
    notification_type: str = "info",
    payload: dict[str, Any] | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
    protect_content: bool = False,
) -> Notification:
    notification = Notification(
        user_id=user.id,
        type=notification_type,
        text=text,
        payload=payload,
    )
    session.add(notification)
    await session.flush()

    if bot is not None:
        try:
            message = await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                reply_markup=reply_markup,
                protect_content=protect_content,
            )
            notification.telegram_message_id = message.message_id
        except TelegramAPIError as exc:
            logger.warning("Notification delivery failed for user %s: %s", user.id, exc)
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected notification error for user %s", user.id)
    return notification


async def notify_many(
    session: AsyncSession,
    bot: Bot | None,
    users: list[User],
    text: str,
    *,
    notification_type: str = "info",
    payload: dict[str, Any] | None = None,
) -> None:
    for user in users:
        await notify(
            session, bot, user, text, notification_type=notification_type, payload=payload
        )
