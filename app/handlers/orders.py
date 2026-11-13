from __future__ import annotations

from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import format_money, platform_display, quantize_money
from app.handlers.helpers import safe_edit
from app.i18n import t, user_locale
from app.keyboards.buyer import review_rating_kb
from app.keyboards.orders import delivery_warning_kb, order_actions_kb, orders_root_kb
from app.models import Order, OrderStatus, User
from app.services import (
    account_service,
    escrow_service,
    notification_service,
    order_service,
    release_service,
)
from app.services.order_service import OrderError, OrderForbidden, OrderStateError
from app.states import SellerStates
from app.utils import esc, format_datetime, truncate

router = Router(name="orders")

ORDER_STATUS_LABELS = {
    OrderStatus.PENDING_PAYMENT.value: "🟡 To'lov kutilmoqda",
    OrderStatus.PAID.value: "🔵 To'langan (escrow)",
    OrderStatus.DELIVERED.value: "📤 Seller topshirdi",
    OrderStatus.COMPLETED.value: "✅ Yakunlangan",
    OrderStatus.DISPUTED.value: "⚠️ Nizoda",
    OrderStatus.CANCELLED.value: "❌ Bekor qilindi",
    OrderStatus.REFUNDED.value: "↩️ Qaytarildi",
    OrderStatus.UNRESOLVED.value: "🕓 Hal qilinmagan",
}

CREDENTIAL_ALLOWED_STATUSES = {
    OrderStatus.PAID.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.DISPUTED.value,
    OrderStatus.UNRESOLVED.value,
    OrderStatus.COMPLETED.value,
}


def order_status_label(status: str) -> str:
    return ORDER_STATUS_LABELS.get(status, status)


def order_detail_text(order: Order, user: User) -> str:
    role = "Buyer" if order.buyer_id == user.id else "Seller"
    locale = user_locale(user)
    account = order.account
    lines = [
        f"📦 <b>Buyurtma #{order.public_id}</b>",
        "",
        f"📌 <b>Holat:</b> {order_status_label(order.status)}",
        f"👤 <b>Sizning rolingiz:</b> {role}",
        "",
        f"🎮 <b>Platforma:</b> {platform_display(account.platform)}",
        f"🔤 <b>Akkaunt:</b> {esc(account.nickname)}",
    ]
    if account.description:
        lines.append(f"📝 {esc(truncate(account.description, 200))}")
    lines.extend(
        [
            "",
            f"💵 <b>Summa:</b> {format_money(order.amount, order.currency)}",
            t(
                "order.seller_share",
                locale,
                amount=format_money(order.seller_amount, order.currency),
            ),
            t("order.hourly_split", locale),
            "",
            f"🕐 <b>Yaratilgan:</b> {format_datetime(order.created_at)}",
        ]
    )
    if order.paid_at:
        lines.append(f"💳 <b>To'langan:</b> {format_datetime(order.paid_at)}")
    if order.delivered_at:
        lines.append(f"📤 <b>Topshirilgan:</b> {format_datetime(order.delivered_at)}")
    if order.completed_at:
        lines.append(f"✅ <b>Yakunlangan:</b> {format_datetime(order.completed_at)}")
    if order.status == OrderStatus.DISPUTED.value and order.dispute is not None:
        lines.append(f"⚠️ <b>Nizo sababi:</b> {esc(truncate(order.dispute.reason, 200))}")
    return "\n".join(lines)


async def _refresh_order_view(
    callback: CallbackQuery, session: AsyncSession, user: User, order_id: int
) -> None:
    order = await order_service.get_order(session, order_id)
    if order is None or user.id not in (order.buyer_id, order.seller_id):
        await callback.message.answer("Buyurtma topilmadi.")
        return
    await safe_edit(
        callback.message,
        order_detail_text(order, user),
        order_actions_kb(order, for_seller=order.seller_id == user.id),
    )


