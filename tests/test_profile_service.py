from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import OrderStatus, TransactionType
from app.services import escrow_service, order_service, profile_service, review_service
from app.services.user_service import upsert_user

pytestmark = pytest.mark.asyncio


async def test_profile_stats_before_and_after_completed_sale(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)

    pending_stats = await profile_service.get_profile_stats(session, seller)
    assert pending_stats.sold_count == 0
    assert pending_stats.active_listings == 0
    assert pending_stats.pending_trades == 1
    assert pending_stats.balance.seller_pending == Decimal("0")
    assert pending_stats.balance.available_total == Decimal("0")

    await escrow_service.hold_funds(session, order.id)
    held_stats = await profile_service.get_profile_stats(session, seller)
    assert held_stats.balance.seller_pending == Decimal("93000.00")
    assert held_stats.balance.pending_total == Decimal("93000.00")

    await escrow_service.complete_order(session, order.id, buyer.id)
    await review_service.create_review(
        session,
        order_id=order.id,
        buyer_id=buyer.id,
        rating=5,
        comment="Great",
    )

    stats = await profile_service.get_profile_stats(session, seller)
    assert stats.sold_count == 1
    assert stats.bought_count == 0
    assert stats.sales_volume == Decimal("100000.00")
    assert stats.commission_total == Decimal("7000.00")
    assert stats.net_earned == Decimal("93000.00")
    assert stats.total_trade == Decimal("100000.00")
    assert stats.active_listings == 0
    assert stats.pending_trades == 0
    assert stats.balance.seller_available == Decimal("93000.00")
    assert stats.balance.seller_pending == Decimal("0")
    assert stats.balance.seller_total_earned == Decimal("93000.00")
    assert stats.balance.available_total == Decimal("93000.00")
    assert stats.rating == Decimal("5.0")
    assert stats.review_count == 1
    assert stats.registered_at is not None

    buyer_stats = await profile_service.get_profile_stats(session, buyer)
    assert buyer_stats.bought_count == 1
    assert buyer_stats.sold_count == 0
    assert buyer_stats.purchases_volume == Decimal("100000.00")
    assert buyer_stats.balance.buyer_total_spent == Decimal("100000.00")
    assert buyer_stats.balance.buyer_held == Decimal("0")
    assert buyer_stats.rating is None


async def test_profile_history_and_sold_bought_lists(session, seller, buyer, account) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    await escrow_service.hold_funds(session, order.id)
    await escrow_service.complete_order(session, order.id, buyer.id)

    seller_transactions = await profile_service.list_transactions(
        session, seller.id, offset=0, limit=10
    )
    seller_types = {tx.type for tx in seller_transactions}
    assert TransactionType.ESCROW_HOLD.value in seller_types
    assert TransactionType.COMPLETION_RELEASE.value in seller_types
    assert await profile_service.count_transactions(session, seller.id) == len(
        seller_transactions
    )

    buyer_transactions = await profile_service.list_transactions(
        session, buyer.id, offset=0, limit=10
    )
    assert TransactionType.PAYMENT.value in {tx.type for tx in buyer_transactions}

    sold = await profile_service.list_sold_orders(session, seller.id, offset=0, limit=10)
    assert [item.id for item in sold] == [order.id]
    assert await profile_service.count_sold_orders(session, seller.id) == 1

    bought = await profile_service.list_bought_orders(session, buyer.id, offset=0, limit=10)
    assert [item.id for item in bought] == [order.id]
    assert await profile_service.count_bought_orders(session, buyer.id) == 1


async def test_bought_list_includes_paid_but_not_pending_orders(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    assert await profile_service.count_bought_orders(session, buyer.id) == 0

    await escrow_service.hold_funds(session, order.id)
    assert await profile_service.count_bought_orders(session, buyer.id) == 1

    loaded = await profile_service.list_bought_orders(session, buyer.id, offset=0, limit=10)
    assert loaded[0].status == OrderStatus.PAID.value


async def test_preferred_language_is_preserved_by_telegram_upsert(session) -> None:
    user = await upsert_user(
        session,
        telegram_id=3003,
        username="locale_user",
        first_name="Locale",
        last_name=None,
        language_code="ru",
    )
    user.preferred_language = "en"
    await session.flush()

    refreshed = await upsert_user(
        session,
        telegram_id=3003,
        username="locale_user",
        first_name="Locale",
        last_name=None,
        language_code="ru",
    )
    assert refreshed.preferred_language == "en"
