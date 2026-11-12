from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.i18n import language_selected, t
from app.keyboards.common import language_kb


class LanguageGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("user")
        if user is None or language_selected(user):
            return await handler(event, data)

        if isinstance(event, Message):
            command = (event.text or "").split(maxsplit=1)[0].split("@", 1)[0]
            if command == "/start":
                return await handler(event, data)
            await event.answer(t("language.title"), reply_markup=language_kb())
            return None

        if isinstance(event, CallbackQuery):
            callback_data = event.data or ""
            if callback_data.startswith(("lang:set:", "settings:lang:")):
                return await handler(event, data)
            await event.answer()
            if event.message is not None:
                await event.message.answer(t("language.title"), reply_markup=language_kb())
            return None

        return await handler(event, data)
