"""Testes do serviço de notificações de ofertas confirmadas."""

from steam_free_games_monitor.database import ErrorRepository
from steam_free_games_monitor.database.repositories import (
    GroupRepository,
    PostRepository,
    SettingsRepository,
)
from steam_free_games_monitor.models import Post
from steam_free_games_monitor.notifications.service import NotificationService

GROUP_URL = "https://steamcommunity.com/groups/jogosbra/rss/"


class RecordingNotifier:
    """Notificador fictício que apenas registra as chamadas."""

    def __init__(self, fail_on: set[str] | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_on = fail_on or set()

    def notify(self, *, title: str, message: str, open_url) -> None:
        if title in self.fail_on:
            raise RuntimeError(f"falha simulada em {title}")
        self.calls.append({"title": title, "message": message, "open_url": open_url})


def _add_group(db) -> int:
    return GroupRepository(db).add("Grupo", GROUP_URL)


def _seed_post(
    db,
    title: str,
    *,
    status: str = "free",
    store_url: str | None = None,
) -> Post:
    group_id = _add_group(db)
    repo = PostRepository(db)
    created = repo.insert_if_missing(
        Post(
            group_id=group_id,
            identifier=f"guid-{title}",
            identifier_source="guid",
            title=title,
            publication_url=f"https://example.com/p/{title}",
            store_url=store_url,
            notified=False,
        )
    )
    assert created is not None and created.id is not None
    repo.update_price_check(created.id, status=status)
    stored = repo.get_by_identifier(created.identifier)
    assert stored is not None
    return stored


class TestNotificationPreference:
    def test_notifica_somente_ofertas_confirmadas(self, db):
        _seed_post(db, "[FREE] Apex", status="free")
        _seed_post(db, "[FREE] Pago", status="not_free")
        _seed_post(db, "[FREE] F2P", status="f2p")
        _seed_post(db, "[FREE] Duvidoso", status="unknown")
        notifier = RecordingNotifier()
        service = NotificationService(db, notifier)

        done = service.process_pending()

        assert len(done) == 1
        assert len(notifier.calls) == 1
        assert notifier.calls[0]["title"] == "Apex"
        assert "100% grátis" in notifier.calls[0]["message"]
        assert "Grupo" in notifier.calls[0]["message"]
        assert notifier.calls[0]["open_url"] == "https://example.com/p/[FREE] Apex"

        repo = PostRepository(db)
        assert repo.get_by_identifier("guid-[FREE] Apex").notified is True
        assert repo.get_by_identifier("guid-[FREE] Pago").notified is False
        assert repo.get_by_identifier("guid-[FREE] F2P").notified is False
        assert repo.get_by_identifier("guid-[FREE] Duvidoso").notified is False

    def test_oferta_confirmada_depois_e_notificada(self, db):
        _seed_post(db, "[FREE] Depois", status="unknown")
        notifier = RecordingNotifier()
        service = NotificationService(db, notifier)

        assert service.process_pending() == []
        assert notifier.calls == []

        repo = PostRepository(db)
        stored = repo.get_by_identifier("guid-[FREE] Depois")
        assert stored is not None and stored.id is not None
        repo.update_price_check(stored.id, status="free")

        assert len(service.process_pending()) == 1
        assert notifier.calls[0]["title"] == "Depois"

    def test_nao_notifica_quando_desabilitado_e_consome_pendentes(self, db):
        _seed_post(db, "[FREE] A")
        notifier = RecordingNotifier()
        service = NotificationService(db, notifier)
        service.set_enabled(False)

        done = service.process_pending()

        assert done == []
        assert notifier.calls == []
        stored = PostRepository(db).get_by_identifier("guid-[FREE] A")
        assert stored is not None and stored.notified is True

    def test_preferencia_persistida(self, db):
        service = NotificationService(db, RecordingNotifier())
        service.set_enabled(False)
        assert SettingsRepository(db).get_bool("notifications_enabled", True) is False

    def test_limite_por_rodada(self, db):
        for index in range(3):
            _seed_post(db, f"[FREE] {index}")
        notifier = RecordingNotifier()
        service = NotificationService(db, notifier)

        assert len(service.process_pending(limit=2)) == 2
        assert len(notifier.calls) == 2
        assert len(service.process_pending(limit=2)) == 1


class TestNotificationFailure:
    def test_falha_registra_erro_e_nao_reprocessa(self, db):
        _seed_post(db, "[FREE] Quebra")
        notifier = RecordingNotifier(fail_on={"Quebra"})
        service = NotificationService(db, notifier)

        done = service.process_pending()

        assert done == []
        stored = PostRepository(db).get_by_identifier("guid-[FREE] Quebra")
        assert stored is not None and stored.notified is True
        recent = ErrorRepository(db).recent()
        assert recent and "notificação" in recent[0].message.lower()
        assert notifier.calls == []

    def test_usar_link_da_loja_quando_disponivel(self, db):
        _seed_post(
            db,
            "[FREE] X",
            store_url="https://store.steampowered.com/app/1",
        )
        notifier = RecordingNotifier()
        service = NotificationService(db, notifier)

        service.process_pending()

        assert notifier.calls[0]["open_url"] == "https://store.steampowered.com/app/1"
