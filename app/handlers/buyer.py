from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import (
    ALL_PLATFORMS,
    PLATFORM_BY_KEY,
    SORT_NEWEST,
    VALID_SORTS,
    format_money,
    platform_display,
)
from app.handlers.helpers import (
    delete_safe,
    safe_edit,
    send_media_group_safe,
    send_photo_or_text,
)
from app.keyboards.buyer import (
    buyer_list_nav_kb,
    buyer_account_detail_kb,
    buyer_platforms_kb,
    purchase_actions_kb,
    purchase_warning_kb,
)
from app.models import Account, AccountStatus, User
from app.services import account_service, notification_service
from app.states import BuyerStates
from app.utils import esc, format_datetime, truncate

router = Router(name="buyer")


def _card_caption(account: Account) -> str:
    seller = account.seller
    seller_name = f"@{seller.username}" if seller and seller.username else "seller"
    lines = [
        f"🖼 <b>{esc(account.nickname)}</b>",
        f"{platform_display(account.platform)}",
        "",
        f"💵 <b>Narx:</b> {format_money(account.price, account.currency)}",
        f"👤 <b>Seller:</b> {esc(seller_name)}",
        f"📅 <b>Sana:</b> {format_datetime(account.created_at)}",
    ]
    if account.description:
        lines.append(f"📝 {esc(truncate(account.description, 120))}")
    return "\n".join(lines)


def _detail_text(account: Account) -> str:
    seller = account.seller
    seller_name = f"@{seller.username}" if seller and seller.username else "seller"
    lines = [
        f"<b>{esc(account.nickname)}</b>",
        "",
        f"🎮 <b>Platforma:</b> {platform_display(account.platform)}",
        f"👤 <b>Seller:</b> {esc(seller_name)}",
        f"💵 <b>Narx:</b> {format_money(account.price, account.currency)}",
        f"📅 <b>E'lon sanasi:</b> {format_datetime(account.created_at)}",
        f"👁 <b>Ko'rishlar:</b> {account.views_count}",
    ]
    if account.description:
        lines.extend(["", "📝 <b>Description:</b>", esc(account.description)])
    if account.additional_info:
        lines.extend(["", "📎 <b>Qo'shimcha ma'lumot:</b>", esc(account.additional_info)])
    if account.credential_fields:
        lines.append("")
        lines.append("<b>🔐 Akkaunt xususiyatlari:</b>")
        for field in account.credential_fields:
            lines.append(f"• {esc(field.label)}")
    lines.extend(
        [
            "",
            "🔒 <b>Login va parollar xarid qilinmaguncha yashirilgan.</b>",
        ]
    )
    return "\n".join(lines)


async def _clear_buyer_cards(bot: Bot, chat_id: int, data: dict) -> None:
    for message_id in list(data.get("buyer_card_messages", [])):
        await delete_safe(bot, chat_id, message_id)
    await delete_safe(bot, chat_id, data.get("buyer_nav_id"))


