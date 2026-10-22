"""Janela principal da aplicação."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME
from ..config import SETTINGS_KEY_CLOSE_TO_TRAY
from ..database.repositories import (
    ErrorRepository,
    GroupRepository,
    PostRepository,
    SettingsRepository,
)
from ..models import CheckResult
from ..notifications.service import NotificationService
from ..services.autostart import AutostartError, WindowsAutostart
from .controller import MonitorController
from .theme import DARK_STYLE
from .tray import TrayIcon
from .util import fmt_datetime
from .views import DashboardView, GroupsView, HistoryView, SettingsView
from .views.dashboard_view import monitor_state_text

APP_TITLE = APP_NAME
logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    """Janela principal com navegação por abas/views."""

    def __init__(
        self,
        conn,
        controller: MonitorController,
        *,
        autostart: Optional[WindowsAutostart] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(DARK_STYLE)

        # Repositórios
        self._conn = conn
        self._groups_repo = GroupRepository(conn)
        self._posts_repo = PostRepository(conn)
        self._settings_repo = SettingsRepository(conn)
        self._errors_repo = ErrorRepository(conn)

        self._controller = controller
        self._autostart = autostart or WindowsAutostart()
        self._tray: Optional[TrayIcon] = None
        self._tray_hint_shown = False
        self._quitting = False

        # Views
        self._dashboard = DashboardView()
        self._groups_view = GroupsView(self._groups_repo)
        self._history_view = HistoryView(self._posts_repo)
        self._settings_view = SettingsView()

        # Navegação
        self._build_ui()
        self._build_tray()

        # Conectar sinais
        self._groups_view.data_changed.connect(self.reload_all)
        self._settings_view.interval_changed.connect(self._change_interval)
        self._settings_view.notifications_changed.connect(self._change_notifications)
        self._settings_view.close_to_tray_changed.connect(
            self._change_close_to_tray
        )
        self._settings_view.start_with_windows_changed.connect(
            self._change_start_with_windows
        )
        self._settings_view.test_notification_requested.connect(
            self._test_notification
        )
        self._settings_view.check_requested.connect(self._request_manual_check)
        self._history_view.check_requested.connect(self._request_manual_check)
        self._controller.check_started.connect(self._on_check_started)
        self._controller.check_finished.connect(self._on_check_finished)
        self._controller.check_failed.connect(self._on_check_failed)

        # Primeiro carregamento
        self.reload_all()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setSpacing(0)
        side_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Steam Free Games")
        title.setObjectName("appTitle")
        side_layout.addWidget(title)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        buttons = [
            ("Painel", self._dashboard, "dashboard"),
            ("Grupos RSS", self._groups_view, "groups"),
            ("Histórico de jogos", self._history_view, "history"),
            ("Configurações", self._settings_view, "settings"),
        ]

        for label, _view, _key in buttons:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            if len(self._nav_group.buttons()) == 0:
                btn.setChecked(True)
            self._nav_group.addButton(btn)
            side_layout.addWidget(btn)

        side_layout.addStretch(1)
        root.addWidget(sidebar)

        # Stacked
        self._stack = QStackedWidget()
        for _label, view, _key in buttons:
            self._stack.addWidget(view)
        root.addWidget(self._stack, 1)

        # Mapear botões ao índice
        map_buttons = list(self._nav_group.buttons())
        for i, btn in enumerate(map_buttons):
            btn.clicked.connect(lambda _b, idx=i: self._stack.setCurrentIndex(idx))

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("Bandeja do sistema indisponível; fechar encerrará o app.")
            return
        self._tray = TrayIcon(self)
        self._tray.open_requested.connect(self.show_window)
        self._tray.check_requested.connect(self._request_manual_check)
        self._tray.notifications_toggled.connect(self._change_notifications)
        self._tray.quit_requested.connect(self.quit_app)
        self._tray.set_notifications_enabled(
            NotificationService(self._conn, None).enabled
        )
        self._tray.show()

    @property
    def tray_available(self) -> bool:
        return self._tray is not None

    def show_window(self) -> None:
        """Restaura e traz a janela para frente."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        """Encerra o aplicativo a partir da bandeja."""
        self._quitting = True
        if self._tray is not None:
            self._tray.hide()
        self.close()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._quitting:
            event.accept()
            return
        if (
            self._tray is not None
            and self._settings_repo.get_bool(SETTINGS_KEY_CLOSE_TO_TRAY, True)
        ):
            self.hide()
            event.ignore()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self._tray.show_background_hint()
            return
        event.accept()

    # ----- Ações e eventos ------------------------------------------------
    def _change_interval(self, minutes: int) -> None:
        self._controller.interval_minutes = minutes
        self._controller.persist_interval()

    def _change_notifications(self, enabled: bool) -> None:
        NotificationService(self._conn, None).set_enabled(enabled)
        if self._tray is not None:
            self._tray.set_notifications_enabled(enabled)

    def _change_close_to_tray(self, enabled: bool) -> None:
        self._settings_repo.set(SETTINGS_KEY_CLOSE_TO_TRAY, "1" if enabled else "0")

    def _change_start_with_windows(self, enabled: bool) -> None:
        try:
            if enabled:
                self._autostart.enable()
            else:
                self._autostart.disable()
        except AutostartError as exc:
            logger.error("Falha ao alterar inicialização automática: %s", exc)
            QMessageBox.critical(self, "Inicialização automática", str(exc))
        except Exception as exc:  # noqa: BLE001 - erro inesperado no registro
            logger.exception("Falha inesperada ao alterar inicialização automática")
            QMessageBox.critical(self, "Inicialização automática", str(exc))
        self.reload_all()

    def _test_notification(self) -> None:
        try:
            self._controller.test_notification()
        except Exception as exc:  # noqa: BLE001 - reportado ao usuário
            logger.error("Falha na notificação de teste: %s", exc)
            QMessageBox.critical(
                self,
                "Testar notificação",
                f"Não foi possível exibir a notificação:\n{exc}",
            )
        else:
            QMessageBox.information(
                self,
                "Testar notificação",
                "Notificação enviada. Verifique a central de notificações "
                "do sistema.",
            )

    def _request_manual_check(self) -> None:
        self._controller.trigger_check(force_prices=True)

    def _on_check_started(self) -> None:
        self.reload_all()

    def _on_check_finished(self, result: CheckResult) -> None:
        self.reload_all()

    def _on_check_failed(self, message: str) -> None:
        self.reload_all()

    # ----- Carregamento ---------------------------------------------------
    def reload_all(self) -> None:
        running = self._controller.is_running
        result = self._controller.last_result
        free_count = self._posts_repo.count_free_now()
        groups = self._groups_repo.list_all()
        groups_count = len(groups)
        raw_last_check = self._settings_repo.get("last_check_at")
        last_check = (
            datetime.fromisoformat(raw_last_check) if raw_last_check else None
        )
        last_text = fmt_datetime(last_check)
        state_text = monitor_state_text(result, running)

        recent = self._posts_repo.list_recent(limit=15, status="free")
        self._dashboard.refresh(
            free_count=free_count,
            groups_count=groups_count,
            state_text=state_text,
            last_check_text=last_text,
            recent=recent,
        )

        self._groups_view.refresh()
        self._history_view.refresh()

        notifications_enabled = NotificationService(self._conn, None).enabled
        close_to_tray = self._settings_repo.get_bool(
            SETTINGS_KEY_CLOSE_TO_TRAY, True
        )
        try:
            start_with_windows = self._autostart.is_enabled()
        except AutostartError as exc:
            logger.warning("Falha ao consultar inicialização automática: %s", exc)
            start_with_windows = False

        self._settings_view.load(
            interval_minutes=self._controller.interval_minutes,
            notifications_enabled=notifications_enabled,
            close_to_tray=close_to_tray,
            tray_available=self._tray is not None,
            start_with_windows=start_with_windows,
            start_with_windows_supported=self._autostart.supported,
            errors=self._errors_repo.recent(),
        )

        if self._tray is not None:
            self._tray.set_free_count(free_count)
            self._tray.set_notifications_enabled(notifications_enabled)
            self._tray.set_check_enabled(not running)