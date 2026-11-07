from __future__ import annotations

import html
import secrets
from datetime import datetime, timezone
from decimal import Decimal


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_datetime(value: datetime | None) -> str:
    value = ensure_utc(value)
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y %H:%M")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def truncate(value: str, length: int = 200) -> str:
    value = value.strip()
    return value if len(value) <= length else value[: length - 1] + "…"


def new_public_id() -> str:
    return secrets.token_hex(5).upper()


def to_decimal(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value).replace(" ", "").replace(",", "."))


def safe_div(value: Decimal, divisor: Decimal) -> Decimal:
    if divisor == 0:
        return Decimal("0")
    return value / divisor
