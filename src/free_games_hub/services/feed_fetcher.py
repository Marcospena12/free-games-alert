"""Busca do conteúdo dos feeds RSS com timeout explícito."""

from __future__ import annotations

from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..config import REQUEST_TIMEOUT_SECONDS

USER_AGENT = "FreeGamesHub/0.1" 


class FeedFetchError(RuntimeError):
    """Falha ao baixar o conteúdo de um feed."""


class FeedFetcher(Protocol):
    """Contrato de busca de conteúdo. Injetável nos testes."""

    def fetch(self, url: str) -> bytes: ...


class UrlFeedFetcher:
    """Busca o feed via urllib com timeout (sem dependências externas)."""

    def __init__(self, timeout: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    def fetch(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise FeedFetchError(f"HTTP {response.status} ao acessar {url}")
                return response.read()
        except FeedFetchError:
            raise
        except (URLError, TimeoutError) as exc:
            raise FeedFetchError(f"Falha ao acessar {url}: {exc}") from exc