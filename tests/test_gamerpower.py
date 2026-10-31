"""Testes unitários do cliente e adaptador da GamerPower API (sem chamadas de rede)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from free_games_hub.sources.gamerpower import GamerPowerApiAdapter
from free_games_hub.sources.gamerpower_client import (
    GamerPowerApiError,
    GamerPowerClient,
)
from free_games_hub.sources.stores import (
    STORE_EPIC,
    STORE_GOG,
    STORE_STEAM,
    TYPE_BETA,
    TYPE_GAME,
    TYPE_LOOT,
    parse_platform_string,
)

SAMPLE_GIVEAWAYS_JSON = [
    {
        "id": 1546,
        "title": "Dead by Daylight 100k Bloodpoints Key Giveaway",
        "worth": "N/A",
        "thumbnail": "https://www.gamerpower.com/offers/1/sample.jpg",
        "image": "https://www.gamerpower.com/offers/1b/sample.jpg",
        "description": "Unlock 100k Bloodpoints in DBD.",
        "instructions": "1. Visit page.",
        "open_giveaway_url": "https://www.gamerpower.com/open/dead-by-daylight",
        "published_date": "2026-10-30 14:26:20",
        "type": "DLC",
        "platforms": "PC, Steam",
        "end_date": "N/A",
        "gamerpower_url": "https://www.gamerpower.com/dead-by-daylight",
    },
    {
        "id": 2048,
        "title": "Amnesia: A Machine for Pigs",
        "worth": "$19.99",
        "thumbnail": "https://www.gamerpower.com/offers/1/amnesia.jpg",
        "image": "https://www.gamerpower.com/offers/1b/amnesia.jpg",
        "description": "A survival horror video game.",
        "instructions": "Claim on Epic Games Store.",
        "open_giveaway_url": "https://www.gamerpower.com/open/amnesia",
        "published_date": "2026-10-25 10:00:00",
        "type": "Game",
        "platforms": "PC, Epic Games Store, GOG",
        "end_date": "2026-11-15 23:59:00",
        "gamerpower_url": "https://www.gamerpower.com/amnesia",
    },
    {
        "id": 3099,
        "title": "Delta Force Playtest",
        "worth": "N/A",
        "thumbnail": "https://www.gamerpower.com/offers/1/delta.jpg",
        "image": "https://www.gamerpower.com/offers/1b/delta.jpg",
        "description": "Join the open beta test.",
        "instructions": "Click to join.",
        "open_giveaway_url": "https://store.steampowered.com/app/2507950/Delta_Force/",
        "published_date": "2026-10-28 12:00:00",
        "type": "Early Access",
        "platforms": "PC, Steam, Playstation 5, Xbox Series X|S",
        "end_date": "2026-12-31 23:59:59",
        "gamerpower_url": "https://www.gamerpower.com/delta",
    },
]


def test_client_status_200_com_sucesso():
    payload = json.dumps(SAMPLE_GIVEAWAYS_JSON).encode("utf-8")
    client = GamerPowerClient(http_requester=lambda url: (200, payload))
    items = client.get_giveaways(platforms=["steam", "epic-games-store"])
    assert len(items) == 3
    assert items[0]["id"] == 1546


def test_client_status_201_retorna_lista_vazia():
    # 201 retorna um dicionário informando que não há giveaways ativos
    payload = json.dumps({"status": 0, "status_message": "No active giveaways available"}).encode("utf-8")
    client = GamerPowerClient(http_requester=lambda url: (201, payload))
    items = client.get_giveaways(platforms=["switch"], types=["beta"])
    assert items == []


def test_client_status_500_gera_erro_explicito():
    client = GamerPowerClient(
        max_retries=1,
        http_requester=lambda url: (500, b"Internal Server Error"),
    )
    with pytest.raises(GamerPowerApiError) as exc_info:
        client.get_giveaways()
    assert "Falha após" in str(exc_info.value) or "500" in str(exc_info.value)


def test_adapter_normaliza_campos_corretamente():
    payload = json.dumps(SAMPLE_GIVEAWAYS_JSON).encode("utf-8")
    client = GamerPowerClient(http_requester=lambda url: (200, payload))
    adapter = GamerPowerApiAdapter(
        client=client,
        get_enabled_stores=lambda: [STORE_STEAM, STORE_EPIC],
    )

    giveaways = adapter.fetch_giveaways()
    assert len(giveaways) == 3

    # Item 1: DLC com worth "N/A" e end_date "N/A"
    g1 = giveaways[0]
    assert g1.external_id == "1546"
    assert g1.type == TYPE_LOOT
    assert g1.worth_usd is None
    assert g1.ends_at is None
    assert g1.store == STORE_STEAM
    assert STORE_STEAM in g1.supported_stores
    assert g1.dedup_key == "gamerpower:1546"

    # Item 2: Jogo pago de valor $19.99 com término definido
    g2 = giveaways[1]
    assert g2.external_id == "2048"
    assert g2.type == TYPE_GAME
    assert g2.worth_usd == 19.99
    assert g2.ends_at == datetime(2026, 11, 15, 23, 59)
    assert g2.store == STORE_EPIC
    assert STORE_GOG in g2.supported_stores

    # Item 3: Beta com Steam app id extraído do link
    g3 = giveaways[2]
    assert g3.type == TYPE_BETA
    assert g3.store == STORE_STEAM
    assert g3.store_app_id == 2507950
    assert g3.dedup_key == "steam:app:2507950"


def test_mapeamento_de_slugs_e_plataformas():
    assert parse_platform_string("PC, Steam, Epic Games Store") == ["steam", "epic-games-store", "pc"]
    assert parse_platform_string("Playstation 5, Xbox Series X|S, Nintendo Switch") == ["ps5", "xbox-series-xs", "switch"]
    assert parse_platform_string("Android, iOS, DRM-Free") == ["android", "ios", "drm-free"]
    assert parse_platform_string("VR") == ["vr"]
    assert parse_platform_string("PC, Ubisoft") == ["ubisoft", "pc"]
    assert parse_platform_string("PC, Battle.net") == ["battlenet", "pc"]
    assert parse_platform_string("") == ["pc"]


def test_deteccao_inteligente_por_titulo_e_url():
    # Detecta Stove a partir do título mesmo que platform seja apenas 'PC'
    stove_stores = parse_platform_string("PC", title="GigaBash (Stove) Giveaway")
    assert "stove" in stove_stores

    # Detecta Prime Gaming a partir do título/URL
    prime_stores = parse_platform_string("PC", title="Apex Loot (Prime Gaming) Drop")
    assert "prime-gaming" in prime_stores

    # Detecta Ubisoft a partir de URL
    ubi_stores = parse_platform_string("PC", url="https://store.ubisoft.com/game")
    assert "ubisoft" in ubi_stores
