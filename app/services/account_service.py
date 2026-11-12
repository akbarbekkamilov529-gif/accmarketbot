from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.constants import (
    PLATFORM_BY_KEY,
    SORT_NEWEST,
    SORT_PRICE_ASC,
    SORT_PRICE_DESC,
    quantize_money,
)
from app.crypto import decrypt_for_account, encrypt_for_account
from app.models import (
    Account,
    AccountCredentials,
    AccountImage,
    AccountStatus,
    CredentialField,
    User,
)


class AccountValidationError(ValueError):
    pass


@dataclass(slots=True)
class AccountDraft:
    platform: str
    nickname: str
    description: str
    login: str
    password: str
    price: Decimal
    images: list[str] = field(default_factory=list)
    extra_fields: list[dict[str, str]] = field(default_factory=list)
    additional_info: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_account_editable(account: Account) -> None:
    if account.status != AccountStatus.ACTIVE.value:
        raise AccountValidationError("Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.")


def validate_draft(draft: AccountDraft) -> None:
    settings = get_settings()
    if draft.platform not in PLATFORM_BY_KEY:
        raise AccountValidationError("Noto'g'ri platforma tanlandi.")
    if not draft.nickname.strip():
        raise AccountValidationError("Akkaunt nomi bo'sh bo'lishi mumkin emas.")
    if not draft.login.strip():
        raise AccountValidationError("Login bo'sh bo'lishi mumkin emas.")
    if not draft.password:
        raise AccountValidationError("Parol bo'sh bo'lishi mumkin emas.")
    if not draft.images:
        raise AccountValidationError("Kamida bitta screenshot yuklang.")
    if len(draft.images) > settings.max_screenshots:
        raise AccountValidationError("Screenshotlar soni juda ko'p.")
    if len(draft.extra_fields) > settings.max_credential_fields:
        raise AccountValidationError("Qo'shimcha maydonlar soni juda ko'p.")
    if draft.price < settings.min_price or draft.price > settings.max_price:
        raise AccountValidationError("Narx ruxsat etilgan chegarada emas.")


async def create_account(session: AsyncSession, seller: User, draft: AccountDraft) -> Account:
    validate_draft(draft)
    settings = get_settings()
    platform = PLATFORM_BY_KEY[draft.platform]

    account = Account(
        seller_id=seller.id,
        platform=platform.key,
        category=platform.category,
        nickname=draft.nickname.strip(),
        description=draft.description.strip(),
        additional_info=(draft.additional_info or "").strip() or None,
        price=quantize_money(draft.price),
        currency=settings.currency,
        status=AccountStatus.ACTIVE.value,
    )
    session.add(account)
    await session.flush()

    for position, file_id in enumerate(draft.images[: settings.max_screenshots]):
        session.add(AccountImage(account_id=account.id, file_id=file_id, position=position))

    fields = draft.extra_fields[: settings.max_credential_fields]
    session.add(
        AccountCredentials(
            account_id=account.id,
            login_encrypted=encrypt_for_account(account.id, draft.login),
            password_encrypted=encrypt_for_account(account.id, draft.password),
        )
    )
    for position, item in enumerate(fields):
        label = (item.get("label") or "").strip()
        value = item.get("value") or ""
        if not label or not value:
            continue
        session.add(
            CredentialField(
                account_id=account.id,
                label=label[:128],
                value_encrypted=encrypt_for_account(account.id, value),
                position=position,
            )
        )

    await session.flush()
    return account


def account_query():
    return select(Account).options(
        selectinload(Account.images),
        selectinload(Account.credentials),
        selectinload(Account.credential_fields),
        selectinload(Account.seller),
    )


async def get_account(session: AsyncSession, account_id: int) -> Account | None:
    return await session.scalar(account_query().where(Account.id == account_id))


async def get_account_for_update(session: AsyncSession, account_id: int) -> Account | None:
    return await session.scalar(account_query().where(Account.id == account_id).with_for_update())


