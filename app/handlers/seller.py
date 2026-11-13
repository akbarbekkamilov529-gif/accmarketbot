from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import (
    GAME_PLATFORMS,
    PLATFORM_BY_KEY,
    SOCIAL_PLATFORMS,
    VALID_SELLER_FILTERS,
    format_money,
    platform_display,
)
from app.handlers.helpers import (
    delete_safe,
    safe_edit,
    send_media_group_safe,
    send_photo_or_text,
)
from app.i18n import t, user_locale
from app.keyboards import main_menu_inline_kb
from app.keyboards.common import cancel_kb
from app.logging_config import get_logger
from app.keyboards.seller import (
    account_delete_confirm_kb,
    edit_menu_kb,
    extra_fields_menu_kb,
    preview_kb,
    screenshots_kb,
    seller_account_detail_kb,
    seller_accounts_menu_kb,
    seller_edit_fields_kb,
    seller_extra_info_kb,
    seller_list_kb,
    seller_platforms_kb,
    warning_kb,
)
from app.models import Account, AccountStatus, User
from app.services import account_service, notification_service
from app.services.account_service import AccountDraft, AccountValidationError
from app.services.user_service import mark_seller
from app.states import SellerStates
from app.utils import esc, format_datetime, now_utc, to_decimal, truncate

router = Router(name="seller")
logger = get_logger(__name__)

MAX_LABEL = 40
MAX_NICKNAME = 128
MAX_DESCRIPTION = 2000
MAX_LOGIN = 200
MAX_PASSWORD = 200
MAX_ADDITIONAL = 1000


def _draft_from_data(data: dict) -> AccountDraft:
    try:
        price = to_decimal(data.get("price", "0"))
    except (InvalidOperation, ValueError) as exc:
        raise AccountValidationError("Narx formati noto'g'ri.") from exc
    return AccountDraft(
        platform=data.get("platform", ""),
        nickname=data.get("nickname", ""),
        description=data.get("description", ""),
        login=data.get("login", ""),
        password=data.get("password", ""),
        price=price,
        images=list(data.get("images", [])),
        extra_fields=list(data.get("extra_fields", [])),
        additional_info=data.get("additional_info"),
    )


def _preview_text(data: dict) -> str:
    platform = platform_display(data.get("platform", ""))
    fields = data.get("extra_fields", [])
    images = data.get("images", [])
    lines = [
        "🔎 <b>E'lon preview</b>",
        "",
        f"🎮 <b>Platforma:</b> {platform}",
        f"🔤 <b>Nickname:</b> {esc(data.get('nickname', '—'))}",
        f"📝 <b>Description:</b> {esc(truncate(data.get('description', '—'), 300))}",
        f"🔐 <b>Login:</b> {esc(data.get('login', '—'))}",
        f"🔑 <b>Asosiy parol:</b> •••••• (shifrlanadi)",
        f"💵 <b>Narx:</b> {format_money(to_decimal(data.get('price', '0')))}",
        f"🖼 <b>Screenshotlar:</b> {len(images)} ta",
    ]
    if data.get("additional_info"):
        lines.append(f"📎 <b>Qo'shimcha:</b> {esc(truncate(data['additional_info'], 300))}")
    if fields:
        lines.append("")
        lines.append("<b>🔐 Qo'shimcha maxfiy maydonlar:</b>")
        for item in fields:
            lines.append(f"• {esc(item.get('label', '—'))}: ••••••")
    lines.append("")
    lines.append("ℹ️ Barcha parollar AES-GCM bilan shifrlanadi.")
    return "\n".join(lines)


async def _send_preview(bot: Bot, chat_id: int, data: dict) -> None:
    await send_media_group_safe(bot, chat_id, list(data.get("images", [])))
    await bot.send_message(chat_id=chat_id, text=_preview_text(data), reply_markup=preview_kb())


def _edit_menu_text(data: dict) -> str:
    return (
        "✏️ <b>Tahrirlash</b>\n\n"
        "Qaysi maydonni o'zgartirmoqchisiz? Quyidagi tugmalardan birini tanlang."
    )


def _account_status_label(status: str) -> str:
    return {
        AccountStatus.ACTIVE.value: "🟢 Sotuvda",
        AccountStatus.RESERVED.value: "🟡 Band qilingan",
        AccountStatus.SOLD.value: "✅ Sotilgan",
        AccountStatus.DELETED.value: "🗑 O'chirilgan",
        AccountStatus.DRAFT.value: "⚪️ Qoralama",
    }.get(status, status)


