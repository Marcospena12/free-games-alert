"""Testes da migração do banco para a versão com status de preço."""

from __future__ import annotations

from steam_free_games_monitor.database.connection import (
    SCHEMA_VERSION,
    connect_db,
    init_db,
)

OLD_SCHEMA = """
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    initialized INTEGER NOT NULL DEFAULT 0,
    last_checked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    identifier TEXT NOT NULL UNIQUE,
    identifier_source TEXT NOT NULL,
    title TEXT NOT NULL,
    publication_url TEXT,
    store_url TEXT,
    description TEXT,
    author TEXT,
    published_at TEXT,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    notified INTEGER NOT NULL DEFAULT 0
);
"""


def test_migra_banco_v1_preservando_posts(tmp_path) -> None:
    conn = connect_db(tmp_path / "old.db")
    conn.executescript(OLD_SCHEMA)
    conn.execute(
        "INSERT INTO groups (name, url) VALUES ('G', 'https://example.com/rss')"
    )
    conn.execute(
        """
        INSERT INTO posts (group_id, identifier, identifier_source, title, store_url)
        VALUES (1, 'guid-1', 'guid', '[FREE] Jogo', 'https://store.steampowered.com/app/1/')
        """
    )
    conn.execute("PRAGMA user_version = 1")
    conn.commit()

    init_db(conn)

    columns = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
    assert {
        "store_app_id",
        "price_status",
        "price_initial_cents",
        "price_final_cents",
        "price_discount_percent",
        "price_currency",
        "price_source",
        "price_checked_at",
        "price_error",
    } <= columns
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION

    row = conn.execute(
        "SELECT title, price_status, price_checked_at FROM posts WHERE identifier = 'guid-1'"
    ).fetchone()
    assert row is not None
    assert row["title"] == "[FREE] Jogo"
    assert row["price_status"] is None
    assert row["price_checked_at"] is None
    conn.close()
