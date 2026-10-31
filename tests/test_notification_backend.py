"""Testes do adaptador desktop-notifier usado no Windows."""

import sys
import types

from free_games_hub.notifications import backend as backend_module


class FakeNotification:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class FakeDesktopNotifier:
    sent: list[FakeNotification] = []

    def __init__(self, app_name: str) -> None:
        self.app_name = app_name

    async def send_notification(self, notification: FakeNotification) -> None:
        self.sent.append(notification)


def _install_fake_module(monkeypatch) -> None:
    module = types.ModuleType("desktop_notifier")
    module.DesktopNotifier = FakeDesktopNotifier
    module.Notification = FakeNotification
    monkeypatch.setitem(sys.modules, "desktop_notifier", module)
    FakeDesktopNotifier.sent = []


class TestDesktopNotifierBackend:
    def test_envia_link_no_construtor_da_notificacao(self, monkeypatch):
        _install_fake_module(monkeypatch)
        opened: list[str] = []
        monkeypatch.setattr(
            backend_module.webbrowser, "open", lambda url: opened.append(url)
        )
        backend = backend_module.DesktopNotifierBackend(app_name="Teste")

        backend.notify(
            title="Oferta",
            message="100% gratis",
            open_url="https://store.steampowered.com/app/1",
        )

        assert len(FakeDesktopNotifier.sent) == 1
        notification = FakeDesktopNotifier.sent[0]
        assert notification.title == "Oferta"
        assert callable(notification.on_clicked)
        notification.on_clicked()
        assert opened == ["https://store.steampowered.com/app/1"]

    def test_sem_link_nao_define_callback(self, monkeypatch):
        _install_fake_module(monkeypatch)
        backend = backend_module.DesktopNotifierBackend(app_name="Teste")

        backend.notify(title="Oferta", message="100% gratis", open_url=None)

        assert FakeDesktopNotifier.sent[0].on_clicked is None
