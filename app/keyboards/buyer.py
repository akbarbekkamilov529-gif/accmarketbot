from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import (
    ALL_PLATFORMS,
    SORT_NEWEST,
    SORT_PRICE_ASC,
    SORT_PRICE_DESC,
    format_money,
    platform_display,
)
from app.i18n import normalize_locale, t
from app.models import Account
from app.utils import esc

MAX_BUTTON_LABEL = 60


def _truncate_button(text: str, limit: int = MAX_BUTTON_LABEL) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def buyer_platforms_kb(locale: str | None = None) -> InlineKeyboardMarkup:
    locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    for platform in ALL_PLATFORMS:
        builder.button(
            text=f"{platform.emoji} {platform.name}",
            callback_data=f"buyer:platform:{platform.key}",
        )
    builder.button(text=t("menu.orders", locale), callback_data="orders:list")
    builder.button(text=t("common.home", locale), callback_data="menu:home")
    total = len(ALL_PLATFORMS)
    builder.adjust(*([2] * ((total + 1) // 2)), 1, 1)
    return builder.as_markup()


def buyer_list_nav_kb(
    platform: str,
    *,
    page: int,
    sort: str,
    has_next: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="⬅️ Oldingi", callback_data=f"buyer:list:{platform}:{page - 1}:{sort}")
    if has_next:
        builder.button(text="Keyingi ➡️", callback_data=f"buyer:list:{platform}:{page + 1}:{sort}")
    builder.button(text="🆕 Eng yangi", callback_data=f"buyer:list:{platform}:0:{SORT_NEWEST}")
    builder.button(text="💸 Eng arzon", callback_data=f"buyer:list:{platform}:0:{SORT_PRICE_ASC}")
    builder.button(
        text="💎 Eng qimmat", callback_data=f"buyer:list:{platform}:0:{SORT_PRICE_DESC}"
    )
    builder.button(text="⬅️ Platformalar", callback_data="menu:buyer")
    builder.adjust(2, 1, 2, 1)
    return builder.as_markup()


def buyer_account_detail_kb(account: Account) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Sotib olish", callback_data=f"buyer:buy:{account.id}")
    builder.button(
        text="⬅️ Orqaga",
        callback_data=f"buyer:list:{account.platform}:0:{SORT_NEWEST}",
    )
    builder.adjust(1)
    return builder.as_markup()


def purchase_warning_kb(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Davom etish", callback_data=f"buyer:continue:{account_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"buyer:view:{account_id}")
    builder.adjust(1)
    return builder.as_markup()


def purchase_actions_kb(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ SKIP PAYMENT", callback_data=f"buyer:skip:{account_id}")
    builder.button(text="❌ Bekor qilish", callback_data=f"buyer:view:{account_id}")
    builder.adjust(1)
    return builder.as_markup()


def review_rating_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for stars in range(1, 6):
        builder.button(text="⭐" * stars, callback_data=f"review:rate:{order_id}:{stars}")
    builder.button(text="⏭ O'tkazib yuborish", callback_data=f"review:skip:{order_id}")
    builder.adjust(5, 1)
    return builder.as_markup()


def review_comment_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Izohsiz", callback_data=f"review:nocomment:{order_id}")
    builder.adjust(1)
    return builder.as_markup()
