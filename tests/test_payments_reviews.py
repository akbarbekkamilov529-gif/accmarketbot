from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import (
    OrderStatus,
    Payment,
    PaymentStatus,
    SellerBalance,
    Transaction,
)
from app.services import escrow_service, order_service, review_service
from app.services.payment_service import PaymentError, PaymentService
from app.services.review_service import ReviewError

pytestmark = pytest.mark.asyncio


async def _pending_payment(session, order) -> Payment:
    payment = Payment(
        order_id=order.id,
        provider="payme",
        status=PaymentStatus.PENDING.value,
        amount=order.amount,
        currency=order.currency,
        idempotency_key=f"test:{order.public_id}",
    )
    session.add(payment)
    await session.flush()
    return payment


async def test_payment_mark_succeeded_is_idempotent(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    payment = await _pending_payment(session, order)
    service = PaymentService()

    paid_order = await service.mark_succeeded(session, payment.id, provider_payment_id="ext-1")
    assert paid_order.status == OrderStatus.PAID.value

    again = await service.mark_succeeded(session, payment.id)
    assert again.id == order.id

    seller_balance = await session.scalar(
        select(SellerBalance).where(SellerBalance.seller_id == seller.id)
    )
    assert seller_balance is not None
    assert seller_balance.pending == Decimal("95000.00")

    payment_tx_count = await session.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.order_id == order.id, Transaction.type == "payment"
        )
    )
    assert payment_tx_count == 1

    with pytest.raises(PaymentError):
        await service.mark_failed(session, payment.id)


async def test_skip_payment_is_demo_only(session, seller, buyer, account) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    service = PaymentService()
    result = await service.initiate(session, order.id, "skip")
    assert result.demo is True
    assert result.payment is None

    payments_count = await session.scalar(select(func.count(Payment.id)))
    assert payments_count == 0
    refreshed = await order_service.get_order(session, order.id)
    assert refreshed is not None
    assert refreshed.status == OrderStatus.PENDING_PAYMENT.value


async def test_review_requires_completed_order(session, seller, buyer, account) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    await escrow_service.hold_funds(session, order.id)

    with pytest.raises(ReviewError):
        await review_service.create_review(
            session, order_id=order.id, buyer_id=buyer.id, rating=5, comment="Great"
        )

    await escrow_service.complete_order(session, order.id, buyer.id)
    review = await review_service.create_review(
        session, order_id=order.id, buyer_id=buyer.id, rating=5, comment="Great"
    )
    assert review.rating == 5

    again = await review_service.create_review(
        session, order_id=order.id, buyer_id=buyer.id, rating=4, comment=None
    )
    assert again.id == review.id
