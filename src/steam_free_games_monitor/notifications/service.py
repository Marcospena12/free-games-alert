"""Serviço que decide quando e como notificar ofertas confirmadas."""

from __future__ import annotations

import sqlite3

from ..config import NOTIFY_MAX_PER_RUN
from ..database.repositories import ErrorRepository, PostRepository, SettingsRepository
from ..models import Post
from ..services.deals import clean_title
from .base import Notifier, NullNotifier

SETTINGS_KEY_ENABLED = "notifications_enabled"


class NotificationService:
    """Despacha notificações de ofertas confirmadas como 100% grátis.

    Depois de processar uma publicação (com ou sem sucesso na exibição), marca
    ``notified = 1`` para nunca reenviar a mesma notificação. Quando as
    notificações estão desligadas, os pendentes são consumidos sem envio para
    evitar uma enxurrada ao reativar a preferência.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        notifier: Notifier | NullNotifier | None = None,
    ) -> None:
        self._conn = conn
        self._posts = PostRepository(conn)
        self._settings = SettingsRepository(conn)
        self._errors = ErrorRepository(conn)
        self._notifier = notifier or NullNotifier()

    @property
    def enabled(self) -> bool:
        return self._settings.get_bool(SETTINGS_KEY_ENABLED, True)

    def set_enabled(self, enabled: bool) -> None:
        self._settings.set(SETTINGS_KEY_ENABLED, "1" if enabled else "0")

    def process_pending(self, limit: int = NOTIFY_MAX_PER_RUN) -> list[Post]:
        """Notifica ofertas grátis pendentes e marca todas como processadas."""
        if not self.enabled:
            self._posts.mark_all_pending_notified()
            return []

        notified: list[Post] = []
        for entry in self._posts.list_pending_notifications(limit):
            post = entry["post"]
            if post.id is None:
                continue
            title = clean_title(post.title) or post.title
            message = "100% grátis na Steam"
            if entry.get("group_name"):
                message += f" · {entry['group_name']}"
            open_url = post.store_url or post.publication_url
            try:
                self._notifier.notify(
                    title=title,
                    message=message,
                    open_url=open_url,
                )
                notified.append(post)
            except Exception as exc:  # noqa: BLE001 - erro nunca derruba o app
                self._errors.add(
                    post.group_id,
                    f"Falha ao exibir notificação ({title}): {exc}",
                )
            self._posts.set_notified(post.id, True)
        return notified
