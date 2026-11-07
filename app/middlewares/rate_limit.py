from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    """Simple in-process sliding-window rate limiter.

    For multi-instance deployments enable Redis and move this counter to Redis.
    """

    def __init__(self, limit_per_minute: int = 30) -> None:
        super().__init__()
        self.limit = max(1, limit_per_minute)
        self.window = 60.0
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._counter = 0

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        now = time.monotonic()
        limited = False
        async with self._lock:
            queue = self._events[tg_user.id]
            while queue and now - queue[0] > self.window:
                queue.popleft()
            if len(queue) >= self.limit:
                limited = True
            else:
                queue.append(now)
            self._counter += 1
            if self._counter % 5000 == 0:
                stale = [uid for uid, q in self._events.items() if not q or now - q[-1] > self.window]
                for uid in stale:
                    self._events.pop(uid, None)

        if limited:
            text = "⏳ Juda ko'p so'rov yubordingiz. Bir daqiqadan so'ng qayta urinib ko'ring."
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(text)
            except Exception:  # noqa: BLE001
                pass
            return None

        return await handler(event, data)