def _account_detail_text(account: Account) -> str:
    lines = [
        f"<b>{esc(account.nickname)}</b>",
        "",
        f"🎮 <b>Platforma:</b> {platform_display(account.platform)}",
        f"💵 <b>Narx:</b> {format_money(account.price, account.currency)}",
        f"📌 <b>Holat:</b> {_account_status_label(account.status)}",
        f"📅 <b>E'lon sanasi:</b> {format_datetime(account.created_at)}",
        f"👁 <b>Ko'rishlar:</b> {account.views_count}",
    ]
    if account.description:
        lines.append(f"📝 <b>Description:</b> {esc(truncate(account.description, 400))}")
    if account.additional_info:
        lines.append(f"📎 <b>Qo'shimcha:</b> {esc(truncate(account.additional_info, 400))}")
    if account.credential_fields:
        lines.append("")
        lines.append("<b>🔐 Maxfiy maydonlar:</b>")
        for field in account.credential_fields:
            lines.append(f"• {esc(field.label)}: ••••••")
    lines.append("")
    lines.append(f"🖼 Screenshotlar: {len(account.images)} ta")
    return "\n".join(lines)


async def _show_edit_menu(
    message: Message,
    state: FSMContext,
    data: dict,
) -> None:
    await state.set_state(SellerStates.edit_menu)
    await message.answer(
        _edit_menu_text(data),
        reply_markup=edit_menu_kb(data.get("extra_fields", []), len(data.get("images", []))),
    )


async def _show_account_edit_menu(
    message: Message,
    state: FSMContext,
    account: Account,
) -> None:
    await state.set_state(SellerStates.account_edit_menu)
    await state.update_data({"edit_account_id": account.id})
    await message.answer(
        "✏️ <b>E'lonni tahrirlash</b>\n\nKerakli maydonni tanlang.",
        reply_markup=seller_edit_fields_kb(account),
    )


async def _load_own_account(
    session: AsyncSession, account_id: int, user: User
) -> Account | None:
    account = await account_service.get_account(session, account_id)
    if account is None or account.seller_id != user.id:
        return None
    return account


# ---------------------------------------------------------------------------
# Seller menu and account creation
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "menu:seller")
async def seller_menu(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    session: AsyncSession,
) -> None:
    await callback.answer()
    await mark_seller(session, user)
    await state.clear()
    await state.set_state(SellerStates.choosing_platform)
    locale = user_locale(user)
    await safe_edit(
        callback.message,
        t("section.seller", locale),
        seller_platforms_kb(locale),
    )


@router.callback_query(F.data == "seller:new")
async def seller_new(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(SellerStates.choosing_platform)
    locale = user_locale(user)
    await safe_edit(
        callback.message,
        t("section.seller", locale),
        seller_platforms_kb(locale),
    )


@router.callback_query(F.data.startswith("seller:platform:"))
async def seller_select_platform(
    callback: CallbackQuery, state: FSMContext
) -> None:
    key = callback.data.split(":", 2)[2]
    platform = PLATFORM_BY_KEY.get(key)
    if platform is None:
        await callback.answer("Platforma topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    await state.update_data(
        {
            "platform": platform.key,
            "images": [],
            "extra_fields": [],
            "nickname": "",
            "description": "",
            "login": "",
            "password": "",
            "price": "",
            "additional_info": None,
            "editing_images": False,
            "field_flow": "extra",
        }
    )
    await state.set_state(SellerStates.nickname)
    await safe_edit(
        callback.message,
        f"{platform.emoji} <b>{platform.name}</b> tanlandi.\n\n"
        "1️⃣ Akkaunt nomi yoki nickname kiriting:",
        cancel_kb(),
    )


@router.message(StateFilter(SellerStates.nickname), F.text)
async def seller_nickname(message: Message, state: FSMContext, bot: Bot) -> None:
    nickname = (message.text or "").strip()
    if not (1 <= len(nickname) <= MAX_NICKNAME):
        await message.answer("Nickname 1 dan 128 belgigacha bo'lishi kerak. Qayta kiriting.")
        return
    await state.update_data({"nickname": nickname})
    await state.set_state(SellerStates.screenshots)
    await state.update_data({"images": [], "editing_images": False})
    settings = get_settings()
    prompt = await message.answer(
        "2️⃣ <b>Screenshotlar</b>\n\n"
        "Akkaunt screenshotlarini rasm sifatida yuboring.\n"
        f"Kamida 1 ta, ko'pi bilan {settings.max_screenshots} ta.\n\n"
        "Tugagach <b>✅ Tayyor</b> tugmasini bosing.",
        reply_markup=screenshots_kb(0, settings.max_screenshots),
    )
    await state.update_data({"shots_prompt_id": prompt.message_id})


async def _collect_screenshot(message: Message, state: FSMContext, bot: Bot, file_id: str) -> None:
    settings = get_settings()
    data = await state.get_data()
    images = list(data.get("images", []))
    if len(images) >= settings.max_screenshots:
        await message.answer(
            f"Limit: {settings.max_screenshots} ta screenshot. "
            "Ortiqchasini yuborish uchun avvalgilarini o'chirib, qayta boshlang."
        )
        await delete_safe(bot, message.chat.id, message.message_id)
        return
    images.append(file_id)
    await state.update_data({"images": images})
    await delete_safe(bot, message.chat.id, message.message_id)

    text = (
        "2️⃣ <b>Screenshotlar</b>\n\n"
        f"Qabul qilindi: <b>{len(images)}/{settings.max_screenshots}</b>\n\n"
        "Yana rasm yuboring yoki <b>✅ Tayyor</b> tugmasini bosing."
    )
    prompt_id = data.get("shots_prompt_id")
    if prompt_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_id,
                text=text,
                reply_markup=screenshots_kb(len(images), settings.max_screenshots),
            )
            return
        except Exception:  # noqa: BLE001
            pass
    prompt = await message.answer(
        text, reply_markup=screenshots_kb(len(images), settings.max_screenshots)
    )
    await state.update_data({"shots_prompt_id": prompt.message_id})


