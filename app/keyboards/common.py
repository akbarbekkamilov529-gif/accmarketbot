from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Buyer — akkaunt sotib olish", callback_data="menu:buyer")
    builder.button(text="💰 Seller — akkaunt sotish", callback_data="menu:seller")
    builder.adjust(1)
    return builder.as_markup()


def back_home_kb(text: str = "🏠 Bosh menyu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data="menu:home")
    return builder.as_markup()


def cancel_kb(text: str = "❌ Bekor qilish") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data="ui:cancel")
    builder.button(text="🏠 Bosh menyu", callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()
