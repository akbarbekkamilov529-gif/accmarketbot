from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import quantize_money
from app.models import Order, OrderStatus, Transaction, TransactionType
from app.services import account_service, release_service
from app.services.order_service import (
    OrderError,
    OrderForbidden,
    OrderStateError,
)
from app.services.user_service import get_buyer_balance, get_seller_balance
from app.utils import now_utc


async def hold_funds(session: AsyncSession, order_id: int) -> Order:
    """Marks an order as paid and moves the seller share into escrow/pending."""

    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.paid_at is not None:
        return order
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise OrderStateError("Buyurtma to'lov uchun mos holatda emas.")

    order.status = OrderStatus.PAID.value
    order.paid_at = now_utc()

    seller_balance = await get_seller_balance(session, order.seller_id)
    buyer_balance = await get_buyer_balance(session, order.buyer_id)

    seller_balance.pending = quantize_money(
        Decimal(seller_balance.pending) + Decimal(order.seller_amount)
    )
    buyer_balance.held = quantize_money(Decimal(buyer_balance.held) + Decimal(order.amount))

    session.add(
        Transaction(
            order_id=order.id,
            user_id=order.buyer_id,
            type=TransactionType.PAYMENT.value,
            amount=order.amount,
            reference=f"payment:{order.id}",
            description="Buyer payment received into escrow",
        )
    )
    session.add(
        Transaction(
            order_id=order.id,
            user_id=order.seller_id,
            type=TransactionType.ESCROW_HOLD.value,
            amount=order.seller_amount,
            balance_after=seller_balance.pending,
            reference=f"escrow:{order.id}",
            description="Seller share held in escrow",
        )
    )
    session.add(
        Transaction(
            order_id=order.id,
            type=TransactionType.PLATFORM_COMMISSION.value,
            amount=order.commission_amount,
            reference=f"commission:{order.id}",
            description="Platform commission",
        )
    )
    await session.flush()
    return order


async def complete_order(session: AsyncSession, order_id: int, buyer_id: int) -> Order:
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.buyer_id != buyer_id:
        raise OrderForbidden("Bu buyurtma sizga tegishli emas.")
    if order.status == OrderStatus.COMPLETED.value:
        return order
    if order.status not in (OrderStatus.PAID.value, OrderStatus.DELIVERED.value):
        raise OrderStateError("Buyurtmani bu holatda yakunlab bo'lmaydi.")

    released = await release_service.hourly_released_total(session, order.id)
    remaining = quantize_money(Decimal(order.seller_amount) - released)
    if remaining < 0:
        remaining = Decimal("0")

    seller_balance = await get_seller_balance(session, order.seller_id)
    buyer_balance = await get_buyer_balance(session, order.buyer_id)

    seller_balance.pending = max(Decimal("0"), quantize_money(Decimal(seller_balance.pending) - remaining))
    seller_balance.available = quantize_money(Decimal(seller_balance.available) + remaining)
    seller_balance.total_released = quantize_money(Decimal(seller_balance.total_released) + remaining)
    seller_balance.total_earned = quantize_money(Decimal(seller_balance.total_earned) + Decimal(order.seller_amount))

    buyer_balance.held = max(Decimal("0"), quantize_money(Decimal(buyer_balance.held) - Decimal(order.amount)))
    buyer_balance.total_spent = quantize_money(Decimal(buyer_balance.total_spent) + Decimal(order.amount))

    if remaining > 0:
        session.add(
            Transaction(
                order_id=order.id,
                user_id=order.seller_id,
                type=TransactionType.COMPLETION_RELEASE.value,
                amount=remaining,
                balance_after=seller_balance.available,
                reference=f"complete:{order.id}",
                description="Remaining escrow released after buyer confirmation",
            )
        )

    order.status = OrderStatus.COMPLETED.value
    order.completed_at = now_utc()
    order.buyer_confirmed_at = now_utc()
    await account_service.mark_account_sold(session, order.account_id)
    await session.flush()
    return order


async def refund_order(session: AsyncSession, order_id: int) -> Order:
    """Internal refund support. Only valid for escaped-dispute or failed delivery flows."""

    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.status == OrderStatus.REFUNDED.value:
        return order
    if order.status not in (OrderStatus.PAID.value, OrderStatus.DELIVERED.value, OrderStatus.DISPUTED.value):
        raise OrderStateError("Bu buyurtmani qaytarish mumkin emas.")

    released = await release_service.hourly_released_total(session, order.id)
    refundable_seller_part = max(Decimal("0"), quantize_money(Decimal(order.seller_amount) - released))

    seller_balance = await get_seller_balance(session, order.seller_id)
    buyer_balance = await get_buyer_balance(session, order.buyer_id)
    seller_balance.pending = max(
        Decimal("0"), quantize_money(Decimal(seller_balance.pending) - refundable_seller_part)
    )
    buyer_balance.held = max(
        Decimal("0"), quantize_money(Decimal(buyer_balance.held) - Decimal(order.amount))
    )

    session.add(
        Transaction(
            order_id=order.id,
            user_id=order.buyer_id,
            type=TransactionType.REFUND.value,
            amount=order.amount,
            reference=f"refund:{order.id}",
            description="Order refunded",
        )
    )
    order.status = OrderStatus.REFUNDED.value
    await account_service.release_reservation(session, order.account_id)
    await session.flush()
    return order
