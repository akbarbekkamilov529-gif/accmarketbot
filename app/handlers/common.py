from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import get_settings
from app.keyboards import main_menu_kb
from app.models import User
from app.utils import esc

router = Router(name="common")

START_TEXT = (
    "👋 <b>Salom, {name}!</b>\n\n"
    "<b>Account Marketplace</b> botiga xush kelibsiz.\n\n"
    "Bu yerda siz:\n"
    "🛍 <b>Buyer</b> — tayyor akkauntlarni sotib olishingiz\n"
    "💰 <b>Seller</b> — o'z akkauntingizni xavfsiz sotishingiz mumkin.\n\n"
    "Ikkala funksiyadan ham bir vaqtda foydalanishingiz mumkin.\n\n"
    "👇 Kerakli bo'limni tanlang:"
)


def start_text(user: User) -> str:
    name = user.first_name or user.username or "foydalanuvchi"
    return START_TEXT.format(name=esc(name))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    await message.answer(start_text(user), reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext, user: User) -> None:
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "🛍 <b>Buyer</b> — platformani tanlab, akkaunt kartasini oching va sotib oling.\n"
        "💰 <b>Seller</b> — platformani tanlab, akkaunt ma'lumotlarini yuboring.\n"
        "📦 <b>Buyurtmalarim</b> — xarid va sotuvlaringiz holatini kuzating.\n\n"
        "⚠️ Parollar faqat shifrlangan holda saqlanadi va faqat xaridorga "
        "to'lovdan keyin ko'rsatiladi.\n\n"
        "Bot administrator panelisiz, to'liq avtomatik ishlaydi."
    )
    support = get_settings().support_contact.strip()
    if support:
        text += f"\n\n📞 <b>Qo'llab-quvvatlash:</b> {esc(support)}"
    await message.answer(text, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(start_text(user), reply_markup=main_menu_kb())
    except Exception:  # noqa: BLE001
        await callback.message.answer(start_text(user), reply_markup=main_menu_kb())


@router.callback_query(F.data == "ui:cancel")
async def ui_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await callback.answer()
    await state.clear()
    text = "❌ Jarayon bekor qilindi.\n\n" + start_text(user)
    try:
        await callback.message.edit_text(text, reply_markup=main_menu_kb())
    except Exception:  # noqa: BLE001
        await callback.message.answer(text, reply_markup=main_menu_kb())


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer("⏳ Bu amal hozircha mavjud emas.", show_alert=False)
