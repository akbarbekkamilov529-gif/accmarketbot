from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "unit-test-passphrase")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("PLATFORM_COMMISSION_RATE", "0")

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.services.account_service import AccountDraft, create_account
from app.services.user_service import upsert_user


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest_asyncio.fixture
async def seller(session: AsyncSession):
    return await upsert_user(
        session,
        telegram_id=1001,
        username="seller_user",
        first_name="Seller",
        last_name=None,
        language_code="uz",
    )


@pytest_asyncio.fixture
async def buyer(session: AsyncSession):
    return await upsert_user(
        session,
        telegram_id=2002,
        username="buyer_user",
        first_name="Buyer",
        last_name=None,
        language_code="uz",
    )


@pytest_asyncio.fixture
async def account(session: AsyncSession, seller):
    draft = AccountDraft(
        platform="brawl_stars",
        nickname="Test Account",
        description="A test account",
        login="seller@gmail.com",
        password="SuperSecret123",
        price=Decimal("100000"),
        images=["photo_file_id_1", "photo_file_id_2"],
        extra_fields=[
            {"label": "Recovery email", "value": "recovery@example.com"},
            {"label": "Recovery code", "value": "ABC-123"},
        ],
        additional_info="Level 50",
    )
    return await create_account(session, seller, draft)
