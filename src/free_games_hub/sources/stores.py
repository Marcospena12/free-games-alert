"""Definições e mapeamentos oficiais de lojas e plataformas."""

from __future__ import annotations

from typing import Final, Optional

# Slugs oficiais validados empiricamente na GamerPower API e extensões suportadas
STORE_STEAM: Final = "steam"
STORE_EPIC: Final = "epic-games-store"
STORE_GOG: Final = "gog"
STORE_ITCHIO: Final = "itchio"
STORE_DRM_FREE: Final = "drm-free"
STORE_UBISOFT: Final = "ubisoft"
STORE_BATTLENET: Final = "battlenet"
STORE_ORIGIN: Final = "origin"
STORE_PRIME: Final = "prime-gaming"
STORE_STOVE: Final = "stove"
STORE_VR: Final = "vr"
STORE_PC: Final = "pc"
STORE_PS5: Final = "ps5"
STORE_PS4: Final = "ps4"
STORE_XBOX_SERIES: Final = "xbox-series-xs"
STORE_XBOX_ONE: Final = "xbox-one"
STORE_SWITCH: Final = "switch"
STORE_ANDROID: Final = "android"
STORE_IOS: Final = "ios"

STORE_LABELS: Final[dict[str, str]] = {
    STORE_STEAM: "Steam",
    STORE_EPIC: "Epic Games Store",
    STORE_GOG: "GOG",
    STORE_ITCHIO: "Itch.io",
    STORE_DRM_FREE: "DRM-Free",
    STORE_UBISOFT: "Ubisoft Connect",
    STORE_BATTLENET: "Battle.net",
    STORE_ORIGIN: "EA App / Origin",
    STORE_PRIME: "Prime Gaming",
    STORE_STOVE: "Smilegate Stove",
    STORE_VR: "VR (Realidade Virtual)",
    STORE_PC: "PC (Outros)",
    STORE_PS5: "PlayStation 5",
    STORE_PS4: "PlayStation 4",
    STORE_XBOX_SERIES: "Xbox Series X|S",
    STORE_XBOX_ONE: "Xbox One",
    STORE_SWITCH: "Nintendo Switch",
    STORE_ANDROID: "Android",
    STORE_IOS: "iOS",
}

# Lojas habilitadas por padrão
DEFAULT_ENABLED_STORES: Final[list[str]] = [
    STORE_STEAM,
    STORE_EPIC,
    STORE_GOG,
    STORE_ITCHIO,
    STORE_DRM_FREE,
    STORE_UBISOFT,
    STORE_BATTLENET,
    STORE_ORIGIN,
    STORE_PRIME,
    STORE_STOVE,
]

# Tipos de giveaway
TYPE_GAME: Final = "game"
TYPE_LOOT: Final = "loot"  # DLC / Itens / Moedas
TYPE_BETA: Final = "beta"  # Acesso antecipado / Playtests
TYPE_OTHER: Final = "other"

TYPE_LABELS: Final[dict[str, str]] = {
    TYPE_GAME: "Jogos completos",
    TYPE_LOOT: "DLCs e Itens",
    TYPE_BETA: "Betas e Acesso antecipado",
    TYPE_OTHER: "Outros",
}

DEFAULT_ENABLED_TYPES: Final[list[str]] = [
    TYPE_GAME,
]


def normalize_store_label(label: str) -> str:
    """Retorna o rótulo amigável a partir do slug da loja."""
    return STORE_LABELS.get(label.lower(), label.title())


def parse_platform_string(
    platforms_str: str,
    title: Optional[str] = None,
    url: Optional[str] = None,
) -> list[str]:
    """Extrai os slugs de lojas a partir do texto de plataformas, com detecção inteligente por título/URL."""
    matched: list[str] = []

    # 1. Detecção inteligente através do título e URL (para casos onde platform é genérica ex: 'PC')
    text_to_scan = f"{title or ''} {url or ''}".lower()
    if "(stove)" in text_to_scan or "onstove.com" in text_to_scan:
        matched.append(STORE_STOVE)
    if "(prime gaming)" in text_to_scan or "(amazon)" in text_to_scan or "gaming.amazon.com" in text_to_scan:
        matched.append(STORE_PRIME)
    if "(ubisoft)" in text_to_scan or "ubisoft.com" in text_to_scan or "uplay" in text_to_scan:
        matched.append(STORE_UBISOFT)
    if "battle.net" in text_to_scan or "battlenet" in text_to_scan:
        matched.append(STORE_BATTLENET)
    if "(origin)" in text_to_scan or "ea.com" in text_to_scan or "origin.com" in text_to_scan:
        matched.append(STORE_ORIGIN)

    # 2. Análise dos termos do campo platforms
    parts = [p.strip().lower() for p in (platforms_str or "").split(",") if p.strip()]

    for part in parts:
        if "steam" in part:
            matched.append(STORE_STEAM)
        elif "epic" in part:
            matched.append(STORE_EPIC)
        elif "gog" in part:
            matched.append(STORE_GOG)
        elif "switch" in part:
            matched.append(STORE_SWITCH)
        elif "itch" in part or "itch.io" in part:
            matched.append(STORE_ITCHIO)
        elif "drm-free" in part:
            matched.append(STORE_DRM_FREE)
        elif "ubisoft" in part:
            matched.append(STORE_UBISOFT)
        elif "battle" in part or "blizzard" in part:
            matched.append(STORE_BATTLENET)
        elif "origin" in part:
            matched.append(STORE_ORIGIN)
        elif "vr" in part or "rift" in part or "quest" in part:
            matched.append(STORE_VR)
        elif "ps5" in part or "playstation 5" in part:
            matched.append(STORE_PS5)
        elif "ps4" in part or "playstation 4" in part:
            matched.append(STORE_PS4)
        elif "series" in part:
            matched.append(STORE_XBOX_SERIES)
        elif "xbox one" in part:
            matched.append(STORE_XBOX_ONE)
        elif "android" in part:
            matched.append(STORE_ANDROID)
        elif "ios" in part:
            matched.append(STORE_IOS)
        elif "pc" in part:
            matched.append(STORE_PC)

    if not matched:
        matched.append(STORE_PC)

    # Remover duplicatas mantendo ordem
    unique: list[str] = []
    for m in matched:
        if m not in unique:
            unique.append(m)

    # Prioritizar lojas e plataformas específicas antes do identificador genérico 'pc'
    if STORE_PC in unique and len(unique) > 1:
        unique.remove(STORE_PC)
        unique.append(STORE_PC)

    return unique


