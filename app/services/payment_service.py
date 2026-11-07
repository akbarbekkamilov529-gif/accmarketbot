from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    Order,
    OrderStatus,
    Payment,
    PaymentProvider,
    PaymentStatus,
)
from app.services import escrow_service
from app.services.order_service import OrderError, OrderStateError
from app.utils import now_utc


class PaymentError(Exception):
    pass


class PaymentConfigurationError(PaymentError):
    pass


@dataclass(slots=True)
class ProviderPaymentResult:
    provider_payment_id: str | None = None
    payment_url: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PaymentInitResult:
    demo: bool
    message: str
    payment: Payment | None = None
    payment_url: str | None = None


class PaymentProviderBase(ABC):
    """Provider interface for future Click/Payme integrations.

    Implement create_payment() to return a hosted checkout URL and/or a
    provider payment id. Implement create_payout() only when the provider
    supports escrow or split payouts.
    """

    name: str
    supports_escrow: bool = False

    @abstractmethod
    async def create_payment(
        self, session: AsyncSession, order: Order, idempotency_key: str
    ) -> ProviderPaymentResult:
        raise NotImplementedError

    async def create_payout(
        self, session: AsyncSession, order: Order, amount: Decimal, reference: str
    ) -> ProviderPaymentResult:
        raise PaymentConfigurationError(f"{self.name} does not support payouts yet")


class SkipPaymentProvider(PaymentProviderBase):
    name = PaymentProvider.SKIP.value
    supports_escrow = False

    async def create_payment(
        self, session: AsyncSession, order: Order, idempotency_key: str
    ) -> ProviderPaymentResult:
        raise PaymentConfigurationError("Skip payment is a demo and cannot charge money")


class ClickPaymentProvider(PaymentProviderBase):
    name = PaymentProvider.CLICK.value
    supports_escrow = False

    async def create_payment(
        self, session: AsyncSession, order: Order, idempotency_key: str
    ) -> ProviderPaymentResult:
        raise PaymentConfigurationError(
            "Click provider is not configured. Add CLICK_SERVICE_ID / CLICK_MERCHANT_ID "
            "and implement create_payment before enabling real payments."
        )


class PaymePaymentProvider(PaymentProviderBase):
    name = PaymentProvider.PAYME.value
    supports_escrow = True

    async def create_payment(
        self, session: AsyncSession, order: Order, idempotency_key: str
    ) -> ProviderPaymentResult:
        raise PaymentConfigurationError(
            "Payme provider is not configured. Add PAYME_MERCHANT_ID / PAYME_KEY "
            "and implement create_payment before enabling real payments."
        )


class PaymentService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.providers: dict[str, PaymentProviderBase] = {
            PaymentProvider.SKIP.value: SkipPaymentProvider(),
            PaymentProvider.CLICK.value: ClickPaymentProvider(),
            PaymentProvider.PAYME.value: PaymePaymentProvider(),
        }

    async def initiate(
        self, session: AsyncSession, order_id: int, provider_name: str | None = None
    ) -> PaymentInitResult:
        provider_name = (provider_name or self.settings.payment_provider or "skip").lower()
        order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
        if order is None:
            raise OrderError("Buyurtma topilmadi.")
        if order.status != OrderStatus.PENDING_PAYMENT.value:
            raise OrderStateError("Buyurtma to'lov uchun mos holatda emas.")

        if provider_name == PaymentProvider.SKIP.value:
            if not self.settings.skip_payment_enabled:
                raise PaymentConfigurationError("Skip payment o'chirilgan.")
            return PaymentInitResult(
                demo=True,
                message=(
                    "⏭ <b>SKIP PAYMENT (DEMO)</b>\n\n"
                    "To'lov provayderi hali ulanmagan.\n"
                    "Bu rejimda <b>haqiqiy to'lov amalga oshirilmaydi</b>, buyurtma "
                    "yakunlanmaydi va sellerga pul yozilmaydi.\n\n"
                    "Akkaunt vaqtincha band qilinmaydi."
                ),
            )

        if not self.settings.payments_enabled:
            raise PaymentConfigurationError(
                "To'lovlar hozircha o'chirilgan. PAYMENTS_ENABLED=true qilib provayderni ulang."
            )

        provider = self.providers.get(provider_name)
        if provider is None:
            raise PaymentError("Noma'lum to'lov provayderi.")

        idempotency_key = f"{order.public_id}:{provider_name}"
        existing = await session.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        if existing is not None:
            url = (existing.raw_payload or {}).get("payment_url")
            return PaymentInitResult(
                demo=False,
                message="To'lov allaqachon yaratilgan.",
                payment=existing,
                payment_url=url,
            )

        payment = Payment(
            order_id=order.id,
            provider=provider_name,
            status=PaymentStatus.CREATED.value,
            amount=order.amount,
            currency=order.currency,
            idempotency_key=idempotency_key,
        )
        session.add(payment)
        await session.flush()

        result = await provider.create_payment(session, order, idempotency_key)
        payment.status = PaymentStatus.PENDING.value
        payment.provider_payment_id = result.provider_payment_id
        payment.raw_payload = {**result.payload, "payment_url": result.payment_url}
        await session.flush()
        return PaymentInitResult(
            demo=False,
            message="To'lov sahifasiga o'ting.",
            payment=payment,
            payment_url=result.payment_url,
        )

    async def mark_succeeded(
        self,
        session: AsyncSession,
        payment_id: int,
        *,
        provider_payment_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Order:
        payment = await session.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        if payment is None:
            raise PaymentError("To'lov topilmadi.")
        if payment.status == PaymentStatus.SUCCEEDED.value:
            order = await session.get(Order, payment.order_id)
            assert order is not None
            return order
        if payment.status not in (PaymentStatus.CREATED.value, PaymentStatus.PENDING.value):
            raise PaymentError("To'lov holati mos emas.")

        order = await escrow_service.hold_funds(session, payment.order_id)
        payment.status = PaymentStatus.SUCCEEDED.value
        payment.paid_at = now_utc()
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        if payload:
            payment.raw_payload = payload
        await session.flush()
        return order

    async def mark_failed(
        self,
        session: AsyncSession,
        payment_id: int,
        *,
        reason: str | None = None,
    ) -> Payment:
        payment = await session.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        if payment is None:
            raise PaymentError("To'lov topilmadi.")
        if payment.status == PaymentStatus.SUCCEEDED.value:
            raise PaymentError("Muvaffaqiyatli to'lovni failed qilib bo'lmaydi.")
        payment.status = PaymentStatus.FAILED.value
        if reason:
            payment.raw_payload = {**(payment.raw_payload or {}), "failure_reason": reason}
        await session.flush()
        return payment


def payment_datetime(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else "—"
