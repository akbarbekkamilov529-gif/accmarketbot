from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models import Dispute, DisputeStatus, Order


def dispute_message_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Nizoga qaytish", callback_data="dispute:back")
    builder.adjust(1)
    return builder.as_markup()


def dispute_kb(dispute: Dispute, order: Order, *, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    active = dispute.status in (
        DisputeStatus.OPEN.value,
        DisputeStatus.SELLER_RESPONDED.value,
    )
    if active:
        builder.button(text="💬 Xabar yuborish", callback_data=f"dispute:msg:{dispute.id}")
        builder.button(text="📎 Dalil yuborish", callback_data=f"dispute:evidence:{dispute.id}")
        if order.buyer_id == user_id:
            builder.button(
                text="✅ Nizoni bekor qilish", callback_data=f"dispute:withdraw:{dispute.id}"
            )
    builder.button(text="⬅️ Buyurtmaga qaytish", callback_data=f"order:view:{order.id}")
    builder.adjust(1)
    return builder.as_markup()
