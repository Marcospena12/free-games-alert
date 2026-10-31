"""Testes dos componentes da grade de cards, cache de capas e barra de lojas."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QPixmap

from free_games_hub.models import Post
from free_games_hub.services.covers import (
    CoverCacheService,
    get_cover_url_for_post,
)
from free_games_hub.ui.widgets.game_card import GameCardWidget
from free_games_hub.ui.widgets.game_grid import GameCardGrid
from free_games_hub.ui.widgets.store_filter_bar import StoreFilterBar


def test_cover_url_discovery():
    post_with_img = Post(
        group_id=None,
        identifier="1",
        identifier_source="gp",
        title="Game",
        image_url="https://example.com/cover.jpg",
    )
    assert get_cover_url_for_post(post_with_img) == "https://example.com/cover.jpg"

    post_with_appid = Post(
        group_id=1,
        identifier="2",
        identifier_source="rss",
        title="Steam Game",
        store_app_id=570,
    )
    assert "apps/570/header.jpg" in get_cover_url_for_post(post_with_appid)


def test_cover_cache_service_memoria_e_disco(qapp, tmp_path):
    service = CoverCacheService(cache_dir=tmp_path)
    url = "https://example.com/test.jpg"

    # Salva uma imagem fake no cache em disco
    cache_file = service._cache_path_for_url(url)
    pixmap = QPixmap(100, 100)
    pixmap.fill()
    pixmap.save(str(cache_file), "PNG")

    # Solicitar deve carregar do disco para a memória
    loaded = service.request_cover(url)
    assert loaded is not None
    assert service.get_cached(url) is not None


def test_store_filter_bar(qapp):
    bar = StoreFilterBar()
    bar.update_stores({"steam": 5, "epic-games-store": 3, "gog": 0})

    selected = bar.get_selected_stores()
    assert "steam" in selected
    assert "epic-games-store" in selected

    # Simula clique no botão Limpar
    bar._select_none()
    assert len(bar.get_selected_stores()) == 0

    # Simula clique no botão Todas
    bar._select_all()
    assert "steam" in bar.get_selected_stores()


def test_game_card_widget(qapp):
    post = Post(
        group_id=None,
        identifier="gp-123",
        identifier_source="gp",
        title="Modern Game Title",
        store="epic-games-store",
        worth_usd=29.99,
        claim_url="https://epicgames.com/claim",
    )
    card = GameCardWidget(post, group_name="GamerPower")
    assert card._title_label.text() == "Modern Game Title"
    assert "De $29.99" in card._format_original_price()

    # Teste de emissão de sinal de resgate
    emitted = []
    card.claim_requested.connect(lambda u, a: emitted.append((u, a)))
    card._on_claim_clicked()
    assert len(emitted) == 1
    assert emitted[0][0] == "https://epicgames.com/claim"


def test_game_card_grid(qapp):
    grid = GameCardGrid()
    entries = [
        {"post": Post(group_id=None, identifier="1", identifier_source="gp", title="Game 1", store="steam"), "group_name": "Steam"},
        {"post": Post(group_id=None, identifier="2", identifier_source="gp", title="Game 2", store="epic-games-store"), "group_name": "Epic"},
    ]
    grid.set_entries(entries)
    assert len(grid._cards) == 2

    # Filtrar apenas Steam
    grid.filter_by_stores({"steam"})
    assert len(grid._cards) == 1
    assert grid._cards[0].post.store == "steam"
