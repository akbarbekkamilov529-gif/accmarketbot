from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import normalize_locale, t
from app.models import Order, OrderStatus


def order_actions_kb(order: Order, *, for_seller: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if for_seller and order.status == OrderStatus.PAID.value:
        builder.button(text="📤 Akkauntni topshirdim", callback_data=f"order:deliver:{order.id}")

    if not for_seller and order.status in (OrderStatus.PAID.value, OrderStatus.DELIVERED.value):
        builder.button(text="🔐 Login ma'lumotlarini ko'rish", callback_data=f"order:creds:{order.id}")
        builder.button(text="✅ Akkauntni tasdiqlash", callback_data=f"order:confirm:{order.id}")
        builder.button(text="⚠️ Nizo ochish", callback_data=f"dispute:open:{order.id}")

    if order.status == OrderStatus.COMPLETED.value:
        builder.button(text="⭐ Baho berish", callback_data=f"review:start:{order.id}")

    if order.status == OrderStatus.DISPUTED.value and order.dispute is not None:
        builder.button(text="💬 Nizoni ko'rish", callback_data=f"dispute:view:{order.dispute.id}")

    if order.status == OrderStatus.PENDING_PAYMENT.value and not for_seller:
        builder.button(text="❌ Buyurtmani bekor qilish", callback_data=f"order:cancel:{order.id}")

    builder.button(text="⬅️ Orqaga", callback_data="orders:list")
    builder.adjust(1)
    return builder.as_markup()


def orders_root_kb(locale: str | None = None) -> InlineKeyboardMarkup:
    locale = normalize_locale(locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=t("orders.buyer", locale), callback_data="orders:mine:buyer:0")
    builder.button(text=t("orders.seller", locale), callback_data="orders:mine:seller:0")
    builder.button(text=t("common.home", locale), callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()


def orders_page_kb(
    kind: str, *, page: int, has_next: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="⬅️ Oldingi", callback_data=f"orders:mine:{kind}:{page - 1}")
    if has_next:
        builder.button(text="Keyingi ➡️", callback_data=f"orders:mine:{kind}:{page + 1}")
    builder.button(text="⬅️ Orqaga", callback_data="orders:list")
    builder.adjust(2, 1)
    return builder.as_markup()
