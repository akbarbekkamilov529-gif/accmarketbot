from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import format_money
from app.handlers.helpers import safe_edit
from app.i18n import (
    LOCALE_LABELS,
    SUPPORTED_LOCALES,
    menu_action_by_text,
    status_label,
    t,
    transaction_label,
    user_locale,
)
from app.keyboards.buyer import buyer_platforms_kb
from app.keyboards.common import main_menu_kb, settings_kb
from app.keyboards.orders import orders_root_kb
from app.keyboards.seller import seller_accounts_menu_kb, seller_platforms_kb
from app.models import Order, Transaction, User
from app.services import profile_service
from app.services.user_service import mark_seller, upsert_user
from app.states import BuyerStates, SellerStates
from app.utils import esc, format_datetime, truncate

router = Router(name="profile")

MENU_ACTIONS = menu_action_by_text()


def _display_name(user: User) -> str:
    name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    return name or user.username or f"ID {user.telegram_id}"


def _profile_text(user: User, stats: profile_service.ProfileStats, locale: str) -> str:
    settings = get_settings()
    username = f"@{user.username}" if user.username else t("profile.no_username", locale)
    if stats.rating is None:
        rating = t("profile.no_rating", locale)
    else:
        rating = f"{stats.rating:.1f} ⭐ · {stats.review_count} {t('stats.reviews', locale)}"
    lines = [
        t("profile.title", locale),
        "",
        f"👤 <b>{t('profile.name', locale)}:</b> {esc(_display_name(user))}",
        f"🔗 <b>{t('profile.username', locale)}:</b> {esc(username)}",
        f"🆔 <b>{t('profile.telegram_id', locale)}:</b> <code>{user.telegram_id}</code>",
        "",
        f"💰 <b>{t('profile.balance', locale)}:</b> "
        f"{format_money(stats.balance.available_total, settings.currency)}",
        f"📤 <b>{t('profile.sold_count', locale)}:</b> {stats.sold_count}",
        f"📥 <b>{t('profile.bought_count', locale)}:</b> {stats.bought_count}",
        f"🏪 <b>{t('profile.active_listings', locale)}:</b> {stats.active_listings}",
        f"⏳ <b>{t('profile.pending_trades', locale)}:</b> {stats.pending_trades}",
        f"💵 <b>{t('profile.total_trade', locale)}:</b> "
        f"{format_money(stats.total_trade, settings.currency)}",
        f"⭐ <b>{t('profile.rating', locale)}:</b> {esc(rating)}",
        f"📅 <b>{t('profile.registered', locale)}:</b> {format_datetime(stats.registered_at)}",
        "",
        f"👇 {t('profile.hint', locale)}",
    ]
    return "\n".join(lines)


def _balance_text(stats: profile_service.ProfileStats, locale: str) -> str:
    settings = get_settings()
    balance = stats.balance
    lines = [
        t("balance.title", locale),
        "",
        f"👤 <b>{t('balance.seller', locale)}</b>",
        f"• {t('balance.available', locale)}: "
        f"{format_money(balance.seller_available, settings.currency)}",
        f"• {t('balance.pending', locale)}: "
        f"{format_money(balance.seller_pending, settings.currency)}",
        f"• {t('balance.total_earned', locale)}: "
        f"{format_money(balance.seller_total_earned, settings.currency)}",
        f"• {t('balance.total_released', locale)}: "
        f"{format_money(balance.seller_total_released, settings.currency)}",
        "",
        f"🛒 <b>{t('balance.buyer', locale)}</b>",
        f"• {t('balance.available', locale)}: "
        f"{format_money(balance.buyer_available, settings.currency)}",
        f"• {t('balance.held', locale)}: "
        f"{format_money(balance.buyer_held, settings.currency)}",
        f"• {t('balance.total_spent', locale)}: "
        f"{format_money(balance.buyer_total_spent, settings.currency)}",
    ]
    return "\n".join(lines)


