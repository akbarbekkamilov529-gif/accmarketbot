from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import quantize_money
from app.models import (
    ACTIVE_ORDER_STATUSES,
    Account,
    AccountStatus,
    HourlyRelease,
    Order,
    OrderStatus,
    Review,
    Transaction,
    User,
)
from app.services.user_service import get_buyer_balance, get_seller_balance

PURCHASE_HISTORY_STATUSES: tuple[str, ...] = (
    OrderStatus.PAID.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.COMPLETED.value,
    OrderStatus.DISPUTED.value,
    OrderStatus.UNRESOLVED.value,
)

RATING_QUANT = Decimal("0.1")


def _money(value: Decimal | None) -> Decimal:
    return quantize_money(value or Decimal("0"))


@dataclass(slots=True)
class BalanceSummary:
    seller_available: Decimal
    seller_pending: Decimal
    seller_total_released: Decimal
    seller_total_earned: Decimal
    buyer_available: Decimal
    buyer_held: Decimal
    buyer_total_spent: Decimal

    @property
    def available_total(self) -> Decimal:
        return _money(self.seller_available + self.buyer_available)

    @property
    def pending_total(self) -> Decimal:
        return _money(self.seller_pending + self.buyer_held)


@dataclass(slots=True)
class ProfileStats:
    balance: BalanceSummary
    sold_count: int
    bought_count: int
    sales_volume: Decimal
    purchases_volume: Decimal
    commission_total: Decimal
    net_earned: Decimal
    total_trade: Decimal
    active_listings: int
    pending_trades: int
    rating: Decimal | None
    review_count: int
    registered_at: datetime | None


async def get_balances(session: AsyncSession, user_id: int) -> BalanceSummary:
    seller_balance = await get_seller_balance(session, user_id, create=False)
    buyer_balance = await get_buyer_balance(session, user_id, create=False)
    return BalanceSummary(
        seller_available=_money(seller_balance.available if seller_balance else None),
        seller_pending=_money(seller_balance.pending if seller_balance else None),
        seller_total_released=_money(seller_balance.total_released if seller_balance else None),
        seller_total_earned=_money(seller_balance.total_earned if seller_balance else None),
        buyer_available=_money(buyer_balance.available if buyer_balance else None),
        buyer_held=_money(buyer_balance.held if buyer_balance else None),
        buyer_total_spent=_money(buyer_balance.total_spent if buyer_balance else None),
    )


async def _scalar_int(session: AsyncSession, stmt) -> int:
    return int(await session.scalar(stmt) or 0)


async def _scalar_money(session: AsyncSession, stmt) -> Decimal:
    return _money(await session.scalar(stmt))


async def get_profile_stats(session: AsyncSession, user: User) -> ProfileStats:
    balance = await get_balances(session, user.id)

    sold_count = await _scalar_int(
        session,
        select(func.count(Order.id)).where(
            Order.seller_id == user.id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )
    bought_count = await _scalar_int(
        session,
        select(func.count(Order.id)).where(
            Order.buyer_id == user.id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )
    sales_volume = await _scalar_money(
        session,
        select(func.sum(Order.amount)).where(
            Order.seller_id == user.id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )
    purchases_volume = await _scalar_money(
        session,
        select(func.sum(Order.amount)).where(
            Order.buyer_id == user.id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )
    legacy_commission_total = await _scalar_money(
        session,
        select(func.sum(Order.commission_amount)).where(
            Order.seller_id == user.id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )
    platform_hourly_total = await _scalar_money(
        session,
        select(func.sum(HourlyRelease.platform_amount))
        .join(Order, Order.id == HourlyRelease.order_id)
        .where(
            Order.seller_id == user.id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )
    commission_total = _money(legacy_commission_total + platform_hourly_total)
    seller_amount_total = await _scalar_money(
        session,
        select(func.sum(Order.seller_amount)).where(
            Order.seller_id == user.id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )
    net_earned = _money(seller_amount_total - platform_hourly_total)
    total_trade = await _scalar_money(
        session,
        select(func.sum(Order.amount)).where(
            Order.status == OrderStatus.COMPLETED.value,
            or_(Order.buyer_id == user.id, Order.seller_id == user.id),
        ),
    )
    active_listings = await _scalar_int(
        session,
        select(func.count(Account.id)).where(
            Account.seller_id == user.id,
            Account.status == AccountStatus.ACTIVE.value,
        ),
    )
    pending_trades = await _scalar_int(
        session,
        select(func.count(Order.id)).where(
            or_(Order.buyer_id == user.id, Order.seller_id == user.id),
            Order.status.in_(ACTIVE_ORDER_STATUSES),
        ),
    )

    rating_row = (
        await session.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(Review.seller_id == user.id)
        )
    ).one()
    rating_value, review_count = rating_row
    rating = (
        Decimal(str(rating_value)).quantize(RATING_QUANT, rounding=ROUND_HALF_UP)
        if rating_value is not None
        else None
    )

    return ProfileStats(
        balance=balance,
        sold_count=sold_count,
        bought_count=bought_count,
        sales_volume=sales_volume,
        purchases_volume=purchases_volume,
        commission_total=commission_total,
        net_earned=net_earned,
        total_trade=total_trade,
        active_listings=active_listings,
        pending_trades=pending_trades,
        rating=rating,
        review_count=int(review_count or 0),
        registered_at=user.created_at,
    )


def _order_list_query():
    return select(Order).options(selectinload(Order.account))


async def count_sold_orders(session: AsyncSession, seller_id: int) -> int:
    return await _scalar_int(
        session,
        select(func.count(Order.id)).where(
            Order.seller_id == seller_id,
            Order.status == OrderStatus.COMPLETED.value,
        ),
    )


async def list_sold_orders(
    session: AsyncSession, seller_id: int, *, offset: int, limit: int
) -> list[Order]:
    stmt = (
        _order_list_query()
        .where(Order.seller_id == seller_id, Order.status == OrderStatus.COMPLETED.value)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.scalars(stmt)
    return list(result.unique().all())


async def count_bought_orders(session: AsyncSession, buyer_id: int) -> int:
    return await _scalar_int(
        session,
        select(func.count(Order.id)).where(
            Order.buyer_id == buyer_id,
            Order.status.in_(PURCHASE_HISTORY_STATUSES),
        ),
    )


async def list_bought_orders(
    session: AsyncSession, buyer_id: int, *, offset: int, limit: int
) -> list[Order]:
    stmt = (
        _order_list_query()
        .where(Order.buyer_id == buyer_id, Order.status.in_(PURCHASE_HISTORY_STATUSES))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.scalars(stmt)
    return list(result.unique().all())


async def count_transactions(session: AsyncSession, user_id: int) -> int:
    return await _scalar_int(
        session,
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id),
    )


async def list_transactions(
    session: AsyncSession, user_id: int, *, offset: int, limit: int
) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.scalars(stmt)
    return list(result.all())
