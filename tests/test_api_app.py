"""Testes do app da API local (CORS e comportamento básico).

O app é testado contra um servidor uvicorn real em loopback: o
``TestClient`` do Starlette reporta o host do cliente como
``testclient``, que é rejeitado pela checagem de loopback em
:mod:`free_games_hub.api.auth`.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from free_games_hub.api.app import create_app


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    headers = {}
    token = getattr(app.state, "token", None)
    if token:
        headers["X-FGH-Token"] = token
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            response = httpx.get(
                f"http://127.0.0.1:{port}/health", headers=headers, timeout=1
            )
            if response.status_code == 200:
                return server
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError("servidor não subiu")


@pytest.fixture
def dev_api(tmp_path: Path):
    """API em loopback com ``dev_cors=True`` (modo desenvolvimento)."""
    db = tmp_path / "dev_cors.db"
    port = _free_port()
    server = _start_server(
        create_app(db, scheduler_enabled=False, dev_cors=True), port
    )
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture
def api_with_posts(tmp_path: Path):
    """API em loopback com posts grátis ativo/expirado e um post pago."""
    from datetime import datetime, timedelta

    from free_games_hub.database import PostRepository, connect_db, init_db
    from free_games_hub.models import Post

    db = tmp_path / "api_posts.db"
    conn = connect_db(db)
    init_db(conn)
    repo = PostRepository(conn)
    now = datetime.now()
    repo.insert_if_missing(
        Post(
            group_id=None,
            identifier="active",
            identifier_source="guid",
            title="Ativa",
            price_status="free",
            ends_at=now + timedelta(days=1),
        )
    )
    repo.insert_if_missing(
        Post(
            group_id=None,
            identifier="expired",
            identifier_source="guid",
            title="Expirada",
            price_status="free",
            ends_at=now - timedelta(days=1),
        )
    )
    repo.insert_if_missing(
        Post(
            group_id=None,
            identifier="paid",
            identifier_source="guid",
            title="Paga",
            price_status="not_free",
        )
    )
    conn.close()

    port = _free_port()
    server = _start_server(create_app(db, scheduler_enabled=False), port)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture
def prod_api(tmp_path: Path):
    """API em loopback com ``dev_cors=False`` (modo produção)."""
    db = tmp_path / "prod_cors.db"
    port = _free_port()
    server = _start_server(
        create_app(db, scheduler_enabled=False, dev_cors=False), port
    )
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_cors_preflight_allowed_in_dev(dev_api: str) -> None:
    """Preflight do Vite (``localhost:5173``) é aceito com ``dev_cors=True``."""
    client = httpx.Client(base_url=dev_api, timeout=5)
    r = client.options(
        "/api/snapshot",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type,x-fgh-token",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "GET" in r.headers["access-control-allow-methods"]


def test_cors_simple_request_header_in_dev(dev_api: str) -> None:
    """Requisição simples com Origin dev recebe o header de CORS."""
    client = httpx.Client(base_url=dev_api, timeout=5)
    r = client.get("/api/snapshot", headers={"Origin": "http://127.0.0.1:5173"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_foreign_origin_denied_in_dev(dev_api: str) -> None:
    """Origin externa (ex.: ``example.com``) não recebe permissão de CORS."""
    client = httpx.Client(base_url=dev_api, timeout=5)
    r = client.options(
        "/api/snapshot",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # O middleware responde 400 sem os headers de permissão.
    assert "access-control-allow-origin" not in r.headers


def test_posts_active_filter_and_free_now(api_with_posts: str) -> None:
    """``active=true`` esconde expiradas e a métrica ``free_now`` as ignora."""
    client = httpx.Client(base_url=api_with_posts, timeout=5)

    r = client.get(
        "/api/posts",
        params={"status": "free", "active": "true", "library": "false"},
    )
    assert r.status_code == 200
    assert [post["title"] for post in r.json()] == ["Ativa"]

    all_free = client.get("/api/posts", params={"status": "free"}).json()
    assert {post["title"] for post in all_free} == {"Ativa", "Expirada"}

    snapshot = client.get("/api/snapshot").json()
    assert snapshot["free_now"] == 1
    assert snapshot["total_posts"] == 3


def test_no_cors_headers_in_production(prod_api: str) -> None:
    """Em produção (SPA mesma origem) não há headers de CORS."""
    client = httpx.Client(base_url=prod_api, timeout=5)
    r = client.get("/api/snapshot", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers


@pytest.fixture
def auth_api(tmp_path: Path):
    """API com token, como no shell Electron em produção."""
    db = tmp_path / "auth.db"
    port = _free_port()
    server = _start_server(
        create_app(db, token="segredo", scheduler_enabled=False), port
    )
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_token_required_and_docs_hidden(auth_api: str) -> None:
    """Sem token a API recusa; documentação interativa fica desativada."""
    client = httpx.Client(base_url=auth_api, timeout=5)
    assert client.get("/health").status_code == 401
    assert client.get("/api/settings").status_code == 401
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404

    ok = client.get("/health", headers={"X-FGH-Token": "segredo"})
    assert ok.status_code == 200
    assert ok.json() == {"status": "ok"}


def test_settings_roundtrip_and_store_filters(prod_api: str) -> None:
    """Configurações e filtros por loja persistem e voltam completos."""
    client = httpx.Client(base_url=prod_api, timeout=5)
    payload = {
        "check_interval_minutes": 12,
        "notifications_enabled": False,
        "close_to_tray": False,
        "gamerpower_enabled": False,
        "enabled_types": ["game", "loot"],
        "stores_enabled": ["steam", "epic-games-store"],
        "store_filters": {
            "steam": {
                "enabled": False,
                "allowed_types": ["game"],
                "min_worth_usd": 4.5,
                "include_na_worth": False,
                "title_exclude_keywords": ["demo", "trial"],
                "ignore_no_end_date": True,
            }
        },
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    saved = response.json()
    assert saved["check_interval_minutes"] == 12
    assert saved["notifications_enabled"] is False
    assert saved["close_to_tray"] is False
    assert saved["gamerpower_enabled"] is False
    assert saved["stores_enabled"] == ["epic-games-store"]
    assert saved["store_filters"]["steam"]["enabled"] is False
    assert saved["store_filters"]["steam"]["min_worth_usd"] == 4.5
    assert saved["store_filters"]["steam"]["title_exclude_keywords"] == ["demo", "trial"]

    read_back = client.get("/api/settings").json()
    assert read_back == saved

    stores = client.get("/api/stores").json()
    steam = next(store for store in stores if store["id"] == "steam")
    epic = next(store for store in stores if store["id"] == "epic-games-store")
    assert steam["enabled"] is False
    assert epic["enabled"] is True


def test_settings_rejects_invalid_values(prod_api: str) -> None:
    client = httpx.Client(base_url=prod_api, timeout=5)
    assert client.put("/api/settings", json={"check_interval_minutes": 0}).status_code == 400
    assert client.put("/api/settings", json={"stores_enabled": "steam"}).status_code == 400
    assert (
        client.put(
            "/api/settings",
            json={"store_filters": {"steam": {"min_worth_usd": -1}}},
        ).status_code
        == 400
    )


def test_search_applied_before_limit(tmp_path: Path) -> None:
    """A busca é feita no SQL; não perde resultados antigos pelo LIMIT."""
    from free_games_hub.database import PostRepository, connect_db, init_db
    from free_games_hub.models import Post

    db = tmp_path / "search.db"
    conn = connect_db(db)
    init_db(conn)
    repo = PostRepository(conn)
    repo.insert_if_missing(
        Post(
            group_id=None,
            identifier="alvo",
            identifier_source="guid",
            title="Oferta Alvo",
            price_status="free",
        )
    )
    for index in range(10):
        repo.insert_if_missing(
            Post(
                group_id=None,
                identifier=f"ruido-{index}",
                identifier_source="guid",
                title=f"Ruído {index}",
                price_status="free",
            )
        )
    conn.close()

    port = _free_port()
    server = _start_server(create_app(db, scheduler_enabled=False), port)
    try:
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5)
        response = client.get("/api/posts", params={"limit": 3, "search": "alvo"})
        assert response.status_code == 200
        assert [post["title"] for post in response.json()] == ["Oferta Alvo"]
    finally:
        server.should_exit = True


def test_errors_limit_and_about(prod_api: str) -> None:
    """``/api/errors`` respeita ``limit`` e ``/api/about`` expõe a versão."""
    from free_games_hub.database import ErrorRepository, connect_db, init_db

    client = httpx.Client(base_url=prod_api, timeout=5)
    about = client.get("/api/about")
    assert about.status_code == 200
    data = about.json()
    assert data["version"]
    assert data["db_path"].endswith(".db")

    # A API usa um banco temporário conhecido; grava erros direto nele.
    from pathlib import Path as _Path

    db_path = _Path(data["db_path"])
    conn = connect_db(db_path)
    init_db(conn)
    errors = ErrorRepository(conn)
    for index in range(6):
        errors.add(None, f"erro {index}")
    conn.close()

    limited = client.get("/api/errors", params={"limit": 2})
    assert limited.status_code == 200
    assert len(limited.json()) == 2
    assert limited.json()[0]["message"] == "erro 5"


def test_spa_fallback_serves_index(tmp_path: Path) -> None:
    """Rotas do cliente caem em ``index.html``; rotas de API continuam 404."""
    spa = tmp_path / "spa"
    spa.mkdir()
    (spa / "index.html").write_text("<html>app</html>", encoding="utf-8")
    db = tmp_path / "spa.db"
    port = _free_port()
    server = _start_server(
        create_app(db, scheduler_enabled=False, spa_dir=spa), port
    )
    try:
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5)
        root = client.get("/")
        nested = client.get("/historico")
        assert root.status_code == 200
        assert root.text == "<html>app</html>"
        assert nested.status_code == 200
        assert nested.text == "<html>app</html>"
        assert client.get("/api/nao-existe").status_code == 404
    finally:
        server.should_exit = True
