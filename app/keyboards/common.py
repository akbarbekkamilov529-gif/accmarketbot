from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import LOCALE_LABELS, SUPPORTED_LOCALES, menu_texts, normalize_locale, t


def main_menu_kb(locale: str | None = None) -> ReplyKeyboardMarkup:
    locale = normalize_locale(locale)
    texts = menu_texts(locale)
    rows = [
        [texts["profile"], texts["balance"]],
        [texts["buyer"], texts["seller"]],
        [texts["orders"], texts["listings"]],
        [texts["sold"], texts["bought"]],
        [texts["stats"], texts["settings"]],
        [texts["help"], texts["home"]],
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text) for text in row] for row in rows],
        resize_keyboard=True,
        is_persistent=True,
    )


def main_menu_inline_kb(locale: str | None = None) -> InlineKeyboardMarkup:
    locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=t("menu.profile", locale), callback_data="menu:home")
    builder.button(text=t("menu.buyer", locale), callback_data="menu:buyer")
    builder.button(text=t("menu.seller", locale), callback_data="menu:seller")
    builder.adjust(1)
    return builder.as_markup()


def settings_kb(locale: str | None = None) -> InlineKeyboardMarkup:
    locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    for code in SUPPORTED_LOCALES:
        label = LOCALE_LABELS[code]
        if code == locale:
            label = f"✅ {label}"
        builder.button(text=label, callback_data=f"settings:lang:{code}")
    builder.button(text=t("settings.refresh_profile", locale), callback_data="settings:refresh")
    builder.button(text=t("common.home", locale), callback_data="menu:home")
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