def _balance_kb(locale: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("balance.history_button", locale), callback_data="profile:history:0")
    builder.button(text=t("common.home", locale), callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()


def _history_text(
    transactions: list[Transaction],
    *,
    page: int,
    total: int,
    page_size: int,
    locale: str,
) -> str:
    settings = get_settings()
    total_pages = max(1, (total + page_size - 1) // page_size)
    lines = [t("balance.history_title", locale)]
    if total:
        lines.extend(["", t("common.page", locale, page=page + 1, total=total_pages)])
    if not transactions:
        lines.extend(["", t("balance.history_empty", locale)])
    else:
        lines.append("")
        for tx in transactions:
            lines.append(
                t(
                    "balance.history_item",
                    locale,
                    date=format_datetime(tx.created_at),
                    type=transaction_label(tx.type, locale),
                    amount=format_money(tx.amount, settings.currency),
                )
            )
    return "\n".join(lines)


def _history_kb(*, page: int, has_next: bool, locale: str):
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="⬅️", callback_data=f"profile:history:{page - 1}")
    if has_next:
        builder.button(text="➡️", callback_data=f"profile:history:{page + 1}")
    builder.button(text=t("common.back", locale), callback_data="profile:balance")
    builder.adjust(2, 1)
    return builder.as_markup()


def _order_label(order: Order, locale: str) -> str:
    account = order.account
    nickname = account.nickname if account else "—"
    return t(
        "order.entry",
        locale,
        status=status_label(order.status, locale),
        public_id=order.public_id,
        nickname=truncate(nickname, 25),
        amount=format_money(order.amount, order.currency),
    )


def _orders_text(
    title: str,
    orders: list[Order],
    *,
    page: int,
    total: int,
    page_size: int,
    empty_text: str,
    locale: str,
) -> str:
    total_pages = max(1, (total + page_size - 1) // page_size)
    lines = [title]
    if not orders:
        lines.extend(["", empty_text])
    else:
        lines.extend(
            [
                "",
                t("list.page", locale, total=total, page=page + 1, total_pages=total_pages),
                "",
            ]
        )
        for order in orders:
            lines.append(
                f"• {esc(_order_label(order, locale))}\n"
                f"  🕒 {format_datetime(order.created_at)}"
            )
    return "\n".join(lines)


def _orders_kb(
    orders: list[Order],
    *,
    kind: str,
    page: int,
    has_next: bool,
    locale: str,
):
    builder = InlineKeyboardBuilder()
    for order in orders:
        builder.button(
            text=truncate(_order_label(order, locale), 60),
            callback_data=f"order:view:{order.id}",
        )
    if page > 0:
        builder.button(text="⬅️", callback_data=f"profile:{kind}:{page - 1}")
    if has_next:
        builder.button(text="➡️", callback_data=f"profile:{kind}:{page + 1}")
    builder.button(text=t("common.home", locale), callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()


def _stats_text(stats: profile_service.ProfileStats, locale: str) -> str:
    settings = get_settings()
    if stats.rating is None:
        rating = t("profile.no_rating", locale)
    else:
        rating = f"{stats.rating:.1f} ⭐"
    lines = [
        t("stats.title", locale),
        "",
        f"📤 <b>{t('stats.sales_title', locale)}</b>",
        f"• {t('stats.completed_sales', locale)}: {stats.sold_count}",
        f"• {t('stats.sales_volume', locale)}: "
        f"{format_money(stats.sales_volume, settings.currency)}",
        f"• {t('stats.commission', locale)}: "
        f"{format_money(stats.commission_total, settings.currency)}",
        f"• {t('stats.net_earned', locale)}: "
        f"{format_money(stats.net_earned, settings.currency)}",
        "",
        f"📥 <b>{t('stats.purchases_title', locale)}</b>",
        f"• {t('stats.completed_purchases', locale)}: {stats.bought_count}",
        f"• {t('stats.purchases_volume', locale)}: "
        f"{format_money(stats.purchases_volume, settings.currency)}",
        "",
        f"💵 {t('stats.total_trade', locale)}: "
        f"{format_money(stats.total_trade, settings.currency)}",
        f"🏪 {t('stats.active_listings', locale)}: {stats.active_listings}",
        f"⏳ {t('stats.pending_trades', locale)}: {stats.pending_trades}",
        f"⭐ {t('stats.rating', locale)}: {esc(rating)}",
        f"💬 {t('stats.reviews', locale)}: {stats.review_count}",
    ]
    return "\n".join(lines)


def _settings_text(locale: str) -> str:
    return "\n".join(
        [
            t("settings.title", locale),
            "",
            f"🌐 <b>{t('settings.current', locale)}:</b> {LOCALE_LABELS[locale]}",
            "",
            t("settings.choose", locale),
        ]
    )


def _help_text(locale: str) -> str:
    text = t("help.title", locale) + "\n\n" + t("help.body", locale)
    support = get_settings().support_contact.strip()
    if support:
        text += "\n\n" + t("help.support", locale, support=esc(support))
    return text


async def send_profile(message: Message, session: AsyncSession, user: User, locale: str) -> None:
    stats = await profile_service.get_profile_stats(session, user)
    await message.answer(
        _profile_text(user, stats, locale),
        reply_markup=main_menu_kb(locale),
    )


async def _replace_with_profile(
    callback: CallbackQuery, session: AsyncSession, user: User, locale: str
) -> None:
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await send_profile(callback.message, session, user, locale)


async def _send_balance(
    message: Message, session: AsyncSession, user: User, locale: str
) -> None:
    stats = await profile_service.get_profile_stats(session, user)
    await message.answer(_balance_text(stats, locale), reply_markup=_balance_kb(locale))


async def _send_history(
    message: Message,
    session: AsyncSession,
    user: User,
    locale: str,
    page: int,
    *,
    edit: bool,
) -> None:
    settings = get_settings()
    page = max(0, page)
    total = await profile_service.count_transactions(session, user.id)
    offset = page * settings.page_size
    transactions = await profile_service.list_transactions(
        session, user.id, offset=offset, limit=settings.page_size
    )
    has_next = offset + len(transactions) < total
    text = _history_text(
        transactions,
        page=page,
        total=total,
        page_size=settings.page_size,
        locale=locale,
    )
    markup = _history_kb(page=page, has_next=has_next, locale=locale)
    if edit:
        await safe_edit(message, text, markup)
    else:
        await message.answer(text, reply_markup=markup)


async def _send_orders(
    message: Message,
    session: AsyncSession,
    user: User,
    locale: str,
    kind: str,
    page: int,
    *,
    edit: bool,
) -> None:
    settings = get_settings()
    page = max(0, page)
    offset = page * settings.page_size
    if kind == "sold":
        total = await profile_service.count_sold_orders(session, user.id)
        orders = await profile_service.list_sold_orders(
            session, user.id, offset=offset, limit=settings.page_size
        )
        title = t("sold.title", locale)
        empty_text = t("sold.empty", locale)
    else:
        total = await profile_service.count_bought_orders(session, user.id)
        orders = await profile_service.list_bought_orders(
            session, user.id, offset=offset, limit=settings.page_size
        )
        title = t("bought.title", locale)
        empty_text = t("bought.empty", locale)

    has_next = offset + len(orders) < total
    text = _orders_text(
        title,
        orders,
        page=page,
        total=total,
        page_size=settings.page_size,
        empty_text=empty_text,
        locale=locale,
    )
    markup = _orders_kb(
        orders,
        kind=kind,
        page=page,
        has_next=has_next,
        locale=locale,
    )
    if edit:
        await safe_edit(message, text, markup)
    else:
        await message.answer(text, reply_markup=markup)


async def _send_stats(
    message: Message, session: AsyncSession, user: User, locale: str
) -> None:
    stats = await profile_service.get_profile_stats(session, user)
    await message.answer(_stats_text(stats, locale), reply_markup=main_menu_kb(locale))


async def _send_settings(message: Message, locale: str) -> None:
    await message.answer(_settings_text(locale), reply_markup=settings_kb(locale))


async def _send_help(message: Message, locale: str) -> None:
    await message.answer(_help_text(locale), reply_markup=main_menu_kb(locale))


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await state.clear()
    await send_profile(message, session, user, user_locale(user))


@router.message(Command("help"))
async def cmd_help(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await state.clear()
    await _send_help(message, user_locale(user))


@router.message(F.text.in_(set(MENU_ACTIONS)))
async def menu_navigate(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    action = MENU_ACTIONS.get(message.text or "")
    if action is None:
        return
    locale = user_locale(user)
    await state.clear()

    if action in {"profile", "home"}:
        await send_profile(message, session, user, locale)
    elif action == "balance":
        await _send_balance(message, session, user, locale)
    elif action == "buyer":
        await state.set_state(BuyerStates.browse)
        await message.answer(
            t("section.buyer", locale), reply_markup=buyer_platforms_kb(locale)
        )
    elif action == "seller":
        await mark_seller(session, user)
        await state.set_state(SellerStates.choosing_platform)
        await message.answer(
            t("section.seller", locale), reply_markup=seller_platforms_kb(locale)
        )
    elif action == "orders":
        await message.answer(t("section.orders", locale), reply_markup=orders_root_kb(locale))
    elif action == "listings":
        await state.set_state(SellerStates.my_accounts)
        await message.answer(
            t("listings.title", locale),
            reply_markup=seller_accounts_menu_kb(locale),
        )
    elif action in {"sold", "bought"}:
        await _send_orders(message, session, user, locale, action, 0, edit=False)
    elif action == "stats":
        await _send_stats(message, session, user, locale)
    elif action == "settings":
        await _send_settings(message, locale)
    elif action == "help":
        await _send_help(message, locale)


@router.callback_query(F.data == "menu:home")
async def menu_home(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await callback.answer()
    await state.clear()
    await _replace_with_profile(callback, session, user, user_locale(user))


@router.callback_query(F.data == "ui:cancel")
async def ui_cancel(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await callback.answer()
    await state.clear()
    await _replace_with_profile(callback, session, user, user_locale(user))


@router.callback_query(F.data == "profile:balance")
async def balance_callback(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    await callback.answer()
    stats = await profile_service.get_profile_stats(session, user)
    locale = user_locale(user)
    await safe_edit(callback.message, _balance_text(stats, locale), _balance_kb(locale))


@router.callback_query(F.data.startswith("profile:history:"))
async def history_callback(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    try:
        page = max(0, int(callback.data.split(":", 2)[2]))
    except (ValueError, IndexError):
        page = 0
    await callback.answer()
    await _send_history(
        callback.message,
        session,
        user,
        user_locale(user),
        page,
        edit=True,
    )


@router.callback_query(F.data.startswith("profile:sold:"))
async def sold_callback(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    try:
        page = max(0, int(callback.data.split(":", 2)[2]))
    except (ValueError, IndexError):
        page = 0
    await callback.answer()
    await _send_orders(
        callback.message,
        session,
        user,
        user_locale(user),
        "sold",
        page,
        edit=True,
    )


@router.callback_query(F.data.startswith("profile:bought:"))
async def bought_callback(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    try:
        page = max(0, int(callback.data.split(":", 2)[2]))
    except (ValueError, IndexError):
        page = 0
    await callback.answer()
    await _send_orders(
        callback.message,
        session,
        user,
        user_locale(user),
        "bought",
        page,
        edit=True,
    )


@router.callback_query(F.data.startswith("settings:lang:"))
async def settings_language(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    code = callback.data.rsplit(":", 1)[-1]
    if code not in SUPPORTED_LOCALES:
        await callback.answer(t("common.empty", user_locale(user)), show_alert=True)
        return
    user.preferred_language = code
    await session.flush()
    await callback.answer(t("settings.language_changed", code))
    await _replace_with_profile(callback, session, user, code)


@router.callback_query(F.data == "settings:refresh")
async def settings_refresh(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    tg_user = callback.from_user
    await upsert_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        language_code=tg_user.language_code,
    )
    locale = user_locale(user)
    await callback.answer(t("settings.profile_refreshed", locale))
    await _replace_with_profile(callback, session, user, locale)
