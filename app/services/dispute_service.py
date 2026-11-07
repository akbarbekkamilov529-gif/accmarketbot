from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models import (
    Dispute,
    DisputeMessage,
    DisputeStatus,
    MessageType,
    Order,
    OrderStatus,
    User,
)
from app.services.order_service import OrderError, OrderForbidden, OrderStateError
from app.utils import ensure_utc, now_utc


class DisputeError(Exception):
    pass


async def open_dispute(
    session: AsyncSession, order_id: int, buyer_id: int, reason: str
) -> Dispute:
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.buyer_id != buyer_id:
        raise OrderForbidden("Faqat xaridor nizo ochishi mumkin.")
    if order.status not in (OrderStatus.PAID.value, OrderStatus.DELIVERED.value):
        raise OrderStateError("Bu buyurtma uchun nizo ochib bo'lmaydi.")

    existing = await session.scalar(select(Dispute).where(Dispute.order_id == order.id))
    if existing is not None and existing.status in (
        DisputeStatus.OPEN.value,
        DisputeStatus.SELLER_RESPONDED.value,
        DisputeStatus.UNRESOLVED.value,
    ):
        return existing

    reason = reason.strip()
    if len(reason) < 5:
        raise DisputeError("Nizo sababini batafsil yozing (kamida 5 belgi).")

    order.status = OrderStatus.DISPUTED.value
    order.dispute_opened_at = now_utc()
    dispute = Dispute(
        order_id=order.id,
        opened_by=buyer_id,
        status=DisputeStatus.OPEN.value,
        reason=reason,
        auto_release_stopped=True,
        last_activity_at=now_utc(),
    )
    session.add(dispute)
    await session.flush()
    return dispute


async def get_dispute(session: AsyncSession, dispute_id: int) -> Dispute | None:
    return await session.scalar(
        select(Dispute)
        .options(selectinload(Dispute.messages))
        .where(Dispute.id == dispute_id)
    )


async def get_dispute_by_order(session: AsyncSession, order_id: int) -> Dispute | None:
    return await session.scalar(
        select(Dispute)
        .options(selectinload(Dispute.messages))
        .where(Dispute.order_id == order_id)
    )


async def add_message(
    session: AsyncSession,
    dispute_id: int,
    sender: User,
    *,
    message_type: str = MessageType.TEXT.value,
    content: str | None = None,
    file_id: str | None = None,
) -> DisputeMessage:
    dispute = await session.scalar(
        select(Dispute).where(Dispute.id == dispute_id).with_for_update()
    )
    if dispute is None:
        raise DisputeError("Nizo topilmadi.")
    order = await session.get(Order, dispute.order_id)
    if order is None:
        raise DisputeError("Buyurtma topilmadi.")
    if sender.id not in (order.buyer_id, order.seller_id):
        raise OrderForbidden("Siz bu nizoning ishtirokchisi emasiz.")
    if dispute.status in (DisputeStatus.CLOSED.value, DisputeStatus.RESOLVED.value):
        raise DisputeError("Bu nizo yopilgan.")

    if message_type == MessageType.TEXT.value and not (content or "").strip():
        raise DisputeError("Xabar bo'sh bo'lishi mumkin emas.")
    if message_type in (MessageType.PHOTO.value, MessageType.DOCUMENT.value) and not file_id:
        raise DisputeError("Fayl topilmadi.")

    message = DisputeMessage(
        dispute_id=dispute.id,
        sender_id=sender.id,
        message_type=message_type,
        content=(content or "").strip() or None,
        file_id=file_id,
    )
    session.add(message)
    if sender.id == order.seller_id and dispute.status == DisputeStatus.OPEN.value:
        dispute.status = DisputeStatus.SELLER_RESPONDED.value
    dispute.last_activity_at = now_utc()
    await session.flush()
    return message


async def withdraw_dispute(session: AsyncSession, dispute_id: int, buyer_id: int) -> Dispute:
    dispute = await session.scalar(
        select(Dispute).where(Dispute.id == dispute_id).with_for_update()
    )
    if dispute is None:
        raise DisputeError("Nizo topilmadi.")
    order = await session.get(Order, dispute.order_id)
    if order is None:
        raise DisputeError("Buyurtma topilmadi.")
    if order.buyer_id != buyer_id:
        raise OrderForbidden("Faqat xaridor nizoni bekor qilishi mumkin.")
    if dispute.status not in (DisputeStatus.OPEN.value, DisputeStatus.SELLER_RESPONDED.value):
        raise DisputeError("Bu nizoni bekor qilib bo'lmaydi.")

    dispute.status = DisputeStatus.CLOSED.value
    dispute.auto_release_stopped = False
    dispute.resolved_at = now_utc()
    dispute.resolution_note = "Buyer withdrew the dispute"
    if order.status == OrderStatus.DISPUTED.value:
        order.status = (
            OrderStatus.DELIVERED.value if order.delivered_at else OrderStatus.PAID.value
        )
    await session.flush()
    return dispute


async def mark_stale_disputes_unresolved(session: AsyncSession) -> int:
    settings = get_settings()
    cutoff = now_utc() - timedelta(hours=settings.dispute_auto_unresolved_hours)
    disputes = list(
        (
            await session.scalars(
                select(Dispute).where(
                    Dispute.status.in_(
                        [DisputeStatus.OPEN.value, DisputeStatus.SELLER_RESPONDED.value]
                    )
                )
            )
        ).all()
    )
    updated = 0
    for dispute in disputes:
        last = ensure_utc(dispute.last_activity_at)
        if last is not None and last < cutoff:
            dispute.status = DisputeStatus.UNRESOLVED.value
            dispute.last_activity_at = now_utc()
            order = await session.get(Order, dispute.order_id)
            if order is not None and order.status == OrderStatus.DISPUTED.value:
                order.status = OrderStatus.UNRESOLVED.value
            updated += 1
    if updated:
        await session.flush()
    return updated
