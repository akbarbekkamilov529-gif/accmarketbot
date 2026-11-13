from __future__ import annotations

from decimal import Decimal

from app.constants import quantize_money

PERCENT_DIVISOR = Decimal("100")
HOURLY_SELLER_SHARE_RATE = Decimal("50")


def calculate_commission(amount: Decimal, rate: Decimal) -> Decimal:
    """Return the platform commission for a payment amount."""

    total = quantize_money(Decimal(amount))
    return quantize_money(total * Decimal(rate) / PERCENT_DIVISOR)


def split_payment_amount(amount: Decimal, rate: Decimal) -> tuple[Decimal, Decimal]:
    """Split a payment into (platform commission, seller amount)."""

    total = quantize_money(Decimal(amount))
    commission = calculate_commission(total, rate)
    seller_amount = quantize_money(total - commission)
    return commission, seller_amount


def split_hourly_amount(amount: Decimal) -> tuple[Decimal, Decimal]:
    """Split an hourly release equally into (seller amount, platform amount)."""

    total = quantize_money(Decimal(amount))
    seller_amount = quantize_money(total * HOURLY_SELLER_SHARE_RATE / PERCENT_DIVISOR)
    platform_amount = quantize_money(total - seller_amount)
    return seller_amount, platform_amount
