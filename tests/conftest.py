"""Fixtures compartilhadas para os testes offline."""

from __future__ import annotations

from pathlib import Path

import pytest

from steam_free_games_monitor.database import connect_db, init_db
from steam_free_games_monitor.models import ParsedItem

FIXTURES_DIR = Path(__file__).parent / "fixtures"
GROUP_URL = "https://steamcommunity.com/groups/jogosbra/rss/"
OTHER_URL = "https://steamcommunity.com/groups/outro/rss/"


def load_fixture(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


@pytest.fixture
def sample_feed_bytes() -> bytes:
    return load_fixture("sample_feed.xml")


@pytest.fixture
def sample_feed_next_bytes() -> bytes:
    return load_fixture("sample_feed_next.xml")


@pytest.fixture
def sample_items(sample_feed_bytes: bytes) -> list[ParsedItem]:
    from steam_free_games_monitor.services.rss_parser import parse_feed

    return parse_feed(sample_feed_bytes)


class FakeFetcher:
    """Fetcher controlado para os testes, sem nenhuma chamada de rede."""

    def __init__(
        self,
        responses: dict[str, bytes] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.errors = errors or {}
        self.calls: list[str] = []

    def fetch(self, url: str) -> bytes:
        self.calls.append(url)
        if url in self.errors:
            raise self.errors[url]
        if url in self.responses:
            return self.responses[url]
        raise AssertionError(f"URL não registrada no fetcher: {url}")


@pytest.fixture
def fetcher() -> FakeFetcher:
    return FakeFetcher()


@pytest.fixture
def db(tmp_path):
    """Conexão SQLite em um diretório temporário, já com o schema criado."""
    conn = connect_db(tmp_path / "test.db")
    init_db(conn)
    yield conn
    conn.close()