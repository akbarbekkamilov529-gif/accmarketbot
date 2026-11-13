from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.models import (
    OrderStatus,
    Payment,
    PaymentStatus,
    SellerBalance,
    Transaction,
)
from app.services import escrow_service, order_service
from app.services.commission_service import split_hourly_amount
from app.services.payment_service import PaymentService


def test_hourly_amount_is_split_evenly() -> None:
    seller_amount, platform_amount = split_hourly_amount(Decimal("5000.00"))

    assert seller_amount == Decimal("2500.00")
    assert platform_amount == Decimal("2500.00")
    assert seller_amount + platform_amount == Decimal("5000.00")


def test_hourly_split_rounding_never_loses_money() -> None:
    seller_amount, platform_amount = split_hourly_amount(Decimal("3333.33"))

    assert seller_amount == Decimal("1666.67")
    assert platform_amount == Decimal("1666.66")
    assert seller_amount + platform_amount == Decimal("3333.33")


def test_legacy_commission_is_disabled_by_default() -> None:
    settings = get_settings()
    assert settings.platform_commission_rate == Decimal("0")
    assert settings.hourly_release_rate == Decimal("5")


async def _pending_payment(session, order) -> Payment:
    payment = Payment(
        order_id=order.id,
        provider="payme",
        status=PaymentStatus.PENDING.value,
        amount=order.amount,
        currency=order.currency,
        idempotency_key=f"commission:{order.public_id}",
    )
    session.add(payment)
    await session.flush()
    return payment


async def _commission_tx_count(session, order_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.order_id == order_id,
                Transaction.type == "platform_commission",
            )
        )
        or 0
    )


async def test_orders_store_full_seller_amount_without_commission(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)

    assert order.commission_amount == Decimal("0.00")
    assert order.seller_amount == Decimal("100000.00")
    assert await _commission_tx_count(session, order.id) == 0


@pytest.mark.asyncio
async def test_payment_creates_no_legacy_commission_transaction(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    payment = await _pending_payment(session, order)

    await PaymentService().mark_succeeded(session, payment.id)

    assert order.status == OrderStatus.PAID.value
    assert order.commission_amount == Decimal("0.00")
    assert order.seller_amount == Decimal("100000.00")
    assert await _commission_tx_count(session, order.id) == 0

    payment_tx = await session.scalar(
        select(Transaction).where(
            Transaction.order_id == order.id,
            Transaction.type == "payment",
        )
    )
    assert payment_tx is not None
    assert payment_tx.amount == Decimal("100000.00")

    escrow_tx = await session.scalar(
        select(Transaction).where(
            Transaction.order_id == order.id,
            Transaction.type == "escrow_hold",
        )
    )
    assert escrow_tx is not None
    assert escrow_tx.amount == Decimal("100000.00")


@pytest.mark.asyncio
async def test_hold_funds_is_idempotent_and_creates_no_commission(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)

    await escrow_service.hold_funds(session, order.id)
    await escrow_service.hold_funds(session, order.id)

    assert await _commission_tx_count(session, order.id) == 0

    seller_balance = await session.scalar(
        select(SellerBalance).where(SellerBalance.seller_id == seller.id)
    )
    assert seller_balance is not None
    assert seller_balance.pending == Decimal("100000.00")


@pytest.mark.asyncio
async def test_legacy_pending_order_is_normalized_on_payment(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    order.commission_amount = Decimal("7000.00")
    order.seller_amount = Decimal("93000.00")
    await session.flush()

    await escrow_service.hold_funds(session, order.id)

    assert order.commission_amount == Decimal("0.00")
    assert order.seller_amount == Decimal("100000.00")
    assert await _commission_tx_count(session, order.id) == 0


@pytest.mark.asyncio
async def test_legacy_commission_env_is_ignored(
    session, seller, buyer, account, monkeypatch
) -> None:
    monkeypatch.setenv("PLATFORM_COMMISSION_RATE", "9")
    get_settings.cache_clear()
    try:
        order = await order_service.create_order(session, buyer, account.id)
        await escrow_service.hold_funds(session, order.id)

        assert order.commission_amount == Decimal("0.00")
        assert order.seller_amount == Decimal("100000.00")
        assert await _commission_tx_count(session, order.id) == 0
    finally:
        get_settings.cache_clear()
