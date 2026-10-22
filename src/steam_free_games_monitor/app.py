"""Ponto de entrada da aplicação."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from . import APP_NAME, __version__
from .config import (
    DEFAULT_CHECK_INTERVAL_MINUTES,
    DEFAULT_FEED_URL,
    DEFAULT_GROUP_NAME,
    REQUEST_TIMEOUT_SECONDS,
    SETTINGS_KEY_CLOSE_TO_TRAY,
    data_dir,
    database_path,
)
from .database import connect_db, init_db
from .database.repositories import GroupRepository, SettingsRepository
from .notifications.backend import build_notifier
from .services.autostart import (
    AUTOSTART_ARG,
    AutostartError,
    WindowsAutostart,
    start_hidden_requested,
)
from .services.feed_fetcher import UrlFeedFetcher
from .ui.controller import MonitorController
from .ui.main_window import MainWindow
from .ui.single_instance import QUIT_ARG, SingleInstance
from .ui.tray import build_app_icon

LOG_FILENAME = "app.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"
logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configura log em arquivo e, quando existir, também no terminal."""
    handlers: list[logging.Handler] = []
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    try:
        handlers.append(
            RotatingFileHandler(
                data_dir() / LOG_FILENAME,
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        )
    except OSError:
        pass
    if not handlers:
        handlers.append(logging.NullHandler())
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=handlers,
        force=True,
    )


def _request_quit(qt_args: list[str]) -> int:
    """Pede o encerramento da instância existente (usado pelo instalador)."""
    app = QCoreApplication(qt_args)
    guard = SingleInstance()
    try:
        sent = guard.send_quit()
    except RuntimeError as exc:
        logger.error("Falha ao encerrar a instância existente: %s", exc)
        return 1
    if sent:
        logger.info("Instância existente encerrada.")
    else:
        logger.info("Nenhuma instância em execução para encerrar.")
    app.processEvents()
    return 0


def main() -> int:
    start_hidden = start_hidden_requested()
    quit_requested = QUIT_ARG in sys.argv[1:]
    qt_args = [
        arg for arg in sys.argv if arg not in (AUTOSTART_ARG, QUIT_ARG)
    ]
    _configure_logging()
    if quit_requested:
        return _request_quit(qt_args)

    app = QApplication(qt_args)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("SteamFreeGamesMonitor")
    app.setWindowIcon(build_app_icon())
    logger.info("Steam Free Games Monitor %s iniciando", __version__)

    guard = SingleInstance()
    if not guard.acquire(activate_existing=not start_hidden):
        return 0

    # Conexão inicial
    db_path = database_path()
    conn = connect_db(db_path)
    init_db(conn)

    # Cadastro automático do feed inicial
    group_repo = GroupRepository(conn)
    if group_repo.get_by_url(DEFAULT_FEED_URL) is None:
        group_repo.add(DEFAULT_GROUP_NAME, DEFAULT_FEED_URL, active=True)

    # Configurações padrão
    settings_repo = SettingsRepository(conn)
    if settings_repo.get("check_interval_minutes") is None:
        settings_repo.set("check_interval_minutes", str(DEFAULT_CHECK_INTERVAL_MINUTES))
    if settings_repo.get("notifications_enabled") is None:
        settings_repo.set("notifications_enabled", "1")
    if settings_repo.get(SETTINGS_KEY_CLOSE_TO_TRAY) is None:
        settings_repo.set(SETTINGS_KEY_CLOSE_TO_TRAY, "1")

    # Serviços
    fetcher = UrlFeedFetcher(timeout=REQUEST_TIMEOUT_SECONDS)
    notifier = build_notifier(on_error=logger.warning)

    # Controlador e janela
    autostart = WindowsAutostart()
    try:
        if autostart.refresh_command():
            logger.info("Comando de inicialização automática atualizado")
    except AutostartError as exc:
        logger.warning("Falha ao atualizar inicialização automática: %s", exc)

    controller = MonitorController(db_path, fetcher, notifier, settings_repo)
    window = MainWindow(conn, controller, autostart=autostart)
    guard.activation_requested.connect(window.show_window)
    guard.quit_requested.connect(window.quit_app)

    if not (start_hidden and window.tray_available):
        window.show()

    # Dispara uma verificação inicial e inicia o agendamento
    controller.trigger_check()

    app.aboutToQuit.connect(controller.shutdown)
    code = app.exec()
    conn.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())