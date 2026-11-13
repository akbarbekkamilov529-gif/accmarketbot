from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import quantize_money
from app.models import (
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Transaction,
    TransactionType,
)
from app.services import account_service, release_service
from app.services.order_service import (
    OrderError,
    OrderForbidden,
    OrderStateError,
)
from app.services.user_service import (
    get_buyer_balance,
    get_platform_balance,
    get_seller_balance,
)
from app.utils import now_utc


async def hold_funds(session: AsyncSession, order_id: int) -> Order:
    """Marks an order as paid and moves the full seller amount into escrow/pending."""

    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.paid_at is not None:
        return order
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise OrderStateError("Buyurtma to'lov uchun mos holatda emas.")

    seller_amount = quantize_money(Decimal(order.amount))
    order.commission_amount = Decimal("0.00")
    order.seller_amount = seller_amount
    order.status = OrderStatus.PAID.value
    order.paid_at = now_utc()

    seller_balance = await get_seller_balance(session, order.seller_id)
    buyer_balance = await get_buyer_balance(session, order.buyer_id)

    seller_balance.pending = quantize_money(
        Decimal(seller_balance.pending) + seller_amount
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
            amount=seller_amount,
            balance_after=seller_balance.pending,
            reference=f"escrow:{order.id}",
            description="Seller share held in escrow",
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
    seller_balance.total_earned = quantize_money(Decimal(seller_balance.total_earned) + remaining)

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
    """Refund the buyer in full and reverse all accrued hourly shares.

    A refunded sale cannot leave the seller or the platform owner with
    earnings or escrow balance. This is the conservative consumer-law
    policy: the buyer receives the full amount paid, while already released
    hourly shares are clawed back from both balances.
    """

    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.status == OrderStatus.REFUNDED.value:
        return order
    if order.status not in (OrderStatus.PAID.value, OrderStatus.DELIVERED.value, OrderStatus.DISPUTED.value):
        raise OrderStateError("Bu buyurtmani qaytarish mumkin emas.")

    released = await release_service.hourly_released_total(session, order.id)
    seller_share, platform_share = await release_service.hourly_share_totals(
        session, order.id
    )
    refundable_seller_part = max(
        Decimal("0"), quantize_money(Decimal(order.seller_amount) - released)
    )

    seller_balance = await get_seller_balance(session, order.seller_id)
    buyer_balance = await get_buyer_balance(session, order.buyer_id)
    platform_balance = await get_platform_balance(session, for_update=True)

    seller_balance.pending = max(
        Decimal("0"), quantize_money(Decimal(seller_balance.pending) - refundable_seller_part)
    )
    seller_balance.available = max(
        Decimal("0"), quantize_money(Decimal(seller_balance.available) - seller_share)
    )
    seller_balance.total_released = max(
        Decimal("0"), quantize_money(Decimal(seller_balance.total_released) - seller_share)
    )
    seller_balance.total_earned = max(
        Decimal("0"), quantize_money(Decimal(seller_balance.total_earned) - seller_share)
    )
    platform_balance.available = max(
        Decimal("0"), quantize_money(Decimal(platform_balance.available) - platform_share)
    )
    platform_balance.total_earned = max(
        Decimal("0"), quantize_money(Decimal(platform_balance.total_earned) - platform_share)
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
    if seller_share > 0:
        session.add(
            Transaction(
                order_id=order.id,
                user_id=order.seller_id,
                type=TransactionType.HOURLY_REVERSAL.value,
                amount=-seller_share,
                balance_after=seller_balance.available,
                reference=f"hourly-reversal:{order.id}",
                description="Accrued seller hourly share reversed by refund",
            )
        )
    if platform_share > 0:
        session.add(
            Transaction(
                order_id=order.id,
                user_id=None,
                type=TransactionType.PLATFORM_HOURLY_REVERSAL.value,
                amount=-platform_share,
                balance_after=platform_balance.available,
                reference=f"hourly-platform-reversal:{order.id}",
                description="Accrued platform hourly share reversed by refund",
            )
        )

    payments = list(
        (
            await session.scalars(select(Payment).where(Payment.order_id == order.id))
        ).all()
    )
    for payment in payments:
        if payment.status == PaymentStatus.SUCCEEDED.value:
            payment.status = PaymentStatus.REFUNDED.value

    order.status = OrderStatus.REFUNDED.value
    await account_service.release_reservation(session, order.account_id)
    await session.flush()
    return order
