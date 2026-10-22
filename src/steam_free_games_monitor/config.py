"""Configuração e localização de diretórios de dados da aplicação.

Os dados são armazenados em um diretório apropriado por sistema operacional,
nunca dependendo do diretório de trabalho atual.

A variável de ambiente ``SFGM_DATA_DIR`` permite sobrescrever o diretório
(útil em testes e em execuções portáteis).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_GROUP_NAME = "Comunidade Jogos Brasil"
DEFAULT_FEED_URL = "https://steamcommunity.com/groups/jogosbra/rss/"

DEFAULT_CHECK_INTERVAL_MINUTES = 5
REQUEST_TIMEOUT_SECONDS = 15.0
FREE_TAG = "[FREE]"
DB_FILENAME = "steam_free_games_monitor.db"
MAX_KEPT_ERRORS = 50

STEAM_STORE_COUNTRY = "br"
STEAM_STORE_LANGUAGE = "portuguese"
PRICE_CHECK_TIMEOUT_SECONDS = 15.0
PRICE_CHECK_DELAY_SECONDS = 0.4
PRICE_CHECK_MAX_PER_RUN = 15
PRICE_CHECK_MAX_AGE_DAYS = 30
PRICE_CHECK_FREE_TTL_MINUTES = 30
PRICE_CHECK_UNKNOWN_TTL_MINUTES = 360
PRICE_CHECK_NOT_FREE_TTL_MINUTES = 1440

NOTIFY_MAX_PER_RUN = 5
NOTIFIER_TIMEOUT_SECONDS = 10.0
SETTINGS_KEY_CLOSE_TO_TRAY = "close_to_tray"


def data_dir() -> Path:
    """Retorna o diretório de dados da aplicação, criando-o se necessário."""
    override = os.environ.get("SFGM_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        folder = "SteamFreeGamesMonitor"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        folder = "steam-free-games-monitor"

    path = base / folder if not override else base
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    """Retorna o caminho do arquivo de banco SQLite."""
    return data_dir() / DB_FILENAME