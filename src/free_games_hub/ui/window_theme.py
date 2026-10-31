"""Ajustes nativos de aparência da janela (Windows)."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_LEGACY = 19
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36

CAPTION_RGB = (0x0B, 0x0F, 0x17)
TEXT_RGB = (0xE6, 0xED, 0xF3)


def _colorref(rgb: tuple[int, int, int]) -> int:
    red, green, blue = rgb
    return red | (green << 8) | (blue << 16)


def _is_windows() -> bool:
    return sys.platform == "win32"


def _is_offscreen() -> bool:
    try:
        return QGuiApplication.platformName() == "offscreen"
    except Exception:  # noqa: BLE001 - sem QGuiApplication instanciada
        return True


def apply_dark_title_bar(widget: QWidget) -> None:
    """Deixa a barra de título nativa escura e integrada ao tema do app.

    Usa a API DWM do Windows: mantém arrasto, botões, cantos arredondados e
    Snap Layouts nativos. Sem efeito em outros sistemas.
    """
    if not _is_windows() or _is_offscreen():
        return

    try:
        dwmapi = ctypes.windll.dwmapi
        hwnd = wintypes.HWND(int(widget.winId()))
    except (AttributeError, OSError, ValueError):
        return

    enabled = ctypes.c_int(1)
    for attribute in (_DWMWA_USE_IMMERSIVE_DARK_MODE, _DWMWA_USE_IMMERSIVE_DARK_MODE_LEGACY):
        try:
            if (
                dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
                )
                == 0
            ):
                break
        except OSError:
            continue

    for attribute, rgb in (
        (_DWMWA_BORDER_COLOR, CAPTION_RGB),
        (_DWMWA_CAPTION_COLOR, CAPTION_RGB),
        (_DWMWA_TEXT_COLOR, TEXT_RGB),
    ):
        value = ctypes.c_uint32(_colorref(rgb))
        try:
            dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
        except OSError:
            continue
