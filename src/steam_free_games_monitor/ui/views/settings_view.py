"""Visão de configurações da aplicação."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...models import MonitorError
from ..util import fmt_datetime


class SettingsView(QWidget):
    interval_changed = Signal(int)
    notifications_changed = Signal(bool)
    close_to_tray_changed = Signal(bool)
    start_with_windows_changed = Signal(bool)
    test_notification_requested = Signal()
    check_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Configurações")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        monitoring_group = QGroupBox("Monitoramento")
        monitoring_form = QFormLayout(monitoring_group)
        self._interval = QSpinBox()
        self._interval.setRange(1, 1440)
        self._interval.setSuffix(" min")
        self._interval.setToolTip("Intervalo entre verificações automáticas dos feeds.")
        monitoring_form.addRow("Intervalo de verificação", self._interval)

        self._notifications = QCheckBox("Notificar novas ofertas gratuitas")
        self._notifications.setToolTip(
            "Notifica somente ofertas confirmadas com 100% de desconto na Steam."
        )
        monitoring_form.addRow(self._notifications)

        self._close_to_tray = QCheckBox("Fechar a janela para a bandeja")
        self._close_to_tray.setToolTip(
            "Ao fechar a janela, o monitor continua rodando no ícone da bandeja."
        )
        monitoring_form.addRow(self._close_to_tray)

        self._start_with_windows = QCheckBox(
            "Iniciar com o Windows (minimizado na bandeja)"
        )
        self._start_with_windows.setToolTip(
            "Cria uma entrada para o usuário atual iniciar o monitor junto com "
            "o Windows, sem abrir a janela."
        )
        monitoring_form.addRow(self._start_with_windows)

        self._check_now = QPushButton("Verificar agora")
        self._check_now.setObjectName("primary")
        self._check_now.setToolTip("Executa uma verificação manual de todos os grupos ativos.")
        self._test_notification = QPushButton("Testar notificação")
        self._test_notification.setToolTip(
            "Envia uma notificação de teste e mostra o resultado."
        )
        actions = QHBoxLayout()
        actions.addWidget(self._check_now)
        actions.addWidget(self._test_notification)
        actions.addStretch(1)
        monitoring_form.addRow(actions)
        layout.addWidget(monitoring_group)

        errors_group = QGroupBox("Erros recentes do monitoramento")
        errors_layout = QVBoxLayout(errors_group)
        self._errors = QListWidget()
        self._errors.setAlternatingRowColors(True)
        errors_layout.addWidget(self._errors)
        layout.addWidget(errors_group, 1)

        self._interval.valueChanged.connect(
            lambda _v: self.interval_changed.emit(self._interval.value())
        )
        self._notifications.toggled.connect(self.notifications_changed.emit)
        self._close_to_tray.toggled.connect(self.close_to_tray_changed.emit)
        self._start_with_windows.toggled.connect(self.start_with_windows_changed.emit)
        self._test_notification.clicked.connect(self.test_notification_requested.emit)
        self._check_now.clicked.connect(self.check_requested.emit)

    def load(
        self,
        *,
        interval_minutes: int,
        notifications_enabled: bool,
        close_to_tray: bool,
        tray_available: bool,
        start_with_windows: bool,
        start_with_windows_supported: bool,
        errors: list[MonitorError],
    ) -> None:
        self._interval.blockSignals(True)
        self._interval.setValue(interval_minutes)
        self._interval.blockSignals(False)

        self._notifications.blockSignals(True)
        self._notifications.setChecked(notifications_enabled)
        self._notifications.blockSignals(False)

        self._close_to_tray.blockSignals(True)
        self._close_to_tray.setChecked(close_to_tray)
        self._close_to_tray.setEnabled(tray_available)
        self._close_to_tray.setToolTip(
            "Ao fechar a janela, o monitor continua rodando no ícone da bandeja."
            if tray_available
            else "Bandeja do sistema indisponível neste ambiente."
        )
        self._close_to_tray.blockSignals(False)

        self._start_with_windows.blockSignals(True)
        self._start_with_windows.setChecked(start_with_windows)
        self._start_with_windows.setEnabled(start_with_windows_supported)
        self._start_with_windows.setToolTip(
            "Cria uma entrada para o usuário atual iniciar o monitor junto com "
            "o Windows, sem abrir a janela."
            if start_with_windows_supported
            else "Disponível apenas no Windows."
        )
        self._start_with_windows.blockSignals(False)

        self._errors.clear()
        for error in errors:
            text = f"{fmt_datetime(error.created_at)} — {error.message}"
            self._errors.addItem(text)
        if not errors:
            self._errors.addItem("Nenhum erro registrado até o momento.")