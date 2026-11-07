from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.helpers import safe_edit
from app.keyboards.common import cancel_kb
from app.keyboards.dispute import dispute_kb, dispute_message_cancel_kb
from app.models import (
    Dispute,
    DisputeStatus,
    MessageType,
    Order,
    OrderStatus,
    User,
)
from app.services import dispute_service, notification_service, order_service
from app.services.dispute_service import DisputeError
from app.services.order_service import OrderError, OrderForbidden, OrderStateError
from app.states import DisputeStates
from app.utils import esc, format_datetime, truncate

router = Router(name="disputes")

DISPUTE_STATUS_LABELS = {
    DisputeStatus.OPEN.value: "⚠️ Ochiq",
    DisputeStatus.SELLER_RESPONDED.value: "💬 Seller javob berdi",
    DisputeStatus.RESOLVED.value: "✅ Hal qilindi",
    DisputeStatus.UNRESOLVED.value: "🕓 Hal qilinmagan",
    DisputeStatus.CLOSED.value: "🔒 Yopildi",
}


def _dispute_text(dispute: Dispute, order: Order) -> str:
    lines = [
        f"⚠️ <b>Nizo #{dispute.id}</b>",
        "",
        f"📦 <b>Buyurtma:</b> #{order.public_id}",
        f"🔤 <b>Akkaunt:</b> {esc(order.account.nickname)}",
        f"📌 <b>Holat:</b> {DISPUTE_STATUS_LABELS.get(dispute.status, dispute.status)}",
        f"🕐 <b>Ochilgan:</b> {format_datetime(dispute.created_at)}",
        "",
        "📝 <b>Sabab:</b>",
        esc(truncate(dispute.reason, 800)),
    ]
    messages = list(dispute.messages)[-10:]
    if messages:
        lines.extend(["", "💬 <b>Xabarlar:</b>"])
        for msg in messages:
            sender = "Buyer" if msg.sender_id == order.buyer_id else "Seller"
            if msg.message_type == MessageType.TEXT.value:
                body = esc(truncate(msg.content or "", 300))
            elif msg.message_type == MessageType.PHOTO.value:
                body = "📸 [foto dalil]"
            else:
                body = "📎 [fayl dalil]"
            lines.append(f"<b>{sender}:</b> {body}")
    lines.extend(
        [
            "",
            "ℹ️ Nizo ochilganda avtomatik payout to'xtatiladi.",
            "Hech qanday tekshirilmagan AI qarori bilan pul qaytarilmaydi.",
        ]
    )
    return "\n".join(lines)


