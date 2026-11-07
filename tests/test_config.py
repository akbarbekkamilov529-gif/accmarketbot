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
