from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.dispute import Dispute
    from app.models.payment import Payment
    from app.models.user import User


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    UNRESOLVED = "unresolved"


ACTIVE_ORDER_STATUSES: tuple[str, ...] = (
    OrderStatus.PENDING_PAYMENT.value,
    OrderStatus.PAID.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.DISPUTED.value,
    OrderStatus.UNRESOLVED.value,
)


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_buyer_status", "buyer_id", "status"),
        Index("ix_orders_seller_status", "seller_id", "status"),
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_paid_at", "paid_at"),
        Index(
            "uq_orders_active_account",
            "account_id",
            unique=True,
            postgresql_where=text(
                "status IN ('pending_payment','paid','delivered','disputed','unresolved')"
            ),
            sqlite_where=text(
                "status IN ('pending_payment','paid','delivered','disputed','unresolved')"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    seller_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="UZS", nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=OrderStatus.PENDING_PAYMENT.value, index=True, nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispute_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    buyer_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped["Account"] = relationship()
    buyer: Mapped["User"] = relationship(back_populates="orders_as_buyer", foreign_keys=[buyer_id])
    seller: Mapped["User"] = relationship(back_populates="orders_as_seller", foreign_keys=[seller_id])
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    dispute: Mapped["Dispute | None"] = relationship(
        back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
