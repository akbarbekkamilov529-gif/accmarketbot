from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True, slots=True)
class Platform:
    key: str
    name: str
    emoji: str
    category: str


GAME_PLATFORMS: tuple[Platform, ...] = (
    Platform("brawl_stars", "Brawl Stars", "⭐", "game"),
    Platform("pubg_mobile", "PUBG Mobile", "🎯", "game"),
    Platform("standoff_2", "Standoff 2", "🔫", "game"),
    Platform("fortnite", "Fortnite", "🏗", "game"),
    Platform("free_fire", "Free Fire", "🔥", "game"),
    Platform("clash_of_clans", "Clash of Clans", "🏰", "game"),
    Platform("clash_royale", "Clash Royale", "👑", "game"),
    Platform("roblox", "Roblox", "🧱", "game"),
    Platform("minecraft", "Minecraft", "⛏", "game"),
    Platform("mobile_legends", "Mobile Legends", "🛡", "game"),
    Platform("genshin_impact", "Genshin Impact", "🌌", "game"),
    Platform("dota_2", "Dota 2", "⚔", "game"),
    Platform("cs2", "CS2", "🎮", "game"),
    Platform("valorant", "Valorant", "🎯", "game"),
    Platform("ea_fc", "EA Sports FC", "⚽", "game"),
    Platform("call_of_duty", "Call of Duty", "💥", "game"),
    Platform("other_games", "Boshqa o'yinlar", "🎲", "game"),
)

SOCIAL_PLATFORMS: tuple[Platform, ...] = (
    Platform("instagram", "Instagram", "📸", "social"),
    Platform("youtube", "YouTube", "▶️", "social"),
    Platform("facebook", "Facebook", "📘", "social"),
    Platform("tiktok", "TikTok", "🎵", "social"),
    Platform("telegram", "Telegram", "✈️", "social"),
    Platform("x_twitter", "X (Twitter)", "🐦", "social"),
    Platform("snapchat", "Snapchat", "👻", "social"),
    Platform("other_social", "Boshqa platformalar", "🌐", "social"),
)

ALL_PLATFORMS: tuple[Platform, ...] = GAME_PLATFORMS + SOCIAL_PLATFORMS
PLATFORM_BY_KEY: dict[str, Platform] = {platform.key: platform for platform in ALL_PLATFORMS}

CALLBACK_SEP = ":"
SORT_NEWEST = "newest"
SORT_PRICE_ASC = "cheap"
SORT_PRICE_DESC = "expensive"
VALID_SORTS = {SORT_NEWEST, SORT_PRICE_ASC, SORT_PRICE_DESC}

SELLER_FILTER_ALL = "all"
SELLER_FILTER_ACTIVE = "active"
SELLER_FILTER_PENDING = "pending"
SELLER_FILTER_SOLD = "sold"
VALID_SELLER_FILTERS = {
    SELLER_FILTER_ALL,
    SELLER_FILTER_ACTIVE,
    SELLER_FILTER_PENDING,
    SELLER_FILTER_SOLD,
}

MONEY_QUANT = Decimal("0.01")


def platform_display(key: str) -> str:
    platform = PLATFORM_BY_KEY.get(key)
    if platform is None:
        return key
    return f"{platform.emoji} {platform.name}"


def quantize_money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def format_money(value: Decimal, currency: str = "UZS") -> str:
    value = quantize_money(value)
    if value == value.to_integral_value():
        formatted = f"{int(value):,}".replace(",", " ")
    else:
        formatted = f"{value:,.2f}".replace(",", " ")
    return f"{formatted} {currency}"


def platform_keyboard_rows(platforms: tuple[Platform, ...], prefix: str) -> list[list[tuple[str, str]]]:
    rows: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for platform in platforms:
        current.append((f"{platform.emoji} {platform.name}", f"{prefix}:{platform.key}"))
        if len(current) == 2:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    return rows
