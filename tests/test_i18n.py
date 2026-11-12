from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup

from app.i18n import (
    MENU_KEYS,
    SUPPORTED_LOCALES,
    menu_action_by_text,
    menu_texts,
    normalize_locale,
    t,
)
from app.keyboards.common import main_menu_kb
from app.models import OrderStatus


def test_locale_normalization_and_fallback() -> None:
    assert normalize_locale("ru-RU") == "ru"
    assert normalize_locale("en_US") == "en"
    assert normalize_locale("uz") == "uz"
    assert normalize_locale(None) == "uz"
    assert normalize_locale("unknown") == "uz"
    assert t("menu.profile", "ru") == "👤 Профиль"
    assert t("menu.profile", "en") == "👤 Profile"


def test_all_menu_labels_are_present_and_unique() -> None:
    actions = menu_action_by_text()
    total_labels = len(SUPPORTED_LOCALES) * len(MENU_KEYS)
    assert len(actions) == total_labels

    for locale in SUPPORTED_LOCALES:
        labels = menu_texts(locale)
        assert set(labels) == set(MENU_KEYS)
        assert all(labels.values())

    assert actions["👤 Profil"] == "profile"
    assert actions["💰 Мой баланс"] == "balance"
    assert actions["📊 Statistics"] == "stats"


def test_main_menu_is_reply_keyboard_and_localized() -> None:
    uz_menu = main_menu_kb("uz")
    ru_menu = main_menu_kb("ru")
    assert isinstance(uz_menu, ReplyKeyboardMarkup)
    assert isinstance(ru_menu, ReplyKeyboardMarkup)
    assert uz_menu.keyboard[0][0].text == "👤 Profil"
    assert ru_menu.keyboard[0][0].text == "👤 Профиль"
    assert len(uz_menu.keyboard) == 6


def test_status_translation() -> None:
    assert t("status.completed", "en") == "✅ Completed"
    assert t("status.completed", "ru") == "✅ Завершён"
    assert OrderStatus.COMPLETED.value == "completed"
