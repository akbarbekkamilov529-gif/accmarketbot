from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

router = Router(name="fallback")


@router.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current:
        await message.answer(
            "Iltimos, jarayonni tugating yoki /start orqali bosh menyuga qayting."
        )
        return
    await message.answer("🏠 Bosh menyu uchun /start buyrug'ini bosing.")


@router.callback_query()
async def fallback_callback(callback: CallbackQuery) -> None:
    await callback.answer("Bu amal eskirgan yoki mavjud emas.", show_alert=False)
