from __future__ import annotations

from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.logging_config import get_logger
from app.services import dispute_service, order_service, release_service

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_hourly_releases() -> None:
    try:
        await release_service.process_all_hourly_releases()
    except Exception:  # noqa: BLE001
        logger.exception("Scheduler job failed: hourly releases")


async def _cancel_expired_orders() -> None:
    settings = get_settings()
    try:
        async with SessionLocal() as session:
            cancelled = await order_service.cancel_expired_pending_orders(
                session, settings.pending_order_ttl_minutes
            )
            await session.commit()
            if cancelled:
                logger.info("Cancelled %s expired pending orders", cancelled)
    except Exception:  # noqa: BLE001
        logger.exception("Scheduler job failed: expired orders")


async def _mark_stale_disputes() -> None:
    try:
        async with SessionLocal() as session:
            updated = await dispute_service.mark_stale_disputes_unresolved(session)
            await session.commit()
            if updated:
                logger.info("Marked %s stale disputes as unresolved", updated)
    except Exception:  # noqa: BLE001
        logger.exception("Scheduler job failed: stale disputes")


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone=timezone.utc)
    scheduler.add_job(
        _run_hourly_releases,
        trigger="interval",
        seconds=settings.hourly_release_interval_seconds,
        id="hourly_releases",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        jitter=30,
    )
    scheduler.add_job(
        _cancel_expired_orders,
        trigger="interval",
        minutes=10,
        id="expire_pending_orders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _mark_stale_disputes,
        trigger="interval",
        hours=1,
        id="stale_disputes",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started")
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None
