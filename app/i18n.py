from __future__ import annotations

from app.models import OrderStatus, TransactionType

SUPPORTED_LOCALES: tuple[str, ...] = ("uz", "ru", "en")
DEFAULT_LOCALE = "uz"

LOCALE_LABELS: dict[str, str] = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

MENU_KEYS: tuple[str, ...] = (
    "profile",
    "balance",
    "buyer",
    "seller",
    "orders",
    "listings",
    "sold",
    "bought",
    "stats",
    "settings",
    "help",
    "home",
)

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "menu.profile": "👤 Profil",
        "menu.balance": "💰 Balansim",
        "menu.buyer": "🛍 Akkaunt sotib olish",
        "menu.seller": "📤 Akkaunt sotish",
        "menu.orders": "📦 Buyurtmalarim",
        "menu.listings": "🏪 Mening e'lonlarim",
        "menu.sold": "📤 Sotgan akkauntlarim",
        "menu.bought": "📥 Sotib olganlarim",
        "menu.stats": "📊 Statistika",
        "menu.settings": "⚙️ Sozlamalar",
        "menu.help": "ℹ️ Yordam",
        "menu.home": "🏠 Bosh menyu",
        "common.back": "⬅️ Orqaga",
        "common.home": "🏠 Bosh menyu",
        "common.cancel": "❌ Bekor qilish",
        "common.page": "Sahifa: <b>{page}/{total}</b>",
        "common.empty": "📭 Ma'lumot topilmadi.",
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
        "balance.title": "💰 <b>Balansim</b>",
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
        "listings.title": "🏪 <b>Mening e'lonlarim</b>\n\nBo'limni tanlang:",
        "listings.active": "🟢 Sotuvdagi akkauntlar",
        "listings.pending": "🟡 Band qilinganlar",
        "listings.sold": "✅ Sotilgan akkauntlar",
        "listings.all": "📚 Barcha e'lonlar",
        "listings.new": "➕ Yangi akkaunt joylash",
        "listings.empty": "📭 Hozircha akkaunt yo'q.",
        "section.buyer": "🛍 <b>Akkaunt sotib olish</b>\n\nPlatformani tanlang:",
        "section.seller": "📤 <b>Akkaunt sotish</b>\n\nPlatformani tanlang.",
        "section.orders": "📦 <b>Buyurtmalarim</b>\n\nXaridlar yoki sotuvlar bo'limini tanlang:",
        "orders.buyer": "🛍 Xaridlarim",
        "orders.seller": "💰 Sotuvlarim",
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
        "help.title": "ℹ️ <b>Yordam</b>",
        "help.body": (
            "🛍 <b>Buyer</b> — platformani tanlab, akkaunt kartasini oching va sotib oling.\n"
            "📤 <b>Seller</b> — platformani tanlab, akkaunt ma'lumotlarini yuboring.\n"
            "📦 <b>Buyurtmalarim</b> — xarid va sotuvlaringiz holatini kuzating.\n"
            "💰 <b>Balansim</b> — balans va tranzaksiyalar tarixini ko'ring.\n\n"
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
    },
    "ru": {
        "menu.profile": "👤 Профиль",
        "menu.balance": "💰 Мой баланс",
        "menu.buyer": "🛍 Купить аккаунт",
        "menu.seller": "📤 Продать аккаунт",
        "menu.orders": "📦 Мои заказы",
        "menu.listings": "🏪 Мои объявления",
        "menu.sold": "📤 Проданные аккаунты",
        "menu.bought": "📥 Купленные аккаунты",
        "menu.stats": "📊 Статистика",
        "menu.settings": "⚙️ Настройки",
        "menu.help": "ℹ️ Помощь",
        "menu.home": "🏠 Главное меню",
        "common.back": "⬅️ Назад",
        "common.home": "🏠 Главное меню",
        "common.cancel": "❌ Отменить",
        "common.page": "Страница: <b>{page}/{total}</b>",
        "common.empty": "📭 Данные не найдены.",
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
        "balance.title": "💰 <b>Мой баланс</b>",
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
        "listings.title": "🏪 <b>Мои объявления</b>\n\nВыберите раздел:",
        "listings.active": "🟢 В продаже",
        "listings.pending": "🟡 Зарезервированные",
        "listings.sold": "✅ Проданные",
        "listings.all": "📚 Все объявления",
        "listings.new": "➕ Новое объявление",
        "listings.empty": "📭 Объявлений пока нет.",
        "section.buyer": "🛍 <b>Покупка аккаунта</b>\n\nВыберите платформу:",
        "section.seller": "📤 <b>Продажа аккаунта</b>\n\nВыберите платформу.",
        "section.orders": "📦 <b>Мои заказы</b>\n\nВыберите покупки или продажи:",
        "orders.buyer": "🛍 Мои покупки",
        "orders.seller": "💰 Мои продажи",
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
        "help.title": "ℹ️ <b>Помощь</b>",
        "help.body": (
            "🛍 <b>Buyer</b> — выберите платформу, откройте карточку аккаунта и купите его.\n"
            "📤 <b>Seller</b> — выберите платформу и отправьте данные аккаунта.\n"
            "📦 <b>Мои заказы</b> — следите за статусом покупок и продаж.\n"
            "💰 <b>Мой баланс</b> — смотрите баланс и историю транзакций.\n\n"
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
    },
    "en": {
        "menu.profile": "👤 Profile",
        "menu.balance": "💰 My balance",
        "menu.buyer": "🛍 Buy account",
        "menu.seller": "📤 Sell account",
        "menu.orders": "📦 My orders",
        "menu.listings": "🏪 My listings",
        "menu.sold": "📤 Sold accounts",
        "menu.bought": "📥 Bought accounts",
        "menu.stats": "📊 Statistics",
        "menu.settings": "⚙️ Settings",
        "menu.help": "ℹ️ Help",
        "menu.home": "🏠 Main menu",
        "common.back": "⬅️ Back",
        "common.home": "🏠 Main menu",
        "common.cancel": "❌ Cancel",
        "common.page": "Page: <b>{page}/{total}</b>",
        "common.empty": "📭 No data found.",
        "profile.title": "👤 <b>Profile</b>",
        "profile.name": "Name",
        "profile.username": "Username",
        "profile.telegram_id": "Telegram ID",
        "profile.balance": "Balance",
        "profile.sold_count": "Sold accounts",
        "profile.bought_count": "Bought accounts",
        "profile.active_listings": "Active listings",
        "profile.pending_trades": "Pending trades",
        "profile.total_trade": "Total trade volume",
        "profile.rating": "Rating",
        "profile.registered": "Registered",
        "profile.hint": "Choose a section from the main menu.",
        "profile.no_rating": "No ratings yet",
        "profile.no_username": "not set",
        "balance.title": "💰 <b>My balance</b>",
        "balance.seller": "Seller balance",
        "balance.buyer": "Buyer balance",
        "balance.available": "Available",
        "balance.pending": "Pending",
        "balance.held": "Held in escrow",
        "balance.total_earned": "Total earned",
        "balance.total_released": "Total released",
        "balance.total_spent": "Total spent",
        "balance.history_button": "📜 Transaction history",
        "balance.history_title": "📜 <b>Transaction history</b>",
        "balance.history_empty": "📭 No transactions yet.",
        "balance.history_item": "• {date} — {type}: <b>{amount}</b>",
        "sold.title": "📤 <b>Sold accounts</b>",
        "sold.empty": "📭 No sold accounts yet.",
        "bought.title": "📥 <b>Bought accounts</b>",
        "bought.empty": "📭 No bought accounts yet.",
        "order.entry": "{status} · {public_id} · {nickname} · {amount}",
        "list.page": "Total: <b>{total}</b>\nPage: <b>{page}/{total_pages}</b>",
        "listings.title": "🏪 <b>My listings</b>\n\nChoose a section:",
        "listings.active": "🟢 Active listings",
        "listings.pending": "🟡 Reserved",
        "listings.sold": "✅ Sold",
        "listings.all": "📚 All listings",
        "listings.new": "➕ New listing",
        "listings.empty": "📭 No listings yet.",
        "section.buyer": "🛍 <b>Buy an account</b>\n\nChoose a platform:",
        "section.seller": "📤 <b>Sell an account</b>\n\nChoose a platform.",
        "section.orders": "📦 <b>My orders</b>\n\nChoose purchases or sales:",
        "orders.buyer": "🛍 My purchases",
        "orders.seller": "💰 My sales",
        "stats.title": "📊 <b>Statistics</b>",
        "stats.sales_title": "Sales",
        "stats.purchases_title": "Purchases",
        "stats.completed_sales": "Completed sales",
        "stats.completed_purchases": "Completed purchases",
        "stats.sales_volume": "Sales volume",
        "stats.purchases_volume": "Purchases volume",
        "stats.total_trade": "Total trade volume",
        "stats.commission": "Platform commission",
        "stats.net_earned": "Net earned",
        "stats.active_listings": "Active listings",
        "stats.pending_trades": "Pending trades",
        "stats.rating": "Rating",
        "stats.reviews": "Reviews",
        "settings.title": "⚙️ <b>Settings</b>",
        "settings.language": "Language",
        "settings.current": "Current language",
        "settings.choose": "Choose a language:",
        "settings.refresh_profile": "🔄 Refresh profile",
        "settings.language_changed": "✅ Language changed.",
        "settings.profile_refreshed": "✅ Profile refreshed.",
        "help.title": "ℹ️ <b>Help</b>",
        "help.body": (
            "🛍 <b>Buyer</b> — choose a platform, open an account card, and buy it.\n"
            "📤 <b>Seller</b> — choose a platform and submit account details.\n"
            "📦 <b>My orders</b> — track the status of your purchases and sales.\n"
            "💰 <b>My balance</b> — view your balance and transaction history.\n\n"
            "⚠️ Passwords are stored encrypted and shown to the buyer only after payment.\n\n"
            "The bot works fully automatically without an admin panel."
        ),
        "help.support": "📞 <b>Support:</b> {support}",
        "status.pending_payment": "⏳ Pending payment",
        "status.paid": "💳 Paid",
        "status.delivered": "📤 Delivered",
        "status.completed": "✅ Completed",
        "status.disputed": "⚠️ Disputed",
        "status.cancelled": "❌ Cancelled",
        "status.refunded": "↩️ Refunded",
        "status.unresolved": "🔴 Unresolved",
        "tx.payment": "Payment",
        "tx.escrow_hold": "Escrow hold",
        "tx.hourly_release": "Hourly release",
        "tx.completion_release": "Completion release",
        "tx.platform_commission": "Platform commission",
        "tx.refund": "Refund",
        "tx.payout": "Payout",
        "tx.adjustment": "Adjustment",
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


def normalize_locale(value: str | None) -> str:
    code = (value or "").strip().lower().replace("_", "-")
    if code.startswith("ru"):
        return "ru"
    if code.startswith("en"):
        return "en"
    return DEFAULT_LOCALE


def user_locale(user: object) -> str:
    preferred = getattr(user, "preferred_language", None)
    if preferred:
        return normalize_locale(preferred)
    return normalize_locale(getattr(user, "language_code", None))


def t(key: str, locale: str | None = None, **kwargs: object) -> str:
    lang = normalize_locale(locale)
    template = TEXTS.get(lang, TEXTS[DEFAULT_LOCALE]).get(key)
    if template is None:
        template = TEXTS[DEFAULT_LOCALE].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template


def menu_texts(locale: str | None = None) -> dict[str, str]:
    lang = normalize_locale(locale)
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
