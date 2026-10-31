"""Testes offscreen da janela principal, bandeja e inicialização automática."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from free_games_hub.database.repositories import SettingsRepository
from free_games_hub.services.autostart import WindowsAutostart
from free_games_hub.ui.controller import MonitorController
from free_games_hub.ui.main_window import MainWindow


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
        "free_games_hub.ui.main_window.QSystemTrayIcon.isSystemTrayAvailable",
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
            "Free Games Hub",
            "Notificações funcionando!",
            None,
        )
    ]
    controller.shutdown()
    window.deleteLater()


def test_marcar_como_adicionado_some_do_dashboard(qapp, db, monkeypatch) -> None:
    from free_games_hub.database.repositories import GroupRepository, PostRepository
    from free_games_hub.models import Post

    group_id = GroupRepository(db).add("G", "https://steamcommunity.com/groups/g/rss/")
    posts_repo = PostRepository(db)
    post = posts_repo.insert_if_missing(
        Post(
            group_id=group_id,
            identifier="g-dash-1",
            identifier_source="guid",
            title="[FREE] Super Game",
            store_url="https://store.steampowered.com/app/100/",
        )
    )
    posts_repo.update_price_check(post.id, status="free")

    window, controller, _notifier, _registry, tray = _build_window(db, monkeypatch)

    # Inicialmente, o dashboard exibe o jogo
    assert window._dashboard._recent.rowCount() == 1
    assert window._dashboard._free_value.text() == "1"

    # Simula o clique do usuário para marcar como adicionado à biblioteca
    window._dashboard.mark_in_library_requested.emit(post.id, True)

    # O jogo sumiu do dashboard e o contador de ofertas grátis zerou!
    assert window._dashboard._recent.rowCount() == 0
    assert window._dashboard._free_value.text() == "0"
    assert tray.free_count == 0

    # O post no banco agora tem in_library = 1
    stored = posts_repo.get_by_identifier("g-dash-1")
    assert stored.in_library is True

    controller.shutdown()
    window.deleteLater()


def test_historico_alterna_biblioteca(qapp, db, monkeypatch) -> None:
    from free_games_hub.database.repositories import GroupRepository, PostRepository
    from free_games_hub.models import Post

    group_id = GroupRepository(db).add("G", "https://steamcommunity.com/groups/g2/rss/")
    posts_repo = PostRepository(db)
    post = posts_repo.insert_if_missing(
        Post(
            group_id=group_id,
            identifier="g-hist-1",
            identifier_source="guid",
            title="[FREE] Hist Game",
            store_url="https://store.steampowered.com/app/200/",
        )
    )
    posts_repo.update_price_check(post.id, status="free")

    window, controller, _notifier, _registry, _tray = _build_window(db, monkeypatch)

    assert window._dashboard._recent.rowCount() == 1

    # Alterna status a partir do histórico
    window._history_view.mark_in_library_requested.emit(post.id, True)
    assert posts_repo.get_by_identifier("g-hist-1").in_library is True
    assert window._dashboard._recent.rowCount() == 0

    # Desmarca da biblioteca
    window._history_view.mark_in_library_requested.emit(post.id, False)
    assert posts_repo.get_by_identifier("g-hist-1").in_library is False
    assert window._dashboard._recent.rowCount() == 1

    controller.shutdown()
    window.deleteLater()
