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
from app.services.user_service import get_seller_balance
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
    """Release the configured hourly percentage of the seller share.

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

        reference = f"hourly:{order.id}:{hour_number}"
        session.add(
            HourlyRelease(
                order_id=order.id,
                hour_number=hour_number,
                amount=amount,
                reference=reference,
            )
        )
        balance.pending = max(Decimal("0"), quantize_money(Decimal(balance.pending) - amount))
        balance.available = quantize_money(Decimal(balance.available) + amount)
        balance.total_released = quantize_money(Decimal(balance.total_released) + amount)
        session.add(
            Transaction(
                order_id=order.id,
                user_id=order.seller_id,
                type=TransactionType.HOURLY_RELEASE.value,
                amount=amount,
                balance_after=balance.available,
                reference=reference,
                description=f"Hourly escrow release #{hour_number}",
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
