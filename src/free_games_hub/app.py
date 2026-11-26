"""Ponto de entrada da aplicação."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from . import APP_NAME, __version__
from .bootstrap import ensure_defaults
from .config import REQUEST_TIMEOUT_SECONDS, database_path
from .database import connect_db, init_db
from .database.repositories import SettingsRepository
from .logging_setup import configure_logging
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
from .ui.splash import SplashScreen
from .ui.tray import build_app_icon

logger = logging.getLogger(__name__)


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
    configure_logging()
    if quit_requested:
        return _request_quit(qt_args)

    app = QApplication(qt_args)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("FreeGamesHub")
    app.setWindowIcon(build_app_icon())
    logger.info("Free Games Hub %s iniciando", __version__)

    guard = SingleInstance()
    if not guard.acquire(activate_existing=not start_hidden):
        return 0

    splash = None
    if not start_hidden:
        splash = SplashScreen()
        splash.start()
        app.processEvents()

    # Conexão inicial: schema atual + grupo e configurações padrão.
    db_path = database_path()
    conn = connect_db(db_path)
    init_db(conn)
    ensure_defaults(conn)
    settings_repo = SettingsRepository(conn)

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
        if splash is not None:
            splash.finish(window)
        else:
            window.show()

    # Dispara uma verificação inicial e inicia o agendamento
    controller.trigger_check()

    app.aboutToQuit.connect(controller.shutdown)
    code = app.exec()
    conn.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())