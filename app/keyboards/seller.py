from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.constants import (
    GAME_PLATFORMS,
    SOCIAL_PLATFORMS,
    format_money,
    platform_display,
)
from app.i18n import normalize_locale, t
from app.models import Account, AccountStatus
from app.utils import esc

MAX_BUTTON_LABEL = 60


def _truncate_button(text: str, limit: int = MAX_BUTTON_LABEL) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def seller_platforms_kb(locale: str | None = None) -> InlineKeyboardMarkup:
    locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    for platform in GAME_PLATFORMS + SOCIAL_PLATFORMS:
        builder.button(
            text=f"{platform.emoji} {platform.name}",
            callback_data=f"seller:platform:{platform.key}",
        )
    builder.button(text=t("menu.listings", locale), callback_data="seller:myaccounts")
    builder.button(text=t("common.home", locale), callback_data="menu:home")
    total = len(GAME_PLATFORMS) + len(SOCIAL_PLATFORMS)
    builder.adjust(*([2] * ((total + 1) // 2)), 1, 1)
    return builder.as_markup()


def screenshots_kb(count: int, max_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ Tayyor ({count}/{max_count})", callback_data="seller:shots:done")
    builder.button(text="❌ Bekor qilish", callback_data="ui:cancel")
    builder.adjust(1)
    return builder.as_markup()


def extra_fields_menu_kb(field_count: int, max_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if field_count < max_count:
        builder.button(text="➕ Add — yangi maydon", callback_data="seller:field:add")
    builder.button(text="✅ Tayyor", callback_data="seller:field:done")
    builder.button(text="❌ Bekor qilish", callback_data="ui:cancel")
    builder.adjust(1)
    return builder.as_markup()


def preview_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit", callback_data="seller:preview:edit")
    builder.button(text="✅ Tasdiqlash", callback_data="seller:preview:confirm")
    builder.button(text="❌ Bekor qilish", callback_data="seller:preview:cancel")
    builder.adjust(1)
    return builder.as_markup()


def edit_menu_kb(fields: list[dict[str, str]], image_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🖼 Screenshotlar", callback_data="seller:editf:images")
    labels = {
        "nickname": "🔤 Nickname",
        "description": "📝 Description",
        "login": "🔐 Login",
        "password": "🔑 Asosiy parol",
        "price": "💵 Narx",
        "additional_info": "📎 Qo'shimcha ma'lumot",
    }
    for key, label in labels.items():
        builder.button(text=label, callback_data=f"seller:editf:{key}")
    for index, item in enumerate(fields):
        builder.button(
            text=_truncate_button(f"✏️ {item.get('label', 'Maydon')}"),
            callback_data=f"seller:editfield:{index}",
        )
    builder.button(text="➕ Maydon qo'shish", callback_data="seller:field:add")
    builder.button(text="⬅️ Preview", callback_data="seller:preview:back")
    builder.button(text="❌ Bekor qilish", callback_data="ui:cancel")
    builder.adjust(2, 2, 2, 1, 1, 1)
    return builder.as_markup()


def warning_kb(locale: str | None = None) -> InlineKeyboardMarkup:
    locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=t("seller.warning_yes", locale), callback_data="seller:warning:yes")
    builder.button(text=t("seller.warning_no", locale), callback_data="seller:warning:back")
    builder.adjust(1)
    return builder.as_markup()


def seller_accounts_menu_kb(locale: str | None = None) -> InlineKeyboardMarkup:
    locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=t("listings.active", locale), callback_data="seller:list:active:0")
    builder.button(text=t("listings.pending", locale), callback_data="seller:list:pending:0")
    builder.button(text=t("listings.sold", locale), callback_data="seller:list:sold:0")
    builder.button(text=t("listings.all", locale), callback_data="seller:list:all:0")
    builder.button(text=t("listings.new", locale), callback_data="seller:new")
    builder.button(text=t("common.home", locale), callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()


def seller_list_kb(
    accounts: list[Account],
    *,
    page: int,
    has_next: bool,
    flt: str,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for account in accounts:
        status_marks = {
            AccountStatus.ACTIVE.value: "🟢",
            AccountStatus.RESERVED.value: "🟡",
            AccountStatus.SOLD.value: "✅",
        }
        mark = status_marks.get(account.status, "⚪️")
        text = _truncate_button(
            f"{mark} {platform_display(account.platform)} · {account.nickname} · "
            f"{format_money(account.price, account.currency)}"
        )
        builder.button(text=text, callback_data=f"seller:acc:view:{account.id}")
    if page > 0:
        builder.button(text="⬅️ Oldingi", callback_data=f"seller:list:{flt}:{page - 1}")
    if has_next:
        builder.button(text="Keyingi ➡️", callback_data=f"seller:list:{flt}:{page + 1}")
    builder.button(text="⬅️ Orqaga", callback_data="seller:myaccounts")
    builder.adjust(1)
    return builder.as_markup()


def seller_account_detail_kb(account: Account) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if account.status == AccountStatus.ACTIVE.value:
        builder.button(text="✏️ E'lonni tahrirlash", callback_data=f"seller:acc:edit:{account.id}")
        builder.button(text="🗑 E'lonni o'chirish", callback_data=f"seller:acc:del:{account.id}")
    if account.status == AccountStatus.RESERVED.value:
        builder.button(text="🟡 Band qilingan", callback_data="noop")
    if account.status == AccountStatus.SOLD.value:
        builder.button(text="✅ Sotilgan", callback_data="noop")
    builder.button(text="⬅️ Orqaga", callback_data=f"seller:list:all:0")
    builder.adjust(1)
    return builder.as_markup()


def seller_edit_fields_kb(account: Account) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    fields = {
        "nickname": "🔤 Nickname",
        "description": "📝 Description",
        "login": "🔐 Login",
        "password": "🔑 Asosiy parol",
        "price": "💵 Narx",
        "additional_info": "📎 Qo'shimcha ma'lumot",
        "images": "🖼 Screenshotlar",
        "addfield": "➕ Maydon qo'shish",
    }
    for key, label in fields.items():
        builder.button(text=label, callback_data=f"seller:acc:editfield:{account.id}:{key}")
    for field in account.credential_fields:
        builder.button(
            text=_truncate_button(f"✏️ {field.label}"),
            callback_data=f"seller:acc:editcf:{account.id}:{field.id}",
        )
        builder.button(
            text="🗑",
            callback_data=f"seller:acc:delfield:{account.id}:{field.id}",
        )
    builder.button(text="⬅️ Orqaga", callback_data=f"seller:acc:view:{account.id}")
    builder.adjust(1)
    return builder.as_markup()


def account_delete_confirm_kb(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Ha, o'chirish", callback_data=f"seller:acc:delconfirm:{account_id}")
    builder.button(text="⬅️ Orqaga", callback_data=f"seller:acc:view:{account_id}")
    builder.adjust(1)
    return builder.as_markup()


def existing_field_value_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="ui:cancel")
    return builder.as_markup()


def buyer_noop_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Orqaga", callback_data="menu:buyer")
    return builder.as_markup()


def seller_extra_info_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ O'tkazib yuborish", callback_data="seller:additional:skip")
    builder.button(text="❌ Bekor qilish", callback_data="ui:cancel")
    builder.adjust(1)
    return builder.as_markup()
