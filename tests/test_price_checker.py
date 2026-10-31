"""Testes da consulta de preços na loja Steam (sem rede)."""

from __future__ import annotations

from free_games_hub.services.price_checker import (
    PriceCheckError,
    SteamPriceChecker,
    extract_app_id,
    normalize_title,
)


def _app_payload(app_id: int, *, is_free: bool = False, price: dict | None = None) -> dict:
    data: dict = {"name": "Jogo", "is_free": is_free}
    if price is not None:
        data["price_overview"] = price
    return {str(app_id): {"success": True, "data": data}}


class FakeHttp:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.urls: list[str] = []

    def __call__(self, url: str) -> dict:
        self.urls.append(url)
        return self.handler(url)


def _checker(handler) -> tuple[SteamPriceChecker, FakeHttp]:
    http = FakeHttp(handler)
    return SteamPriceChecker(http_get_json=http, delay_seconds=0), http


def test_extrai_appid_do_link_da_loja() -> None:
    url = "https://store.steampowered.com/app/674750/Yet_Another/?curator_clanid=1"
    assert extract_app_id(url) == 674750
    assert extract_app_id("https://store.steampowered.com/sub/123/") is None
    assert extract_app_id(None) is None


def test_normaliza_titulo_remove_tag_acentos_e_pontuacao() -> None:
    assert normalize_title("[FREE]  Moonlighter™ ") == "moonlighter"
    assert normalize_title("[free] Deponia") == "deponia"
    assert normalize_title("Jogão Ção & Cia.") == "jogao cao cia"


def test_oferta_com_100_por_cento_de_desconto() -> None:
    payload = _app_payload(
        10,
        price={
            "currency": "BRL",
            "initial": 3999,
            "final": 0,
            "discount_percent": 100,
        },
    )
    checker, http = _checker(lambda _url: payload)

    result = checker.check("https://store.steampowered.com/app/10/x/", "[FREE] Jogo")

    assert result.status == "free"
    assert result.app_id == 10
    assert result.discount_percent == 100
    assert result.initial_cents == 3999
    assert result.final_cents == 0
    assert result.currency == "BRL"
    assert result.source == "link"
    assert "appids=10" in http.urls[0]
    assert "cc=br" in http.urls[0]
    assert not result.retryable


def test_oferta_expirada_com_preco_atual() -> None:
    payload = _app_payload(
        11,
        price={
            "currency": "BRL",
            "initial": 1379,
            "final": 262,
            "discount_percent": 81,
        },
    )
    checker, _ = _checker(lambda _url: payload)

    result = checker.check("https://store.steampowered.com/app/11/x/", "[FREE] Jogo")

    assert result.status == "not_free"
    assert result.final_cents == 262
    assert result.discount_percent == 81


def test_calcula_desconto_quando_api_nao_informa() -> None:
    payload = _app_payload(
        12,
        price={"currency": "BRL", "initial": 1000, "final": 250},
    )
    checker, _ = _checker(lambda _url: payload)

    result = checker.check("https://store.steampowered.com/app/12/x/", "[FREE] Jogo")

    assert result.status == "not_free"
    assert result.discount_percent == 75


def test_jogo_free_to_play_nao_conta_como_promocao() -> None:
    payload = _app_payload(13, is_free=True)
    checker, _ = _checker(lambda _url: payload)

    result = checker.check("https://store.steampowered.com/app/13/x/", "[FREE] Jogo")

    assert result.status == "f2p"


def test_detalhes_indisponiveis_viram_nao_verificado() -> None:
    payload = {"14": {"success": False, "data": []}}
    checker, _ = _checker(lambda _url: payload)

    result = checker.check("https://store.steampowered.com/app/14/x/", "[FREE] Jogo")

    assert result.status == "unknown"
    assert not result.retryable
    assert result.error


def test_falha_de_rede_marca_retentativa() -> None:
    def handler(_url: str) -> dict:
        raise PriceCheckError("HTTP 429")

    checker, _ = _checker(handler)

    result = checker.check("https://store.steampowered.com/app/15/x/", "[FREE] Jogo")

    assert result.status == "unknown"
    assert result.retryable


def test_sem_link_busca_pelo_titulo_e_confirma_no_appdetails() -> None:
    def handler(url: str) -> dict:
        if "storesearch" in url:
            return {
                "items": [
                    {"type": "app", "name": "Moonlighter", "id": 606150},
                    {"type": "app", "name": "Moonlighter 2", "id": 1},
                ]
            }
        return _app_payload(
            606150,
            price={"currency": "BRL", "initial": 4100, "final": 4100},
        )

    checker, http = _checker(handler)

    result = checker.check(None, "[FREE] Moonlighter")

    assert result.status == "not_free"
    assert result.app_id == 606150
    assert result.source == "search"
    assert len(http.urls) == 2
    assert "storesearch" in http.urls[0]
    assert "appids=606150" in http.urls[1]


def test_sem_correspondencia_confiavel_nao_verifica() -> None:
    payload = {
        "items": [
            {"type": "app", "name": "Outro Jogo", "id": 999},
        ]
    }
    checker, http = _checker(lambda _url: payload)

    result = checker.check(None, "[FREE] Jogo Desconhecido")

    assert result.status == "unknown"
    assert not result.retryable
    assert len(http.urls) == 1


def test_correspondencia_ambigua_nao_verifica() -> None:
    payload = {
        "items": [
            {"type": "app", "name": "Deponia", "id": 1, "price": {"initial": 100, "final": 100}},
            {"type": "app", "name": "Deponia", "id": 2},
        ]
    }
    checker, http = _checker(lambda _url: payload)

    result = checker.check(None, "[FREE] Deponia")

    assert result.status == "unknown"
    assert len(http.urls) == 1


def test_preco_indisponivel_na_regiao_nao_verifica() -> None:
    payload = _app_payload(16, is_free=False)
    checker, _ = _checker(lambda _url: payload)

    result = checker.check("https://store.steampowered.com/app/16/x/", "[FREE] Jogo")

    assert result.status == "unknown"
    assert not result.retryable
