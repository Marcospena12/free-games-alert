"""Contrato e implementação mínima (sem SO) para notificações."""

from __future__ import annotations

from typing import Optional, Protocol


class Notifier(Protocol):
    """Contrato de emissão de notificação nativa do sistema operacional."""

    def notify(
        self, *, title: str, message: str, open_url: Optional[str]
    ) -> None: ...


class NullNotifier:
    """Notificador que não exibe nada.

    Usado quando o ambiente não oferece suporte a notificações nativas.
    A limitação é registrada, mas o aplicativo continua funcionando com o
    histórico e os alertas visíveis na interface.
    """

    def __init__(self, reason: str = "notificações nativas indisponíveis") -> None:
        self.reason = reason

    def notify(
        self, *, title: str, message: str, open_url: Optional[str]
    ) -> None:
        # Sem integração real: não simulamos uma notificação bem-sucedida.
        return