STORE_STYLES: Final[dict[str, dict[str, str]]] = {
    STORE_STEAM: {"bg": "#0f2133", "border": "#1b5886", "text": "#66c0f4", "short": "Steam", "icon_symbol": "🎮"},
    STORE_EPIC: {"bg": "#1e2024", "border": "#4a5160", "text": "#ffffff", "short": "Epic Games", "icon_symbol": "⚡"},
    STORE_GOG: {"bg": "#2a124d", "border": "#7c3aed", "text": "#d8b4fe", "short": "GOG", "icon_symbol": "✨"},
    STORE_ITCHIO: {"bg": "#450a0a", "border": "#b91c1c", "text": "#fca5a5", "short": "Itch.io", "icon_symbol": "🕹️"},
    STORE_DRM_FREE: {"bg": "#064e3b", "border": "#059669", "text": "#6ee7b7", "short": "DRM-Free", "icon_symbol": "🔓"},
    STORE_UBISOFT: {"bg": "#0c2d48", "border": "#0284c7", "text": "#38bdf8", "short": "Ubisoft", "icon_symbol": "🌀"},
    STORE_BATTLENET: {"bg": "#0a192f", "border": "#1d4ed8", "text": "#60a5fa", "short": "Battle.net", "icon_symbol": "🛡️"},
    STORE_ORIGIN: {"bg": "#2e0f0f", "border": "#ea580c", "text": "#fb923c", "short": "EA / Origin", "icon_symbol": "🎯"},
    STORE_PRIME: {"bg": "#2e1065", "border": "#9333ea", "text": "#d8b4fe", "short": "Prime Gaming", "icon_symbol": "👑"},
    STORE_STOVE: {"bg": "#2e1205", "border": "#f97316", "text": "#fdba74", "short": "Stove", "icon_symbol": "🔥"},
    STORE_VR: {"bg": "#042f2e", "border": "#0d9488", "text": "#5eead4", "short": "VR", "icon_symbol": "🥽"},
    STORE_PS5: {"bg": "#0c2d48", "border": "#2563eb", "text": "#93c5fd", "short": "PlayStation", "icon_symbol": "🔷"},
    STORE_PS4: {"bg": "#0c2d48", "border": "#2563eb", "text": "#93c5fd", "short": "PlayStation", "icon_symbol": "🔷"},
    STORE_XBOX_SERIES: {"bg": "#064e3b", "border": "#16a34a", "text": "#86efac", "short": "Xbox", "icon_symbol": "❎"},
    STORE_XBOX_ONE: {"bg": "#064e3b", "border": "#16a34a", "text": "#86efac", "short": "Xbox", "icon_symbol": "❎"},
    STORE_SWITCH: {"bg": "#450a0a", "border": "#dc2626", "text": "#fca5a5", "short": "Switch", "icon_symbol": "🔴"},
    STORE_ANDROID: {"bg": "#1e1b4b", "border": "#4f46e5", "text": "#c7d2fe", "short": "Mobile", "icon_symbol": "📱"},
    STORE_IOS: {"bg": "#1e1b4b", "border": "#4f46e5", "text": "#c7d2fe", "short": "Mobile", "icon_symbol": "📱"},
    STORE_PC: {"bg": "#1e293b", "border": "#475569", "text": "#cbd5e1", "short": "PC", "icon_symbol": "💻"},
}


def get_store_style(store_slug: str) -> dict[str, str]:
    """Retorna cores e símbolos para badge da loja."""
    return STORE_STYLES.get(store_slug.lower(), STORE_STYLES[STORE_PC])
