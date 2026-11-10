from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import DisputeStatus, Order, OrderStatus, SellerBalance
from app.services import dispute_service, escrow_service, order_service, release_service
from app.utils import ensure_utc

pytestmark = pytest.mark.asyncio


async def test_dispute_stops_and_resumes_hourly_release(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    order = await escrow_service.hold_funds(session, order.id)
    await session.refresh(order)

    dispute = await dispute_service.open_dispute(
        session, order.id, buyer.id, "Akkaunt ma'lumotlari noto'g'ri chiqdi."
    )
    await session.refresh(order)
    assert order.status == OrderStatus.DISPUTED.value
    assert dispute.status == DisputeStatus.OPEN.value

    one_hour = ensure_utc(order.paid_at) + timedelta(hours=1)
    released = await release_service.process_order_releases(
        session, order.id, reference_time=one_hour
    )
    assert released == Decimal("0.00")

    withdrawn = await dispute_service.withdraw_dispute(session, dispute.id, buyer.id)
    assert withdrawn.status == DisputeStatus.CLOSED.value
    await session.refresh(order)
    assert order.status in (OrderStatus.PAID.value, OrderStatus.DELIVERED.value)

    two_hours = ensure_utc(order.paid_at) + timedelta(hours=2)
    released_after = await release_service.process_order_releases(
        session, order.id, reference_time=two_hours
    )
    assert released_after == Decimal("9300.00")


async def test_only_participants_can_send_dispute_messages(
    session, seller, buyer, account
) -> None:
    from app.services.user_service import upsert_user

    outsider = await upsert_user(
        session,
        telegram_id=9999,
        username="outsider",
        first_name="Out",
        last_name=None,
        language_code="uz",
    )
    order = await order_service.create_order(session, buyer, account.id)
    order = await escrow_service.hold_funds(session, order.id)
    dispute = await dispute_service.open_dispute(session, order.id, buyer.id, "Muammo bor.")

    message = await dispute_service.add_message(
        session, dispute.id, buyer, content="Dalil yubordim"
    )
    assert message.content == "Dalil yubordim"

    from app.services.order_service import OrderForbidden

    with pytest.raises(OrderForbidden):
        await dispute_service.add_message(
            session, dispute.id, outsider, content="Men ham yozaman"
        )


async def test_seller_response_changes_status(session, seller, buyer, account) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    order = await escrow_service.hold_funds(session, order.id)
    dispute = await dispute_service.open_dispute(session, order.id, buyer.id, "Muammo bor.")

    await dispute_service.add_message(session, dispute.id, seller, content="Tekshiryapman")
    refreshed = await dispute_service.get_dispute(session, dispute.id)
    assert refreshed is not None
    assert refreshed.status == DisputeStatus.SELLER_RESPONDED.value
