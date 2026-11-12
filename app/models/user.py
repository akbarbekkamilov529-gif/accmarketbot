from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.balance import BuyerBalance, SellerBalance
    from app.models.notification import Notification
    from app.models.order import Order


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_seller: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    orders_as_buyer: Mapped[list["Order"]] = relationship(
        back_populates="buyer", foreign_keys="Order.buyer_id"
    )
    orders_as_seller: Mapped[list["Order"]] = relationship(
        back_populates="seller", foreign_keys="Order.seller_id"
    )
    seller_balance: Mapped["SellerBalance | None"] = relationship(
        back_populates="seller", uselist=False, cascade="all, delete-orphan"
    )
    buyer_balance: Mapped["BuyerBalance | None"] = relationship(
        back_populates="buyer", uselist=False, cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
