"""Testes offscreen da janela principal, bandeja e inicialização automática."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from steam_free_games_monitor.database.repositories import SettingsRepository
from steam_free_games_monitor.services.autostart import WindowsAutostart
from steam_free_games_monitor.ui.controller import MonitorController
from steam_free_games_monitor.ui.main_window import MainWindow


class FakeFetcher:
    def fetch(self, url: str) -> bytes:
        raise AssertionError("fetch não deveria ser chamado neste teste")


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Optional[str]]] = []

    def notify(self, *, title: str, message: str, open_url: Optional[str]) -> None:
        self.calls.append((title, message, open_url))


class FakeTray:
    def __init__(self) -> None:
        self.hints = 0
        self.free_count = 0
        self.notifications: Optional[bool] = None
        self.check_enabled: Optional[bool] = None

    def show_background_hint(self) -> None:
        self.hints += 1

    def hide(self) -> None:
        pass

    def set_free_count(self, count: int) -> None:
        self.free_count = count

    def set_notifications_enabled(self, enabled: bool) -> None:
        self.notifications = enabled

    def set_check_enabled(self, enabled: bool) -> None:
        self.check_enabled = enabled


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def read(self, value_name: str) -> Optional[str]:
        return self.values.get(value_name)

    def write(self, value_name: str, value: str) -> None:
        self.values[value_name] = value

    def delete(self, value_name: str) -> None:
        if value_name not in self.values:
            raise FileNotFoundError(value_name)
        del self.values[value_name]


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _build_window(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "steam_free_games_monitor.ui.main_window.QSystemTrayIcon.isSystemTrayAvailable",
        staticmethod(lambda: False),
    )
    settings = SettingsRepository(db)
    settings.set("check_interval_minutes", "5")
    settings.set("close_to_tray", "1")
    notifier = RecordingNotifier()
    controller = MonitorController(
        Path("test.db"), FakeFetcher(), notifier, settings
    )
    registry = FakeRegistry()
    autostart = WindowsAutostart(
        registry,
        value_name="Teste",
        command="cmd --hidden",
        platform="win32",
    )
    window = MainWindow(db, controller, autostart=autostart)
    fake_tray = FakeTray()
    window._tray = fake_tray
    window.reload_all()
    return window, controller, notifier, registry, fake_tray


def test_fechar_esconde_na_bandeja(qapp, db, monkeypatch) -> None:
    window, controller, _notifier, _registry, tray = _build_window(db, monkeypatch)
    window.show()

    window.close()

    assert window.isVisible() is False
    assert tray.hints == 1
    controller.shutdown()
    window.deleteLater()


def test_sair_nao_mostra_aviso_de_segundo_plano(qapp, db, monkeypatch) -> None:
    window, controller, _notifier, _registry, tray = _build_window(db, monkeypatch)
    window.show()
    window._quitting = True

    window.close()

    assert tray.hints == 0
    controller.shutdown()
    window.deleteLater()


def test_alternar_inicializacao_com_windows(qapp, db, monkeypatch) -> None:
    window, controller, _notifier, registry, _tray = _build_window(db, monkeypatch)

    window._change_start_with_windows(True)
    assert registry.values["Teste"] == "cmd --hidden"
    assert window._settings_view._start_with_windows.isChecked() is True

    window._change_start_with_windows(False)
    assert registry.values == {}
    assert window._settings_view._start_with_windows.isChecked() is False

    controller.shutdown()
    window.deleteLater()


def test_persistir_preferencia_de_bandeja(qapp, db, monkeypatch) -> None:
    window, controller, _notifier, _registry, tray = _build_window(db, monkeypatch)

    window._change_close_to_tray(False)

    assert SettingsRepository(db).get_bool("close_to_tray", True) is False
    assert tray.notifications is True
    controller.shutdown()
    window.deleteLater()


def test_notificacao_de_teste_usa_notificador(qapp, db, monkeypatch) -> None:
    window, controller, notifier, _registry, _tray = _build_window(db, monkeypatch)

    controller.test_notification()

    assert notifier.calls == [
        (
            "Steam Free Games Monitor",
            "Notificações funcionando!",
            None,
        )
    ]
    controller.shutdown()
    window.deleteLater()
