"""Testes da camada de persistência (SQLite)."""

from steam_free_games_monitor.database import (
    ErrorRepository,
    GroupRepository,
    PostRepository,
    SettingsRepository,
)
from steam_free_games_monitor.database.repositories import hash_identifier
from steam_free_games_monitor.models import Post

GROUP_URL = "https://steamcommunity.com/groups/jogosbra/rss/"


def _sample_post(group_id: int, identifier: str, title: str) -> Post:
    return Post(
        group_id=group_id,
        identifier=identifier,
        identifier_source="guid",
        title=title,
        publication_url=f"https://steamcommunity.com/groups/jogosbra/detail/{identifier}",
        store_url="https://store.steampowered.com/app/1/x",
    )


class TestPostRepository:
    def test_insert_e_detecta_duplicata(self, db):
        group_id = GroupRepository(db).add("G", GROUP_URL)
        assert group_id is not None
        repo = PostRepository(db)

        created = repo.insert_if_missing(_sample_post(group_id, "guid-1", "[FREE] A"))
        assert created is not None
        assert created.id is not None
        assert created.discovered_at is not None
        assert not created.notified

        duplicated = repo.insert_if_missing(_sample_post(group_id, "guid-1", "[FREE] A"))
        assert duplicated is None
        assert PostRepository(db).count() == 1

    def test_identificador_por_link_e_por_hash(self, db):
        group_id = GroupRepository(db).add("G", GROUP_URL)
        repo = PostRepository(db)
        assert repo.insert_if_missing(
            Post(group_id=group_id, identifier="https://x/1", identifier_source="link", title="[FREE] 1")
        ) is not None
        assert repo.insert_if_missing(
            Post(group_id=group_id, identifier="hash:abc", identifier_source="hash", title="[FREE] 2")
        ) is not None
        assert PostRepository(db).count() == 2

    def test_hash_identifier_deterministico(self):
        from datetime import datetime

        first = hash_identifier("[FREE] X", datetime(2026, 1, 1))
        second = hash_identifier("[FREE] X", datetime(2026, 1, 1))
        assert first == second
        assert first.startswith("hash:")


class TestSettings:
    def test_defaults(self, db):
        repo = SettingsRepository(db)
        assert repo.get_int("check_interval_minutes", 5) == 5
        assert repo.get_bool("notifications_enabled", True) is True

    def test_set_e_get(self, db):
        repo = SettingsRepository(db)
        repo.set("check_interval_minutes", "10")
        repo.set("notifications_enabled", "false")
        assert repo.get_int("check_interval_minutes", 5) == 10
        assert repo.get_bool("notifications_enabled", True) is False

    def test_sobrescrita(self, db):
        repo = SettingsRepository(db)
        repo.set("k", "1")
        repo.set("k", "2")
        assert repo.get("k") == "2"


class TestErrors:
    def test_adiciona_e_lista_recentes(self, db):
        group_id = GroupRepository(db).add("G", GROUP_URL)
        repo = ErrorRepository(db)
        repo.add(None, "erro global")
        repo.add(group_id, "erro do grupo")
        recent = repo.recent()
        assert len(recent) == 2
        assert recent[0].message == "erro do grupo"
        assert recent[0].group_id == group_id
        assert any(e.group_id is None for e in recent)

    def test_erros_nao_perdem_outros_dados(self, db, sample_feed_bytes):
        from steam_free_games_monitor.services.monitor import MonitorService

        from conftest import FakeFetcher

        group_id = GroupRepository(db).add("G", GROUP_URL)
        fetcher = FakeFetcher(responses={
            GROUP_URL: sample_feed_bytes,
        })
        MonitorService(db, fetcher).check_all()
        from steam_free_games_monitor.services.feed_fetcher import FeedFetchError

        ErrorRepository(db).add(group_id, "feed caiu")
        assert PostRepository(db).count() == 2
        assert len(ErrorRepository(db).recent()) == 1