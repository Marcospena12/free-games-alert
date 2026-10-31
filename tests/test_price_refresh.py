"""Testes da atualização periódica do status das ofertas."""

from __future__ import annotations

from datetime import datetime, timedelta

from free_games_hub.database.repositories import (
    GroupRepository,
    PostRepository,
)
from free_games_hub.models import Post
from free_games_hub.services.price_checker import PriceResult
from free_games_hub.services.price_refresh import PriceRefreshService

GROUP_URL = "https://steamcommunity.com/groups/jogosbra/rss/"


class FakeChecker:
    def __init__(self, results: dict[str, PriceResult]) -> None:
        self.results = results
        self.calls: list[str] = []

    def check(self, store_url, title):
        self.calls.append(title)
        return self.results[title]


def _add_post(
    repo: PostRepository,
    group_id: int,
    identifier: str,
    title: str,
    *,
    store_url: str | None = None,
    published_at: datetime | None = None,
) -> Post:
    created = repo.insert_if_missing(
        Post(
            group_id=group_id,
            identifier=identifier,
            identifier_source="guid",
            title=title,
            store_url=store_url,
            published_at=published_at,
        )
    )
    assert created is not None
    return created


def _free_result() -> PriceResult:
    return PriceResult(
        status="free",
        app_id=1,
        initial_cents=3999,
        final_cents=0,
        discount_percent=100,
        currency="BRL",
        source="link",
    )


def _paid_result() -> PriceResult:
    return PriceResult(
        status="not_free",
        app_id=2,
        initial_cents=4100,
        final_cents=4100,
        discount_percent=0,
        currency="BRL",
        source="link",
    )


def test_refresh_persiste_status_dos_posts(db) -> None:
    group_id = GroupRepository(db).add("G", GROUP_URL)
    repo = PostRepository(db)
    _add_post(repo, group_id, "a", "[FREE] A", store_url="https://store.steampowered.com/app/1/")
    _add_post(repo, group_id, "b", "[FREE] B", store_url="https://store.steampowered.com/app/2/")
    checker = FakeChecker({"[FREE] A": _free_result(), "[FREE] B": _paid_result()})

    updated = PriceRefreshService(db, checker).refresh()

    assert updated == 2
    post_a = repo.get_by_identifier("a")
    post_b = repo.get_by_identifier("b")
    assert post_a is not None and post_b is not None
    assert post_a.price_status == "free"
    assert post_a.price_checked_at is not None
    assert post_b.price_status == "not_free"
    assert post_b.price_final_cents == 4100


def test_ttl_impede_reverificacao_imediata(db) -> None:
    group_id = GroupRepository(db).add("G", GROUP_URL)
    repo = PostRepository(db)
    post = _add_post(repo, group_id, "a", "[FREE] A")
    checker = FakeChecker({"[FREE] A": _free_result()})
    service = PriceRefreshService(db, checker)

    assert service.refresh() == 1
    assert service.refresh() == 0

    assert post.id is not None
    repo.update_price_check(
        post.id,
        status="free",
        initial_cents=3999,
        final_cents=0,
        discount_percent=100,
        currency="BRL",
        checked_at=datetime.now() - timedelta(minutes=60),
    )
    assert service.refresh() == 1


def test_force_ignora_ttl(db) -> None:
    group_id = GroupRepository(db).add("G", GROUP_URL)
    repo = PostRepository(db)
    _add_post(repo, group_id, "a", "[FREE] A")
    checker = FakeChecker({"[FREE] A": _free_result()})
    service = PriceRefreshService(db, checker)

    assert service.refresh() == 1
    assert service.refresh(force=True) == 1
    assert len(checker.calls) == 2


def test_limite_por_rodada(db) -> None:
    group_id = GroupRepository(db).add("G", GROUP_URL)
    repo = PostRepository(db)
    for index in range(3):
        _add_post(repo, group_id, f"p{index}", f"[FREE] {index}")
    checker = FakeChecker(
        {f"[FREE] {index}": _free_result() for index in range(3)}
    )
    service = PriceRefreshService(db, checker, limit=2)

    assert service.refresh() == 2
    assert len(checker.calls) == 2
    assert service.refresh() == 1


def test_erro_retentavel_interrompe_rodada(db) -> None:
    group_id = GroupRepository(db).add("G", GROUP_URL)
    repo = PostRepository(db)
    for index in range(3):
        _add_post(repo, group_id, f"p{index}", f"[FREE] {index}")
    retryable = PriceResult(status="unknown", error="HTTP 429", retryable=True)
    checker = FakeChecker(
        {f"[FREE] {index}": retryable for index in range(3)}
    )

    updated = PriceRefreshService(db, checker).refresh()

    assert updated == 1
    assert len(checker.calls) == 1


def test_unknown_preserva_ultimo_preco_conhecido(db) -> None:
    group_id = GroupRepository(db).add("G", GROUP_URL)
    repo = PostRepository(db)
    post = _add_post(repo, group_id, "a", "[FREE] A")
    assert post.id is not None
    repo.update_price_check(
        post.id,
        status="free",
        initial_cents=3999,
        final_cents=0,
        discount_percent=100,
        currency="BRL",
    )

    repo.update_price_check(post.id, status="unknown", error="HTTP 429")

    updated = repo.get_by_identifier("a")
    assert updated is not None
    assert updated.price_status == "unknown"
    assert updated.price_initial_cents == 3999
    assert updated.price_final_cents == 0
    assert updated.price_error == "HTTP 429"


def test_posts_antigos_sao_verificados_uma_vez(db) -> None:
    group_id = GroupRepository(db).add("G", GROUP_URL)
    repo = PostRepository(db)
    post = _add_post(
        repo,
        group_id,
        "antigo",
        "[FREE] Antigo",
        published_at=datetime.now() - timedelta(days=40),
    )
    checker = FakeChecker({"[FREE] Antigo": _free_result()})
    service = PriceRefreshService(db, checker)

    assert service.refresh() == 1
    assert service.refresh() == 0

    assert post.id is not None
    repo.update_price_check(
        post.id,
        status="free",
        initial_cents=3999,
        final_cents=0,
        discount_percent=100,
        currency="BRL",
        checked_at=datetime.now() - timedelta(hours=25),
    )
    assert service.refresh() == 0
