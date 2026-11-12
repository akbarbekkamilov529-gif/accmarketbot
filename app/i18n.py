from __future__ import annotations

from contextvars import ContextVar, Token

from app.models import AccountStatus, DisputeStatus, OrderStatus, TransactionType

SUPPORTED_LOCALES: tuple[str, ...] = ("uz", "ru")
DEFAULT_LOCALE = "uz"

LOCALE_LABELS: dict[str, str] = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
}

MENU_KEYS: tuple[str, ...] = (
    "profile",
    "buyer",
    "seller",
    "listings",
    "balance",
    "stats",
    "settings",
    "help",
    "orders",
    "sold",
    "bought",
    "home",
)

_CURRENT_LOCALE: ContextVar[str] = ContextVar("current_locale", default=DEFAULT_LOCALE)

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "language.title": "🌐 Tilni tanlang / Выберите язык",
        "language.invalid": "Tilni tanlashda xatolik yuz berdi.",
        "menu.profile": "👤 Profil",
        "menu.buyer": "🛒 Akkaunt sotib olish",
        "menu.seller": "📤 Akkaunt sotish",
        "menu.listings": "📦 Mening e'lonlarim",
        "menu.balance": "💰 Balans",
        "menu.stats": "📊 Statistika",
        "menu.settings": "⚙️ Sozlamalar",
        "menu.help": "🆘 Yordam",
        "menu.orders": "📦 Buyurtmalarim",
        "menu.sold": "📤 Sotgan akkauntlarim",
        "menu.bought": "📥 Sotib olganlarim",
        "menu.home": "🏠 Bosh menyu",
        "common.back": "⬅️ Orqaga",
        "common.home": "🏠 Bosh menyu",
        "common.cancel": "❌ Bekor qilish",
        "common.page": "Sahifa: <b>{page}/{total}</b>",
        "common.empty": "📭 Ma'lumot topilmadi.",
        "common.not_found": "Topilmadi.",
        "common.invalid_request": "Noto'g'ri so'rov.",
        "common.previous": "⬅️ Oldingi",
        "common.next": "Keyingi ➡️",
        "common.updated": "✅ Yangilandi.",
        "common.deleted": "🗑 O'chirildi.",
        "common.saved": "✅ Saqlandi.",
        "common.skip": "⏭ O'tkazib yuborish",
        "common.done": "✅ Tayyor",
        "common.yes": "✅ Ha",
        "common.no": "❌ Yo'q",
        "profile.title": "👤 <b>Profil</b>",
        "profile.name": "Ism",
        "profile.username": "Username",
        "profile.telegram_id": "Telegram ID",
        "profile.balance": "Balans",
        "profile.sold_count": "Sotilgan akkauntlar",
        "profile.bought_count": "Sotib olingan akkauntlar",
        "profile.active_listings": "Faol e'lonlar",
        "profile.pending_trades": "Kutilayotgan bitimlar",
        "profile.total_trade": "Umumiy savdo hajmi",
        "profile.rating": "Reyting",
        "profile.registered": "Ro'yxatdan o'tgan",
        "profile.hint": "Asosiy menyudan kerakli bo'limni tanlang.",
        "profile.no_rating": "Hozircha baho yo'q",
        "profile.no_username": "mavjud emas",
        "profile.orders_button": "📦 Buyurtmalarim",
        "profile.sold_button": "📤 Sotganlarim",
        "profile.bought_button": "📥 Sotib olganlarim",
        "balance.title": "💰 <b>Balans</b>",
        "balance.seller": "Seller balansi",
        "balance.buyer": "Buyer balansi",
        "balance.available": "Mavjud",
        "balance.pending": "Kutilayotgan",
        "balance.held": "Escrowda ushlangan",
        "balance.total_earned": "Jami ishlangan",
        "balance.total_released": "Jami chiqarilgan",
        "balance.total_spent": "Jami sarflangan",
        "balance.history_button": "📜 Tranzaksiyalar tarixi",
        "balance.history_title": "📜 <b>Tranzaksiyalar tarixi</b>",
        "balance.history_empty": "📭 Hozircha tranzaksiyalar yo'q.",
        "balance.history_item": "• {date} — {type}: <b>{amount}</b>",
        "sold.title": "📤 <b>Sotgan akkauntlarim</b>",
        "sold.empty": "📭 Hozircha sotilgan akkaunt yo'q.",
        "bought.title": "📥 <b>Sotib olgan akkauntlarim</b>",
        "bought.empty": "📭 Hozircha sotib olingan akkaunt yo'q.",
        "order.entry": "{status} · {public_id} · {nickname} · {amount}",
        "list.page": "Jami: <b>{total}</b> ta\nSahifa: <b>{page}/{total_pages}</b>",
        "listings.title": "📦 <b>Mening e'lonlarim</b>\n\nBo'limni tanlang:",
        "listings.active": "🟢 Sotuvdagi akkauntlar",
        "listings.pending": "🟡 Band qilinganlar",
        "listings.sold": "✅ Sotilgan akkauntlar",
        "listings.all": "📚 Barcha e'lonlar",
        "listings.new": "➕ Yangi akkaunt joylash",
        "listings.empty": "📭 Hozircha akkaunt yo'q.",
        "section.buyer": "🛒 <b>Akkaunt sotib olish</b>\n\nPlatformani tanlang:",
        "section.seller": "📤 <b>Akkaunt sotish</b>\n\nPlatformani tanlang.",
        "section.orders": "📦 <b>Buyurtmalarim</b>\n\nXaridlar yoki sotuvlar bo'limini tanlang:",
        "orders.buyer": "🛍 Xaridlarim",
        "orders.seller": "💰 Sotuvlarim",
        "orders.title_buyer": "🛍 Xaridlarim",
        "orders.title_seller": "💰 Sotuvlarim",
        "orders.empty": "📭 Buyurtmalar yo'q.",
        "orders.hint": "Buyurtmani tanlang:",
        "stats.title": "📊 <b>Statistika</b>",
        "stats.sales_title": "Sotuvlar",
        "stats.purchases_title": "Xaridlar",
        "stats.completed_sales": "Yakunlangan sotuvlar",
        "stats.completed_purchases": "Yakunlangan xaridlar",
        "stats.sales_volume": "Sotuv hajmi",
        "stats.purchases_volume": "Xarid hajmi",
        "stats.total_trade": "Jami savdo hajmi",
        "stats.commission": "Platforma komissiyasi",
        "stats.net_earned": "Sof daromad",
        "stats.active_listings": "Faol e'lonlar",
        "stats.pending_trades": "Kutilayotgan bitimlar",
        "stats.rating": "Reyting",
        "stats.reviews": "Sharhlar",
        "settings.title": "⚙️ <b>Sozlamalar</b>",
        "settings.language": "Til",
        "settings.current": "Joriy til",
        "settings.choose": "Tilni tanlang:",
        "settings.refresh_profile": "🔄 Profilni yangilash",
        "settings.language_changed": "✅ Til o'zgartirildi.",
        "settings.profile_refreshed": "✅ Profil yangilandi.",
        "help.title": "🆘 <b>Yordam</b>",
        "help.body": (
            "🛒 <b>Buyer</b> — platformani tanlab, akkaunt kartasini oching va sotib oling.\n"
            "📤 <b>Seller</b> — platformani tanlab, akkaunt ma'lumotlarini yuboring.\n"
            "📦 <b>Mening e'lonlarim</b> — e'lonlaringizni boshqaring.\n"
            "💰 <b>Balans</b> — balans va tranzaksiyalar tarixini ko'ring.\n\n"
            "⚠️ Parollar faqat shifrlangan holda saqlanadi va faqat xaridorga "
            "to'lovdan keyin ko'rsatiladi.\n\n"
            "Bot administrator panelisiz, to'liq avtomatik ishlaydi."
        ),
        "help.support": "📞 <b>Qo'llab-quvvatlash:</b> {support}",
        "status.pending_payment": "⏳ To'lov kutilmoqda",
        "status.paid": "💳 To'langan",
        "status.delivered": "📤 Topshirilgan",
        "status.completed": "✅ Yakunlangan",
        "status.disputed": "⚠️ Nizoda",
        "status.cancelled": "❌ Bekor qilingan",
        "status.refunded": "↩️ Qaytarilgan",
        "status.unresolved": "🔴 Hal qilinmagan",
        "tx.payment": "To'lov",
        "tx.escrow_hold": "Escrowga ushlash",
        "tx.hourly_release": "Soatlik chiqarish",
        "tx.completion_release": "Yakuniy chiqarish",
        "tx.platform_commission": "Platforma komissiyasi",
        "tx.refund": "Qaytarish",
        "tx.payout": "Pul chiqarish",
        "tx.adjustment": "Tuzatish",
        "account.status.active": "🟢 Sotuvda",
        "account.status.reserved": "🟡 Band qilingan",
        "account.status.sold": "✅ Sotilgan",
        "account.status.deleted": "🗑 O'chirilgan",
        "account.status.draft": "⚪️ Qoralama",
        "dispute.status.open": "⚠️ Ochiq",
        "dispute.status.seller_responded": "💬 Seller javob berdi",
        "dispute.status.resolved": "✅ Hal qilindi",
        "dispute.status.unresolved": "🕓 Hal qilinmagan",
        "dispute.status.closed": "🔒 Yopildi",
        "order.detail_title": "📦 <b>Buyurtma #{public_id}</b>",
        "order.status_label": "📌 <b>Holat:</b> {status}",
        "order.your_role": "👤 <b>Sizning rolingiz:</b> {role}",
        "order.role_buyer": "Buyer",
        "order.role_seller": "Seller",
        "order.platform": "🎮 <b>Platforma:</b> {platform}",
        "order.account": "🔤 <b>Akkaunt:</b> {nickname}",
        "order.amount": "💵 <b>Summa:</b> {amount}",
        "order.commission": "🏦 <b>Platforma komissiyasi:</b> {amount}",
        "order.seller_share": "💰 <b>Seller ulushi:</b> {amount}",
        "order.created": "🕐 <b>Yaratilgan:</b> {date}",
        "order.paid_at": "💳 <b>To'langan:</b> {date}",
        "order.delivered_at": "📤 <b>Topshirilgan:</b> {date}",
        "order.completed_at": "✅ <b>Yakunlangan:</b> {date}",
        "order.dispute_reason": "⚠️ <b>Nizo sababi:</b> {reason}",
        "order.not_found": "Buyurtma topilmadi.",
        "order.not_yours": "Bu buyurtma sizga tegishli emas.",
        "order.creds_only_buyer": "Bu ma'lumotlar faqat xaridorga ko'rsatiladi.",
        "order.creds_locked": "Ma'lumotlar hali ochilmagan.",
        "order.creds_title": "🔐 <b>AKKAUNT MAXFIY MA'LUMOTLARI</b>",
        "order.creds_nickname": "🔤 <b>Nickname:</b> {nickname}",
        "order.creds_platform": "🎮 <b>Platforma:</b> {platform}",
        "order.creds_login": "👤 <b>Login:</b> <code>{login}</code>",
        "order.creds_password": "🔑 <b>Asosiy parol:</b> <code>{password}</code>",
        "order.creds_fields_title": "<b>Qo'shimcha maydonlar:</b>",
        "order.creds_field": "• <b>{label}:</b> <code>{value}</code>",
        "order.creds_warning": "⚠️ Bu ma'lumotlarni hech kimga bermang. Akkauntga qayta kirmang.",
        "order.completed_alert": "Buyurtma yakunlandi.",
        "order.completed_title": "✅ <b>Buyurtma yakunlandi!</b>",
        "order.completed_body": (
            "Akkaunt SOLD holatiga o'tdi.\n"
            "Seller ulushi escrow'dan chiqarildi.\n\n"
            "Xizmatni baholaysizmi?"
        ),
        "order.completed_notify": (
            "✅ <b>Buyurtma yakunlandi!</b>\n\n"
            "📦 #{public_id}\n"
            "💰 Seller ulushi: {amount}\n\n"
            "Mablag' balansingizga o'tkazildi."
        ),
        "order.delivered_alert": "Topshirilgan deb belgilandi.",
        "order.delivered_notify": (
            "📤 <b>Seller akkauntni topshirdi!</b>\n\n"
            "📦 #{public_id}\n"
            "🔤 {nickname}\n\n"
            "Akkauntni tekshirib, tasdiqlang. Muammo bo'lsa nizo oching."
        ),
        "order.cancelled_alert": "Buyurtma bekor qilindi.",
        "order.cancelled_notify": (
            "ℹ️ <b>To'lov holati o'zgardi</b>\n\n"
            "📦 #{public_id} buyurtmasi bekor qilindi.\n"
            "Akkaunt yana sotuvga qaytdi."
        ),
        "order.cancelled_body": "❌ Buyurtma bekor qilindi. Akkaunt yana sotuvga qaytdi.",
        "order.action_deliver": "📤 Akkauntni topshirdim",
        "order.action_creds": "🔐 Login ma'lumotlarini ko'rish",
        "order.action_confirm": "✅ Akkauntni tasdiqlash",
        "order.action_dispute": "⚠️ Nizo ochish",
        "order.action_review": "⭐ Baho berish",
        "order.action_view_dispute": "💬 Nizoni ko'rish",
        "order.action_cancel": "❌ Buyurtmani bekor qilish",
        "seller.preview_title": "🔎 <b>E'lon preview</b>",
        "seller.preview_platform": "🎮 <b>Platforma:</b> {platform}",
        "seller.preview_nickname": "🔤 <b>Nickname:</b> {nickname}",
        "seller.preview_description": "📝 <b>Description:</b> {description}",
        "seller.preview_login": "🔐 <b>Login:</b> {login}",
        "seller.preview_password": "🔑 <b>Asosiy parol:</b> •••••• (shifrlanadi)",
        "seller.preview_price": "💵 <b>Narx:</b> {price}",
        "seller.preview_screenshots": "🖼 <b>Screenshotlar:</b> {count} ta",
        "seller.preview_additional": "📎 <b>Qo'shimcha:</b> {text}",
        "seller.preview_fields_title": "<b>🔐 Qo'shimcha maxfiy maydonlar:</b>",
        "seller.preview_field_item": "• {label}: ••••••",
        "seller.preview_encrypted_note": "ℹ️ Barcha parollar AES-GCM bilan shifrlanadi.",
        "seller.edit_title": (
            "✏️ <b>Tahrirlash</b>\n\n"
            "Qaysi maydonni o'zgartirmoqchisiz? Quyidagi tugmalardan birini tanlang."
        ),
        "seller.edit_account_title": "✏️ <b>E'lonni tahrirlash</b>\n\nKerakli maydonni tanlang.",
        "seller.platform_not_found": "Platforma topilmadi.",
        "seller.platform_selected": "{emoji} <b>{name}</b> tanlandi.\n\n1️⃣ Akkaunt nomi yoki nickname kiriting:",
        "seller.nickname_invalid": "Nickname 1 dan 128 belgigacha bo'lishi kerak. Qayta kiriting.",
        "seller.screenshots_prompt": (
            "2️⃣ <b>Screenshotlar</b>\n\n"
            "Akkaunt screenshotlarini rasm sifatida yuboring.\n"
            "Kamida 1 ta, ko'pi bilan {max} ta.\n\n"
            "Tugagach <b>✅ Tayyor</b> tugmasini bosing."
        ),
        "seller.screenshots_limit": (
            "Limit: {max} ta screenshot. Ortiqchasini yuborish uchun avvalgilarini "
            "o'chirib, qayta boshlang."
        ),
        "seller.screenshots_received": (
            "2️⃣ <b>Screenshotlar</b>\n\n"
            "Qabul qilindi: <b>{count}/{max}</b>\n\n"
            "Yana rasm yuboring yoki <b>✅ Tayyor</b> tugmasini bosing."
        ),
        "seller.screenshots_updated": "🖼 Screenshotlar yangilandi.",
        "seller.please_image": "Iltimos, rasm fayl yuboring.",
        "seller.min_screenshot": "Kamida bitta screenshot yuboring.",
        "seller.description_prompt": "3️⃣ <b>Description</b>\n\nAkkaunt haqida qisqacha ma'lumot yozing:",
        "seller.description_invalid": "Description 3 dan 2000 belgigacha bo'lishi kerak.",
        "seller.login_prompt": "4️⃣ <b>Gmail yoki login</b>\n\nAkkauntning login ma'lumotini kiriting:",
        "seller.login_invalid": "Login 1 dan 200 belgigacha bo'lishi kerak.",
        "seller.password_prompt": (
            "5️⃣ <b>Asosiy parol</b>\n\n"
            "Parolni yuboring. Xavfsizlik uchun bu xabar avtomatik o'chiriladi.\n"
            "Parol AES-GCM orqali shifrlanadi."
        ),
        "seller.password_invalid": "Parol 1 dan 200 belgigacha bo'lishi kerak.",
        "seller.extra_fields_title": (
            "6️⃣ <b>Boshqa parollar va qo'shimcha ma'lumotlar</b>\n\n"
            "➕ <b>Add</b> orqali Gmail paroli, recovery email, recovery code, "
            "boshqa login yoki qo'shimcha parol qo'shishingiz mumkin.\n\n"
            "Maydonlar limiti: <b>{count}/{max}</b>"
        ),
        "seller.field_add_prompt": (
            "➕ <b>Yangi maydon</b>\n\n"
            "Maydon nomini kiriting (masalan: <i>Gmail paroli</i>, <i>Recovery email</i>):"
        ),
        "seller.field_label_invalid": "Maydon nomi 1-{max} belgi bo'lishi kerak.",
        "seller.field_value_prompt": (
            "<b>{label}</b> qiymatini kiriting.\n\n"
            "Xavfsizlik uchun xabar avtomatik o'chiriladi."
        ),
        "seller.field_value_empty": "Qiymat bo'sh bo'lishi mumkin emas.",
        "seller.field_added": (
            "✅ Maydon qo'shildi.\n\n"
            "Maydonlar: <b>{count}/{max}</b>\n"
            "Yana qo'shishingiz yoki <b>✅ Tayyor</b> tugmasini bosishingiz mumkin."
        ),
        "seller.price_prompt": (
            "7️⃣ <b>Akkaunt narxi</b>\n\n"
            "Narxni faqat raqamlarda kiriting (masalan: 250000):"
        ),
        "seller.price_invalid": "Narxni faqat raqamlarda kiriting. Masalan: 250000",
        "seller.price_range": "Narx {min} va {max} oralig'ida bo'lishi kerak.",
        "seller.additional_title": (
            "8️⃣ <b>Qo'shimcha ma'lumotlar</b>\n\n"
            "Akkaunt haqida qo'shimcha ma'lumot bo'lsa yozing. "
            "Bo'lmasa <b>⏭ O'tkazib yuborish</b> tugmasini bosing."
        ),
        "seller.additional_too_long": "Qo'shimcha ma'lumot {max} belgidan oshmasin.",
        "seller.additional_skipped": "⏭ Qo'shimcha ma'lumot o'tkazib yuborildi.",
        "seller.preview_cancel": "❌ E'lon joylash bekor qilindi.\n\nBosh menyu:",
        "seller.new_screenshots_title": (
            "🖼 <b>Yangi screenshotlar</b>\n\n"
            "Yangi rasmlarni yuboring. Eski rasmlar almashtiriladi."
        ),
        "seller.edit_prompt_nickname": "Yangi nickname kiriting:",
        "seller.edit_prompt_description": "Yangi description kiriting:",
        "seller.edit_prompt_login": "Yangi login kiriting:",
        "seller.edit_prompt_password": "Yangi asosiy parolni kiriting:",
        "seller.edit_prompt_price": "Yangi narxni raqamlarda kiriting:",
        "seller.edit_prompt_additional_info": "Yangi qo'shimcha ma'lumotni kiriting:",
        "seller.edit_prompt_default": "Yangi qiymat kiriting:",
        "seller.field_not_found": "Maydon topilmadi.",
        "seller.edit_extra_prompt": "<b>{label}</b> uchun yangi qiymat kiriting:",
        "seller.invalid_price": "Narxni raqamlarda kiriting.",
        "seller.price_not_allowed": "Narx ruxsat etilgan chegarada emas.",
        "seller.value_invalid": "Qiymat formati noto'g'ri.",
        "seller.warning": (
            "⚠️ <b>MUHIM OGOHLANTIRISH</b>\n\n"
            "Siz joylayotgan akkaunt o'zingizga tegishli ekanligini tasdiqlaysizmi?\n\n"
            "Siz bu akkauntdan foydalanishni to'xtatishga va xaridordan keyin "
            "akkauntga qayta kirmaslikka rozimisiz?\n\n"
            "Akkauntni sotish uchun tegishli platforma qoidalariga rioya qilishingiz kerak.\n\n"
            "Tasdiqlasangiz, akkaunt marketplace'da <b>ACTIVE</b> holatida e'lon qilinadi."
        ),
        "seller.already_publishing": "E'lon allaqachon joylanmoqda...",
        "seller.publish_error": "❌ E'lonni joylashda xatolik yuz berdi. Qayta urinib ko'ring.",
        "seller.published_notify_title": "✅ <b>Akkauntingiz marketplace'ga joylandi!</b>",
        "seller.published_notify_body": "🎮 {platform}\n🔤 {nickname}\n💵 {price}",
        "seller.publish_success_title": "🎉 <b>E'lon muvaffaqiyatli joylandi!</b>",
        "seller.publish_success_body": (
            "Akkaunt ACTIVE holatida marketplace'da ko'rinadi.\n"
            "Buyurtmalar va holat o'zgarishlari haqida sizga xabar beriladi."
        ),
        "seller.my_accounts_button": "📚 Mening akkauntlarim",
        "seller.invalid_filter": "Noto'g'ri filtr.",
        "seller.account_not_found": "E'lon topilmadi.",
        "seller.account_detail_platform": "🎮 <b>Platforma:</b> {platform}",
        "seller.account_detail_price": "💵 <b>Narx:</b> {price}",
        "seller.account_detail_status": "📌 <b>Holat:</b> {status}",
        "seller.account_detail_created": "📅 <b>E'lon sanasi:</b> {date}",
        "seller.account_detail_views": "👁 <b>Ko'rishlar:</b> {count}",
        "seller.account_detail_description": "📝 <b>Description:</b> {text}",
        "seller.account_detail_additional": "📎 <b>Qo'shimcha:</b> {text}",
        "seller.account_detail_fields_title": "<b>🔐 Maxfiy maydonlar:</b>",
        "seller.account_detail_field_item": "• {label}: ••••••",
        "seller.account_detail_screenshots": "🖼 Screenshotlar: {count} ta",
        "seller.delete_confirm_title": (
            "🗑 <b>{nickname}</b> e'lonini o'chirmoqchimisiz?\n\n"
            "Bu amalni qaytarib bo'lmaydi."
        ),
        "seller.deleted": "🗑 E'lon o'chirildi.",
        "seller.deleted_notify": "🗑 E'lon o'chirildi: <b>{nickname}</b>",
        "seller.not_editable": "Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.",
        "seller.edit_not_allowed": "Bu e'lonni tahrirlab bo'lmaydi.",
        "seller.new_secret_prompt": "Yangi maxfiy qiymatni kiriting:",
        "seller.new_field_label_prompt": "➕ Yangi maxfiy maydon nomini kiriting:",
        "seller.account_field_value_prompt": "Yangi maxfiy qiymatni kiriting:",
        "seller.account_screenshots_new": "🖼 Yangi screenshotlarni yuboring. Eski rasmlar almashtiriladi.",
        "seller.screenshot_limit_simple": "Limit: {max} ta screenshot.",
        "seller.screenshots_received_simple": (
            "🖼 Screenshotlar\n\n"
            "Qabul qilindi: <b>{count}/{max}</b>\n\n"
            "Yana yuboring yoki <b>✅ Tayyor</b> tugmasini bosing."
        ),
        "seller.field_added_simple": "✅ Maydon qo'shildi.",
        "seller.screenshots_updated_alert": "Screenshotlar yangilandi.",
        "seller.shots_done": "✅ Tayyor ({count}/{max})",
        "seller.add_field": "➕ Add — yangi maydon",
        "seller.add_field_short": "➕ Maydon qo'shish",
        "seller.edit": "✏️ Edit",
        "seller.confirm": "✅ Tasdiqlash",
        "seller.preview_back": "⬅️ Preview",
        "seller.warning_yes": "✅ Ha, tasdiqlayman",
        "seller.warning_no": "❌ Yo'q, qaytish",
        "seller.delete": "🗑 E'lonni o'chirish",
        "seller.edit_listing": "✏️ E'lonni tahrirlash",
        "seller.delete_yes": "🗑 Ha, o'chirish",
        "seller.reserved": "🟡 Band qilingan",
        "seller.sold": "✅ Sotilgan",
        "seller.nickname": "🔤 Nickname",
        "seller.description": "📝 Description",
        "seller.login": "🔐 Login",
        "seller.password": "🔑 Asosiy parol",
        "seller.price": "💵 Narx",
        "seller.additional_info": "📎 Qo'shimcha ma'lumot",
        "seller.images": "🖼 Screenshotlar",
        "buyer.seller_default": "seller",
        "buyer.card_price": "💵 <b>Narx:</b> {price}",
        "buyer.card_seller": "👤 <b>Seller:</b> {seller}",
        "buyer.card_date": "📅 <b>Sana:</b> {date}",
        "buyer.detail_platform": "🎮 <b>Platforma:</b> {platform}",
        "buyer.detail_seller": "👤 <b>Seller:</b> {seller}",
        "buyer.detail_price": "💵 <b>Narx:</b> {price}",
        "buyer.detail_date": "📅 <b>E'lon sanasi:</b> {date}",
        "buyer.detail_views": "👁 <b>Ko'rishlar:</b> {count}",
        "buyer.detail_description_title": "📝 <b>Description:</b>",
        "buyer.detail_additional_title": "📎 <b>Qo'shimcha ma'lumot:</b>",
        "buyer.detail_features_title": "<b>🔐 Akkaunt xususiyatlari:</b>",
        "buyer.detail_hidden_note": "🔒 <b>Login va parollar xarid qilinmaguncha yashirilgan.</b>",
        "buyer.list_title": (
            "{emoji} <b>{name}</b>\n\n"
            "{count_label}: <b>{total}</b> ta\n"
            "{page_label}: <b>{page}/{pages}</b>"
        ),
        "buyer.list_count": "Sotuvdagi akkauntlar",
        "buyer.list_page": "Sahifa",
        "buyer.list_empty": "📭 Bu platformada hozircha akkaunt yo'q.",
        "buyer.platform_not_found": "Platforma topilmadi.",
        "buyer.account_not_found": "E'lon topilmadi.",
        "buyer.not_available": "Akkaunt hozir sotuvda mavjud emas.",
        "buyer.own_account": "O'z akkauntingizni sotib ololmaysiz.",
        "buyer.purchase_warning": (
            "⚠️ <b>XARID QILISHDAN OLDIN DIQQAT!</b>\n\n"
            "Siz akkauntni sotib olishga qaror qilyapsiz.\n\n"
            "• Xarid qilishdan oldin e'lon ma'lumotlarini tekshiring.\n"
            "• Akkaunt boshqa odamga tegishli ekanligi aniqlansa, bu haqda xabar berish "
            "imkoniyati bo'lsin.\n"
            "• Xaridni tasdiqlaganingizdan keyin pulni qaytarish avtomatik kafolatlanmaydi.\n"
            "• Nizolar bo'yicha avtomatik tizim ishlaydi.\n"
            "• Seller akkauntni topshirish uchun javobgar."
        ),
        "buyer.payment_title": "💳 <b>To'lov</b>",
        "buyer.payment_body": (
            "🎮 {platform}\n"
            "🔤 {nickname}\n"
            "💵 {price}\n\n"
            "To'lov tizimi hali ulanmagan.\n"
            "Hozircha faqat <b>⏭ SKIP PAYMENT</b> (demo) mavjud.\n\n"
            "⚠️ Demo rejimida haqiqiy buyurtma yaratilmaydi, to'lov olinmaydi va "
            "sellerga mablag' yozilmaydi."
        ),
        "buyer.skip_title": "⏭ <b>SKIP PAYMENT — DEMO REJIM</b>",
        "buyer.skip_body": (
            "Bu demo tugma. Haqiqiy to'lov provayderi ulanmagan.\n\n"
            "❌ Buyurtma yaratilmadi.\n"
            "❌ To'lov amalga oshirilmadi.\n"
            "❌ Akkaunt band qilinmadi.\n"
            "❌ Sellerga mablag' yozilmadi.\n\n"
            "Haqiqiy xarid uchun to'lov provayderi (Click/Payme) ulanishi kerak."
        ),
        "buyer.viewed_notify_title": "👀 <b>Akkauntingizga xaridor qiziqdi!</b>",
        "buyer.viewed_notify_body": "🎮 {platform}\n🔤 {nickname}\n💵 {price}",
        "buyer.buy": "🛒 Sotib olish",
        "buyer.back_listing": "⬅️ E'longa qaytish",
        "buyer.continue": "✅ Davom etish",
        "buyer.skip_payment": "⏭ SKIP PAYMENT",
        "buyer.sort_newest": "🆕 Eng yangi",
        "buyer.sort_cheap": "💸 Eng arzon",
        "buyer.sort_expensive": "💎 Eng qimmat",
        "buyer.platforms": "⬅️ Platformalar",
        "buyer.prev": "⬅️ Oldingi",
        "buyer.next": "Keyingi ➡️",
        "dispute.title": "⚠️ <b>Nizo #{id}</b>",
        "dispute.order": "📦 <b>Buyurtma:</b> #{public_id}",
        "dispute.account": "🔤 <b>Akkaunt:</b> {nickname}",
        "dispute.status_label": "📌 <b>Holat:</b> {status}",
        "dispute.opened": "🕐 <b>Ochilgan:</b> {date}",
        "dispute.reason_title": "📝 <b>Sabab:</b>",
        "dispute.messages_title": "💬 <b>Xabarlar:</b>",
        "dispute.buyer": "Buyer",
        "dispute.seller": "Seller",
        "dispute.photo_evidence": "📸 [foto dalil]",
        "dispute.file_evidence": "📎 [fayl dalil]",
        "dispute.note_stopped": "ℹ️ Nizo ochilganda avtomatik payout to'xtatiladi.",
        "dispute.note_no_ai": "Hech qanday tekshirilmagan AI qarori bilan pul qaytarilmaydi.",
        "dispute.not_found": "Nizo topilmadi.",
        "dispute.order_not_found": "Buyurtma topilmadi.",
        "dispute.only_buyer_open": "Faqat xaridor nizo ochishi mumkin.",
        "dispute.cannot_open": "Bu buyurtma uchun nizo ochib bo'lmaydi.",
        "dispute.open_title": (
            "⚠️ <b>Nizo ochish</b>\n\n"
            "Muammoni batafsil yozing. Nima sodir bo'ldi?\n"
            "Seller akkauntni topshirmadimi, ma'lumotlar noto'g'rimi yoki boshqa muammo?\n\n"
            "Nizo ochilganda avtomatik payout to'xtatiladi."
        ),
        "dispute.back_order": "⬅️ Buyurtmaga qaytish",
        "dispute.opened_success": (
            "✅ Nizo ochildi. Avtomatik payout to'xtatildi.\n"
            "Seller javob berishi mumkin."
        ),
        "dispute.seller_notify": (
            "⚠️ <b>Xaridor nizo ochdi!</b>\n\n"
            "📦 Buyurtma: #{public_id}\n"
            "🔤 Akkaunt: {nickname}\n\n"
            "Sabab: {reason}\n\n"
            "Javob bering va dalillarni yuboring."
        ),
        "dispute.view_button": "💬 Nizoni ko'rish",
        "dispute.message_title": (
            "💬 <b>Nizo bo'yicha xabar</b>\n\n"
            "Xabaringizni yozing yoki foto dalil yuboring."
        ),
        "dispute.evidence_title": (
            "📎 <b>Dalil yuborish</b>\n\n"
            "Rasm yoki fayl (screenshot, chat, to'lov cheki) yuboring."
        ),
        "dispute.message_added": "✅ Xabar nizoga qo'shildi.",
        "dispute.new_message_notify": (
            "💬 <b>Nizo bo'yicha yangi xabar</b>\n\n"
            "📦 #{public_id}\n"
            "Yuboruvchi: {sender}"
        ),
        "dispute.withdraw_cancel": "✅ Nizo bekor qilindi. Buyurtma avvalgi holatiga qaytdi.",
        "dispute.withdrawn_alert": "Nizo bekor qilindi.",
        "dispute.withdrawn_notify": (
            "ℹ️ <b>Nizo bekor qilindi</b>\n\n"
            "📦 #{public_id}\n"
            "Xaridor nizoni qaytarib oldi. Avtomatik payout davom etadi."
        ),
        "dispute.back": "⬅️ Nizoga qaytish",
        "dispute.action_message": "💬 Xabar yuborish",
        "dispute.action_evidence": "📎 Dalil yuborish",
        "dispute.action_withdraw": "✅ Nizoni bekor qilish",
        "review.order_not_found": "Buyurtma topilmadi.",
        "review.not_completed": "Faqat yakunlangan buyurtmaga baho beriladi.",
        "review.title": "⭐ <b>Xizmatni baholang</b>\n\nSeller qanday ishladi?",
        "review.invalid_rating": "Noto'g'ri baho.",
        "review.rating_range": "Baho 1-5 oralig'ida bo'lishi kerak.",
        "review.comment_title": (
            "⭐ Baho: <b>{rating}/5</b>\n\n"
            "Izoh qoldirmoqchimisiz? Yozing yoki <b>⏭ Izohsiz</b> tugmasini bosing."
        ),
        "review.comment_too_long": "Izoh 2000 belgidan oshmasin.",
        "review.thanks": "🙏 Rahmat! Bahoyingiz qabul qilindi.",
        "review.skipped": "Baho berilmadi.",
        "review.notify": "⭐ <b>Yangi baho: {rating}/5</b>\n\n📦 #{public_id}",
        "review.notify_comment": "💬 {comment}",
        "review.skip_button": "⏭ O'tkazib yuborish",
        "review.no_comment": "⏭ Izohsiz",
        "errors.unexpected": "❌ Kutilmagan xatolik. Qayta urinib ko'ring.",
        "errors.start_menu": "❌ Kutilmagan xatolik yuz berdi. Iltimos, /start orqali qayta boshlang.",
        "errors.process_finish": "Iltimos, jarayonni tugating yoki /start orqali bosh menyuga qayting.",
        "errors.stale_action": "Bu amal eskirgan yoki mavjud emas.",
        "errors.rate_limit": "⏳ Juda ko'p so'rov yubordingiz. Bir daqiqadan so'ng qayta urinib ko'ring.",
        "error.account.not_available": "Akkaunt topilmadi.",
        "error.account.not_for_sale": "Akkaunt hozir sotuvda mavjud emas.",
        "error.account.own": "O'z akkauntingizni sotib ololmaysiz.",
        "error.account.reserved_by_other": "Akkaunt boshqa xaridor tomonidan band qilindi.",
        "error.account.not_editable": "Band yoki sotilgan e'lonni tahrirlab bo'lmaydi.",
        "error.account.not_deletable": "Band yoki sotilgan akkauntni o'chirib bo'lmaydi.",
        "error.account.invalid_platform": "Noto'g'ri platforma tanlandi.",
        "error.account.nickname_empty": "Akkaunt nomi bo'sh bo'lishi mumkin emas.",
        "error.account.login_empty": "Login bo'sh bo'lishi mumkin emas.",
        "error.account.password_empty": "Parol bo'sh bo'lishi mumkin emas.",
        "error.account.screenshots_required": "Kamida bitta screenshot yuklang.",
        "error.account.too_many_screenshots": "Screenshotlar soni juda ko'p.",
        "error.account.too_many_fields": "Qo'shimcha maydonlar soni juda ko'p.",
        "error.account.price_out_of_range": "Narx ruxsat etilgan chegarada emas.",
        "error.account.screenshot_required": "Kamida bitta screenshot kerak.",
        "error.account.fields_limit": "Qo'shimcha maydonlar limiti tugagan.",
        "error.account.field_empty": "Maydon nomi va qiymati bo'sh bo'lishi mumkin emas.",
        "error.account.field_value_empty": "Maydon qiymati bo'sh bo'lishi mumkin emas.",
        "error.account.price_format": "Narx formati noto'g'ri.",
        "error.order.not_found": "Buyurtma topilmadi.",
        "error.order.not_yours": "Bu buyurtma sizga tegishli emas.",
        "error.order.cannot_cancel": "Faqat to'lov kutilayotgan buyurtmani bekor qilish mumkin.",
        "error.order.not_deliverable": "Buyurtma holati topshirish uchun mos emas.",
        "error.order.not_completable": "Buyurtmani bu holatda yakunlab bo'lmaydi.",
        "error.order.not_payable": "Buyurtma to'lov uchun mos holatda emas.",
        "error.order.not_refundable": "Bu buyurtmani qaytarish mumkin emas.",
        "error.dispute.not_found": "Nizo topilmadi.",
        "error.dispute.order_not_found": "Buyurtma topilmadi.",
        "error.dispute.only_buyer_open": "Faqat xaridor nizo ochishi mumkin.",
        "error.dispute.cannot_open": "Bu buyurtma uchun nizo ochib bo'lmaydi.",
        "error.dispute.reason_short": "Nizo sababini batafsil yozing (kamida 5 belgi).",
        "error.dispute.not_participant": "Siz bu nizoning ishtirokchisi emasiz.",
        "error.dispute.closed": "Bu nizo yopilgan.",
        "error.dispute.empty_message": "Xabar bo'sh bo'lishi mumkin emas.",
        "error.dispute.file_missing": "Fayl topilmadi.",
        "error.dispute.only_buyer_withdraw": "Faqat xaridor nizoni bekor qilishi mumkin.",
        "error.dispute.cannot_withdraw": "Bu nizoni bekor qilib bo'lmaydi.",
        "error.review.rating_range": "Baho 1 dan 5 gacha bo'lishi kerak.",
        "error.review.order_not_found": "Buyurtma topilmadi.",
        "error.review.not_yours": "Bu buyurtma sizga tegishli emas.",
        "error.review.not_completed": "Faqat yakunlangan buyurtmaga baho berish mumkin.",
        "error.payment.not_found": "To'lov topilmadi.",
        "error.payment.provider_unknown": "Noma'lum to'lov provayderi.",
        "error.payment.skip_disabled": "Skip payment o'chirilgan.",
        "error.payment.disabled": (
            "To'lovlar hozircha o'chirilgan. PAYMENTS_ENABLED=true qilib provayderni ulang."
        ),
        "error.payment.status_mismatch": "To'lov holati mos emas.",
        "error.payment.cannot_fail_succeeded": "Muvaffaqiyatli to'lovni failed qilib bo'lmaydi.",
    },
    "ru": {
        "language.title": "🌐 Tilni tanlang / Выберите язык",
        "language.invalid": "Ошибка выбора языка.",
        "menu.profile": "👤 Профиль",
        "menu.buyer": "🛒 Купить аккаунт",
        "menu.seller": "📤 Продать аккаунт",
        "menu.listings": "📦 Мои объявления",
        "menu.balance": "💰 Баланс",
        "menu.stats": "📊 Статистика",
        "menu.settings": "⚙️ Настройки",
        "menu.help": "🆘 Помощь",
        "menu.orders": "📦 Мои заказы",
        "menu.sold": "📤 Проданные аккаунты",
        "menu.bought": "📥 Купленные аккаунты",
        "menu.home": "🏠 Главное меню",
        "common.back": "⬅️ Назад",
        "common.home": "🏠 Главное меню",
        "common.cancel": "❌ Отменить",
        "common.page": "Страница: <b>{page}/{total}</b>",
        "common.empty": "📭 Данные не найдены.",
        "common.not_found": "Не найдено.",
        "common.invalid_request": "Неверный запрос.",
        "common.previous": "⬅️ Назад",
        "common.next": "Далее ➡️",
        "common.updated": "✅ Обновлено.",
        "common.deleted": "🗑 Удалено.",
        "common.saved": "✅ Сохранено.",
        "common.skip": "⏭ Пропустить",
        "common.done": "✅ Готово",
        "common.yes": "✅ Да",
        "common.no": "❌ Нет",
        "profile.title": "👤 <b>Профиль</b>",
        "profile.name": "Имя",
        "profile.username": "Username",
        "profile.telegram_id": "Telegram ID",
        "profile.balance": "Баланс",
        "profile.sold_count": "Проданные аккаунты",
        "profile.bought_count": "Купленные аккаунты",
        "profile.active_listings": "Активные объявления",
        "profile.pending_trades": "Ожидающие сделки",
        "profile.total_trade": "Общий объём сделок",
        "profile.rating": "Рейтинг",
        "profile.registered": "Дата регистрации",
        "profile.hint": "Выберите нужный раздел в главном меню.",
        "profile.no_rating": "Пока нет оценок",
        "profile.no_username": "нет",
        "profile.orders_button": "📦 Мои заказы",
        "profile.sold_button": "📤 Проданные",
        "profile.bought_button": "📥 Купленные",
        "balance.title": "💰 <b>Баланс</b>",
        "balance.seller": "Баланс продавца",
        "balance.buyer": "Баланс покупателя",
        "balance.available": "Доступно",
        "balance.pending": "В ожидании",
        "balance.held": "В escrow",
        "balance.total_earned": "Всего заработано",
        "balance.total_released": "Всего выведено",
        "balance.total_spent": "Всего потрачено",
        "balance.history_button": "📜 История транзакций",
        "balance.history_title": "📜 <b>История транзакций</b>",
        "balance.history_empty": "📭 Транзакций пока нет.",
        "balance.history_item": "• {date} — {type}: <b>{amount}</b>",
        "sold.title": "📤 <b>Проданные аккаунты</b>",
        "sold.empty": "📭 Проданных аккаунтов пока нет.",
        "bought.title": "📥 <b>Купленные аккаунты</b>",
        "bought.empty": "📭 Купленных аккаунтов пока нет.",
        "order.entry": "{status} · {public_id} · {nickname} · {amount}",
        "list.page": "Всего: <b>{total}</b>\nСтраница: <b>{page}/{total_pages}</b>",
        "listings.title": "📦 <b>Мои объявления</b>\n\nВыберите раздел:",
        "listings.active": "🟢 В продаже",
        "listings.pending": "🟡 Зарезервированные",
        "listings.sold": "✅ Проданные",
        "listings.all": "📚 Все объявления",
        "listings.new": "➕ Новое объявление",
        "listings.empty": "📭 Объявлений пока нет.",
        "section.buyer": "🛒 <b>Покупка аккаунта</b>\n\nВыберите платформу:",
        "section.seller": "📤 <b>Продажа аккаунта</b>\n\nВыберите платформу.",
        "section.orders": "📦 <b>Мои заказы</b>\n\nВыберите покупки или продажи:",
        "orders.buyer": "🛍 Мои покупки",
        "orders.seller": "💰 Мои продажи",
        "orders.title_buyer": "🛍 Мои покупки",
        "orders.title_seller": "💰 Мои продажи",
        "orders.empty": "📭 Заказов нет.",
        "orders.hint": "Выберите заказ:",
        "stats.title": "📊 <b>Статистика</b>",
        "stats.sales_title": "Продажи",
        "stats.purchases_title": "Покупки",
        "stats.completed_sales": "Завершённые продажи",
        "stats.completed_purchases": "Завершённые покупки",
        "stats.sales_volume": "Объём продаж",
        "stats.purchases_volume": "Объём покупок",
        "stats.total_trade": "Общий объём сделок",
        "stats.commission": "Комиссия платформы",
        "stats.net_earned": "Чистый доход",
        "stats.active_listings": "Активные объявления",
        "stats.pending_trades": "Ожидающие сделки",
        "stats.rating": "Рейтинг",
        "stats.reviews": "Отзывы",
        "settings.title": "⚙️ <b>Настройки</b>",
        "settings.language": "Язык",
        "settings.current": "Текущий язык",
        "settings.choose": "Выберите язык:",
        "settings.refresh_profile": "🔄 Обновить профиль",
        "settings.language_changed": "✅ Язык изменён.",
        "settings.profile_refreshed": "✅ Профиль обновлён.",
        "help.title": "🆘 <b>Помощь</b>",
        "help.body": (
            "🛒 <b>Buyer</b> — выберите платформу, откройте карточку аккаунта и купите его.\n"
            "📤 <b>Seller</b> — выберите платформу и отправьте данные аккаунта.\n"
            "📦 <b>Мои объявления</b> — управляйте своими объявлениями.\n"
            "💰 <b>Баланс</b> — смотрите баланс и историю транзакций.\n\n"
            "⚠️ Пароли хранятся только в зашифрованном виде и показываются покупателю "
            "только после оплаты.\n\n"
            "Бот работает полностью автоматически, без панели администратора."
        ),
        "help.support": "📞 <b>Поддержка:</b> {support}",
        "status.pending_payment": "⏳ Ожидает оплаты",
        "status.paid": "💳 Оплачен",
        "status.delivered": "📤 Передан",
        "status.completed": "✅ Завершён",
        "status.disputed": "⚠️ В споре",
        "status.cancelled": "❌ Отменён",
        "status.refunded": "↩️ Возвращён",
        "status.unresolved": "🔴 Не решён",
        "tx.payment": "Оплата",
        "tx.escrow_hold": "Резерв в escrow",
        "tx.hourly_release": "Почасовое начисление",
        "tx.completion_release": "Финальное начисление",
        "tx.platform_commission": "Комиссия платформы",
        "tx.refund": "Возврат",
        "tx.payout": "Вывод средств",
        "tx.adjustment": "Корректировка",
        "account.status.active": "🟢 В продаже",
        "account.status.reserved": "🟡 Зарезервирован",
        "account.status.sold": "✅ Продан",
        "account.status.deleted": "🗑 Удалён",
        "account.status.draft": "⚪️ Черновик",
        "dispute.status.open": "⚠️ Открыт",
        "dispute.status.seller_responded": "💬 Продавец ответил",
        "dispute.status.resolved": "✅ Решён",
        "dispute.status.unresolved": "🕓 Не решён",
        "dispute.status.closed": "🔒 Закрыт",
        "order.detail_title": "📦 <b>Заказ #{public_id}</b>",
        "order.status_label": "📌 <b>Статус:</b> {status}",
        "order.your_role": "👤 <b>Ваша роль:</b> {role}",
        "order.role_buyer": "Покупатель",
        "order.role_seller": "Продавец",
        "order.platform": "🎮 <b>Платформа:</b> {platform}",
        "order.account": "🔤 <b>Аккаунт:</b> {nickname}",
        "order.amount": "💵 <b>Сумма:</b> {amount}",
        "order.commission": "🏦 <b>Комиссия платформы:</b> {amount}",
        "order.seller_share": "💰 <b>Доля продавца:</b> {amount}",
        "order.created": "🕐 <b>Создан:</b> {date}",
        "order.paid_at": "💳 <b>Оплачен:</b> {date}",
        "order.delivered_at": "📤 <b>Передан:</b> {date}",
        "order.completed_at": "✅ <b>Завершён:</b> {date}",
        "order.dispute_reason": "⚠️ <b>Причина спора:</b> {reason}",
        "order.not_found": "Заказ не найден.",
        "order.not_yours": "Этот заказ вам не принадлежит.",
        "order.creds_only_buyer": "Эти данные видит только покупатель.",
        "order.creds_locked": "Данные ещё не открыты.",
        "order.creds_title": "🔐 <b>СЕКРЕТНЫЕ ДАННЫЕ АККАУНТА</b>",
        "order.creds_nickname": "🔤 <b>Nickname:</b> {nickname}",
        "order.creds_platform": "🎮 <b>Платформа:</b> {platform}",
        "order.creds_login": "👤 <b>Логин:</b> <code>{login}</code>",
        "order.creds_password": "🔑 <b>Основной пароль:</b> <code>{password}</code>",
        "order.creds_fields_title": "<b>Дополнительные поля:</b>",
        "order.creds_field": "• <b>{label}:</b> <code>{value}</code>",
        "order.creds_warning": "⚠️ Не передавайте эти данные никому. Не входите в аккаунт повторно.",
        "order.completed_alert": "Заказ завершён.",
        "order.completed_title": "✅ <b>Заказ завершён!</b>",
        "order.completed_body": (
            "Аккаунт переведён в статус SOLD.\n"
            "Доля продавца выведена из escrow.\n\n"
            "Оцените сервис?"
        ),
        "order.completed_notify": (
            "✅ <b>Заказ завершён!</b>\n\n"
            "📦 #{public_id}\n"
            "💰 Доля продавца: {amount}\n\n"
            "Средства переведены на ваш баланс."
        ),
        "order.delivered_alert": "Отмечено как переданное.",
        "order.delivered_notify": (
            "📤 <b>Продавец передал аккаунт!</b>\n\n"
            "📦 #{public_id}\n"
            "🔤 {nickname}\n\n"
            "Проверьте аккаунт и подтвердите. При проблеме откройте спор."
        ),
        "order.cancelled_alert": "Заказ отменён.",
        "order.cancelled_notify": (
            "ℹ️ <b>Статус оплаты изменился</b>\n\n"
            "📦 Заказ #{public_id} отменён.\n"
            "Аккаунт снова выставлен на продажу."
        ),
        "order.cancelled_body": "❌ Заказ отменён. Аккаунт снова выставлен на продажу.",
        "order.action_deliver": "📤 Я передал аккаунт",
        "order.action_creds": "🔐 Показать данные для входа",
        "order.action_confirm": "✅ Подтвердить аккаунт",
        "order.action_dispute": "⚠️ Открыть спор",
        "order.action_review": "⭐ Оставить оценку",
        "order.action_view_dispute": "💬 Посмотреть спор",
        "order.action_cancel": "❌ Отменить заказ",
        "seller.preview_title": "🔎 <b>Предпросмотр объявления</b>",
        "seller.preview_platform": "🎮 <b>Платформа:</b> {platform}",
        "seller.preview_nickname": "🔤 <b>Nickname:</b> {nickname}",
        "seller.preview_description": "📝 <b>Описание:</b> {description}",
        "seller.preview_login": "🔐 <b>Логин:</b> {login}",
        "seller.preview_password": "🔑 <b>Основной пароль:</b> •••••• (будет зашифрован)",
        "seller.preview_price": "💵 <b>Цена:</b> {price}",
        "seller.preview_screenshots": "🖼 <b>Скриншоты:</b> {count} шт.",
        "seller.preview_additional": "📎 <b>Дополнительно:</b> {text}",
        "seller.preview_fields_title": "<b>🔐 Дополнительные секретные поля:</b>",
        "seller.preview_field_item": "• {label}: ••••••",
        "seller.preview_encrypted_note": "ℹ️ Все пароли шифруются с помощью AES-GCM.",
        "seller.edit_title": (
            "✏️ <b>Редактирование</b>\n\n"
            "Какое поле хотите изменить? Выберите одну из кнопок ниже."
        ),
        "seller.edit_account_title": "✏️ <b>Редактирование объявления</b>\n\nВыберите нужное поле.",
        "seller.platform_not_found": "Платформа не найдена.",
        "seller.platform_selected": "{emoji} <b>{name}</b> выбран.\n\n1️⃣ Введите название аккаунта или nickname:",
        "seller.nickname_invalid": "Nickname должен содержать от 1 до 128 символов. Введите снова.",
        "seller.screenshots_prompt": (
            "2️⃣ <b>Скриншоты</b>\n\n"
            "Отправьте скриншоты аккаунта как изображения.\n"
            "Минимум 1, максимум {max}.\n\n"
            "Когда закончите, нажмите <b>✅ Готово</b>."
        ),
        "seller.screenshots_limit": (
            "Лимит: {max} скриншотов. Чтобы отправить больше, удалите предыдущие "
            "и начните заново."
        ),
        "seller.screenshots_received": (
            "2️⃣ <b>Скриншоты</b>\n\n"
            "Принято: <b>{count}/{max}</b>\n\n"
            "Отправьте ещё или нажмите <b>✅ Готово</b>."
        ),
        "seller.screenshots_updated": "🖼 Скриншоты обновлены.",
        "seller.please_image": "Пожалуйста, отправьте изображение.",
        "seller.min_screenshot": "Отправьте хотя бы один скриншот.",
        "seller.description_prompt": "3️⃣ <b>Описание</b>\n\nНапишите краткую информацию об аккаунте:",
        "seller.description_invalid": "Описание должно содержать от 3 до 2000 символов.",
        "seller.login_prompt": "4️⃣ <b>Gmail или логин</b>\n\nВведите данные для входа в аккаунт:",
        "seller.login_invalid": "Логин должен содержать от 1 до 200 символов.",
        "seller.password_prompt": (
            "5️⃣ <b>Основной пароль</b>\n\n"
            "Отправьте пароль. В целях безопасности это сообщение будет удалено автоматически.\n"
            "Пароль шифруется через AES-GCM."
        ),
        "seller.password_invalid": "Пароль должен содержать от 1 до 200 символов.",
        "seller.extra_fields_title": (
            "6️⃣ <b>Другие пароли и дополнительная информация</b>\n\n"
            "Через <b>➕ Добавить</b> можно указать пароль Gmail, recovery email, recovery code, "
            "другой логин или дополнительный пароль.\n\n"
            "Лимит полей: <b>{count}/{max}</b>"
        ),
        "seller.field_add_prompt": (
            "➕ <b>Новое поле</b>\n\n"
            "Введите название поля (например: <i>Пароль Gmail</i>, <i>Recovery email</i>):"
        ),
        "seller.field_label_invalid": "Название поля должно содержать 1-{max} символов.",
        "seller.field_value_prompt": (
            "Введите значение для <b>{label}</b>.\n\n"
            "В целях безопасности сообщение будет удалено автоматически."
        ),
        "seller.field_value_empty": "Значение не может быть пустым.",
        "seller.field_added": (
            "✅ Поле добавлено.\n\n"
            "Полей: <b>{count}/{max}</b>\n"
            "Можете добавить ещё или нажать <b>✅ Готово</b>."
        ),
        "seller.price_prompt": (
            "7️⃣ <b>Цена аккаунта</b>\n\n"
            "Введите цену только цифрами (например: 250000):"
        ),
        "seller.price_invalid": "Введите цену только цифрами. Например: 250000",
        "seller.price_range": "Цена должна быть в диапазоне от {min} до {max}.",
        "seller.additional_title": (
            "8️⃣ <b>Дополнительная информация</b>\n\n"
            "Напишите дополнительную информацию об аккаунте, если есть. "
            "Если нет — нажмите <b>⏭ Пропустить</b>."
        ),
        "seller.additional_too_long": "Дополнительная информация не должна превышать {max} символов.",
        "seller.additional_skipped": "⏭ Дополнительная информация пропущена.",
        "seller.preview_cancel": "❌ Публикация объявления отменена.\n\nГлавное меню:",
        "seller.new_screenshots_title": (
            "🖼 <b>Новые скриншоты</b>\n\n"
            "Отправьте новые изображения. Старые будут заменены."
        ),
        "seller.edit_prompt_nickname": "Введите новый nickname:",
        "seller.edit_prompt_description": "Введите новое описание:",
        "seller.edit_prompt_login": "Введите новый логин:",
        "seller.edit_prompt_password": "Введите новый основной пароль:",
        "seller.edit_prompt_price": "Введите новую цену цифрами:",
        "seller.edit_prompt_additional_info": "Введите новую дополнительную информацию:",
        "seller.edit_prompt_default": "Введите новое значение:",
        "seller.field_not_found": "Поле не найдено.",
        "seller.edit_extra_prompt": "Введите новое значение для <b>{label}</b>:",
        "seller.invalid_price": "Введите цену цифрами.",
        "seller.price_not_allowed": "Цена вне допустимого диапазона.",
        "seller.value_invalid": "Неверный формат значения.",
        "seller.warning": (
            "⚠️ <b>ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
            "Подтверждаете, что публикуемый аккаунт принадлежит вам?\n\n"
            "Согласны прекратить использование этого аккаунта и не входить в него "
            "после покупки?\n\n"
            "Для продажи аккаунта необходимо соблюдать правила соответствующей платформы.\n\n"
            "После подтверждения аккаунт будет опубликован на маркетплейсе в статусе <b>ACTIVE</b>."
        ),
        "seller.already_publishing": "Объявление уже публикуется...",
        "seller.publish_error": "❌ Ошибка при публикации объявления. Попробуйте снова.",
        "seller.published_notify_title": "✅ <b>Ваш аккаунт опубликован на маркетплейсе!</b>",
        "seller.published_notify_body": "🎮 {platform}\n🔤 {nickname}\n💵 {price}",
        "seller.publish_success_title": "🎉 <b>Объявление успешно опубликовано!</b>",
        "seller.publish_success_body": (
            "Аккаунт отображается на маркетплейсе в статусе ACTIVE.\n"
            "Вы будете получать уведомления о заказах и изменениях статуса."
        ),
        "seller.my_accounts_button": "📚 Мои аккаунты",
        "seller.invalid_filter": "Неверный фильтр.",
        "seller.account_not_found": "Объявление не найдено.",
        "seller.account_detail_platform": "🎮 <b>Платформа:</b> {platform}",
        "seller.account_detail_price": "💵 <b>Цена:</b> {price}",
        "seller.account_detail_status": "📌 <b>Статус:</b> {status}",
        "seller.account_detail_created": "📅 <b>Дата объявления:</b> {date}",
        "seller.account_detail_views": "👁 <b>Просмотры:</b> {count}",
        "seller.account_detail_description": "📝 <b>Описание:</b> {text}",
        "seller.account_detail_additional": "📎 <b>Дополнительно:</b> {text}",
        "seller.account_detail_fields_title": "<b>🔐 Секретные поля:</b>",
        "seller.account_detail_field_item": "• {label}: ••••••",
        "seller.account_detail_screenshots": "🖼 Скриншоты: {count} шт.",
        "seller.delete_confirm_title": (
            "🗑 Удалить объявление <b>{nickname}</b>?\n\n"
            "Это действие нельзя отменить."
        ),
        "seller.deleted": "🗑 Объявление удалено.",
        "seller.deleted_notify": "🗑 Объявление удалено: <b>{nickname}</b>",
        "seller.not_editable": "Нельзя редактировать зарезервированное или проданное объявление.",
        "seller.edit_not_allowed": "Это объявление нельзя редактировать.",
        "seller.new_secret_prompt": "Введите новое секретное значение:",
        "seller.new_field_label_prompt": "➕ Введите название нового секретного поля:",
        "seller.account_field_value_prompt": "Введите новое секретное значение:",
        "seller.account_screenshots_new": "🖼 Отправьте новые скриншоты. Старые будут заменены.",
        "seller.screenshot_limit_simple": "Лимит: {max} скриншотов.",
        "seller.screenshots_received_simple": (
            "🖼 Скриншоты\n\n"
            "Принято: <b>{count}/{max}</b>\n\n"
            "Отправьте ещё или нажмите <b>✅ Готово</b>."
        ),
        "seller.field_added_simple": "✅ Поле добавлено.",
        "seller.screenshots_updated_alert": "Скриншоты обновлены.",
        "seller.shots_done": "✅ Готово ({count}/{max})",
        "seller.add_field": "➕ Добавить — новое поле",
        "seller.add_field_short": "➕ Добавить поле",
        "seller.edit": "✏️ Изменить",
        "seller.confirm": "✅ Подтвердить",
        "seller.preview_back": "⬅️ Предпросмотр",
        "seller.warning_yes": "✅ Да, подтверждаю",
        "seller.warning_no": "❌ Нет, вернуться",
        "seller.delete": "🗑 Удалить объявление",
        "seller.edit_listing": "✏️ Редактировать объявление",
        "seller.delete_yes": "🗑 Да, удалить",
        "seller.reserved": "🟡 Зарезервирован",
        "seller.sold": "✅ Продан",
        "seller.nickname": "🔤 Nickname",
        "seller.description": "📝 Описание",
        "seller.login": "🔐 Логин",
        "seller.password": "🔑 Основной пароль",
        "seller.price": "💵 Цена",
        "seller.additional_info": "📎 Дополнительная информация",
        "seller.images": "🖼 Скриншоты",
        "buyer.seller_default": "продавец",
        "buyer.card_price": "💵 <b>Цена:</b> {price}",
        "buyer.card_seller": "👤 <b>Продавец:</b> {seller}",
        "buyer.card_date": "📅 <b>Дата:</b> {date}",
        "buyer.detail_platform": "🎮 <b>Платформа:</b> {platform}",
        "buyer.detail_seller": "👤 <b>Продавец:</b> {seller}",
        "buyer.detail_price": "💵 <b>Цена:</b> {price}",
        "buyer.detail_date": "📅 <b>Дата объявления:</b> {date}",
        "buyer.detail_views": "👁 <b>Просмотры:</b> {count}",
        "buyer.detail_description_title": "📝 <b>Описание:</b>",
        "buyer.detail_additional_title": "📎 <b>Дополнительная информация:</b>",
        "buyer.detail_features_title": "<b>🔐 Характеристики аккаунта:</b>",
        "buyer.detail_hidden_note": "🔒 <b>Логин и пароли скрыты до покупки.</b>",
        "buyer.list_title": (
            "{emoji} <b>{name}</b>\n\n"
            "{count_label}: <b>{total}</b>\n"
            "{page_label}: <b>{page}/{pages}</b>"
        ),
        "buyer.list_count": "Аккаунтов в продаже",
        "buyer.list_page": "Страница",
        "buyer.list_empty": "📭 На этой платформе пока нет аккаунтов.",
        "buyer.platform_not_found": "Платформа не найдена.",
        "buyer.account_not_found": "Объявление не найдено.",
        "buyer.not_available": "Аккаунт сейчас не продаётся.",
        "buyer.own_account": "Вы не можете купить собственный аккаунт.",
        "buyer.purchase_warning": (
            "⚠️ <b>ВНИМАНИЕ ПЕРЕД ПОКУПКОЙ!</b>\n\n"
            "Вы собираетесь купить аккаунт.\n\n"
            "• Проверьте информацию в объявлении перед покупкой.\n"
            "• Если выяснится, что аккаунт принадлежит другому человеку, сообщите об этом.\n"
            "• После подтверждения покупки возврат средств не гарантируется автоматически.\n"
            "• По спорам работает автоматическая система.\n"
            "• Продавец отвечает за передачу аккаунта."
        ),
        "buyer.payment_title": "💳 <b>Оплата</b>",
        "buyer.payment_body": (
            "🎮 {platform}\n"
            "🔤 {nickname}\n"
            "💵 {price}\n\n"
            "Платёжная система ещё не подключена.\n"
            "Пока доступен только <b>⏭ SKIP PAYMENT</b> (демо).\n\n"
            "⚠️ В демо-режиме реальный заказ не создаётся, оплата не взимается, "
            "а продавцу не начисляются средства."
        ),
        "buyer.skip_title": "⏭ <b>SKIP PAYMENT — ДЕМО-РЕЖИМ</b>",
        "buyer.skip_body": (
            "Это демо-кнопка. Реальный платёжный провайдер не подключён.\n\n"
            "❌ Заказ не создан.\n"
            "❌ Оплата не произведена.\n"
            "❌ Аккаунт не зарезервирован.\n"
            "❌ Продавцу не начислены средства.\n\n"
            "Для реальной покупки необходимо подключить платёжный провайдер (Click/Payme)."
        ),
        "buyer.viewed_notify_title": "👀 <b>Покупатель заинтересовался вашим аккаунтом!</b>",
        "buyer.viewed_notify_body": "🎮 {platform}\n🔤 {nickname}\n💵 {price}",
        "buyer.buy": "🛒 Купить",
        "buyer.back_listing": "⬅️ К объявлению",
        "buyer.continue": "✅ Продолжить",
        "buyer.skip_payment": "⏭ SKIP PAYMENT",
        "buyer.sort_newest": "🆕 Новые",
        "buyer.sort_cheap": "💸 Самые дешёвые",
        "buyer.sort_expensive": "💎 Самые дорогие",
        "buyer.platforms": "⬅️ Платформы",
        "buyer.prev": "⬅️ Назад",
        "buyer.next": "Далее ➡️",
        "dispute.title": "⚠️ <b>Спор #{id}</b>",
        "dispute.order": "📦 <b>Заказ:</b> #{public_id}",
        "dispute.account": "🔤 <b>Аккаунт:</b> {nickname}",
        "dispute.status_label": "📌 <b>Статус:</b> {status}",
        "dispute.opened": "🕐 <b>Открыт:</b> {date}",
        "dispute.reason_title": "📝 <b>Причина:</b>",
        "dispute.messages_title": "💬 <b>Сообщения:</b>",
        "dispute.buyer": "Покупатель",
        "dispute.seller": "Продавец",
        "dispute.photo_evidence": "📸 [фото-доказательство]",
        "dispute.file_evidence": "📎 [файл-доказательство]",
        "dispute.note_stopped": "ℹ️ При открытии спора автоматическая выплата останавливается.",
        "dispute.note_no_ai": "Возврат средств не происходит по непроверенному решению AI.",
        "dispute.not_found": "Спор не найден.",
        "dispute.order_not_found": "Заказ не найден.",
        "dispute.only_buyer_open": "Только покупатель может открыть спор.",
        "dispute.cannot_open": "Для этого заказа нельзя открыть спор.",
        "dispute.open_title": (
            "⚠️ <b>Открытие спора</b>\n\n"
            "Опишите проблему подробно. Что произошло?\n"
            "Продавец не передал аккаунт, данные неверные или другая проблема?\n\n"
            "При открытии спора автоматическая выплата останавливается."
        ),
        "dispute.back_order": "⬅️ К заказу",
        "dispute.opened_success": (
            "✅ Спор открыт. Автоматическая выплата остановлена.\n"
            "Продавец может ответить."
        ),
        "dispute.seller_notify": (
            "⚠️ <b>Покупатель открыл спор!</b>\n\n"
            "📦 Заказ: #{public_id}\n"
            "🔤 Аккаунт: {nickname}\n\n"
            "Причина: {reason}\n\n"
            "Ответьте и отправьте доказательства."
        ),
        "dispute.view_button": "💬 Посмотреть спор",
        "dispute.message_title": (
            "💬 <b>Сообщение по спору</b>\n\n"
            "Напишите сообщение или отправьте фото-доказательство."
        ),
        "dispute.evidence_title": (
            "📎 <b>Отправка доказательства</b>\n\n"
            "Отправьте изображение или файл (скриншот, чат, чек оплаты)."
        ),
        "dispute.message_added": "✅ Сообщение добавлено в спор.",
        "dispute.new_message_notify": (
            "💬 <b>Новое сообщение по спору</b>\n\n"
            "📦 #{public_id}\n"
            "Отправитель: {sender}"
        ),
        "dispute.withdraw_cancel": "✅ Спор отменён. Заказ вернулся в предыдущий статус.",
        "dispute.withdrawn_alert": "Спор отменён.",
        "dispute.withdrawn_notify": (
            "ℹ️ <b>Спор отменён</b>\n\n"
            "📦 #{public_id}\n"
            "Покупатель отозвал спор. Автоматическая выплата продолжается."
        ),
        "dispute.back": "⬅️ К спору",
        "dispute.action_message": "💬 Отправить сообщение",
        "dispute.action_evidence": "📎 Отправить доказательство",
        "dispute.action_withdraw": "✅ Отменить спор",
        "review.order_not_found": "Заказ не найден.",
        "review.not_completed": "Оценить можно только завершённый заказ.",
        "review.title": "⭐ <b>Оцените сервис</b>\n\nКак работал продавец?",
        "review.invalid_rating": "Неверная оценка.",
        "review.rating_range": "Оценка должна быть от 1 до 5.",
        "review.comment_title": (
            "⭐ Оценка: <b>{rating}/5</b>\n\n"
            "Хотите оставить комментарий? Напишите или нажмите <b>⏭ Без комментария</b>."
        ),
        "review.comment_too_long": "Комментарий не должен превышать 2000 символов.",
        "review.thanks": "🙏 Спасибо! Ваша оценка принята.",
        "review.skipped": "Оценка не поставлена.",
        "review.notify": "⭐ <b>Новая оценка: {rating}/5</b>\n\n📦 #{public_id}",
        "review.notify_comment": "💬 {comment}",
        "review.skip_button": "⏭ Пропустить",
        "review.no_comment": "⏭ Без комментария",
        "errors.unexpected": "❌ Неожиданная ошибка. Попробуйте снова.",
        "errors.start_menu": "❌ Произошла неожиданная ошибка. Пожалуйста, начните заново через /start.",
        "errors.process_finish": "Пожалуйста, завершите процесс или вернитесь в меню через /start.",
        "errors.stale_action": "Это действие устарело или недоступно.",
        "errors.rate_limit": "⏳ Слишком много запросов. Попробуйте снова через минуту.",
        "error.account.not_available": "Аккаунт не найден.",
        "error.account.not_for_sale": "Аккаунт сейчас не продаётся.",
        "error.account.own": "Вы не можете купить собственный аккаунт.",
        "error.account.reserved_by_other": "Аккаунт уже зарезервирован другим покупателем.",
        "error.account.not_editable": "Нельзя редактировать зарезервированное или проданное объявление.",
        "error.account.not_deletable": "Нельзя удалить зарезервированный или проданный аккаунт.",
        "error.account.invalid_platform": "Выбрана неверная платформа.",
        "error.account.nickname_empty": "Название аккаунта не может быть пустым.",
        "error.account.login_empty": "Логин не может быть пустым.",
        "error.account.password_empty": "Пароль не может быть пустым.",
        "error.account.screenshots_required": "Загрузите хотя бы один скриншот.",
        "error.account.too_many_screenshots": "Слишком много скриншотов.",
        "error.account.too_many_fields": "Слишком много дополнительных полей.",
        "error.account.price_out_of_range": "Цена вне допустимого диапазона.",
        "error.account.screenshot_required": "Нужен хотя бы один скриншот.",
        "error.account.fields_limit": "Лимит дополнительных полей исчерпан.",
        "error.account.field_empty": "Название и значение поля не могут быть пустыми.",
        "error.account.field_value_empty": "Значение поля не может быть пустым.",
        "error.account.price_format": "Неверный формат цены.",
        "error.order.not_found": "Заказ не найден.",
        "error.order.not_yours": "Этот заказ вам не принадлежит.",
        "error.order.cannot_cancel": "Отменить можно только заказ, ожидающий оплаты.",
        "error.order.not_deliverable": "Статус заказа не подходит для передачи.",
        "error.order.not_completable": "Заказ нельзя завершить в этом статусе.",
        "error.order.not_payable": "Заказ не подходит для оплаты.",
        "error.order.not_refundable": "Этот заказ нельзя вернуть.",
        "error.dispute.not_found": "Спор не найден.",
        "error.dispute.order_not_found": "Заказ не найден.",
        "error.dispute.only_buyer_open": "Только покупатель может открыть спор.",
        "error.dispute.cannot_open": "Для этого заказа нельзя открыть спор.",
        "error.dispute.reason_short": "Опишите причину спора подробнее (минимум 5 символов).",
        "error.dispute.not_participant": "Вы не участник этого спора.",
        "error.dispute.closed": "Этот спор закрыт.",
        "error.dispute.empty_message": "Сообщение не может быть пустым.",
        "error.dispute.file_missing": "Файл не найден.",
        "error.dispute.only_buyer_withdraw": "Только покупатель может отменить спор.",
        "error.dispute.cannot_withdraw": "Этот спор нельзя отменить.",
        "error.review.rating_range": "Оценка должна быть от 1 до 5.",
        "error.review.order_not_found": "Заказ не найден.",
        "error.review.not_yours": "Этот заказ вам не принадлежит.",
        "error.review.not_completed": "Оценить можно только завершённый заказ.",
        "error.payment.not_found": "Платёж не найден.",
        "error.payment.provider_unknown": "Неизвестный платёжный провайдер.",
        "error.payment.skip_disabled": "Skip payment отключён.",
        "error.payment.disabled": (
            "Платежи пока отключены. Установите PAYMENTS_ENABLED=true и подключите провайдера."
        ),
        "error.payment.status_mismatch": "Статус платежа не подходит.",
        "error.payment.cannot_fail_succeeded": "Нельзя пометить успешный платёж как failed.",
    },
}

