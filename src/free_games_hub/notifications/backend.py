"""Backend de notificações via desktop-notifier.

O desktop-notifier é assíncrono (D-Bus no Linux, WinRT no Windows). Para não
acoplar a interface a um loop asyncio, o backend executa o notificador em uma
thread dedicada com um event loop próprio. ``notify`` aguarda a conclusão do
envio para que falhas sejam registradas e reportadas ao chamador.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import webbrowser
from typing import Callable, Optional

from .. import APP_NAME
from ..config import NOTIFIER_TIMEOUT_SECONDS


class DesktopNotifierBackend:
    """Adaptador do desktop-notifier executado em thread própria."""

    def __init__(
        self,
        app_name: str = APP_NAME,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._app_name = app_name
        self.on_error = on_error
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._notifier = None
        self._ready = threading.Event()

        self._thread = threading.Thread(
            target=self._run_loop, name="fgh-notifier", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            raise RuntimeError("O notificador não inicializou a tempo")

    def _run_loop(self) -> None:
        from desktop_notifier import DesktopNotifier

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._notifier = DesktopNotifier(app_name=self._app_name)
        self._ready.set()
        self._loop.run_forever()

    def notify(self, *, title: str, message: str, open_url: Optional[str]) -> None:
        if self._loop is None or self._notifier is None:
            raise RuntimeError("Notificador não inicializado")

        from desktop_notifier import Notification

        async def _send() -> None:
            on_clicked = (
                (lambda: webbrowser.open(open_url)) if open_url else None
            )
            notification = Notification(
                title=title,
                message=message,
                on_clicked=on_clicked,
            )
            await self._notifier.send_notification(notification)

        future = asyncio.run_coroutine_threadsafe(_send(), self._loop)
        try:
            future.result(timeout=NOTIFIER_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            future.cancel()
            error_message = "Tempo esgotado ao exibir a notificação"
            if self.on_error is not None:
                self.on_error(error_message)
            raise RuntimeError(error_message) from exc
        except Exception as exc:  # noqa: BLE001 - erro repassado ao chamador
            error_message = f"Falha ao exibir notificação: {exc}"
            if self.on_error is not None:
                self.on_error(error_message)
            raise RuntimeError(error_message) from exc


class NullNotifierWithError:
    """Notificador no-op que reporta a limitação, sem simular sucesso."""

    def __init__(self, reason: str, on_error: Optional[Callable[[str], None]] = None) -> None:
        from .base import NullNotifier

        self._inner = NullNotifier(reason)
        self.on_error = on_error

    def notify(self, *, title: str, message: str, open_url: Optional[str]) -> None:
        if self.on_error is not None:
            self.on_error(self._inner.reason)
        raise RuntimeError(self._inner.reason)


def build_notifier(
    on_error: Optional[Callable[[str], None]] = None,
) -> object:
    """Cria o notificador adequado à plataforma (Windows/Linux) ou o fallback."""
    if sys.platform in ("win32", "linux"):
        try:
            return DesktopNotifierBackend(app_name=APP_NAME, on_error=on_error)
        except Exception as exc:  # noqa: BLE001 - degradação graciosa
            return NullNotifierWithError(
                f"notificações nativas indisponíveis ({exc})", on_error=on_error
            )
    return NullNotifierWithError(
        f"plataforma '{sys.platform}' sem suporte a notificações", on_error=on_error
    )