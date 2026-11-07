from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus, Review


class ReviewError(Exception):
    pass


async def create_review(
    session: AsyncSession,
    *,
    order_id: int,
    buyer_id: int,
    rating: int,
    comment: str | None,
) -> Review:
    if rating < 1 or rating > 5:
        raise ReviewError("Baho 1 dan 5 gacha bo'lishi kerak.")
    order = await session.get(Order, order_id)
    if order is None:
        raise ReviewError("Buyurtma topilmadi.")
    if order.buyer_id != buyer_id:
        raise ReviewError("Bu buyurtma sizga tegishli emas.")
    if order.status != OrderStatus.COMPLETED.value:
        raise ReviewError("Faqat yakunlangan buyurtmaga baho berish mumkin.")

    existing = await session.scalar(select(Review).where(Review.order_id == order.id))
    if existing is not None:
        return existing

    review = Review(
        order_id=order.id,
        account_id=order.account_id,
        buyer_id=buyer_id,
        seller_id=order.seller_id,
        rating=rating,
        comment=(comment or "").strip()[:2000] or None,
    )
    session.add(review)
    await session.flush()
    return review
