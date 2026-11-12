from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BuyerBalance, SellerBalance, User


async def upsert_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    language_code: str | None,
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        session.add(user)
        await session.flush()
        await session.refresh(user, attribute_names=["created_at", "updated_at"])
        return user

    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.language_code = language_code
    return user


async def mark_seller(session: AsyncSession, user: User) -> None:
    if not user.is_seller:
        user.is_seller = True


async def get_seller_balance(session: AsyncSession, seller_id: int, *, create: bool = True) -> SellerBalance | None:
    balance = await session.scalar(select(SellerBalance).where(SellerBalance.seller_id == seller_id))
    if balance is None and create:
        balance = SellerBalance(seller_id=seller_id)
        session.add(balance)
        await session.flush()
    return balance


async def get_buyer_balance(session: AsyncSession, buyer_id: int, *, create: bool = True) -> BuyerBalance | None:
    balance = await session.scalar(select(BuyerBalance).where(BuyerBalance.buyer_id == buyer_id))
    if balance is None and create:
        balance = BuyerBalance(buyer_id=buyer_id)
        session.add(balance)
        await session.flush()
    return balance


def display_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    name = " ".join(part for part in (user.first_name, user.last_name) if part)
    return name or f"ID {user.telegram_id}"
