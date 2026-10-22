"""Consulta da validade das ofertas na loja da Steam.

A API pública da loja (não documentada) é usada para descobrir se uma
publicação marcada como ``[FREE]`` continua com 100% de desconto. Quando o
post não tem link direto de aplicativo, a busca da loja é usada pelo título,
exigindo correspondência confiável.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import Callable, Optional

from ..config import (
    PRICE_CHECK_DELAY_SECONDS,
    PRICE_CHECK_TIMEOUT_SECONDS,
    STEAM_STORE_COUNTRY,
    STEAM_STORE_LANGUAGE,
)
from .deals import clean_title
from .feed_fetcher import USER_AGENT

STATUS_FREE = "free"
STATUS_NOT_FREE = "not_free"
STATUS_F2P = "f2p"
STATUS_UNKNOWN = "unknown"

APP_URL_RE = re.compile(r"store\.steampowered\.com/app/(\d+)", re.IGNORECASE)
MATCH_RATIO = 0.95


class PriceCheckError(RuntimeError):
    """Falha ao consultar a API da loja."""


@dataclass
class PriceResult:
    status: str
    app_id: Optional[int] = None
    initial_cents: Optional[int] = None
    final_cents: Optional[int] = None
    discount_percent: Optional[int] = None
    currency: Optional[str] = None
    source: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    retryable: bool = False


def extract_app_id(store_url: Optional[str]) -> Optional[int]:
    """Extrai o appid de um link ``/app/{id}`` da loja Steam."""
    if not store_url:
        return None
    match = APP_URL_RE.search(store_url)
    return int(match.group(1)) if match else None


def normalize_title(title: str) -> str:
    """Normaliza o título para comparação (caixa, acentos e pontuação)."""
    text = clean_title(title)
    for symbol in ("™", "®", "©", "℠"):
        text = text.replace(symbol, "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def _match_candidate(title: str, items: list[dict]) -> Optional[dict]:
    """Escolhe um resultado da busca com correspondência confiável."""
    wanted = normalize_title(title)
    if not wanted:
        return None

    exact: list[dict] = []
    near: list[tuple[float, dict]] = []
    for item in items:
        if item.get("type") != "app" or not item.get("id"):
            continue
        name = normalize_title(str(item.get("name") or ""))
        if not name:
            continue
        if name == wanted:
            exact.append(item)
        else:
            ratio = SequenceMatcher(None, wanted, name).ratio()
            if ratio >= MATCH_RATIO:
                near.append((ratio, item))

    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    if len(near) == 1:
        return near[0][1]
    return None


def _get_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise PriceCheckError(f"HTTP {response.status} ao acessar a loja")
            return json.loads(response.read().decode("utf-8"))
    except PriceCheckError:
        raise
    except Exception as exc:  # noqa: BLE001 - convertido em erro consultável
        raise PriceCheckError(f"Falha ao consultar a loja: {exc}") from exc


class SteamPriceChecker:
    """Consulta o preço atual de um jogo na loja Steam."""

    def __init__(
        self,
        http_get_json: Optional[Callable[[str], dict]] = None,
        *,
        timeout: float = PRICE_CHECK_TIMEOUT_SECONDS,
        country: str = STEAM_STORE_COUNTRY,
        language: str = STEAM_STORE_LANGUAGE,
        delay_seconds: float = PRICE_CHECK_DELAY_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http_get_json = http_get_json or (lambda url: _get_json(url, timeout))
        self._country = country
        self._language = language
        self._delay_seconds = max(0.0, delay_seconds)
        self._sleep = sleep
        self._last_request_at = 0.0

    def check(self, store_url: Optional[str], title: str) -> PriceResult:
        app_id = extract_app_id(store_url)
        if app_id is not None:
            return self._check_app(app_id, source="link")
        return self._check_search(title)

    def _throttled_get(self, url: str) -> dict:
        if self._delay_seconds:
            elapsed = time.monotonic() - self._last_request_at
            remaining = self._delay_seconds - elapsed
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = time.monotonic()
        return self._http_get_json(url)

    def _appdetails_url(self, app_id: int) -> str:
        return (
            "https://store.steampowered.com/api/appdetails"
            f"?appids={app_id}&cc={self._country}&l={self._language}"
        )

    def _check_app(self, app_id: int, *, source: str) -> PriceResult:
        try:
            payload = self._throttled_get(self._appdetails_url(app_id))
            entry = payload.get(str(app_id)) or {}
            if not entry.get("success"):
                return PriceResult(
                    status=STATUS_UNKNOWN,
                    app_id=app_id,
                    source=source,
                    error="detalhes do aplicativo indisponíveis",
                )
            data = entry.get("data") or {}
            return self._classify(app_id, data, source)
        except Exception as exc:  # noqa: BLE001 - falha nunca derruba o app
            return PriceResult(
                status=STATUS_UNKNOWN,
                app_id=app_id,
                source=source,
                error=str(exc),
                retryable=True,
            )

    def _classify(self, app_id: int, data: dict, source: str) -> PriceResult:
        price = data.get("price_overview") or {}
        initial = price.get("initial")
        final = price.get("final")
        discount = price.get("discount_percent")
        currency = price.get("currency")
        is_free = bool(data.get("is_free"))

        if initial is not None and final is not None and initial > 0:
            percent = discount
            if percent is None:
                percent = round((initial - final) / initial * 100)
            status = STATUS_FREE if final == 0 or percent == 100 else STATUS_NOT_FREE
            return PriceResult(
                status=status,
                app_id=app_id,
                initial_cents=initial,
                final_cents=final,
                discount_percent=100 if status == STATUS_FREE else percent,
                currency=currency,
                source=source,
            )

        if is_free or (initial == 0 and final == 0):
            return PriceResult(
                status=STATUS_F2P,
                app_id=app_id,
                initial_cents=initial,
                final_cents=final,
                discount_percent=discount,
                currency=currency,
                source=source,
            )

        return PriceResult(
            status=STATUS_UNKNOWN,
            app_id=app_id,
            source=source,
            error="preço indisponível (jogo removido ou fora da região)",
        )

    def _check_search(self, title: str) -> PriceResult:
        query = clean_title(title)
        if not query:
            return PriceResult(
                status=STATUS_UNKNOWN,
                source="search",
                error="título vazio para busca",
            )

        url = (
            "https://store.steampowered.com/api/storesearch/"
            f"?term={urllib.parse.quote_plus(query)}"
            f"&cc={self._country}&l={self._language}"
        )
        try:
            payload = self._throttled_get(url)
        except Exception as exc:  # noqa: BLE001
            return PriceResult(
                status=STATUS_UNKNOWN,
                source="search",
                error=str(exc),
                retryable=True,
            )

        candidate = _match_candidate(title, payload.get("items") or [])
        if candidate is None:
            return PriceResult(
                status=STATUS_UNKNOWN,
                source="search",
                error="nenhuma correspondência confiável na busca da Steam",
            )

        app_id = int(candidate["id"])
        return self._check_app(app_id, source="search")
