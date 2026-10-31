"""Conexão e inicialização do banco SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    initialized INTEGER NOT NULL DEFAULT 0,
    last_checked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    identifier TEXT NOT NULL UNIQUE,
    identifier_source TEXT NOT NULL,
    title TEXT NOT NULL,
    publication_url TEXT,
    store_url TEXT,
    description TEXT,
    author TEXT,
    published_at TEXT,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    notified INTEGER NOT NULL DEFAULT 0,
    store_app_id INTEGER,
    price_status TEXT,
    price_initial_cents INTEGER,
    price_final_cents INTEGER,
    price_discount_percent INTEGER,
    price_currency TEXT,
    price_source TEXT,
    price_checked_at TEXT,
    price_error TEXT,
    in_library INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'steam_group',
    store TEXT NOT NULL DEFAULT 'steam',
    external_id TEXT,
    worth_usd REAL,
    ends_at TEXT,
    claim_url TEXT,
    image_url TEXT,
    dedup_key TEXT
);

CREATE INDEX IF NOT EXISTS idx_posts_group_id ON posts(group_id);
CREATE INDEX IF NOT EXISTS idx_posts_discovered_at ON posts(discovered_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect_db(path: str | Path) -> sqlite3.Connection:
    """Abre uma conexão SQLite configurada para a aplicação."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


_PRICE_COLUMNS = {
    "store_app_id": "INTEGER",
    "price_status": "TEXT",
    "price_initial_cents": "INTEGER",
    "price_final_cents": "INTEGER",
    "price_discount_percent": "INTEGER",
    "price_currency": "TEXT",
    "price_source": "TEXT",
    "price_checked_at": "TEXT",
    "price_error": "TEXT",
    "in_library": "INTEGER NOT NULL DEFAULT 0",
}

_V4_COLUMNS = {
    "source": "TEXT NOT NULL DEFAULT 'steam_group'",
    "store": "TEXT NOT NULL DEFAULT 'steam'",
    "external_id": "TEXT",
    "worth_usd": "REAL",
    "ends_at": "TEXT",
    "claim_url": "TEXT",
    "image_url": "TEXT",
    "dedup_key": "TEXT",
}


def _ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(posts)")}
    for column, column_type in {**_PRICE_COLUMNS, **_V4_COLUMNS}.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE posts ADD COLUMN {column} {column_type}")

    # Inicializar dedup_key para posts existentes se estiver vazio
    conn.execute("UPDATE posts SET dedup_key = identifier WHERE dedup_key IS NULL")


def _migrate_group_id_nullable(conn: sqlite3.Connection) -> None:
    """Garante que group_id possa ser NULL para permitir fontes globais (ex: GamerPower)."""
    table_info = conn.execute("PRAGMA table_info(posts)").fetchall()
    if not table_info:
        return
    group_col = next((r for r in table_info if r[1] == "group_id"), None)
    if group_col is not None and bool(group_col[3]):  # notnull == 1
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("""
            CREATE TABLE posts_v4 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
                identifier TEXT NOT NULL UNIQUE,
                identifier_source TEXT NOT NULL,
                title TEXT NOT NULL,
                publication_url TEXT,
                store_url TEXT,
                description TEXT,
                author TEXT,
                published_at TEXT,
                discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
                notified INTEGER NOT NULL DEFAULT 0,
                store_app_id INTEGER,
                price_status TEXT,
                price_initial_cents INTEGER,
                price_final_cents INTEGER,
                price_discount_percent INTEGER,
                price_currency TEXT,
                price_source TEXT,
                price_checked_at TEXT,
                price_error TEXT,
                in_library INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'steam_group',
                store TEXT NOT NULL DEFAULT 'steam',
                external_id TEXT,
                worth_usd REAL,
                ends_at TEXT,
                claim_url TEXT,
                image_url TEXT,
                dedup_key TEXT
            )
        """)
        existing_cols = {r[1] for r in table_info}
        all_possible = [
            "id", "group_id", "identifier", "identifier_source", "title",
            "publication_url", "store_url", "description", "author",
            "published_at", "discovered_at", "notified", "store_app_id",
            "price_status", "price_initial_cents", "price_final_cents",
            "price_discount_percent", "price_currency", "price_source",
            "price_checked_at", "price_error", "in_library", "source",
            "store", "external_id", "worth_usd", "ends_at", "claim_url",
            "image_url", "dedup_key"
        ]
        copy_cols = [c for c in all_possible if c in existing_cols]
        cols_str = ", ".join(copy_cols)
        conn.execute(f"INSERT INTO posts_v4 ({cols_str}) SELECT {cols_str} FROM posts")
        conn.execute("DROP TABLE posts")
        conn.execute("ALTER TABLE posts_v4 RENAME TO posts")
        conn.execute("PRAGMA foreign_keys = ON")


def init_db(conn: sqlite3.Connection) -> None:
    """Cria as tabelas e aplica migrações básicas."""
    conn.executescript(_SCHEMA)
    _ensure_columns(conn)
    _migrate_group_id_nullable(conn)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_price_status ON posts(price_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_in_library ON posts(in_library)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_dedup_key ON posts(dedup_key)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_store ON posts(store)"
    )
    # Garante que giveaways de fontes ativas como GamerPower fiquem com status 'free'
    conn.execute(
        "UPDATE posts SET price_status = 'free' WHERE source = 'gamerpower' AND (price_status = 'unknown' OR price_status IS NULL)"
    )
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()