@router.callback_query(F.data == "orders:list")
async def orders_root(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    await callback.answer()
    await state.clear()
    locale = user_locale(user)
    await safe_edit(
        callback.message,
        t("section.orders", locale),
        orders_root_kb(locale),
    )


@router.callback_query(F.data.startswith("orders:mine:"))
async def orders_mine(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return
    _, _, kind, page_raw = parts
    if kind not in {"buyer", "seller"}:
        await callback.answer("Noto'g'ri bo'lim.", show_alert=True)
        return
    try:
        page = max(0, int(page_raw))
    except ValueError:
        page = 0
    await callback.answer()
    await state.clear()
    settings = get_settings()
    page_size = settings.page_size
    offset = page * page_size
    if kind == "buyer":
        total = await order_service.count_orders(session, buyer_id=user.id)
        orders = await order_service.list_orders(
            session, buyer_id=user.id, offset=offset, limit=page_size
        )
        title = "🛍 Xaridlarim"
    else:
        total = await order_service.count_orders(session, seller_id=user.id)
        orders = await order_service.list_orders(
            session, seller_id=user.id, offset=offset, limit=page_size
        )
        title = "💰 Sotuvlarim"

    max_page = max(0, (total - 1) // page_size) if total else 0
    if total == 0:
        text = f"{title}\n\n📭 Buyurtmalar yo'q."
    else:
        text = (
            f"{title}\n\nJami: <b>{total}</b> ta\n"
            f"Sahifa: <b>{page + 1}/{max_page + 1}</b>\n\nBuyurtmani tanlang:"
        )

    builder = InlineKeyboardBuilder()
    for order in orders:
        account_name = order.account.nickname if order.account else "—"
        builder.button(
            text=f"{order_status_label(order.status)} · {order.public_id} · {truncate(account_name, 25)}",
            callback_data=f"order:view:{order.id}",
        )
    if page > 0:
        builder.button(text="⬅️ Oldingi", callback_data=f"orders:mine:{kind}:{page - 1}")
    if offset + len(orders) < total:
        builder.button(text="Keyingi ➡️", callback_data=f"orders:mine:{kind}:{page + 1}")
    builder.button(text="⬅️ Orqaga", callback_data="orders:list")
    builder.adjust(1)
    await safe_edit(callback.message, text, builder.as_markup())


@router.callback_query(F.data.startswith("order:view:"))
async def order_view(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        order_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, order_id)
    if order is None or user.id not in (order.buyer_id, order.seller_id):
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await safe_edit(
        callback.message,
        order_detail_text(order, user),
        order_actions_kb(order, for_seller=order.seller_id == user.id),
    )


@router.callback_query(F.data.startswith("order:creds:"))
async def order_credentials(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        order_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, order_id)
    if order is None:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    if order.buyer_id != user.id:
        await callback.answer("Bu ma'lumotlar faqat xaridorga ko'rsatiladi.", show_alert=True)
        return
    if order.status not in CREDENTIAL_ALLOWED_STATUSES:
        await callback.answer("Ma'lumotlar hali ochilmagan.", show_alert=True)
        return
    await callback.answer()

    login, password, fields = await account_service.decrypt_credentials(order.account)
    lines = [
        "🔐 <b>AKKAUNT MAXFIY MA'LUMOTLARI</b>",
        "",
        f"🔤 <b>Nickname:</b> {esc(order.account.nickname)}",
        f"🎮 <b>Platforma:</b> {platform_display(order.account.platform)}",
        "",
        f"👤 <b>Login:</b> <code>{esc(login)}</code>",
        f"🔑 <b>Asosiy parol:</b> <code>{esc(password)}</code>",
    ]
    if fields:
        lines.append("")
        lines.append("<b>Qo'shimcha maydonlar:</b>")
        for label, value in fields:
            lines.append(f"• <b>{esc(label)}:</b> <code>{esc(value)}</code>")
    lines.extend(
        [
            "",
            "⚠️ Bu ma'lumotlarni hech kimga bermang. Akkauntga qayta kirmang.",
        ]
    )
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="\n".join(lines),
        protect_content=True,
    )


@router.callback_query(F.data.startswith("order:confirm:"))
async def order_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        order_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, order_id)
    if order is None:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    released_total = await release_service.hourly_released_total(session, order.id)
    remaining = max(
        Decimal("0"),
        quantize_money(Decimal(order.seller_amount) - released_total),
    )
    try:
        order = await escrow_service.complete_order(session, order.id, user.id)
    except OrderForbidden as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except (OrderError, OrderStateError) as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    locale = user_locale(user)
    await callback.answer(t("order.completed_alert", locale))
    seller_locale = user_locale(order.seller)
    await notification_service.notify(
        session,
        bot,
        order.seller,
        t(
            "order.completed_notify",
            seller_locale,
            public_id=order.public_id,
            amount=format_money(remaining, order.currency),
        ),
        notification_type="order_completed",
        payload={"order_id": order.id},
    )
    await callback.message.answer(
        t("order.completed_body", locale),
        reply_markup=review_rating_kb(order.id),
    )


@router.callback_query(F.data.startswith("order:deliver:confirm:"))
async def order_deliver_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        order_id = int(callback.data.split(":", 3)[3])
    except (ValueError, IndexError):
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    data = await state.get_data()
    if (
        await state.get_state() != SellerStates.delivery_warning.state
        or data.get("delivery_order_id") != order_id
    ):
        await callback.answer("Sessiya eskirgan. Buyurtmani qaytadan oching.", show_alert=True)
        return
    try:
        order = await order_service.mark_delivered(session, order_id, user.id)
    except OrderForbidden as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except (OrderError, OrderStateError) as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await state.clear()
    locale = user_locale(user)
    await callback.answer(t("order.delivered_alert", locale))
    buyer_locale = user_locale(order.buyer)
    await notification_service.notify(
        session,
        bot,
        order.buyer,
        t(
            "order.delivered_notify",
            buyer_locale,
            public_id=order.public_id,
            nickname=esc(order.account.nickname),
        ),
        notification_type="order_delivered",
        payload={"order_id": order.id},
    )
    await _refresh_order_view(callback, session, user, order.id)


@router.callback_query(F.data.startswith("order:deliver:"))
async def order_deliver(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        order_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, order_id)
    if order is None or order.seller_id != user.id:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    if order.status != OrderStatus.PAID.value:
        await callback.answer("Buyurtma holati topshirish uchun mos emas.", show_alert=True)
        return
    await callback.answer()
    locale = user_locale(user)
    await state.set_state(SellerStates.delivery_warning)
    await state.update_data({"delivery_order_id": order.id})
    await safe_edit(
        callback.message,
        t("seller.delivery_warning", locale, public_id=order.public_id),
        delivery_warning_kb(order.id, locale),
    )


@router.callback_query(F.data.startswith("order:cancel:"))
async def order_cancel(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        order_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    try:
        order = await order_service.cancel_order(session, order_id, user.id)
    except OrderForbidden as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    except (OrderError, OrderStateError) as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("Buyurtma bekor qilindi.")
    await notification_service.notify(
        session,
        bot,
        order.seller,
        "ℹ️ <b>To'lov holati o'zgardi</b>\n\n"
        f"📦 #{order.public_id} buyurtmasi bekor qilindi.\n"
        "Akkaunt yana sotuvga qaytdi.",
        notification_type="order_cancelled",
        payload={"order_id": order.id},
    )
    await callback.message.answer(
        "❌ Buyurtma bekor qilindi. Akkaunt yana sotuvga qaytdi.",
        reply_markup=orders_root_kb(),
    )
