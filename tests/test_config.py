from __future__ import annotations

from app.config import Settings


def _settings(database_url: str) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=database_url,
    )


def test_postgres_url_is_normalized_for_asyncpg() -> None:
    settings = _settings("postgres://user:pass@db:5432/market?sslmode=require")
    assert settings.database_url == (
        "postgresql+asyncpg://user:pass@db:5432/market?ssl=require"
    )


def test_ssl_boolean_query_is_mapped_to_asyncpg_value() -> None:
    assert (
        _settings("postgresql://user:pass@db/market?ssl=true").database_url
        == "postgresql+asyncpg://user:pass@db/market?ssl=require"
    )
    assert (
        _settings("postgresql://user:pass@db/market?ssl=false").database_url
        == "postgresql+asyncpg://user:pass@db/market?ssl=disable"
    )


def test_sqlite_url_is_left_unchanged() -> None:
    url = "sqlite+aiosqlite:///./local.db"
    assert _settings(url).database_url == url


def test_render_environment_enables_webhook() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        render_external_url="https://demo.onrender.com",
    )
    assert settings.is_render is True
    assert settings.webhook_enabled is True
    assert settings.webhook_url == "https://demo.onrender.com/webhook"


def test_webhook_secret_is_sanitized_for_telegram() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        webhook_secret="ab+c/1=_x",
    )
    assert settings.webhook_secret == "abc1_x"


def test_webhook_path_cannot_shadow_health_endpoint() -> None:
    settings = Settings(_env_file=None, environment="test", webhook_path="/health")
    assert settings.webhook_path == "/webhook"


def test_empty_port_falls_back_to_default() -> None:
    settings = Settings(_env_file=None, environment="test", port="")
    assert settings.port == 8080
