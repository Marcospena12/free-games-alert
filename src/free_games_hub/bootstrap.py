"""Inicialização compartilhada do banco de dados.

Tanto a API headless quanto o aplicativo legado PySide6 precisam garantir o
mesmo estado inicial: grupo RSS padrão e configurações mínimas. Manter isso em
um único lugar evita que uma interface nova abra com o banco vazio.
"""

from __future__ import annotations

import sqlite3

from .config import (
    DEFAULT_CHECK_INTERVAL_MINUTES,
    DEFAULT_FEED_URL,
    DEFAULT_GROUP_NAME,
    SETTINGS_KEY_CLOSE_TO_TRAY,
)
from .database.repositories import GroupRepository, SettingsRepository
from .services.filters import SETTINGS_KEY_GAMERPOWER_ENABLED

DEFAULT_SETTINGS: dict[str, str] = {
    "check_interval_minutes": str(DEFAULT_CHECK_INTERVAL_MINUTES),
    "notifications_enabled": "1",
    SETTINGS_KEY_GAMERPOWER_ENABLED: "1",
    SETTINGS_KEY_CLOSE_TO_TRAY: "1",
}


def ensure_defaults(conn: sqlite3.Connection) -> None:
    """Cria o grupo padrão e grava configurações ausentes.

    A operação é idempotente e não sobrescreve escolhas existentes do usuário.
    """
    groups = GroupRepository(conn)
    if groups.get_by_url(DEFAULT_FEED_URL) is None:
        groups.add(DEFAULT_GROUP_NAME, DEFAULT_FEED_URL, active=True)

    settings = SettingsRepository(conn)
    for key, value in DEFAULT_SETTINGS.items():
        if settings.get(key) is None:
            settings.set(key, value)
