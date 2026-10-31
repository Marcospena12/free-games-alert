"""Testes do motor de filtros por loja e configurações."""

from __future__ import annotations

from datetime import datetime, timedelta

from free_games_hub.database.repositories import SettingsRepository
from free_games_hub.services.filters import (
    StoreFilterConfig,
    StoreFilterService,
)
from free_games_hub.sources.base import RawGiveaway
from free_games_hub.sources.stores import (
    STORE_EPIC,
    STORE_GOG,
    STORE_STEAM,
    TYPE_BETA,
    TYPE_GAME,
    TYPE_LOOT,
)


def _make_deal(
    store=STORE_STEAM,
    type_=TYPE_GAME,
    worth_usd=9.99,
    title="Epic Game Edition",
    ends_at=None,
    supported_stores=None,
):
    return RawGiveaway(
        source_id="test",
        external_id="1",
        title=title,
        store=store,
        type=type_,
        worth_usd=worth_usd,
        ends_at=ends_at,
        supported_stores=supported_stores or [store],
    )


def test_filtro_por_loja_habilitada(db):
    settings = SettingsRepository(db)
    service = StoreFilterService(settings)

    # Permitir apenas Steam
    service.set_enabled_stores([STORE_STEAM])

    steam_deal = _make_deal(store=STORE_STEAM)
    epic_deal = _make_deal(store=STORE_EPIC)

    assert service.matches(steam_deal) is True
    assert service.matches(epic_deal) is False

    # Jogo multi-loja que suporta Steam e Epic deve passar
    multi_deal = _make_deal(store=STORE_EPIC, supported_stores=[STORE_EPIC, STORE_STEAM])
    assert service.matches(multi_deal) is True


def test_filtro_por_tipo(db):
    settings = SettingsRepository(db)
    service = StoreFilterService(settings)

    game_deal = _make_deal(type_=TYPE_GAME)
    loot_deal = _make_deal(type_=TYPE_LOOT)
    beta_deal = _make_deal(type_=TYPE_BETA)

    # Apenas jogos completos permitidos
    service.set_enabled_types([TYPE_GAME])
    assert service.matches(game_deal) is True
    assert service.matches(loot_deal) is False
    assert service.matches(beta_deal) is False

    # Permitir jogos e loot
    service.set_enabled_types([TYPE_GAME, TYPE_LOOT])
    assert service.matches(game_deal) is True
    assert service.matches(loot_deal) is True
    assert service.matches(beta_deal) is False


def test_filtro_por_valor_usd(db):
    settings = SettingsRepository(db)
    service = StoreFilterService(settings)

    config = StoreFilterConfig(min_worth_usd=10.0, include_na_worth=True)
    expensive_deal = _make_deal(worth_usd=19.99)
    cheap_deal = _make_deal(worth_usd=4.99)
    na_deal = _make_deal(worth_usd=None)

    assert service.matches(expensive_deal, config) is True
    assert service.matches(cheap_deal, config) is False
    assert service.matches(na_deal, config) is True

    # Desativando include_na_worth
    config.include_na_worth = False
    assert service.matches(na_deal, config) is False


def test_filtro_por_palavras_chave(db):
    settings = SettingsRepository(db)
    service = StoreFilterService(settings)

    config = StoreFilterConfig(
        title_include_keywords=["remastered"],
        title_exclude_keywords=["beta", "trial"],
    )

    good_deal = _make_deal(title="Quake II Remastered")
    bad_exclude = _make_deal(title="Quake II Remastered Closed Beta")
    missing_include = _make_deal(title="Quake II Original")

    assert service.matches(good_deal, config) is True
    assert service.matches(bad_exclude, config) is False
    assert service.matches(missing_include, config) is False