async def count_active_accounts(session: AsyncSession, platform: str) -> int:
    return int(
        await session.scalar(
            select(func.count(Account.id)).where(
                Account.platform == platform, Account.status == AccountStatus.ACTIVE.value
            )
        )
        or 0
    )


async def list_active_accounts(
    session: AsyncSession,
    platform: str,
    *,
    offset: int,
    limit: int,
    sort: str = SORT_NEWEST,
) -> list[Account]:
    stmt = (
        account_query()
        .where(Account.platform == platform, Account.status == AccountStatus.ACTIVE.value)
    )
    if sort == SORT_PRICE_ASC:
        stmt = stmt.order_by(Account.price.asc(), Account.id.asc())
    elif sort == SORT_PRICE_DESC:
        stmt = stmt.order_by(Account.price.desc(), Account.id.desc())
    else:
        stmt = stmt.order_by(Account.created_at.desc(), Account.id.desc())
    stmt = stmt.offset(offset).limit(limit)
    result = await session.scalars(stmt)
    return list(result.unique().all())


async def count_seller_accounts(session: AsyncSession, seller_id: int, flt: str) -> int:
    stmt = select(func.count(Account.id)).where(Account.seller_id == seller_id)
    if flt == "active":
        stmt = stmt.where(Account.status == AccountStatus.ACTIVE.value)
    elif flt == "pending":
        stmt = stmt.where(Account.status == AccountStatus.RESERVED.value)
    elif flt == "sold":
        stmt = stmt.where(Account.status == AccountStatus.SOLD.value)
    else:
        stmt = stmt.where(Account.status != AccountStatus.DELETED.value)
    return int(await session.scalar(stmt) or 0)


async def list_seller_accounts(
    session: AsyncSession,
    seller_id: int,
    *,
    flt: str,
    offset: int,
    limit: int,
) -> list[Account]:
    stmt = account_query().where(Account.seller_id == seller_id)
    if flt == "active":
        stmt = stmt.where(Account.status == AccountStatus.ACTIVE.value)
    elif flt == "pending":
        stmt = stmt.where(Account.status == AccountStatus.RESERVED.value)
    elif flt == "sold":
        stmt = stmt.where(Account.status == AccountStatus.SOLD.value)
    else:
        stmt = stmt.where(Account.status != AccountStatus.DELETED.value)
    stmt = stmt.order_by(Account.created_at.desc(), Account.id.desc()).offset(offset).limit(limit)
    result = await session.scalars(stmt)
    return list(result.unique().all())


async def update_account_main_fields(
    session: AsyncSession,
    account: Account,
    *,
    nickname: str | None = None,
    description: str | None = None,
    price: Decimal | None = None,
    additional_info: str | None = None,
    login: str | None = None,
    password: str | None = None,
) -> None:
    ensure_account_editable(account)
    if nickname is not None:
        account.nickname = nickname.strip()[:128]
    if description is not None:
        account.description = description.strip()
    if price is not None:
        account.price = quantize_money(price)
    if additional_info is not None:
        account.additional_info = additional_info.strip() or None
    if login is not None or password is not None:
        credentials = account.credentials
        if credentials is None:
            credentials = AccountCredentials(
                account_id=account.id,
                login_encrypted=encrypt_for_account(account.id, login or ""),
                password_encrypted=encrypt_for_account(account.id, password or ""),
            )
            session.add(credentials)
        else:
            if login is not None:
                credentials.login_encrypted = encrypt_for_account(account.id, login)
            if password is not None:
                credentials.password_encrypted = encrypt_for_account(account.id, password)
    await session.flush()


async def replace_account_images(session: AsyncSession, account: Account, file_ids: list[str]) -> None:
    settings = get_settings()
    ensure_account_editable(account)
    if not file_ids:
        raise AccountValidationError("Kamida bitta screenshot kerak.")
    await session.execute(delete(AccountImage).where(AccountImage.account_id == account.id))
    for position, file_id in enumerate(file_ids[: settings.max_screenshots]):
        session.add(AccountImage(account_id=account.id, file_id=file_id, position=position))
    await session.flush()
    await session.refresh(account, attribute_names=["images"])


