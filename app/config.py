from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded exclusively from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    bot_token: str = ""
    bot_username: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketplace"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    auto_create_tables: bool = False

    # Security
    credential_encryption_key: str = ""
    webhook_secret: str = ""

    # Runtime
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8080

    # Webhook / polling
    use_webhook: bool = False
    webhook_base_url: str = ""
    webhook_path: str = "/webhook"
    webhook_drop_pending: bool = False
    render_external_url: str = ""

    # Optional Redis (FSM storage / distributed rate limits)
    redis_url: str | None = None

    # Business rules
    platform_commission_rate: Decimal = Field(default=Decimal("5"), ge=0, le=100)
    hourly_release_rate: Decimal = Field(default=Decimal("5"), ge=0, le=100)
    hourly_release_interval_seconds: int = Field(default=3600, ge=60)
    currency: str = "UZS"

    # Limits
    rate_limit_per_minute: int = Field(default=30, ge=1)
    max_credential_fields: int = Field(default=8, ge=1, le=20)
    max_screenshots: int = Field(default=8, ge=1, le=10)
    min_price: Decimal = Field(default=Decimal("1"), ge=0)
    max_price: Decimal = Field(default=Decimal("1000000000"), ge=1)
    page_size: int = Field(default=5, ge=1, le=10)
    pending_order_ttl_minutes: int = Field(default=30, ge=1)
    dispute_auto_unresolved_hours: int = Field(default=72, ge=1)

    # Payments (real provider integration is intentionally disabled by default)
    payments_enabled: bool = False
    payment_provider: str = "skip"
    skip_payment_enabled: bool = True
    support_contact: str = ""

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        value = value.strip()
        if value.startswith("postgres://"):
            value = "postgresql+asyncpg://" + value[len("postgres://") :]
        elif value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://") :]

        parts = urlsplit(value)
        if parts.scheme != "postgresql+asyncpg":
            return value

        query: list[tuple[str, str]] = []
        for key, query_value in parse_qsl(parts.query, keep_blank_values=True):
            if key == "sslmode":
                key = "ssl"
            if key == "ssl":
                lowered = query_value.lower()
                if lowered in {"true", "1"}:
                    query_value = "require"
                elif lowered in {"false", "0"}:
                    query_value = "disable"
            query.append((key, query_value))

        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

    @field_validator("webhook_path")
    @classmethod
    def normalize_webhook_path(cls, value: str) -> str:
        value = value.strip() or "/webhook"
        return value if value.startswith("/") else "/" + value

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.environment == "production":
            missing = []
            if not self.bot_token:
                missing.append("BOT_TOKEN")
            if not self.credential_encryption_key:
                missing.append("CREDENTIAL_ENCRYPTION_KEY")
            if not self.database_url:
                missing.append("DATABASE_URL")
            if self.use_webhook and not self.effective_webhook_base_url:
                missing.append("WEBHOOK_BASE_URL")
            if missing:
                raise ValueError("Missing required production environment variables: " + ", ".join(missing))
        if self.use_webhook and not self.effective_webhook_base_url:
            raise ValueError(
                "WEBHOOK_BASE_URL (or RENDER_EXTERNAL_URL) is required when USE_WEBHOOK=true"
            )
        return self

    @property
    def effective_webhook_base_url(self) -> str:
        return (self.webhook_base_url or self.render_external_url).strip().rstrip("/")

    @property
    def webhook_url(self) -> str:
        return self.effective_webhook_base_url + self.webhook_path

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