def test_filtro_por_prazo_de_expiracao(db):
    settings = SettingsRepository(db)
    service = StoreFilterService(settings)

    # Ignorar sem data de término
    config = StoreFilterConfig(ignore_no_end_date=True)
    no_end_deal = _make_deal(ends_at=None)
    with_end_deal = _make_deal(ends_at=datetime.now() + timedelta(days=2))

    assert service.matches(no_end_deal, config) is False
    assert service.matches(with_end_deal, config) is True

    # Tempo mínimo antes de expirar (ex: não avisar se expirar em menos de 2 horas)
    config = StoreFilterConfig(min_hours_before_expiration=2)
    expiring_soon = _make_deal(ends_at=datetime.now() + timedelta(minutes=30))
    expiring_later = _make_deal(ends_at=datetime.now() + timedelta(hours=5))

    assert service.matches(expiring_soon, config) is False
    assert service.matches(expiring_later, config) is True


def test_filtros_independentes_por_loja(db):
    settings = SettingsRepository(db)
    service = StoreFilterService(settings)

    # Configuração independente:
    # Steam: só jogos completos
    # Epic: jogos completos e DLCs/loot
    # GOG: desabilitada
    service.set_store_filter(
        STORE_STEAM,
        StoreFilterConfig(enabled=True, allowed_types={TYPE_GAME}),
    )
    service.set_store_filter(
        STORE_EPIC,
        StoreFilterConfig(enabled=True, allowed_types={TYPE_GAME, TYPE_LOOT}),
    )
    service.set_store_filter(
        STORE_GOG,
        StoreFilterConfig(enabled=False, allowed_types={TYPE_GAME}),
    )

    # Checar união de tipos requeridos para a GamerPower API
    effective_types = service.get_effective_query_types()
    assert set(effective_types) == {TYPE_GAME, TYPE_LOOT}

    # 1. Jogo completo na Steam -> aceito
    steam_game = _make_deal(store=STORE_STEAM, type_=TYPE_GAME)
    assert service.matches(steam_game) is True

    # 2. DLC na Steam -> rejeitado (Steam só aceita jogos)
    steam_dlc = _make_deal(store=STORE_STEAM, type_=TYPE_LOOT)
    assert service.matches(steam_dlc) is False

    # 3. DLC na Epic -> aceito (Epic aceita DLCs)
    epic_dlc = _make_deal(store=STORE_EPIC, type_=TYPE_LOOT)
    assert service.matches(epic_dlc) is True

    # 4. Jogo no GOG -> rejeitado (GOG desabilitada)
    gog_game = _make_deal(store=STORE_GOG, type_=TYPE_GAME)
    assert service.matches(gog_game) is False

    # 5. DLC multi-loja (disponível na Steam e na Epic) -> aceito pela Epic!
    multi_dlc = _make_deal(
        store=STORE_STEAM,
        type_=TYPE_LOOT,
        supported_stores=[STORE_STEAM, STORE_EPIC],
    )
    assert service.matches(multi_dlc) is True
    # O store deve ter sido ajustado para a loja que deu match (Epic)
    assert multi_dlc.store == STORE_EPIC


def test_copiar_filtros_de_uma_loja_para_todas(db):
    settings = SettingsRepository(db)
    service = StoreFilterService(settings)

    # Personalizar Steam com valor mínimo e tipos específicos
    service.set_store_filter(
        STORE_STEAM,
        StoreFilterConfig(
            enabled=True,
            allowed_types={TYPE_GAME, TYPE_BETA},
            min_worth_usd=15.0,
            include_na_worth=False,
            title_exclude_keywords=["prologue"],
            ignore_no_end_date=True,
        ),
    )

    # Replicar para todas as lojas
    service.copy_store_filter_to_all(STORE_STEAM)

    epic_cfg = service.get_store_filter(STORE_EPIC)
    assert epic_cfg.allowed_types == {TYPE_GAME, TYPE_BETA}
    assert epic_cfg.min_worth_usd == 15.0
    assert epic_cfg.include_na_worth is False
    assert epic_cfg.title_exclude_keywords == ["prologue"]
    assert epic_cfg.ignore_no_end_date is True