async def add_credential_field(
    session: AsyncSession, account: Account, label: str, value: str
) -> CredentialField | None:
    settings = get_settings()
    ensure_account_editable(account)
    count = int(
        await session.scalar(
            select(func.count(CredentialField.id)).where(CredentialField.account_id == account.id)
        )
        or 0
    )
    if count >= settings.max_credential_fields:
        raise AccountValidationError("Qo'shimcha maydonlar limiti tugagan.")
    max_position = await session.scalar(
        select(func.max(CredentialField.position)).where(CredentialField.account_id == account.id)
    )
    label = label.strip()
    value = value.strip()
    if not label or not value:
        raise AccountValidationError("Maydon nomi va qiymati bo'sh bo'lishi mumkin emas.")
    field = CredentialField(
        account_id=account.id,
        label=label[:128],
        value_encrypted=encrypt_for_account(account.id, value),
        position=int(max_position) + 1 if max_position is not None else 0,
    )
    session.add(field)
    await session.flush()
    await session.refresh(account, attribute_names=["credential_fields"])
    return field


async def update_credential_field(
    session: AsyncSession, account: Account, field_id: int, value: str
) -> CredentialField | None:
    ensure_account_editable(account)
    field = await session.scalar(
        select(CredentialField).where(
            CredentialField.id == field_id, CredentialField.account_id == account.id
        )
    )
    if field is None:
        return None
    value = value.strip()
    if not value:
        raise AccountValidationError("Maydon qiymati bo'sh bo'lishi mumkin emas.")
    field.value_encrypted = encrypt_for_account(account.id, value)
    await session.flush()
    await session.refresh(account, attribute_names=["credential_fields"])
    return field


async def delete_credential_field(session: AsyncSession, account: Account, field_id: int) -> bool:
    ensure_account_editable(account)
    field = await session.scalar(
        select(CredentialField).where(
            CredentialField.id == field_id, CredentialField.account_id == account.id
        )
    )
    if field is None:
        return False
    await session.delete(field)
    await session.flush()
    await session.refresh(account, attribute_names=["credential_fields"])
    return True


async def soft_delete_account(session: AsyncSession, account: Account) -> None:
    if account.status in (AccountStatus.RESERVED.value, AccountStatus.SOLD.value):
        raise AccountValidationError("Band yoki sotilgan akkauntni o'chirib bo'lmaydi.")
    account.status = AccountStatus.DELETED.value
    account.deleted_at = _now()
    await session.flush()


async def reserve_account(session: AsyncSession, account_id: int) -> bool:
    result = await session.execute(
        update(Account)
        .where(Account.id == account_id, Account.status == AccountStatus.ACTIVE.value)
        .values(status=AccountStatus.RESERVED.value, reserved_at=_now())
        .returning(Account.id)
    )
    return result.scalar_one_or_none() is not None


async def release_reservation(session: AsyncSession, account_id: int) -> None:
    await session.execute(
        update(Account)
        .where(Account.id == account_id, Account.status == AccountStatus.RESERVED.value)
        .values(status=AccountStatus.ACTIVE.value, reserved_at=None)
    )


async def mark_account_sold(session: AsyncSession, account_id: int) -> None:
    await session.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(status=AccountStatus.SOLD.value, sold_at=_now())
    )


async def decrypt_credentials(account: Account) -> tuple[str, str, list[tuple[str, str]]]:
    credentials = account.credentials
    login = decrypt_for_account(account.id, credentials.login_encrypted) if credentials else ""
    password = decrypt_for_account(account.id, credentials.password_encrypted) if credentials else ""
    fields = [
        (item.label, decrypt_for_account(account.id, item.value_encrypted))
        for item in account.credential_fields
    ]
    return login, password, fields


async def increment_views(session: AsyncSession, account_id: int) -> None:
    await session.execute(
        update(Account).where(Account.id == account_id).values(views_count=Account.views_count + 1)
    )
