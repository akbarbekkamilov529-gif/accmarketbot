from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class SellerBalance(Base, TimestampMixin):
    __tablename__ = "seller_balances"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    available: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    pending: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    total_released: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), nullable=False
    )
    total_earned: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)

    seller: Mapped["User"] = relationship(back_populates="seller_balance")


class BuyerBalance(Base, TimestampMixin):
    __tablename__ = "buyer_balances"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    available: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    held: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)

    buyer: Mapped["User"] = relationship(back_populates="buyer_balance")


class PlatformBalance(Base, TimestampMixin):
    __tablename__ = "platform_balances"

    id: Mapped[int] = mapped_column(
        BigIntPK, primary_key=True, autoincrement=False, default=1
    )
    available: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), nullable=False)
    total_earned: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), nullable=False
    )
