"""Testes de integração do monitor com múltiplas fontes (RSS + GamerPower mockada)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from free_games_hub.database.repositories import (
    GroupRepository,
    PostRepository,
    SettingsRepository,
)
from free_games_hub.models import Group
from free_games_hub.services.feed_fetcher import FeedFetchError
from free_games_hub.services.filters import StoreFilterService
from free_games_hub.services.monitor import MonitorService
from free_games_hub.sources.base import RawGiveaway
from free_games_hub.sources.gamerpower import GamerPowerApiAdapter
from free_games_hub.sources.stores import STORE_EPIC, STORE_STEAM, TYPE_GAME

from conftest import GROUP_URL


class MockGamerPowerAdapter(GamerPowerApiAdapter):
    """Adaptador GamerPower para testes que retorna ofertas pré-definidas ou falhas."""

    def __init__(self, giveaways=None, error=None) -> None:
        self.giveaways = giveaways or []
        self.error = error
        self.fetch_calls = 0

    def is_enabled(self) -> bool:
        return True

    def fetch_giveaways(self) -> list[RawGiveaway]:
        self.fetch_calls += 1
        if self.error:
            raise self.error
        return self.giveaways


def test_primeira_leitura_gamerpower_semeia_historico_sem_alertar(db, fetcher, sample_feed_bytes):
    # Cadastrar grupo RSS
    GroupRepository(db).add("Grupo Steam", GROUP_URL)
    fetcher.responses[GROUP_URL] = sample_feed_bytes

    gp_giveaway = RawGiveaway(
        source_id="gamerpower",
        external_id="101",
        title="Death Stranding",
        store=STORE_EPIC,
        type=TYPE_GAME,
        worth_usd=29.99,
        supported_stores=[STORE_EPIC],
    )
    gp_adapter = MockGamerPowerAdapter(giveaways=[gp_giveaway])

    filters = StoreFilterService(SettingsRepository(db))
    filters.set_gamerpower_enabled(True)

    monitor = MonitorService(db, fetcher=fetcher, gamerpower_adapter=gp_adapter, filter_service=filters)
    result = monitor.check_all()

    # Na primeira execução: nenhum novo post para alertar (semeadura de histórico)
    assert result.new_posts == []

    # Posts devem estar salvos e marcados como notified=1
    posts = PostRepository(db).list_recent(limit=10)
    assert len(posts) > 0
    gp_post = next(p["post"] for p in posts if p["post"].identifier == "gp-101")
    assert gp_post.notified is True
    assert gp_post.store == STORE_EPIC


def test_leituras_seguintes_detectam_novo_post_da_gamerpower(db, fetcher, sample_feed_bytes):
    GroupRepository(db).add("Grupo Steam", GROUP_URL)
    fetcher.responses[GROUP_URL] = sample_feed_bytes

    gp_adapter = MockGamerPowerAdapter(giveaways=[])
    filters = StoreFilterService(SettingsRepository(db))
    filters.set_gamerpower_enabled(True)

    monitor = MonitorService(db, fetcher=fetcher, gamerpower_adapter=gp_adapter, filter_service=filters)
    # Primeira rodada (inicialização)
    monitor.check_all()

    # Segunda rodada com novo giveaway da GamerPower
    new_giveaway = RawGiveaway(
        source_id="gamerpower",
        external_id="202",
        title="Bioshock Infinite",
        store=STORE_EPIC,
        type=TYPE_GAME,
        worth_usd=19.99,
        supported_stores=[STORE_EPIC],
    )
    gp_adapter.giveaways = [new_giveaway]

    result = monitor.check_all()
    assert len(result.new_posts) == 1
    assert result.new_posts[0].identifier == "gp-202"
    assert result.new_posts[0].notified is False


def test_deduplicacao_entre_grupo_rss_e_gamerpower(db, fetcher):
    # XML com jogo Steam contendo appid 12345
    rss_xml = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>Steam Group</title>
      <item>
        <title>[FREE] Super Game</title>
        <guid>rss-guid-1</guid>
        <description>&lt;a href="https://store.steampowered.com/app/12345/"&gt;Store&lt;/a&gt;</description>
      </item>
    </channel></rss>"""
    GroupRepository(db).add("Grupo", GROUP_URL)
    fetcher.responses[GROUP_URL] = rss_xml

    # Inicializar grupo
    monitor = MonitorService(db, fetcher=fetcher)
    monitor.check_all()

    # Agora a GamerPower anuncia o mesmo jogo Steam com appid 12345
    gp_deal = RawGiveaway(
        source_id="gamerpower",
        external_id="999",
        title="Super Game (Steam)",
        store=STORE_STEAM,
        type=TYPE_GAME,
        worth_usd=9.99,
        store_app_id=12345,
        supported_stores=[STORE_STEAM],
    )
    gp_adapter = MockGamerPowerAdapter(giveaways=[gp_deal])
    filters = StoreFilterService(SettingsRepository(db))
    filters.set_gamerpower_enabled(True)
    # Marcar gamerpower como inicializada para testar inserção
    SettingsRepository(db).set("gamerpower_initialized", "1")

    monitor = MonitorService(db, fetcher=fetcher, gamerpower_adapter=gp_adapter, filter_service=filters)
    result = monitor.check_all()

    # Não deve duplicar nem notificar novamente
    assert len(result.new_posts) == 0
    assert PostRepository(db).count() == 1


def test_resiliencia_falha_gamerpower_nao_derruba_rss(db, fetcher, sample_feed_bytes):
    GroupRepository(db).add("Grupo Steam", GROUP_URL)
    fetcher.responses[GROUP_URL] = sample_feed_bytes

    # GamerPower com erro de rede
    gp_adapter = MockGamerPowerAdapter(error=RuntimeError("GamerPower offline 503"))
    filters = StoreFilterService(SettingsRepository(db))
    filters.set_gamerpower_enabled(True)

    monitor = MonitorService(db, fetcher=fetcher, gamerpower_adapter=gp_adapter, filter_service=filters)
    result = monitor.check_all()

    # Erro da GamerPower foi registrado
    assert any("[GamerPower API]" in e.message for e in result.errors)
    # Mas o RSS foi processado normalmente com sucesso
    assert GroupRepository(db).get_by_url(GROUP_URL).initialized is True