STATUS_KEYS: dict[str, str] = {
    OrderStatus.PENDING_PAYMENT.value: "status.pending_payment",
    OrderStatus.PAID.value: "status.paid",
    OrderStatus.DELIVERED.value: "status.delivered",
    OrderStatus.COMPLETED.value: "status.completed",
    OrderStatus.DISPUTED.value: "status.disputed",
    OrderStatus.CANCELLED.value: "status.cancelled",
    OrderStatus.REFUNDED.value: "status.refunded",
    OrderStatus.UNRESOLVED.value: "status.unresolved",
}

TRANSACTION_KEYS: dict[str, str] = {
    TransactionType.PAYMENT.value: "tx.payment",
    TransactionType.ESCROW_HOLD.value: "tx.escrow_hold",
    TransactionType.HOURLY_RELEASE.value: "tx.hourly_release",
    TransactionType.COMPLETION_RELEASE.value: "tx.completion_release",
    TransactionType.PLATFORM_COMMISSION.value: "tx.platform_commission",
    TransactionType.REFUND.value: "tx.refund",
    TransactionType.PAYOUT.value: "tx.payout",
    TransactionType.ADJUSTMENT.value: "tx.adjustment",
}

ACCOUNT_STATUS_KEYS: dict[str, str] = {
    AccountStatus.ACTIVE.value: "account.status.active",
    AccountStatus.RESERVED.value: "account.status.reserved",
    AccountStatus.SOLD.value: "account.status.sold",
    AccountStatus.DELETED.value: "account.status.deleted",
    AccountStatus.DRAFT.value: "account.status.draft",
}

