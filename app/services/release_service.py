from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_CEILING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import quantize_money
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import (
    Dispute,
    DisputeStatus,
    HourlyRelease,
    Order,
    OrderStatus,
    Transaction,
    TransactionType,
)
from app.services.commission_service import split_hourly_amount
from app.services.user_service import get_platform_balance, get_seller_balance
from app.utils import ensure_utc, now_utc

logger = get_logger(__name__)

RELEASABLE_STATUSES = (OrderStatus.PAID.value, OrderStatus.DELIVERED.value)


def releaseable_hours(elapsed_seconds: float, interval_seconds: int, rate: Decimal) -> int:
    if rate <= 0 or interval_seconds <= 0 or elapsed_seconds <= 0:
        return 0
    elapsed_hours = int(elapsed_seconds // interval_seconds)
    maximum_hours = int((Decimal("100") / rate).to_integral_value(rounding=ROUND_CEILING))
    return max(0, min(elapsed_hours, maximum_hours))


async def hourly_released_total(session: AsyncSession, order_id: int) -> Decimal:
    value = await session.scalar(
        select(func.coalesce(func.sum(HourlyRelease.amount), 0)).where(
            HourlyRelease.order_id == order_id
        )
    )
    return quantize_money(Decimal(str(value or 0)))


async def hourly_share_totals(session: AsyncSession, order_id: int) -> tuple[Decimal, Decimal]:
    seller_total, platform_total = (
        await session.execute(
            select(
                func.coalesce(func.sum(HourlyRelease.seller_amount), 0),
                func.coalesce(func.sum(HourlyRelease.platform_amount), 0),
            ).where(HourlyRelease.order_id == order_id)
        )
    ).one()
    return (
        quantize_money(Decimal(str(seller_total or 0))),
        quantize_money(Decimal(str(platform_total or 0))),
    )


async def released_hour_numbers(session: AsyncSession, order_id: int) -> set[int]:
    result = await session.scalars(
        select(HourlyRelease.hour_number).where(HourlyRelease.order_id == order_id)
    )
    return set(result.all())


async def process_order_releases(
    session: AsyncSession,
    order_id: int,
    *,
    reference_time: datetime | None = None,
) -> Decimal:
    """Release the configured hourly percentage and split it 50/50.

    The function is idempotent: hourly_releases has a unique (order_id, hour_number)
    constraint and every transaction uses a deterministic reference.
    """

    settings = get_settings()
    reference_time = ensure_utc(reference_time) or now_utc()

    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None or order.paid_at is None or order.status not in RELEASABLE_STATUSES:
        return Decimal("0")

    dispute = await session.scalar(select(Dispute).where(Dispute.order_id == order.id))
    if dispute is not None and dispute.status in (
        DisputeStatus.OPEN.value,
        DisputeStatus.SELLER_RESPONDED.value,
        DisputeStatus.UNRESOLVED.value,
        DisputeStatus.RESOLVED.value,
    ):
        return Decimal("0")

    paid_at = ensure_utc(order.paid_at)
    elapsed_seconds = max(0.0, (reference_time - paid_at).total_seconds())
    eligible_hours = releaseable_hours(
        elapsed_seconds, settings.hourly_release_interval_seconds, Decimal(settings.hourly_release_rate)
    )
    if eligible_hours <= 0:
        return Decimal("0")

    existing_hours = await released_hour_numbers(session, order.id)
    released_total = await hourly_released_total(session, order.id)
    per_hour = quantize_money(
        Decimal(order.seller_amount) * Decimal(settings.hourly_release_rate) / Decimal("100")
    )
    if per_hour <= 0:
        return Decimal("0")

    balance = await get_seller_balance(session, order.seller_id)
    platform_balance = await get_platform_balance(session, for_update=True)
    released_now = Decimal("0")

    for hour_number in range(1, eligible_hours + 1):
        if hour_number in existing_hours:
            continue
        remaining = quantize_money(Decimal(order.seller_amount) - released_total)
        if remaining <= 0:
            break
        amount = quantize_money(min(per_hour, remaining))
        if amount <= 0:
            break

        seller_share, platform_share = split_hourly_amount(amount)
        reference = f"hourly:{order.id}:{hour_number}"
        platform_reference = f"hourly-platform:{order.id}:{hour_number}"
        session.add(
            HourlyRelease(
                order_id=order.id,
                hour_number=hour_number,
                amount=amount,
                seller_amount=seller_share,
                platform_amount=platform_share,
                reference=reference,
            )
        )
        balance.pending = max(Decimal("0"), quantize_money(Decimal(balance.pending) - amount))
        balance.available = quantize_money(Decimal(balance.available) + seller_share)
        balance.total_released = quantize_money(Decimal(balance.total_released) + seller_share)
        balance.total_earned = quantize_money(Decimal(balance.total_earned) + seller_share)
        platform_balance.available = quantize_money(
            Decimal(platform_balance.available) + platform_share
        )
        platform_balance.total_earned = quantize_money(
            Decimal(platform_balance.total_earned) + platform_share
        )
        session.add(
            Transaction(
                order_id=order.id,
                user_id=order.seller_id,
                type=TransactionType.HOURLY_RELEASE.value,
                amount=seller_share,
                balance_after=balance.available,
                reference=reference,
                description=f"Hourly seller share #{hour_number}",
            )
        )
        if platform_share > 0:
            session.add(
                Transaction(
                    order_id=order.id,
                    user_id=None,
                    type=TransactionType.PLATFORM_HOURLY_SHARE.value,
                    amount=platform_share,
                    balance_after=platform_balance.available,
                    reference=platform_reference,
                    description=f"Hourly platform owner share #{hour_number}",
                )
            )
        released_total = quantize_money(released_total + amount)
        released_now = quantize_money(released_now + amount)

    await session.flush()
    if released_now > 0:
        logger.info("Hourly release order=%s amount=%s", order.id, released_now)
    return released_now


async def process_all_hourly_releases() -> None:
    """Scheduler entrypoint. Uses one transaction per order to isolate failures."""

    async with SessionLocal() as session:
        order_ids = list(
            (
                await session.scalars(
                    select(Order.id).where(
                        Order.status.in_(RELEASABLE_STATUSES), Order.paid_at.is_not(None)
                    )
                )
            ).all()
        )

    for order_id in order_ids:
        try:
            async with SessionLocal() as session:
                released = await process_order_releases(session, order_id)
                await session.commit()
                if released > 0:
                    logger.info("Processed hourly release for order %s", order_id)
        except Exception:  # noqa: BLE001
            logger.exception("Hourly release failed for order %s", order_id)
