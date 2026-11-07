from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.helpers import safe_edit
from app.keyboards.buyer import review_comment_kb, review_rating_kb
from app.models import OrderStatus, User
from app.services import notification_service, order_service, review_service
from app.services.review_service import ReviewError
from app.states import BuyerStates
from app.utils import esc

router = Router(name="reviews")


@router.callback_query(F.data.startswith("review:start:"))
async def review_start(
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
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    if order.status != OrderStatus.COMPLETED.value:
        await callback.answer("Faqat yakunlangan buyurtmaga baho beriladi.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(BuyerStates.review_rating)
    await state.update_data({"review_order_id": order.id})
    await safe_edit(
        callback.message,
        "⭐ <b>Xizmatni baholang</b>\n\nSeller qanday ishladi?",
        review_rating_kb(order.id),
    )


@router.callback_query(StateFilter(BuyerStates.review_rating), F.data.startswith("review:rate:"))
async def review_rate(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return
    try:
        order_id = int(parts[2])
        rating = int(parts[3])
    except ValueError:
        await callback.answer("Noto'g'ri baho.", show_alert=True)
        return
    if not (1 <= rating <= 5):
        await callback.answer("Baho 1-5 oralig'ida bo'lishi kerak.", show_alert=True)
        return
    order = await order_service.get_order(session, order_id)
    if order is None or order.buyer_id != user.id:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.update_data({"review_rating": rating})
    await state.set_state(BuyerStates.review_comment)
    await safe_edit(
        callback.message,
        f"⭐ Baho: <b>{rating}/5</b>\n\n"
        "Izoh qoldirmoqchimisiz? Yozing yoki <b>⏭ Izohsiz</b> tugmasini bosing.",
        review_comment_kb(order_id),
    )


async def _save_review(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
    *,
    comment: str | None,
) -> None:
    data = await state.get_data()
    order_id = data.get("review_order_id", 0)
    rating = data.get("review_rating", 0)
    try:
        review = await review_service.create_review(
            session,
            order_id=order_id,
            buyer_id=user.id,
            rating=int(rating),
            comment=comment,
        )
    except (ReviewError, ValueError) as exc:
        await message.answer(f"❌ {esc(str(exc))}")
        await state.clear()
        return

    order = await order_service.get_order(session, review.order_id)
    if order is not None:
        await notification_service.notify(
            session,
            bot,
            order.seller,
            f"⭐ <b>Yangi baho: {review.rating}/5</b>\n\n"
            f"📦 #{order.public_id}\n"
            + (f"💬 {esc(review.comment)}" if review.comment else ""),
            notification_type="review_received",
            payload={"review_id": review.id, "order_id": order.id},
        )
    await state.clear()
    await message.answer("🙏 Rahmat! Bahoyingiz qabul qilindi.")


@router.message(StateFilter(BuyerStates.review_comment), F.text)
async def review_comment(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    comment = (message.text or "").strip()
    if len(comment) > 2000:
        await message.answer("Izoh 2000 belgidan oshmasin.")
        return
    await _save_review(message, state, session, user, bot, comment=comment or None)


@router.callback_query(StateFilter(BuyerStates.review_comment), F.data.startswith("review:nocomment:"))
async def review_nocomment(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    await callback.answer()
    await _save_review(callback.message, state, session, user, bot, comment=None)


@router.callback_query(F.data.startswith("review:skip:"))
async def review_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await safe_edit(callback.message, "Baho berilmadi.", None)
