"""Tela de abertura com a logo transparente do aplicativo."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PySide6.QtGui import QCursor, QGuiApplication, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .tray import build_app_icon

SPLASH_FILENAME = "splash.png"
DEFAULT_DURATION_MS = 3000
MAX_LOGO_SIZE = 480
FADE_IN_MS = 200
FADE_OUT_MS = 240
WINDOW_FADE_MS = 320


def _asset_dirs() -> list[Path]:
    """Diretórios onde a imagem da splash pode estar (empacotado ou dev)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return [Path(sys._MEIPASS) / "free_games_hub" / "assets"]

    root = Path(__file__).resolve().parents[3]
    candidates = [
        Path(__file__).resolve().parent.parent / "assets",
        root / "packaging" / "assets",
    ]
    return [path for path in candidates if path.is_dir()]


def _fit(pixmap: QPixmap) -> QPixmap:
    if pixmap.width() <= MAX_LOGO_SIZE and pixmap.height() <= MAX_LOGO_SIZE:
        return pixmap
    return pixmap.scaled(
        MAX_LOGO_SIZE,
        MAX_LOGO_SIZE,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _load_logo() -> QPixmap:
    directories = _asset_dirs()
    for name in (SPLASH_FILENAME, "app.png", "app.ico"):
        for directory in directories:
            path = directory / name
            if not path.exists():
                continue
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return _fit(pixmap)
    return _fit(build_app_icon().pixmap(256, 256))


class SplashScreen(QWidget):
    """Logo flutuante, sem molduras, exibida por alguns segundos."""

    def __init__(
        self,
        duration_ms: int = DEFAULT_DURATION_MS,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("Free Games Hub")

        self._duration_ms = max(0, duration_ms)
        self._elapsed = QElapsedTimer()
        self._target: Optional[QWidget] = None
        self._revealed = False

        logo = QLabel(self)
        logo.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        logo.setPixmap(_load_logo())
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(logo)
        self.setFixedSize(logo.pixmap().size())

        self._fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_in.setDuration(FADE_IN_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_out.setDuration(FADE_OUT_MS)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self.close)

        self._window_fade: Optional[QPropertyAnimation] = None

    def start(self) -> None:
        """Exibe a splash e inicia a contagem do tempo de permanência."""
        self._elapsed.start()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._fade_in.start()

    def finish(self, window: QWidget) -> None:
        """Agenda a revelação da janela principal respeitando a duração."""
        self._target = window
        elapsed = self._elapsed.elapsed() if self._elapsed.isValid() else 0
        remaining = max(0, self._duration_ms - elapsed)
        QTimer.singleShot(remaining, self._reveal)

    def _reveal(self) -> None:
        if self._revealed:
            return
        self._revealed = True

        window = self._target
        if window is not None:
            window.setWindowOpacity(0.0)
            window.show()
            window.raise_()
            window.activateWindow()
            self._window_fade = QPropertyAnimation(window, b"windowOpacity", window)
            self._window_fade.setDuration(WINDOW_FADE_MS)
            self._window_fade.setStartValue(0.0)
            self._window_fade.setEndValue(1.0)
            self._window_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._window_fade.start(
                QPropertyAnimation.DeletionPolicy.DeleteWhenStopped
            )

        self._fade_out.setStartValue(self.windowOpacity())
        self._fade_out.setEndValue(0.0)
        self._fade_out.start()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - assinatura Qt
        """Permite pular a splash com um clique."""
        if self._target is not None:
            self._reveal()
        super().mousePressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802 - assinatura Qt
        super().showEvent(event)
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.move(geometry.center() - self.rect().center())