DISPUTE_STATUS_KEYS: dict[str, str] = {
    DisputeStatus.OPEN.value: "dispute.status.open",
    DisputeStatus.SELLER_RESPONDED.value: "dispute.status.seller_responded",
    DisputeStatus.RESOLVED.value: "dispute.status.resolved",
    DisputeStatus.UNRESOLVED.value: "dispute.status.unresolved",
    DisputeStatus.CLOSED.value: "dispute.status.closed",
}


def normalize_locale(value: str | None) -> str:
    code = (value or "").strip().lower().replace("_", "-")
    if code.startswith("ru"):
        return "ru"
    return DEFAULT_LOCALE


def user_locale(user: object) -> str:
    preferred = getattr(user, "preferred_language", None)
    if preferred in SUPPORTED_LOCALES:
        return str(preferred)
    return DEFAULT_LOCALE


def language_selected(user: object) -> bool:
    return getattr(user, "preferred_language", None) in SUPPORTED_LOCALES


def set_current_locale(locale: str | None) -> Token[str]:
    return _CURRENT_LOCALE.set(normalize_locale(locale))


def current_locale() -> str:
    return _CURRENT_LOCALE.get()


def reset_current_locale(token: Token[str]) -> None:
    _CURRENT_LOCALE.reset(token)


def resolve_locale(locale: str | None = None) -> str:
    if locale:
        return normalize_locale(locale)
    return current_locale()


def t(key: str, locale: str | None = None, **kwargs: object) -> str:
    lang = resolve_locale(locale)
    template = TEXTS.get(lang, TEXTS[DEFAULT_LOCALE]).get(key)
    if template is None:
        template = TEXTS[DEFAULT_LOCALE].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


def menu_texts(locale: str | None = None) -> dict[str, str]:
    lang = resolve_locale(locale)
    return {key: t(f"menu.{key}", lang) for key in MENU_KEYS}


def menu_action_by_text() -> dict[str, str]:
    return {
        text: key
        for locale in SUPPORTED_LOCALES
        for key, text in menu_texts(locale).items()
    }


def status_label(status: str, locale: str | None = None) -> str:
    return t(STATUS_KEYS.get(status, "common.empty"), locale)


def transaction_label(tx_type: str, locale: str | None = None) -> str:
    return t(TRANSACTION_KEYS.get(tx_type, "tx.adjustment"), locale)


def account_status_label(status: str, locale: str | None = None) -> str:
    return t(ACCOUNT_STATUS_KEYS.get(status, "account.status.draft"), locale)


def dispute_status_label(status: str, locale: str | None = None) -> str:
    return t(DISPUTE_STATUS_KEYS.get(status, "dispute.status.open"), locale)
