from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message

from app.logging_config import get_logger

logger = get_logger(__name__)


async def safe_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    try:
        return await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        error = str(exc).lower()
        if "message is not modified" in error:
            return message
        try:
            return await message.answer(text, reply_markup=reply_markup)
        except TelegramAPIError:
            logger.exception("Failed to send fallback message")
            return message


async def safe_edit_caption(
    message: Message,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    try:
        return await message.edit_caption(caption=caption, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        error = str(exc).lower()
        if "message is not modified" in error:
            return message
        try:
            return await message.answer(caption, reply_markup=reply_markup)
        except TelegramAPIError:
            logger.exception("Failed to send fallback caption")
            return message


async def delete_safe(bot: Bot, chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramAPIError:
        pass


async def send_media_group_safe(bot: Bot, chat_id: int, file_ids: list[str]) -> None:
    if not file_ids:
        return
    media = [InputMediaPhoto(media=file_id) for file_id in file_ids[:10]]
    try:
        await bot.send_media_group(chat_id=chat_id, media=media)
    except TelegramAPIError as exc:
        logger.warning("Failed to send media group: %s", exc)


async def send_photo_or_text(
    bot: Bot,
    chat_id: int,
    *,
    file_id: str | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    if file_id:
        try:
            return await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=text,
                reply_markup=reply_markup,
            )
        except TelegramAPIError:
            logger.warning("Failed to send photo card, falling back to text")
    return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
