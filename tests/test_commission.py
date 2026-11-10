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
from app.services.commission_service import calculate_commission, split_payment_amount
from app.services.payment_service import PaymentService


def test_split_payment_amount_uses_seven_percent() -> None:
    commission, seller_amount = split_payment_amount(Decimal("100000"), Decimal("7"))

    assert commission == Decimal("7000.00")
    assert seller_amount == Decimal("93000.00")
    assert commission + seller_amount == Decimal("100000.00")


def test_commission_is_rounded_to_kopecks() -> None:
    commission = calculate_commission(Decimal("33333.33"), Decimal("7"))
    total_commission, seller_amount = split_payment_amount(
        Decimal("33333.33"), Decimal("7")
    )

    assert commission == Decimal("2333.33")
    assert total_commission == Decimal("2333.33")
    assert seller_amount == Decimal("31000.00")
    assert total_commission + seller_amount == Decimal("33333.33")


def test_commission_rate_comes_from_settings() -> None:
    assert get_settings().platform_commission_rate == Decimal("7")


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


@pytest.mark.asyncio
async def test_commission_transactions_are_created_only_after_payment(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    payment = await _pending_payment(session, order)

    assert order.commission_amount == Decimal("7000.00")
    assert order.seller_amount == Decimal("93000.00")

    commission_count = await session.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.order_id == order.id,
            Transaction.type == "platform_commission",
        )
    )
    assert commission_count == 0

    await PaymentService().mark_succeeded(session, payment.id)

    assert order.status == OrderStatus.PAID.value
    assert order.commission_amount == Decimal("7000.00")
    assert order.seller_amount == Decimal("93000.00")

    commission_tx = await session.scalar(
        select(Transaction).where(
            Transaction.order_id == order.id,
            Transaction.type == "platform_commission",
        )
    )
    assert commission_tx is not None
    assert commission_tx.amount == Decimal("7000.00")

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
    assert escrow_tx.amount == Decimal("93000.00")


@pytest.mark.asyncio
async def test_hold_funds_does_not_double_charge_commission(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)

    await escrow_service.hold_funds(session, order.id)
    await escrow_service.hold_funds(session, order.id)

    commission_count = await session.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.order_id == order.id,
            Transaction.type == "platform_commission",
        )
    )
    assert commission_count == 1

    seller_balance = await session.scalar(
        select(SellerBalance).where(SellerBalance.seller_id == seller.id)
    )
    assert seller_balance is not None
    assert seller_balance.pending == Decimal("93000.00")


@pytest.mark.asyncio
async def test_final_commission_uses_rate_at_payment_success(
    session, seller, buyer, account, monkeypatch
) -> None:
    monkeypatch.setenv("PLATFORM_COMMISSION_RATE", "5")
    get_settings.cache_clear()
    try:
        order = await order_service.create_order(session, buyer, account.id)
        assert order.commission_amount == Decimal("5000.00")
        assert order.seller_amount == Decimal("95000.00")

        monkeypatch.setenv("PLATFORM_COMMISSION_RATE", "7")
        get_settings.cache_clear()

        await escrow_service.hold_funds(session, order.id)

        assert order.commission_amount == Decimal("7000.00")
        assert order.seller_amount == Decimal("93000.00")

        commission_tx = await session.scalar(
            select(Transaction).where(
                Transaction.order_id == order.id,
                Transaction.type == "platform_commission",
            )
        )
        assert commission_tx is not None
        assert commission_tx.amount == Decimal("7000.00")
    finally:
        get_settings.cache_clear()
