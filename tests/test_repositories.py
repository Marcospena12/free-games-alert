"""Testes da camada de persistência (SQLite)."""

from free_games_hub.database import (
    ErrorRepository,
    GroupRepository,
    PostRepository,
    SettingsRepository,
)
from free_games_hub.database.repositories import hash_identifier
from free_games_hub.models import Post

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

    def test_in_library_persistencia_e_filtros(self, db):
        group_id = GroupRepository(db).add("G", GROUP_URL)
        repo = PostRepository(db)

        post1 = repo.insert_if_missing(
            Post(group_id=group_id, identifier="g-1", identifier_source="guid", title="[FREE] Game 1")
        )
        post2 = repo.insert_if_missing(
            Post(group_id=group_id, identifier="g-2", identifier_source="guid", title="[FREE] Game 2")
        )
        assert post1 is not None and post2 is not None
        repo.update_price_check(post1.id, status="free")
        repo.update_price_check(post2.id, status="free")

        assert not repo.get_by_identifier("g-1").in_library
        assert not repo.get_by_identifier("g-2").in_library

        assert repo.count_free_now(include_in_library=False) == 2
        assert repo.count_free_now(include_in_library=True) == 2

        # Marca post1 como adicionado à biblioteca
        repo.set_in_library(post1.id, True)

        # Agora count_free_now sem include_in_library deve ser 1
        assert repo.count_free_now(include_in_library=False) == 1
        assert repo.count_free_now(include_in_library=True) == 2

        # list_recent com in_library=False deve trazer apenas post2
        recent_unclaimed = repo.list_recent(status="free", in_library=False)
        assert len(recent_unclaimed) == 1
        assert recent_unclaimed[0]["post"].id == post2.id

        # list_recent com status="in_library" deve trazer apenas post1
        recent_claimed = repo.list_recent(status="in_library")
        assert len(recent_claimed) == 1
        assert recent_claimed[0]["post"].id == post1.id
        assert recent_claimed[0]["post"].in_library is True

        # Desmarca da biblioteca
        repo.set_in_library(post1.id, False)
        assert repo.count_free_now(include_in_library=False) == 2
        recent_all_free = repo.list_recent(status="free", in_library=False)
        assert len(recent_all_free) == 2

    def test_list_pending_notifications_ignora_jogos_na_biblioteca(self, db):
        group_id = GroupRepository(db).add("G", GROUP_URL)
        repo = PostRepository(db)

        post = repo.insert_if_missing(
            Post(
                group_id=group_id,
                identifier="g-lib-notif",
                identifier_source="guid",
                title="[FREE] In Lib",
                notified=False,
                in_library=True,
            )
        )
        assert post is not None
        repo.update_price_check(post.id, status="free")
        pending = repo.list_pending_notifications()
        assert len(pending) == 0


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
        from free_games_hub.services.monitor import MonitorService

        from conftest import FakeFetcher

        group_id = GroupRepository(db).add("G", GROUP_URL)
        fetcher = FakeFetcher(responses={
            GROUP_URL: sample_feed_bytes,
        })
        MonitorService(db, fetcher).check_all()
        from free_games_hub.services.feed_fetcher import FeedFetchError

        ErrorRepository(db).add(group_id, "feed caiu")
        assert PostRepository(db).count() == 2
        assert len(ErrorRepository(db).recent()) == 1