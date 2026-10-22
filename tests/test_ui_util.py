"""Testes dos utilitários de formatação da interface."""

from __future__ import annotations

from datetime import datetime

from steam_free_games_monitor.models import Post
from steam_free_games_monitor.ui.util import fmt_post_status, fmt_price, fmt_price_tooltip


def _post(**kwargs) -> Post:
    base = {
        "group_id": 1,
        "identifier": "x",
        "identifier_source": "guid",
        "title": "[FREE] Jogo",
        "price_currency": "BRL",
    }
    base.update(kwargs)
    return Post(**base)


def test_formata_precos_em_reais() -> None:
    assert fmt_price(None) == "—"
    assert fmt_price(0, "BRL") == "R$ 0,00"
    assert fmt_price(1234, "BRL") == "R$ 12,34"
    assert fmt_price(123456, "BRL") == "R$ 1.234,56"
    assert fmt_price(999, "USD") == "9,99 USD"


def test_status_de_oferta_gratuita() -> None:
    assert fmt_post_status(_post(price_status="free")) == "Grátis (-100%)"


def test_status_de_oferta_expirada_com_preco() -> None:
    post = _post(
        price_status="not_free",
        price_initial_cents=1379,
        price_final_cents=262,
        price_discount_percent=81,
    )
    assert fmt_post_status(post) == "Expirado · R$ 2,62 (-81%)"


def test_status_f2p_nao_verificado_e_pendente() -> None:
    assert fmt_post_status(_post(price_status="f2p")) == "F2P (não é promoção)"
    assert fmt_post_status(_post(price_status="unknown")) == "Não verificado"
    assert fmt_post_status(_post()) == "Pendente"


def test_tooltip_mostra_preco_e_verificacao() -> None:
    post = _post(
        price_status="not_free",
        price_initial_cents=3999,
        price_final_cents=4100,
        price_checked_at=datetime(2026, 10, 21, 20, 5),
    )
    tooltip = fmt_price_tooltip(post)
    assert "Preço original: R$ 39,99" in tooltip
    assert "Preço atual: R$ 41,00" in tooltip
    assert "Verificado em: 21/10/2026 20:05" in tooltip