async def _send_dispute_view(
    message: Message,
    *,
    dispute_id: int,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    dispute = await dispute_service.get_dispute(session, dispute_id)
    if dispute is None:
        await message.answer("Nizo topilmadi.")
        return
    order = await order_service.get_order(session, dispute.order_id)
    if order is None or user.id not in (order.buyer_id, order.seller_id):
        await message.answer("Nizo topilmadi.")
        return
    await message.answer(
        _dispute_text(dispute, order),
        reply_markup=dispute_kb(dispute, order, user_id=user.id),
    )


@router.callback_query(F.data.startswith("dispute:open:"))
async def dispute_open(
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
    if order is None or order.buyer_id != user.id:
        await callback.answer("Faqat xaridor nizo ochishi mumkin.", show_alert=True)
        return
    if order.status not in (OrderStatus.PAID.value, OrderStatus.DELIVERED.value):
        await callback.answer("Bu buyurtma uchun nizo ochib bo'lmaydi.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(DisputeStates.reason)
    await state.update_data({"dispute_order_id": order.id})
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Buyurtmaga qaytish", callback_data=f"order:view:{order.id}")
    builder.adjust(1)
    await safe_edit(
        callback.message,
        "⚠️ <b>Nizo ochish</b>\n\n"
        "Muammoni batafsil yozing. Nima sodir bo'ldi?\n"
        "Seller akkauntni topshirmadimi, ma'lumotlar noto'g'rimi yoki boshqa muammo?\n\n"
        "Nizo ochilganda avtomatik payout to'xtatiladi.",
        builder.as_markup(),
    )


@router.message(StateFilter(DisputeStates.reason), F.text)
async def dispute_reason(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    reason = (message.text or "").strip()
    try:
        dispute = await dispute_service.open_dispute(
            session, data.get("dispute_order_id", 0), user.id, reason
        )
    except (DisputeError, OrderError, OrderForbidden, OrderStateError) as exc:
        await message.answer(f"❌ {esc(str(exc))}")
        return
    await state.clear()

    order = await order_service.get_order(session, dispute.order_id)
    if order is not None:
        builder = InlineKeyboardBuilder()
        builder.button(text="💬 Nizoni ko'rish", callback_data=f"dispute:view:{dispute.id}")
        builder.adjust(1)
        await notification_service.notify(
            session,
            bot,
            order.seller,
            "⚠️ <b>Xaridor nizo ochdi!</b>\n\n"
            f"📦 Buyurtma: #{order.public_id}\n"
            f"🔤 Akkaunt: {esc(order.account.nickname)}\n\n"
            f"Sabab: {esc(truncate(reason, 400))}\n\n"
            "Javob bering va dalillarni yuboring.",
            notification_type="dispute_opened",
            payload={"dispute_id": dispute.id, "order_id": order.id},
            reply_markup=builder.as_markup(),
        )
        await message.answer(
            "✅ Nizo ochildi. Avtomatik payout to'xtatildi.\n"
            "Seller javob berishi mumkin."
        )
        await _send_dispute_view(
            message, dispute_id=dispute.id, user=user, session=session, bot=bot
        )


@router.callback_query(F.data.startswith("dispute:view:"))
async def dispute_view(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        dispute_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    dispute = await dispute_service.get_dispute(session, dispute_id)
    if dispute is None:
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, dispute.order_id)
    if order is None or user.id not in (order.buyer_id, order.seller_id):
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    await callback.answer()
    await safe_edit(
        callback.message,
        _dispute_text(dispute, order),
        dispute_kb(dispute, order, user_id=user.id),
    )


@router.callback_query(F.data.startswith("dispute:msg:"))
async def dispute_message_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        dispute_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    dispute = await dispute_service.get_dispute(session, dispute_id)
    if dispute is None:
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, dispute.order_id)
    if order is None or user.id not in (order.buyer_id, order.seller_id):
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(DisputeStates.message)
    await state.update_data({"dispute_id": dispute.id})
    await safe_edit(
        callback.message,
        "💬 <b>Nizo bo'yicha xabar</b>\n\n"
        "Xabaringizni yozing yoki foto dalil yuboring.",
        dispute_message_cancel_kb(),
    )


@router.callback_query(F.data.startswith("dispute:evidence:"))
async def dispute_evidence_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        dispute_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    dispute = await dispute_service.get_dispute(session, dispute_id)
    if dispute is None:
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, dispute.order_id)
    if order is None or user.id not in (order.buyer_id, order.seller_id):
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(DisputeStates.evidence)
    await state.update_data({"dispute_id": dispute.id})
    await safe_edit(
        callback.message,
        "📎 <b>Dalil yuborish</b>\n\n"
        "Rasm yoki fayl (screenshot, chat, to'lov cheki) yuboring.",
        dispute_message_cancel_kb(),
    )


async def _save_dispute_message(
    message: Message,
    *,
    dispute_id: int,
    session: AsyncSession,
    user: User,
    bot: Bot,
    message_type: str,
    content: str | None,
    file_id: str | None,
) -> None:
    try:
        await dispute_service.add_message(
            session,
            dispute_id,
            user,
            message_type=message_type,
            content=content,
            file_id=file_id,
        )
    except (DisputeError, OrderForbidden) as exc:
        await message.answer(f"❌ {esc(str(exc))}")
        return

    dispute = await dispute_service.get_dispute(session, dispute_id)
    if dispute is None:
        return
    order = await order_service.get_order(session, dispute.order_id)
    if order is None:
        return
    other_id = order.seller_id if user.id == order.buyer_id else order.buyer_id
    other = order.seller if other_id == order.seller_id else order.buyer
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Nizoni ko'rish", callback_data=f"dispute:view:{dispute.id}")
    builder.adjust(1)
    await notification_service.notify(
        session,
        bot,
        other,
        "💬 <b>Nizo bo'yicha yangi xabar</b>\n\n"
        f"📦 #{order.public_id}\n"
        f"Yuboruvchi: {'Buyer' if user.id == order.buyer_id else 'Seller'}",
        notification_type="dispute_message",
        payload={"dispute_id": dispute.id, "order_id": order.id},
        reply_markup=builder.as_markup(),
    )
    await message.answer("✅ Xabar nizoga qo'shildi.")
    await _send_dispute_view(
        message, dispute_id=dispute.id, user=user, session=session, bot=bot
    )


@router.message(StateFilter(DisputeStates.message), F.text)
async def dispute_text_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    await _save_dispute_message(
        message,
        dispute_id=data.get("dispute_id", 0),
        session=session,
        user=user,
        bot=bot,
        message_type=MessageType.TEXT.value,
        content=message.text,
        file_id=None,
    )


@router.message(StateFilter(DisputeStates.message), F.photo)
async def dispute_photo_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    await _save_dispute_message(
        message,
        dispute_id=data.get("dispute_id", 0),
        session=session,
        user=user,
        bot=bot,
        message_type=MessageType.PHOTO.value,
        content=message.caption,
        file_id=message.photo[-1].file_id,
    )


@router.message(StateFilter(DisputeStates.evidence), F.photo)
async def dispute_evidence_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    await _save_dispute_message(
        message,
        dispute_id=data.get("dispute_id", 0),
        session=session,
        user=user,
        bot=bot,
        message_type=MessageType.PHOTO.value,
        content=message.caption,
        file_id=message.photo[-1].file_id,
    )


@router.message(StateFilter(DisputeStates.evidence), F.document)
async def dispute_evidence_document(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    document = message.document
    await _save_dispute_message(
        message,
        dispute_id=data.get("dispute_id", 0),
        session=session,
        user=user,
        bot=bot,
        message_type=MessageType.DOCUMENT.value,
        content=document.file_name if document else None,
        file_id=document.file_id if document else None,
    )


@router.callback_query(F.data == "dispute:back")
async def dispute_back(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    dispute_id = data.get("dispute_id")
    await callback.answer()
    if not dispute_id:
        await state.clear()
        await safe_edit(callback.message, "Nizo topilmadi.", None)
        return
    await _send_dispute_view(
        callback.message, dispute_id=dispute_id, user=user, session=session, bot=bot
    )


@router.callback_query(F.data.startswith("dispute:withdraw:"))
async def dispute_withdraw(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        dispute_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    dispute = await dispute_service.get_dispute(session, dispute_id)
    if dispute is None:
        await callback.answer("Nizo topilmadi.", show_alert=True)
        return
    order = await order_service.get_order(session, dispute.order_id)
    if order is None:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    try:
        await dispute_service.withdraw_dispute(session, dispute.id, user.id)
    except (DisputeError, OrderForbidden) as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("Nizo bekor qilindi.")
    await state.clear()
    await notification_service.notify(
        session,
        bot,
        order.seller,
        "ℹ️ <b>Nizo bekor qilindi</b>\n\n"
        f"📦 #{order.public_id}\n"
        "Xaridor nizoni qaytarib oldi. Avtomatik payout davom etadi.",
        notification_type="dispute_withdrawn",
        payload={"dispute_id": dispute.id, "order_id": order.id},
    )
    await callback.message.answer(
        "✅ Nizo bekor qilindi. Buyurtma avvalgi holatiga qaytdi.",
        reply_markup=dispute_kb(dispute, order, user_id=user.id),
    )
