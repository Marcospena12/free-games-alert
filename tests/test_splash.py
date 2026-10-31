"""Testes da splash screen e do tema da barra de título."""

from __future__ import annotations

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from free_games_hub.ui.splash import SplashScreen, _asset_dirs, _load_logo
from free_games_hub.ui.window_theme import apply_dark_title_bar


def test_asset_dirs_inclui_packaging(qapp) -> None:
    dirs = _asset_dirs()

    assert dirs
    assert any(directory.name == "assets" for directory in dirs)
    assert any(directory.parent.name == "packaging" for directory in dirs)


def test_logo_carrega_imagem_valida(qapp) -> None:
    pixmap = _load_logo()

    assert not pixmap.isNull()
    assert pixmap.width() > 0
    assert pixmap.height() > 0


def test_splash_revela_janela_principal(qapp) -> None:
    window = QWidget()
    splash = SplashScreen(duration_ms=0)

    splash.start()
    qapp.processEvents()
    splash.finish(window)
    QTest.qWait(700)

    assert window.isVisible()
    assert window.windowOpacity() > 0.9

    window.close()


def test_splash_sem_imagem_usa_fallback(qapp) -> None:
    splash = SplashScreen(duration_ms=0)

    assert splash.size().width() > 0
    assert splash.size().height() > 0

    splash.close()


def test_tema_nao_falha_no_offscreen(qapp) -> None:
    widget = QWidget()
    widget.show()
    apply_dark_title_bar(widget)
    widget.close()
