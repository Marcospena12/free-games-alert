"""Configuração e localização de diretórios de dados da aplicação.

Os dados são armazenados em um diretório apropriado por sistema operacional,
nunca dependendo do diretório de trabalho atual.

A variável de ambiente ``FGH_DATA_DIR`` permite sobrescrever o diretório
(útil em testes e em execuções portáteis). A variável antiga
``SFGM_DATA_DIR`` continua aceita por compatibilidade.

Na primeira execução após a renomeação de *Steam Free Games Monitor* para
*Free Games Hub*, o banco da versão antiga é copiado automaticamente para o
novo diretório, preservando histórico, configurações e filtros.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

DEFAULT_GROUP_NAME = "Comunidade Jogos Brasil"
DEFAULT_FEED_URL = "https://steamcommunity.com/groups/jogosbra/rss/"

DEFAULT_CHECK_INTERVAL_MINUTES = 5
REQUEST_TIMEOUT_SECONDS = 15.0
FREE_TAG = "[FREE]"
DB_FILENAME = "free_games_hub.db"
LEGACY_DB_FILENAME = "steam_free_games_monitor.db"
DATA_DIR_ENV = "FGH_DATA_DIR"
LEGACY_DATA_DIR_ENV = "SFGM_DATA_DIR"
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


def _base_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def _app_folder() -> str:
    return "FreeGamesHub" if sys.platform == "win32" else "free-games-hub"


def _legacy_folder() -> str:
    return (
        "SteamFreeGamesMonitor"
        if sys.platform == "win32"
        else "steam-free-games-monitor"
    )


def _environment_override() -> str | None:
    return os.environ.get(DATA_DIR_ENV) or os.environ.get(LEGACY_DATA_DIR_ENV)


def data_dir() -> Path:
    """Retorna o diretório de dados da aplicação, criando-o se necessário."""
    override = _environment_override()
    if override:
        path = Path(override)
    else:
        path = _base_dir() / _app_folder()

    path.mkdir(parents=True, exist_ok=True)
    return path


def migrate_legacy_data(target: Path) -> bool:
    """Copia o banco da versão antiga quando o novo ainda não existe."""
    if _environment_override():
        return False

    legacy = _base_dir() / _legacy_folder() / LEGACY_DB_FILENAME
    destination = target / DB_FILENAME
    if not legacy.is_file() or destination.exists():
        return False

    try:
        shutil.copy2(legacy, destination)
    except OSError:
        return False
    return True


def database_path() -> Path:
    """Retorna o caminho do arquivo de banco SQLite."""
    path = data_dir()
    migrate_legacy_data(path)
    return path / DB_FILENAME
