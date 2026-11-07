from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.constants import quantize_money
from app.models import Account, AccountStatus, Order, OrderStatus, User
from app.services import account_service
from app.services.user_service import get_buyer_balance, get_seller_balance
from app.utils import new_public_id, now_utc


class OrderError(Exception):
    pass


class AccountNotAvailable(OrderError):
    pass


class OrderForbidden(OrderError):
    pass


class OrderStateError(OrderError):
    pass


def order_query():
    return (
        select(Order)
        .options(
            selectinload(Order.account).selectinload(Account.images),
            selectinload(Order.account).selectinload(Account.credentials),
            selectinload(Order.account).selectinload(Account.credential_fields),
            selectinload(Order.buyer),
            selectinload(Order.seller),
            selectinload(Order.dispute),
        )
    )


async def get_order(session: AsyncSession, order_id: int) -> Order | None:
    return await session.scalar(order_query().where(Order.id == order_id))


async def get_order_for_update(session: AsyncSession, order_id: int) -> Order | None:
    return await session.scalar(order_query().where(Order.id == order_id).with_for_update())


async def create_order(session: AsyncSession, buyer: User, account_id: int) -> Order:
    settings = get_settings()
    account = await session.get(Account, account_id)
    if account is None or account.status == AccountStatus.DELETED.value:
        raise AccountNotAvailable("Akkaunt topilmadi.")
    if account.seller_id == buyer.id:
        raise OrderForbidden("O'z akkauntingizni sotib ololmaysiz.")
    if account.status != AccountStatus.ACTIVE.value:
        raise AccountNotAvailable("Akkaunt hozir sotuvda mavjud emas.")

    reserved = await account_service.reserve_account(session, account.id)
    if not reserved:
        raise AccountNotAvailable("Akkaunt boshqa xaridor tomonidan band qilindi.")

    amount = quantize_money(Decimal(account.price))
    rate = Decimal(settings.platform_commission_rate)
    commission = quantize_money(amount * rate / Decimal("100"))
    seller_amount = quantize_money(amount - commission)

    order = Order(
        public_id=new_public_id(),
        account_id=account.id,
        buyer_id=buyer.id,
        seller_id=account.seller_id,
        amount=amount,
        commission_amount=commission,
        seller_amount=seller_amount,
        currency=account.currency or settings.currency,
        status=OrderStatus.PENDING_PAYMENT.value,
    )
    session.add(order)
    await session.flush()

    await get_seller_balance(session, account.seller_id)
    await get_buyer_balance(session, buyer.id)
    return order


async def get_active_order_for_account(session: AsyncSession, account_id: int) -> Order | None:
    return await session.scalar(
        order_query()
        .where(
            Order.account_id == account_id,
            Order.status.in_(
                [
                    OrderStatus.PENDING_PAYMENT.value,
                    OrderStatus.PAID.value,
                    OrderStatus.DELIVERED.value,
                    OrderStatus.DISPUTED.value,
                    OrderStatus.UNRESOLVED.value,
                ]
            ),
        )
        .order_by(Order.id.desc())
    )


async def cancel_order(session: AsyncSession, order_id: int, buyer_id: int) -> Order:
    order = await get_order_for_update(session, order_id)
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.buyer_id != buyer_id:
        raise OrderForbidden("Bu buyurtma sizga tegishli emas.")
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise OrderStateError("Faqat to'lov kutilayotgan buyurtmani bekor qilish mumkin.")
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = now_utc()
    await account_service.release_reservation(session, order.account_id)
    await session.flush()
    return order


async def cancel_expired_pending_orders(session: AsyncSession, older_than_minutes: int) -> int:
    from datetime import timedelta

    from app.utils import ensure_utc

    cutoff = now_utc() - timedelta(minutes=older_than_minutes)
    orders = list(
        (
            await session.scalars(
                select(Order).where(
                    Order.status == OrderStatus.PENDING_PAYMENT.value,
                    Order.created_at < cutoff,
                )
            )
        ).all()
    )
    cancelled = 0
    for order in orders:
        if ensure_utc(order.created_at) and ensure_utc(order.created_at) > cutoff:
            continue
        order.status = OrderStatus.CANCELLED.value
        order.cancelled_at = now_utc()
        await account_service.release_reservation(session, order.account_id)
        cancelled += 1
    if cancelled:
        await session.flush()
    return cancelled


async def mark_delivered(session: AsyncSession, order_id: int, seller_id: int) -> Order:
    order = await get_order_for_update(session, order_id)
    if order is None:
        raise OrderError("Buyurtma topilmadi.")
    if order.seller_id != seller_id:
        raise OrderForbidden("Bu buyurtma sizga tegishli emas.")
    if order.status not in (OrderStatus.PAID.value,):
        raise OrderStateError("Buyurtma holati topshirish uchun mos emas.")
    order.status = OrderStatus.DELIVERED.value
    order.delivered_at = now_utc()
    await session.flush()
    return order


async def count_orders(session: AsyncSession, *, buyer_id: int | None = None, seller_id: int | None = None) -> int:
    stmt = select(func.count(Order.id))
    if buyer_id is not None:
        stmt = stmt.where(Order.buyer_id == buyer_id)
    if seller_id is not None:
        stmt = stmt.where(Order.seller_id == seller_id)
    return int(await session.scalar(stmt) or 0)


async def list_orders(
    session: AsyncSession,
    *,
    buyer_id: int | None = None,
    seller_id: int | None = None,
    offset: int = 0,
    limit: int = 10,
) -> list[Order]:
    stmt = order_query()
    if buyer_id is not None:
        stmt = stmt.where(Order.buyer_id == buyer_id)
    if seller_id is not None:
        stmt = stmt.where(Order.seller_id == seller_id)
    stmt = stmt.order_by(Order.created_at.desc(), Order.id.desc()).offset(offset).limit(limit)
    result = await session.scalars(stmt)
    return list(result.unique().all())
