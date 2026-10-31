"""Testes do monitoramento: inicialização, duplicação, falhas e continuidade."""

from datetime import datetime
from pathlib import Path

import pytest

from free_games_hub.database.repositories import (
    GroupRepository,
    PostRepository,
    SettingsRepository,
)
from free_games_hub.services.feed_fetcher import FeedFetchError
from free_games_hub.services.monitor import MonitorService

from conftest import GROUP_URL, OTHER_URL


def _add_group(db, name="Comunidade Jogos Brasil", url=GROUP_URL, active=True) -> int:
    repo = GroupRepository(db)
    return repo.add(name, url, active)


def _fetch(initial: bytes, next_: bytes, fetcher):
    fetcher.responses[GROUP_URL] = initial
    fetcher.responses[OTHER_URL] = next_


class TestInitialization:
    def test_primeira_leitura_importa_sem_notificacoes_retroativas(self, db, sample_feed_bytes, fetcher):
        group_id = _add_group(db)
        fetcher.responses[GROUP_URL] = sample_feed_bytes

        result = MonitorService(db, fetcher).check_all()

        assert result.new_posts == []
        assert result.errors == []
        posts = PostRepository(db).list_for_group(group_id)
        assert len(posts) == 2
        assert all(p.notified for p in posts)
        group = GroupRepository(db).get(group_id)
        assert group is not None and group.initialized
        assert group.last_checked_at is not None

    def test_falha_na_primeira_consulta_nao_marca_inicializado(self, db, sample_feed_bytes, fetcher):
        group_id = _add_group(db)
        fetcher.errors[GROUP_URL] = FeedFetchError("tempo esgotado")

        MonitorService(db, fetcher).check_all()

        group = GroupRepository(db).get(group_id)
        assert group is not None
        assert not group.initialized
        assert PostRepository(db).list_for_group(group_id) == []

        fetcher.errors.pop(GROUP_URL, None)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        result = MonitorService(db, fetcher).check_all()
        assert result.new_posts == []
        group = GroupRepository(db).get(group_id)
        assert group is not None and group.initialized

    def test_sem_itens_relevantes_ainda_inicializa(self, db, fetcher):
        _add_group(db)
        xml = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><title>t</title>
          <item><title>Apenas aviso</title><guid>x-1</guid></item>
        </channel></rss>"""
        fetcher.responses[GROUP_URL] = xml

        MonitorService(db, fetcher).check_all()

        group = GroupRepository(db).get_by_url(GROUP_URL)
        assert group is not None and group.initialized
        assert PostRepository(db).count() == 0


class TestNewPosts:
    def test_novas_publicacoes_detectadas_depois_da_inicializacao(
        self, db, sample_feed_bytes, sample_feed_next_bytes, fetcher
    ):
        _add_group(db)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        monitor = MonitorService(db, fetcher)
        monitor.check_all()

        fetcher.responses[GROUP_URL] = sample_feed_next_bytes
        result = monitor.check_all()

        assert len(result.new_posts) == 1
        new = result.new_posts[0]
        assert new.title == "[FREE] Deadshot"
        assert (
            new.store_url
            == "https://store.steampowered.com/app/2484180/Deadshot/?curator_clanid=6250352"
        )
        assert not new.notified

    def test_item_repetido_nao_gera_duplicata_na_rodada_seguinte(
        self, db, sample_feed_bytes, sample_feed_next_bytes, fetcher
    ):
        _add_group(db)
        fetcher.responses[GROUP_URL] = sample_feed_next_bytes
        monitor = MonitorService(db, fetcher)
        monitor.check_all()
        monitor.check_all()

        result = monitor.check_all()
        assert result.new_posts == []
        assert PostRepository(db).count() == 3

    def test_publicacoes_sem_tag_sao_ignoradas(self, db, sample_feed_bytes, fetcher):
        _add_group(db)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        monitor = MonitorService(db, fetcher)
        monitor.check_all()
        titles = [p.title for p in PostRepository(db).list_for_group(1)]
        assert not any("Post normal" in t for t in titles)


class TestFailures:
    def test_feed_indisponivel_mantem_historico_e_registra_erro(
        self, db, sample_feed_bytes, fetcher
    ):
        _add_group(db)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        monitor = MonitorService(db, fetcher)
        monitor.check_all()

        fetcher.errors[GROUP_URL] = FeedFetchError("conexao recusada")
        result = monitor.check_all()

        assert result.failed_groups == 1
        assert len(result.errors) == 1
        assert PostRepository(db).count() == 2

        fetcher.errors.pop(GROUP_URL, None)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        result = monitor.check_all()
        assert result.failed_groups == 0
        assert PostRepository(db).count() == 2
        assert result.new_posts == []

    def test_continuidade_quando_um_grupo_falha(
        self, db, sample_feed_bytes, fetcher
    ):
        other_bytes = (Path(__file__).parent / "fixtures" / "sample_feed_other.xml").read_bytes()
        _add_group(db, name="Grupo A", url=GROUP_URL)
        _add_group(db, name="Grupo B", url=OTHER_URL)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        fetcher.responses[OTHER_URL] = other_bytes
        monitor = MonitorService(db, fetcher)
        monitor.check_all()

        fetcher.errors[OTHER_URL] = FeedFetchError("erro no grupo B")
        result = monitor.check_all()

        assert result.failed_groups == 1
        assert len(result.errors) == 1
        assert "Grupo B" in result.errors[0].message
        assert result.new_posts == []
        assert PostRepository(db).count() == 4

    def test_ultima_verificacao_global_atualizada(self, db, sample_feed_bytes, fetcher):
        _add_group(db)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        MonitorService(db, fetcher).check_all()
        stored = SettingsRepository(db).get("last_check_at")
        assert stored is not None
        datetime.fromisoformat(stored)


class TestPersistence:
    def test_dados_preservados_apos_reabrir_banco(self, tmp_path, sample_feed_bytes, fetcher):
        db_path = tmp_path / "persistida.db"
        from free_games_hub.database import connect_db, init_db

        conn = connect_db(db_path)
        init_db(conn)
        _add_group(conn)
        fetcher.responses[GROUP_URL] = sample_feed_bytes
        MonitorService(conn, fetcher).check_all()
        conn.close()

        conn2 = connect_db(db_path)
        repo = GroupRepository(conn2)
        group = repo.get_by_url(GROUP_URL)
        assert group is not None and group.initialized
        assert PostRepository(conn2).count() == 2
        conn2.close()