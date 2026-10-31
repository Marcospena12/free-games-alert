"""Teste de integração do worker: feed -> preço -> notificação."""

from __future__ import annotations

from pathlib import Path

from free_games_hub.database import connect_db, init_db
from free_games_hub.database.repositories import (
    GroupRepository,
    PostRepository,
)
from free_games_hub.services.monitor import MonitorService
from free_games_hub.services.price_checker import PriceResult
from free_games_hub.ui.worker import CheckWorker

from conftest import GROUP_URL


class FakePriceChecker:
    def __init__(self) -> None:
        self.calls: list[tuple[str | None, str]] = []

    def check(self, store_url, title):
        self.calls.append((store_url, title))
        return PriceResult(
            status="free",
            app_id=2484180,
            initial_cents=1999,
            final_cents=0,
            discount_percent=100,
            currency="BRL",
            source="link",
        )


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def notify(self, *, title: str, message: str, open_url) -> None:
        self.calls.append({"title": title, "message": message, "open_url": open_url})


def test_worker_notifica_somente_depois_de_confirmar_preco(
    tmp_path: Path,
    sample_feed_bytes: bytes,
    sample_feed_next_bytes: bytes,
    fetcher,
) -> None:
    db_path = tmp_path / "worker.db"
    conn = connect_db(db_path)
    init_db(conn)
    GroupRepository(conn).add("Grupo", GROUP_URL)
    fetcher.responses[GROUP_URL] = sample_feed_bytes
    MonitorService(conn, fetcher).check_all()
    fetcher.responses[GROUP_URL] = sample_feed_next_bytes
    conn.close()

    checker = FakePriceChecker()
    notifier = RecordingNotifier()
    worker = CheckWorker(
        db_path,
        fetcher,
        notifier,
        price_checker=checker,
    )

    results: list[object] = []
    failures: list[str] = []
    worker.signals.finished.connect(results.append)
    worker.signals.failed.connect(failures.append)

    worker.run()

    assert failures == []
    assert len(results) == 1
    result = results[0]
    assert len(result.new_posts) == 1
    assert result.new_posts[0].title == "[FREE] Deadshot"
    assert (
        "https://store.steampowered.com/app/2484180/Deadshot/"
        "?curator_clanid=6250352",
        "[FREE] Deadshot",
    ) in checker.calls
    assert len(notifier.calls) == 1
    assert notifier.calls[0]["title"] == "Deadshot"
    assert "100% grátis" in notifier.calls[0]["message"]

    conn = connect_db(db_path)
    stored = PostRepository(conn).get_by_identifier(
        result.new_posts[0].identifier
    )
    assert stored is not None and stored.notified is True
    conn.close()