async def _render_list(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    *,
    platform_key: str,
    page: int,
    sort: str,
    bot: Bot,
) -> None:
    platform = PLATFORM_BY_KEY.get(platform_key)
    if platform is None:
        await callback.answer("Platforma topilmadi.", show_alert=True)
        return
    if sort not in VALID_SORTS:
        sort = SORT_NEWEST
    settings = get_settings()
    total = await account_service.count_active_accounts(session, platform.key)
    max_page = max(0, (total - 1) // settings.page_size) if total else 0
    page = max(0, min(page, max_page))
    offset = page * settings.page_size
    accounts = await account_service.list_active_accounts(
        session, platform.key, offset=offset, limit=settings.page_size, sort=sort
    )

    data = await state.get_data()
    await _clear_buyer_cards(bot, callback.message.chat.id, data)
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass

    nav_text = (
        f"{platform.emoji} <b>{platform.name}</b>\n\n"
        f"Sotuvdagi akkauntlar: <b>{total}</b> ta\n"
        f"Sahifa: <b>{page + 1}/{max_page + 1}</b>"
    )
    if not accounts:
        nav_text += "\n\n📭 Bu platformada hozircha akkaunt yo'q."

    nav_message = await callback.message.answer(
        nav_text,
        reply_markup=buyer_list_nav_kb(
            platform.key,
            page=page,
            sort=sort,
            has_next=offset + len(accounts) < total,
        ),
    )

    card_ids: list[int] = []
    for account in accounts:
        file_id = account.images[0].file_id if account.images else None
        card = await send_photo_or_text(
            bot,
            callback.message.chat.id,
            file_id=file_id,
            text=_card_caption(account),
            reply_markup=buyer_account_detail_kb(account),
        )
        card_ids.append(card.message_id)

    await state.set_state(BuyerStates.browse)
    await state.update_data(
        {
            "platform": platform.key,
            "sort": sort,
            "page": page,
            "buyer_nav_id": nav_message.message_id,
            "buyer_card_messages": card_ids,
        }
    )


@router.callback_query(F.data == "menu:buyer")
async def buyer_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(BuyerStates.browse)
    await safe_edit(
        callback.message,
        "🛍 <b>Buyer bo'limi</b>\n\n"
        "Qaysi platformadagi akkauntlar qiziqtiradi?\n"
        "Platformani tanlang:",
        buyer_platforms_kb(),
    )


@router.callback_query(F.data.startswith("buyer:platform:"))
async def buyer_select_platform(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    key = callback.data.split(":", 2)[2]
    if key not in PLATFORM_BY_KEY:
        await callback.answer("Platforma topilmadi.", show_alert=True)
        return
    await callback.answer()
    await _render_list(
        callback, state, session, platform_key=key, page=0, sort=SORT_NEWEST, bot=bot
    )


@router.callback_query(F.data.startswith("buyer:list:"))
async def buyer_list(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return
    _, _, platform_key, page_raw, sort = parts
    try:
        page = max(0, int(page_raw))
    except ValueError:
        page = 0
    await callback.answer()
    await _render_list(
        callback, state, session, platform_key=platform_key, page=page, sort=sort, bot=bot
    )


@router.callback_query(F.data.startswith("buyer:view:"))
async def buyer_view_account(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    try:
        account_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await account_service.get_account(session, account_id)
    if account is None or account.status == AccountStatus.DELETED.value:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    if account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Akkaunt hozir sotuvda mavjud emas.", show_alert=True)
        return

    previous_views = account.views_count
    await account_service.increment_views(session, account.id)
    account.views_count = previous_views + 1

    if previous_views == 0 and account.seller and account.seller.id != user.id:
        await notification_service.notify(
            session,
            bot,
            account.seller,
            "👀 <b>Akkauntingizga xaridor qiziqdi!</b>\n\n"
            f"🎮 {platform_display(account.platform)}\n"
            f"🔤 {esc(account.nickname)}\n"
            f"💵 {format_money(account.price, account.currency)}",
            notification_type="account_viewed",
            payload={"account_id": account.id},
        )

    await callback.answer()
    if account.images:
        await send_media_group_safe(
            bot, callback.message.chat.id, [image.file_id for image in account.images]
        )
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=_detail_text(account),
        reply_markup=buyer_account_detail_kb(account),
    )
    await state.set_state(BuyerStates.view_account)
    await state.update_data({"view_account_id": account.id})


PURCHASE_WARNING = (
    "⚠️ <b>XARID QILISHDAN OLDIN DIQQAT!</b>\n\n"
    "Siz akkauntni sotib olishga qaror qilyapsiz.\n\n"
    "• Xarid qilishdan oldin e'lon ma'lumotlarini tekshiring.\n"
    "• Akkaunt boshqa odamga tegishli ekanligi aniqlansa, bu haqda xabar berish "
    "imkoniyati bo'lsin.\n"
    "• Xaridni tasdiqlaganingizdan keyin pulni qaytarish avtomatik kafolatlanmaydi.\n"
    "• Nizolar bo'yicha avtomatik tizim ishlaydi.\n"
    "• Seller akkauntni topshirish uchun javobgar."
)


@router.callback_query(F.data.startswith("buyer:buy:"))
async def buyer_buy(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        account_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await account_service.get_account(session, account_id)
    if account is None or account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Akkaunt hozir sotuvda mavjud emas.", show_alert=True)
        return
    if account.seller_id == user.id:
        await callback.answer("O'z akkauntingizni sotib ololmaysiz.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(BuyerStates.purchase_warning)
    await state.update_data({"purchase_account_id": account.id})
    await safe_edit(callback.message, PURCHASE_WARNING, purchase_warning_kb(account.id))


@router.callback_query(F.data.startswith("buyer:continue:"))
async def buyer_continue(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        account_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await account_service.get_account(session, account_id)
    if account is None or account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Akkaunt hozir sotuvda mavjud emas.", show_alert=True)
        return
    await callback.answer()
    text = (
        "💳 <b>To'lov</b>\n\n"
        f"🎮 {platform_display(account.platform)}\n"
        f"🔤 {esc(account.nickname)}\n"
        f"💵 {format_money(account.price, account.currency)}\n\n"
        "To'lov tizimi hali ulanmagan.\n"
        "Hozircha faqat <b>⏭ SKIP PAYMENT</b> (demo) mavjud.\n\n"
        "⚠️ Demo rejimida haqiqiy buyurtma yaratilmaydi, to'lov olinmaydi va "
        "sellerga mablag' yozilmaydi."
    )
    await state.set_state(BuyerStates.purchase_warning)
    await state.update_data({"purchase_account_id": account.id})
    await safe_edit(callback.message, text, purchase_actions_kb(account.id))


@router.callback_query(F.data.startswith("buyer:skip:"))
async def buyer_skip_payment(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        account_id = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await account_service.get_account(session, account_id)
    if account is None or account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Akkaunt hozir sotuvda mavjud emas.", show_alert=True)
        return
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ E'longa qaytish", callback_data=f"buyer:view:{account.id}")
    builder.button(text="🏠 Bosh menyu", callback_data="menu:home")
    builder.adjust(1)
    await safe_edit(
        callback.message,
        "⏭ <b>SKIP PAYMENT — DEMO REJIM</b>\n\n"
        "Bu demo tugma. Haqiqiy to'lov provayderi ulanmagan.\n\n"
        "❌ Buyurtma yaratilmadi.\n"
        "❌ To'lov amalga oshirilmadi.\n"
        "❌ Akkaunt band qilinmadi.\n"
        "❌ Sellerga mablag' yozilmadi.\n\n"
        "Haqiqiy xarid uchun to'lov provayderi (Click/Payme) ulanishi kerak.",
        builder.as_markup(),
    )
    await state.clear()