@router.message(StateFilter(SellerStates.screenshots), F.photo)
async def seller_screenshot_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    await _collect_screenshot(message, state, bot, message.photo[-1].file_id)


@router.message(StateFilter(SellerStates.screenshots), F.document)
async def seller_screenshot_document(message: Message, state: FSMContext, bot: Bot) -> None:
    document = message.document
    if document is None or not (document.mime_type or "").startswith("image/"):
        await message.answer("Iltimos, rasm fayl yuboring.")
        return
    await _collect_screenshot(message, state, bot, document.file_id)


@router.callback_query(StateFilter(SellerStates.screenshots), F.data == "seller:shots:done")
async def seller_screenshots_done(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    images = list(data.get("images", []))
    if not images:
        await callback.answer("Kamida bitta screenshot yuboring.", show_alert=True)
        return
    await callback.answer()

    if data.get("editing_images"):
        await state.set_state(SellerStates.preview)
        await safe_edit(callback.message, "🖼 Screenshotlar yangilandi.", None)
        await _send_preview(bot, callback.message.chat.id, data)
        return

    await state.set_state(SellerStates.description)
    await safe_edit(
        callback.message,
        "3️⃣ <b>Description</b>\n\nAkkaunt haqida qisqacha ma'lumot yozing:",
        cancel_kb(),
    )


@router.message(StateFilter(SellerStates.description), F.text)
async def seller_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if not (3 <= len(description) <= MAX_DESCRIPTION):
        await message.answer("Description 3 dan 2000 belgigacha bo'lishi kerak.")
        return
    await state.update_data({"description": description})
    await state.set_state(SellerStates.login)
    await message.answer(
        "4️⃣ <b>Gmail yoki login</b>\n\nAkkauntning login ma'lumotini kiriting:",
        reply_markup=cancel_kb(),
    )


@router.message(StateFilter(SellerStates.login), F.text)
async def seller_login(message: Message, state: FSMContext, bot: Bot) -> None:
    login = (message.text or "").strip()
    if not (1 <= len(login) <= MAX_LOGIN):
        await message.answer("Login 1 dan 200 belgigacha bo'lishi kerak.")
        return
    await state.update_data({"login": login})
    await delete_safe(bot, message.chat.id, message.message_id)
    await state.set_state(SellerStates.password)
    await message.answer(
        "5️⃣ <b>Asosiy parol</b>\n\n"
        "Parolni yuboring. Xavfsizlik uchun bu xabar avtomatik o'chiriladi.\n"
        "Parol AES-GCM orqali shifrlanadi.",
        reply_markup=cancel_kb(),
    )


@router.message(StateFilter(SellerStates.password), F.text)
async def seller_password(message: Message, state: FSMContext, bot: Bot) -> None:
    password = message.text or ""
    if not (1 <= len(password) <= MAX_PASSWORD):
        await message.answer("Parol 1 dan 200 belgigacha bo'lishi kerak.")
        return
    await state.update_data({"password": password})
    await delete_safe(bot, message.chat.id, message.message_id)
    await state.set_state(SellerStates.extra_fields_menu)
    data = await state.get_data()
    settings = get_settings()
    await message.answer(
        "6️⃣ <b>Boshqa parollar va qo'shimcha ma'lumotlar</b>\n\n"
        "➕ <b>Add</b> orqali Gmail paroli, recovery email, recovery code, "
        "boshqa login yoki qo'shimcha parol qo'shishingiz mumkin.\n\n"
        "Maydonlar limiti: <b>"
        f"{len(data.get('extra_fields', []))}/{settings.max_credential_fields}</b>",
        reply_markup=extra_fields_menu_kb(
            len(data.get("extra_fields", [])), settings.max_credential_fields
        ),
    )


@router.callback_query(StateFilter(SellerStates.extra_fields_menu), F.data == "seller:field:add")
async def seller_add_field(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data({"field_flow": "extra"})
    await state.set_state(SellerStates.field_label)
    await safe_edit(
        callback.message,
        "➕ <b>Yangi maydon</b>\n\nMaydon nomini kiriting "
        "(masalan: <i>Gmail paroli</i>, <i>Recovery email</i>):",
        cancel_kb(),
    )


@router.message(StateFilter(SellerStates.field_label), F.text)
async def seller_field_label(message: Message, state: FSMContext) -> None:
    label = (message.text or "").strip()
    if not (1 <= len(label) <= MAX_LABEL):
        await message.answer(f"Maydon nomi 1-{MAX_LABEL} belgi bo'lishi kerak.")
        return
    await state.update_data({"field_label": label})
    await state.set_state(SellerStates.field_value)
    await message.answer(
        f"<b>{esc(label)}</b> qiymatini kiriting.\n\n"
        "Xavfsizlik uchun xabar avtomatik o'chiriladi.",
        reply_markup=cancel_kb(),
    )


@router.message(StateFilter(SellerStates.field_value), F.text)
async def seller_field_value(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("Qiymat bo'sh bo'lishi mumkin emas.")
        return
    data = await state.get_data()
    fields = list(data.get("extra_fields", []))
    fields.append({"label": data.get("field_label", "Maydon"), "value": value})
    await state.update_data({"extra_fields": fields, "field_label": None, "field_value": None})
    await delete_safe(bot, message.chat.id, message.message_id)
    settings = get_settings()

    if data.get("field_flow") == "edit":
        await state.set_state(SellerStates.edit_menu)
        await message.answer(
            _edit_menu_text(data | {"extra_fields": fields}),
            reply_markup=edit_menu_kb(fields, len(data.get("images", []))),
        )
        return

    await state.set_state(SellerStates.extra_fields_menu)
    await message.answer(
        "✅ Maydon qo'shildi.\n\n"
        f"Maydonlar: <b>{len(fields)}/{settings.max_credential_fields}</b>\n"
        "Yana qo'shishingiz yoki <b>✅ Tayyor</b> tugmasini bosishingiz mumkin.",
        reply_markup=extra_fields_menu_kb(len(fields), settings.max_credential_fields),
    )


@router.callback_query(StateFilter(SellerStates.extra_fields_menu), F.data == "seller:field:done")
async def seller_fields_done(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    await callback.answer()
    await state.set_state(SellerStates.price)
    await safe_edit(
        callback.message,
        "7️⃣ <b>Akkaunt narxi</b>\n\nNarxni faqat raqamlarda kiriting "
        "(masalan: 250000):",
        cancel_kb(),
    )


@router.message(StateFilter(SellerStates.price), F.text)
async def seller_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        price = to_decimal(raw)
    except (InvalidOperation, ValueError):
        await message.answer("Narxni faqat raqamlarda kiriting. Masalan: 250000")
        return
    settings = get_settings()
    if price < settings.min_price or price > settings.max_price:
        await message.answer(
            f"Narx {format_money(settings.min_price)} va {format_money(settings.max_price)} "
            "oralig'ida bo'lishi kerak."
        )
        return
    await state.update_data({"price": str(price)})
    await state.set_state(SellerStates.additional_info)
    await message.answer(
        "8️⃣ <b>Qo'shimcha ma'lumotlar</b>\n\n"
        "Akkaunt haqida qo'shimcha ma'lumot bo'lsa yozing. "
        "Bo'lmasa <b>⏭ O'tkazib yuborish</b> tugmasini bosing.",
        reply_markup=seller_extra_info_kb(),
    )


@router.message(StateFilter(SellerStates.additional_info), F.text)
async def seller_additional_info(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    info = (message.text or "").strip()
    if len(info) > MAX_ADDITIONAL:
        await message.answer(f"Qo'shimcha ma'lumot {MAX_ADDITIONAL} belgidan oshmasin.")
        return
    await state.update_data({"additional_info": info or None})
    await state.set_state(SellerStates.preview)
    data = await state.get_data()
    await _send_preview(bot, message.chat.id, data)


@router.callback_query(StateFilter(SellerStates.additional_info), F.data == "seller:additional:skip")
async def seller_additional_skip(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    await callback.answer()
    await state.update_data({"additional_info": None})
    await state.set_state(SellerStates.preview)
    data = await state.get_data()
    await callback.message.answer("⏭ Qo'shimcha ma'lumot o'tkazib yuborildi.")
    await _send_preview(bot, callback.message.chat.id, data)


# ---------------------------------------------------------------------------
# Preview / edit / publish
# ---------------------------------------------------------------------------


@router.callback_query(StateFilter(SellerStates.preview), F.data == "seller:preview:edit")
async def seller_preview_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.set_state(SellerStates.edit_menu)
    await safe_edit(
        callback.message,
        _edit_menu_text(data),
        edit_menu_kb(data.get("extra_fields", []), len(data.get("images", []))),
    )


@router.callback_query(StateFilter(SellerStates.preview), F.data == "seller:preview:back")
async def seller_preview_back(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    await callback.answer()
    await state.set_state(SellerStates.preview)
    data = await state.get_data()
    await _send_preview(bot, callback.message.chat.id, data)


@router.callback_query(StateFilter(SellerStates.preview), F.data == "seller:preview:cancel")
async def seller_preview_cancel(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    await callback.answer()
    await state.clear()
    text = "❌ E'lon joylash bekor qilindi.\n\nBosh menyu:"
    try:
        await callback.message.edit_text(text, reply_markup=main_menu_inline_kb())
    except Exception:  # noqa: BLE001
        await callback.message.answer(text, reply_markup=main_menu_inline_kb())


@router.callback_query(StateFilter(SellerStates.edit_menu), F.data.startswith("seller:editf:"))
async def seller_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":", 2)[2]
    await callback.answer()
    if field == "images":
        get_settings()
        await state.update_data({"images": [], "editing_images": True})
        await state.set_state(SellerStates.screenshots)
        settings = get_settings()
        await callback.message.answer(
            "🖼 <b>Yangi screenshotlar</b>\n\n"
            "Yangi rasmlarni yuboring. Eski rasmlar almashtiriladi.",
            reply_markup=screenshots_kb(0, settings.max_screenshots),
        )
        await state.update_data({"shots_prompt_id": None})
        return
    await state.update_data({"edit_field": field})
    await state.set_state(SellerStates.edit_value)
    prompts = {
        "nickname": "Yangi nickname kiriting:",
        "description": "Yangi description kiriting:",
        "login": "Yangi login kiriting:",
        "password": "Yangi asosiy parolni kiriting:",
        "price": "Yangi narxni raqamlarda kiriting:",
        "additional_info": "Yangi qo'shimcha ma'lumotni kiriting:",
    }
    await safe_edit(callback.message, prompts.get(field, "Yangi qiymat kiriting:"), cancel_kb())


@router.callback_query(StateFilter(SellerStates.edit_menu), F.data.startswith("seller:editfield:"))
async def seller_edit_extra_field(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        index = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer("Maydon topilmadi.", show_alert=True)
        return
    data = await state.get_data()
    fields = list(data.get("extra_fields", []))
    if index < 0 or index >= len(fields):
        await callback.answer("Maydon topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.update_data({"edit_field": f"extra:{index}"})
    await state.set_state(SellerStates.edit_value)
    await safe_edit(
        callback.message,
        f"<b>{esc(fields[index].get('label', 'Maydon'))}</b> uchun yangi qiymat kiriting:",
        cancel_kb(),
    )


@router.message(StateFilter(SellerStates.edit_value), F.text)
async def seller_edit_value(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    field = data.get("edit_field", "")
    value = (message.text or "").strip()
    if not value:
        await message.answer("Qiymat bo'sh bo'lishi mumkin emas.")
        return
    if field.startswith("extra:"):
        try:
            index = int(field.split(":", 1)[1])
        except ValueError:
            index = -1
        fields = list(data.get("extra_fields", []))
        if index < 0 or index >= len(fields):
            await message.answer("Maydon topilmadi.")
            return
        fields[index]["value"] = value
        await state.update_data({"extra_fields": fields})
    elif field == "password":
        await state.update_data({"password": value})
        await delete_safe(bot, message.chat.id, message.message_id)
    elif field == "price":
        try:
            price = to_decimal(value)
        except (InvalidOperation, ValueError):
            await message.answer("Narxni raqamlarda kiriting.")
            return
        settings = get_settings()
        if price < settings.min_price or price > settings.max_price:
            await message.answer("Narx ruxsat etilgan chegarada emas.")
            return
        await state.update_data({"price": str(price)})
    elif field in {"nickname", "description", "login", "additional_info"}:
        await state.update_data({field: value})
        if field in {"login"}:
            await delete_safe(bot, message.chat.id, message.message_id)
    else:
        await message.answer("Maydon topilmadi.")
        return

    await state.set_state(SellerStates.preview)
    data = await state.get_data()
    await message.answer("✅ Yangilandi.")
    await _send_preview(bot, message.chat.id, data)


@router.callback_query(StateFilter(SellerStates.edit_menu), F.data == "seller:preview:back")
async def seller_edit_back(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    await state.set_state(SellerStates.preview)
    data = await state.get_data()
    await _send_preview(bot, callback.message.chat.id, data)


@router.callback_query(StateFilter(SellerStates.edit_menu), F.data == "seller:field:add")
async def seller_edit_add_field(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data({"field_flow": "edit"})
    await state.set_state(SellerStates.field_label)
    await safe_edit(
        callback.message,
        "➕ Yangi maxfiy maydon nomini kiriting:",
        cancel_kb(),
    )


@router.callback_query(StateFilter(SellerStates.preview), F.data == "seller:preview:confirm")
async def seller_preview_confirm(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    await callback.answer()
    await state.set_state(SellerStates.warning)
    locale = user_locale(user)
    await safe_edit(callback.message, t("seller.warning", locale), warning_kb(locale))


@router.callback_query(StateFilter(SellerStates.warning), F.data == "seller:warning:back")
async def seller_warning_back(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    await callback.answer()
    await state.set_state(SellerStates.preview)
    data = await state.get_data()
    await _send_preview(bot, callback.message.chat.id, data)


@router.callback_query(StateFilter(SellerStates.warning), F.data == "seller:warning:yes")
async def seller_warning_yes(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    data = await state.get_data()
    if data.get("publishing"):
        await callback.answer("E'lon allaqachon joylanmoqda...", show_alert=True)
        return
    await state.update_data({"publishing": True})
    await callback.answer()

    try:
        draft = _draft_from_data(data)
        account = await account_service.create_account(session, user, draft)
        await mark_seller(session, user)
    except AccountValidationError as exc:
        await state.update_data({"publishing": False})
        await callback.message.answer(f"❌ {esc(str(exc))}", reply_markup=preview_kb())
        await state.set_state(SellerStates.preview)
        return
    except Exception:  # noqa: BLE001
        await session.rollback()
        await state.update_data({"publishing": False})
        await state.set_state(SellerStates.preview)
        logger.exception("Account publishing failed for user %s", user.id)
        await callback.message.answer(
            "❌ E'lonni joylashda xatolik yuz berdi. Qayta urinib ko'ring.",
            reply_markup=preview_kb(),
        )
        return

    try:
        async with session.begin_nested():
            await notification_service.notify(
                session,
                bot,
                user,
                "✅ <b>Akkauntingiz marketplace'ga joylandi!</b>\n\n"
                f"🎮 {platform_display(account.platform)}\n"
                f"🔤 {esc(account.nickname)}\n"
                f"💵 {format_money(account.price, account.currency)}",
                notification_type="account_published",
                payload={"account_id": account.id},
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to queue publish notification for user %s", user.id)
    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Mening akkauntlarim", callback_data="seller:myaccounts")
    builder.button(text="🏠 Bosh menyu", callback_data="menu:home")
    builder.adjust(1)
    await callback.message.answer(
        "🎉 <b>E'lon muvaffaqiyatli joylandi!</b>\n\n"
        "Akkaunt ACTIVE holatida marketplace'da ko'rinadi.\n"
        "Buyurtmalar va holat o'zgarishlari haqida sizga xabar beriladi.",
        reply_markup=builder.as_markup(),
    )


# ---------------------------------------------------------------------------
# My accounts
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "seller:myaccounts")
async def seller_myaccounts(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(SellerStates.my_accounts)
    locale = user_locale(user)
    await safe_edit(
        callback.message,
        t("listings.title", locale),
        seller_accounts_menu_kb(locale),
    )


@router.callback_query(F.data.startswith("seller:list:"))
async def seller_list(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return
    _, _, flt, page_raw = parts
    if flt not in VALID_SELLER_FILTERS:
        await callback.answer("Noto'g'ri filtr.", show_alert=True)
        return
    try:
        page = max(0, int(page_raw))
    except ValueError:
        page = 0
    await callback.answer()
    await state.set_state(SellerStates.my_accounts)
    settings = get_settings()
    total = await account_service.count_seller_accounts(session, user.id, flt)
    offset = page * settings.page_size
    accounts = await account_service.list_seller_accounts(
        session, user.id, flt=flt, offset=offset, limit=settings.page_size
    )
    has_next = offset + len(accounts) < total

    locale = user_locale(user)
    titles = {
        "active": t("listings.active", locale),
        "pending": t("listings.pending", locale),
        "sold": t("listings.sold", locale),
        "all": t("listings.all", locale),
    }
    title = titles[flt]
    total_pages = max(1, (total + settings.page_size - 1) // settings.page_size)
    if total == 0:
        text = f"{title}\n\n{t('listings.empty', locale)}"
    else:
        text = (
            f"{title}\n\n"
            + t(
                "list.page",
                locale,
                total=total,
                page=page + 1,
                total_pages=total_pages,
            )
        )
    await safe_edit(
        callback.message,
        text,
        seller_list_kb(accounts, page=page, has_next=has_next, flt=flt),
    )


@router.callback_query(F.data.startswith("seller:acc:view:"))
async def seller_account_view(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, bot: Bot
) -> None:
    try:
        account_id = int(callback.data.split(":", 3)[3])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await _load_own_account(session, account_id, user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(SellerStates.my_accounts)
    first_image = account.images[0].file_id if account.images else None
    await send_photo_or_text(
        bot,
        callback.message.chat.id,
        file_id=first_image,
        text=_account_detail_text(account),
        reply_markup=seller_account_detail_kb(account),
    )


@router.callback_query(F.data.startswith("seller:acc:delconfirm:"))
async def seller_account_delete_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, bot: Bot
) -> None:
    try:
        account_id = int(callback.data.split(":", 3)[3])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await _load_own_account(session, account_id, user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    try:
        await account_service.soft_delete_account(session, account)
    except AccountValidationError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("E'lon o'chirildi.")
    await notification_service.notify(
        session,
        bot,
        user,
        f"🗑 E'lon o'chirildi: <b>{esc(account.nickname)}</b>",
        notification_type="account_deleted",
        payload={"account_id": account.id},
    )
    await state.set_state(SellerStates.my_accounts)
    await callback.message.answer(
        "🗑 E'lon o'chirildi.", reply_markup=seller_accounts_menu_kb()
    )


@router.callback_query(F.data.startswith("seller:acc:del:"))
async def seller_account_delete_prompt(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    try:
        account_id = int(callback.data.split(":", 3)[3])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await _load_own_account(session, account_id, user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(SellerStates.account_delete_confirm)
    await safe_edit(
        callback.message,
        f"🗑 <b>{esc(account.nickname)}</b> e'lonini o'chirmoqchimisiz?\n\n"
        "Bu amalni qaytarib bo'lmaydi.",
        account_delete_confirm_kb(account.id),
    )


@router.callback_query(F.data.startswith("seller:acc:edit:"))
async def seller_account_edit(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    try:
        account_id = int(callback.data.split(":", 3)[3])
    except (ValueError, IndexError):
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    account = await _load_own_account(session, account_id, user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    if account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.", show_alert=True)
        return
    await callback.answer()
    await _show_account_edit_menu(callback.message, state, account)


@router.callback_query(F.data.startswith("seller:acc:editfield:"))
async def seller_account_edit_field(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return
    try:
        account_id = int(parts[3])
    except ValueError:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    field = parts[4]
    account = await _load_own_account(session, account_id, user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    if account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Bu e'lonni tahrirlab bo'lmaydi.", show_alert=True)
        return

    await callback.answer()
    if field == "images":
        settings = get_settings()
        await state.update_data(
            {
                "edit_account_id": account.id,
                "acc_images": [],
                "acc_images_prompt_id": None,
            }
        )
        await state.set_state(SellerStates.account_images)
        await callback.message.answer(
            "🖼 Yangi screenshotlarni yuboring. Eski rasmlar almashtiriladi.",
            reply_markup=screenshots_kb(0, settings.max_screenshots),
        )
        return
    if field == "addfield":
        await state.update_data({"edit_account_id": account.id})
        await state.set_state(SellerStates.account_field_label)
        await safe_edit(callback.message, "➕ Yangi maxfiy maydon nomini kiriting:", cancel_kb())
        return

    await state.update_data({"edit_account_id": account.id, "acc_edit_field": field})
    await state.set_state(SellerStates.account_edit_value)
    prompts = {
        "nickname": "Yangi nickname:",
        "description": "Yangi description:",
        "login": "Yangi login:",
        "password": "Yangi asosiy parol:",
        "price": "Yangi narx (raqamlarda):",
        "additional_info": "Yangi qo'shimcha ma'lumot:",
    }
    await safe_edit(callback.message, prompts.get(field, "Yangi qiymat:"), cancel_kb())


@router.callback_query(F.data.startswith("seller:acc:editcf:"))
async def seller_account_edit_cf(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return
    try:
        account_id = int(parts[3])
        field_id = int(parts[4])
    except ValueError:
        await callback.answer("Maydon topilmadi.", show_alert=True)
        return
    account = await _load_own_account(session, account_id, user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    if account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.", show_alert=True)
        return
    await callback.answer()
    await state.update_data(
        {"edit_account_id": account.id, "acc_edit_cf_id": field_id, "acc_edit_field": "cf"}
    )
    await state.set_state(SellerStates.account_edit_value)
    await safe_edit(callback.message, "Yangi maxfiy qiymatni kiriting:", cancel_kb())


@router.callback_query(F.data.startswith("seller:acc:delfield:"))
async def seller_account_delete_field(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return
    try:
        account_id = int(parts[3])
        field_id = int(parts[4])
    except ValueError:
        await callback.answer("Maydon topilmadi.", show_alert=True)
        return
    account = await _load_own_account(session, account_id, user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    try:
        deleted = await account_service.delete_credential_field(session, account, field_id)
    except AccountValidationError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("O'chirildi." if deleted else "Maydon topilmadi.")
    account = await account_service.get_account(session, account.id)
    if account is not None:
        await _show_account_edit_menu(callback.message, state, account)


@router.message(StateFilter(SellerStates.account_edit_value), F.text)
async def seller_account_edit_value(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    account = await _load_own_account(session, data.get("edit_account_id", 0), user)
    if account is None:
        await message.answer("E'lon topilmadi.")
        await state.clear()
        return
    if account.status != AccountStatus.ACTIVE.value:
        await message.answer("Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.")
        await state.clear()
        return
    value = (message.text or "").strip()
    if not value:
        await message.answer("Qiymat bo'sh bo'lishi mumkin emas.")
        return
    field = data.get("acc_edit_field")
    try:
        if field == "cf":
            updated = await account_service.update_credential_field(
                session, account, data.get("acc_edit_cf_id", 0), value
            )
            if updated is None:
                await message.answer("Maydon topilmadi.")
                return
        elif field == "price":
            price = to_decimal(value)
            settings = get_settings()
            if price < settings.min_price or price > settings.max_price:
                await message.answer("Narx ruxsat etilgan chegarada emas.")
                return
            await account_service.update_account_main_fields(session, account, price=price)
        elif field in {"nickname", "description", "login", "password", "additional_info"}:
            await account_service.update_account_main_fields(session, account, **{field: value})
        else:
            await message.answer("Maydon topilmadi.")
            return
    except AccountValidationError as exc:
        await message.answer(f"❌ {esc(str(exc))}")
        return
    except (InvalidOperation, ValueError):
        await message.answer("Qiymat formati noto'g'ri.")
        return

    await delete_safe(bot, message.chat.id, message.message_id)
    account = await account_service.get_account(session, account.id)
    if account is None:
        await state.clear()
        return
    await message.answer("✅ Yangilandi.")
    await _show_account_edit_menu(message, state, account)


@router.message(StateFilter(SellerStates.account_field_label), F.text)
async def seller_account_field_label(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    label = (message.text or "").strip()
    if not (1 <= len(label) <= MAX_LABEL):
        await message.answer(f"Maydon nomi 1-{MAX_LABEL} belgi bo'lishi kerak.")
        return
    await state.update_data({"acc_field_label": label})
    await state.set_state(SellerStates.account_field_value)
    await message.answer("Yangi maxfiy qiymatni kiriting:", reply_markup=cancel_kb())


@router.message(StateFilter(SellerStates.account_field_value), F.text)
async def seller_account_field_value(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    data = await state.get_data()
    account = await _load_own_account(session, data.get("edit_account_id", 0), user)
    if account is None:
        await message.answer("E'lon topilmadi.")
        await state.clear()
        return
    if account.status != AccountStatus.ACTIVE.value:
        await message.answer("Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.")
        await state.clear()
        return
    value = (message.text or "").strip()
    try:
        await account_service.add_credential_field(
            session, account, data.get("acc_field_label", "Maydon"), value
        )
    except AccountValidationError as exc:
        await message.answer(f"❌ {esc(str(exc))}")
        return
    await delete_safe(bot, message.chat.id, message.message_id)
    account = await account_service.get_account(session, account.id)
    if account is None:
        await state.clear()
        return
    await message.answer("✅ Maydon qo'shildi.")
    await _show_account_edit_menu(message, state, account)


async def _collect_account_image(
    message: Message, state: FSMContext, bot: Bot, file_id: str
) -> None:
    settings = get_settings()
    data = await state.get_data()
    images = list(data.get("acc_images", []))
    if len(images) >= settings.max_screenshots:
        await message.answer(f"Limit: {settings.max_screenshots} ta screenshot.")
        await delete_safe(bot, message.chat.id, message.message_id)
        return
    images.append(file_id)
    await state.update_data({"acc_images": images})
    await delete_safe(bot, message.chat.id, message.message_id)
    text = (
        "🖼 Screenshotlar\n\n"
        f"Qabul qilindi: <b>{len(images)}/{settings.max_screenshots}</b>\n\n"
        "Yana yuboring yoki <b>✅ Tayyor</b> tugmasini bosing."
    )
    prompt_id = data.get("acc_images_prompt_id")
    if prompt_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_id,
                text=text,
                reply_markup=screenshots_kb(len(images), settings.max_screenshots),
            )
            return
        except Exception:  # noqa: BLE001
            pass
    prompt = await message.answer(
        text, reply_markup=screenshots_kb(len(images), settings.max_screenshots)
    )
    await state.update_data({"acc_images_prompt_id": prompt.message_id})


@router.message(StateFilter(SellerStates.account_images), F.photo)
async def seller_account_image_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    await _collect_account_image(message, state, bot, message.photo[-1].file_id)


@router.message(StateFilter(SellerStates.account_images), F.document)
async def seller_account_image_document(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    document = message.document
    if document is None or not (document.mime_type or "").startswith("image/"):
        await message.answer("Iltimos, rasm fayl yuboring.")
        return
    await _collect_account_image(message, state, bot, document.file_id)


@router.callback_query(StateFilter(SellerStates.account_images), F.data == "seller:shots:done")
async def seller_account_images_done(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    data = await state.get_data()
    images = list(data.get("acc_images", []))
    if not images:
        await callback.answer("Kamida bitta screenshot yuboring.", show_alert=True)
        return
    account = await _load_own_account(session, data.get("edit_account_id", 0), user)
    if account is None:
        await callback.answer("E'lon topilmadi.", show_alert=True)
        return
    if account.status != AccountStatus.ACTIVE.value:
        await callback.answer("Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.", show_alert=True)
        return
    try:
        await account_service.replace_account_images(session, account, images)
    except AccountValidationError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer("Screenshotlar yangilandi.")
    account = await account_service.get_account(session, account.id)
    if account is not None:
        data = await state.get_data()
        await state.update_data({"images": [], "editing_images": False})
        await _show_account_edit_menu(callback.message, state, account)
