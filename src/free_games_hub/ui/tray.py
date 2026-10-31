"""Ícone da bandeja do sistema e menu de segundo plano."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

ICON_COLORS = ("#66c0f4", "#171a21")


def _find_icon_asset() -> Optional[Path]:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / "free_games_hub" / "assets"
    else:
        candidate = Path(__file__).resolve().parent.parent / "assets"
    for filename in ("app.ico", "app.png"):
        path = candidate / filename
        if path.exists():
            return path
    return None


def build_app_icon() -> QIcon:
    """Retorna o ícone do aplicativo (do arquivo de asset ou desenhado via QPainter)."""
    asset = _find_icon_asset()
    if asset is not None:
        icon = QIcon(str(asset))
        if not icon.isNull():
            return icon

    icon = QIcon()
    for size in (16, 22, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = max(1, round(size * 0.06))
        radius = size * 0.22
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ICON_COLORS[0]))
        painter.drawRoundedRect(
            margin,
            margin,
            size - 2 * margin,
            size - 2 * margin,
            radius,
            radius,
        )

        font = QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(max(8, round(size * 0.62)))
        painter.setFont(font)
        painter.setPen(QColor(ICON_COLORS[1]))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")
        painter.end()

        icon.addPixmap(pixmap)
    return icon


class TrayIcon(QSystemTrayIcon):
    """Ícone da bandeja com atalhos para abrir, verificar e sair."""

    open_requested = Signal()
    check_requested = Signal()
    notifications_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(build_app_icon(), parent)
        self.setToolTip("Free Games Hub")

        self._menu = QMenu(parent)
        self._open_action = self._menu.addAction("Abrir painel")
        self._check_action = self._menu.addAction("Verificar agora")
        self._notifications_action = self._menu.addAction("Notificações")
        self._notifications_action.setCheckable(True)
        self._menu.addSeparator()
        self._quit_action = self._menu.addAction("Sair")
        self.setContextMenu(self._menu)

        self._open_action.triggered.connect(self.open_requested.emit)
        self._check_action.triggered.connect(self.check_requested.emit)
        self._notifications_action.toggled.connect(self.notifications_toggled.emit)
        self._quit_action.triggered.connect(self.quit_requested.emit)
        self.activated.connect(self._on_activated)
        self.messageClicked.connect(self.open_requested.emit)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_requested.emit()

    def set_free_count(self, count: int) -> None:
        label = "oferta grátis" if count == 1 else "ofertas grátis"
        self.setToolTip(f"Free Games Hub — {count} {label}")

    def set_notifications_enabled(self, enabled: bool) -> None:
        self._notifications_action.blockSignals(True)
        self._notifications_action.setChecked(enabled)
        self._notifications_action.blockSignals(False)

    def set_check_enabled(self, enabled: bool) -> None:
        self._check_action.setEnabled(enabled)

    def show_background_hint(self) -> None:
        self.showMessage(
            "Free Games Hub",
            "O monitor continua rodando em segundo plano. "
            "Use este ícone para abrir a janela ou sair.",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )
