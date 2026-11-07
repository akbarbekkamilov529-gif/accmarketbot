from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class DisputeStatus(StrEnum):
    OPEN = "open"
    SELLER_RESPONDED = "seller_responded"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CLOSED = "closed"


class MessageType(StrEnum):
    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"


class Dispute(Base, TimestampMixin):
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    opened_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), default=DisputeStatus.OPEN.value, index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_release_stopped: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped["Order"] = relationship(back_populates="dispute")
    opened_by_user: Mapped["User"] = relationship(foreign_keys=[opened_by])
    messages: Mapped[list["DisputeMessage"]] = relationship(
        back_populates="dispute", cascade="all, delete-orphan", order_by="DisputeMessage.created_at"
    )


class DisputeMessage(Base):
    __tablename__ = "dispute_messages"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    dispute_id: Mapped[int] = mapped_column(
        ForeignKey("disputes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    message_type: Mapped[str] = mapped_column(
        String(16), default=MessageType.TEXT.value, nullable=False
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dispute: Mapped["Dispute"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()
