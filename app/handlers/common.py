from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router(name="common")


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer("⏳ Bu amal hozircha mavjud emas.", show_alert=False)
