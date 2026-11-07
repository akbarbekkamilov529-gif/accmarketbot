from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AccountStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    DELETED = "deleted"


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_platform_status", "platform", "status"),
        Index("ix_accounts_status_created", "status", "created_at"),
        Index("ix_accounts_seller_status", "seller_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="game", nullable=False)
    nickname: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    additional_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="UZS", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=AccountStatus.ACTIVE.value, index=True, nullable=False
    )
    views_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    seller: Mapped["User"] = relationship(back_populates="accounts")
    images: Mapped[list["AccountImage"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="AccountImage.position",
    )
    credentials: Mapped["AccountCredentials | None"] = relationship(
        back_populates="account", uselist=False, cascade="all, delete-orphan"
    )
    credential_fields: Mapped[list["CredentialField"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="CredentialField.position",
    )

    @property
    def first_image(self) -> "AccountImage | None":
        return self.images[0] if self.images else None


class AccountImage(Base):
    __tablename__ = "account_images"
    __table_args__ = (UniqueConstraint("account_id", "position", name="uq_account_images_position"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["Account"] = relationship(back_populates="images")


class AccountCredentials(Base, TimestampMixin):
    __tablename__ = "account_credentials"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    login_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="credentials")


class CredentialField(Base):
    __tablename__ = "credential_fields"
    __table_args__ = (UniqueConstraint("account_id", "position", name="uq_credential_fields_position"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["Account"] = relationship(back_populates="credential_fields")
