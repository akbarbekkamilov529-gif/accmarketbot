from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import (
    AccountStatus,
    HourlyRelease,
    Order,
    OrderStatus,
    SellerBalance,
    Transaction,
)
from app.services import account_service, escrow_service, order_service, release_service
from app.services.account_service import AccountValidationError
from app.services.order_service import AccountNotAvailable
from app.utils import ensure_utc

pytestmark = pytest.mark.asyncio


async def test_credentials_are_encrypted_at_rest(session, account) -> None:
    loaded = await account_service.get_account(session, account.id)
    assert loaded is not None
    credentials = loaded.credentials
    assert credentials is not None
    assert "seller@gmail.com" not in credentials.login_encrypted
    assert "SuperSecret123" not in credentials.password_encrypted
    login, password, fields = await account_service.decrypt_credentials(loaded)
    assert login == "seller@gmail.com"
    assert password == "SuperSecret123"
    assert ("Recovery email", "recovery@example.com") in fields


async def test_order_reservation_and_commission(session, seller, buyer, account) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    await session.refresh(account)
    assert account.status == AccountStatus.RESERVED.value
    assert order.status == OrderStatus.PENDING_PAYMENT.value
    assert order.amount == Decimal("100000.00")
    assert order.commission_amount == Decimal("7000.00")
    assert order.seller_amount == Decimal("93000.00")
    commission_tx_count = await session.scalar(
        select(func.count(Transaction.id)).where(
            Transaction.order_id == order.id,
            Transaction.type == "platform_commission",
        )
    )
    assert commission_tx_count == 0

    with pytest.raises(AccountNotAvailable):
        await order_service.create_order(session, buyer, account.id)


async def test_hourly_release_is_idempotent_and_capped(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    order = await escrow_service.hold_funds(session, order.id)
    await session.refresh(order)

    one_hour_later = ensure_utc(order.paid_at) + timedelta(hours=1)
    released = await release_service.process_order_releases(
        session, order.id, reference_time=one_hour_later
    )
    assert released == Decimal("4650.00")

    released_again = await release_service.process_order_releases(
        session, order.id, reference_time=one_hour_later
    )
    assert released_again == Decimal("0.00")

    count = await session.scalar(
        select(func.count(HourlyRelease.id)).where(HourlyRelease.order_id == order.id)
    )
    assert count == 1

    seller_balance = await session.scalar(
        select(SellerBalance).where(SellerBalance.seller_id == seller.id)
    )
    assert seller_balance is not None
    assert seller_balance.available == Decimal("4650.00")
    assert seller_balance.pending == Decimal("88350.00")


async def test_completion_releases_remaining_and_marks_sold(
    session, seller, buyer, account
) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    order = await escrow_service.hold_funds(session, order.id)
    await session.refresh(order)

    one_hour_later = ensure_utc(order.paid_at) + timedelta(hours=1)
    await release_service.process_order_releases(
        session, order.id, reference_time=one_hour_later
    )

    completed = await escrow_service.complete_order(session, order.id, buyer.id)
    assert completed.status == OrderStatus.COMPLETED.value
    await session.refresh(account)
    assert account.status == AccountStatus.SOLD.value

    seller_balance = await session.scalar(
        select(SellerBalance).where(SellerBalance.seller_id == seller.id)
    )
    assert seller_balance is not None
    assert seller_balance.total_released == Decimal("93000.00")
    assert seller_balance.pending == Decimal("0.00")
    assert seller_balance.available == Decimal("93000.00")

    completion_tx = await session.scalar(
        select(Transaction).where(
            Transaction.order_id == order.id,
            Transaction.type == "completion_release",
        )
    )
    assert completion_tx is not None
    assert completion_tx.amount == Decimal("88350.00")


async def test_release_never_exceeds_seller_amount(session, seller, buyer, account) -> None:
    order = await order_service.create_order(session, buyer, account.id)
    order = await escrow_service.hold_funds(session, order.id)
    await session.refresh(order)

    much_later = ensure_utc(order.paid_at) + timedelta(hours=500)
    await release_service.process_order_releases(
        session, order.id, reference_time=much_later
    )
    total = await release_service.hourly_released_total(session, order.id)
    assert total == Decimal("93000.00")

    count = await session.scalar(
        select(func.count(HourlyRelease.id)).where(HourlyRelease.order_id == order.id)
    )
    assert count == 20


async def test_editing_is_blocked_after_account_is_reserved(
    session, seller, buyer, account
) -> None:
    await order_service.create_order(session, buyer, account.id)
    await session.refresh(account)
    loaded = await account_service.get_account(session, account.id)
    assert loaded is not None
    assert loaded.status == AccountStatus.RESERVED.value

    with pytest.raises(AccountValidationError):
        await account_service.update_account_main_fields(session, loaded, nickname="Changed")
    with pytest.raises(AccountValidationError):
        await account_service.add_credential_field(session, loaded, "New field", "value")
    with pytest.raises(AccountValidationError):
        await account_service.delete_credential_field(
            session, loaded, loaded.credential_fields[0].id
        )


async def test_credential_field_add_after_delete_uses_unique_position(session, account) -> None:
    loaded = await account_service.get_account(session, account.id)
    assert loaded is not None
    first = loaded.credential_fields[0]

    assert await account_service.delete_credential_field(session, loaded, first.id) is True

    loaded = await account_service.get_account(session, account.id)
    assert loaded is not None
    created = await account_service.add_credential_field(
        session, loaded, "New field", "new value"
    )
    assert created is not None
    assert created.position == 2

    login, password, fields = await account_service.decrypt_credentials(
        await account_service.get_account(session, account.id)
    )
    assert login == "seller@gmail.com"
    assert password == "SuperSecret123"
    assert ("New field", "new value") in fields
