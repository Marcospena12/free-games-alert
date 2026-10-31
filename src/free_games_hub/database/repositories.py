"""Repositórios de acesso ao SQLite.

Cada repositório é responsável por um conjunto de tabelas, encapsulando as
consultas e a conversão entre linhas e objetos de domínio.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from ..models import MonitorError, Post, Group


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat(timespec="seconds")


def _from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class GroupRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, name: str, url: str, active: bool = True) -> Optional[int]:
        existing = self.get_by_url(url)
        if existing is not None:
            return existing.id
        cursor = self._conn.execute(
            "INSERT OR IGNORE INTO groups (name, url, active) VALUES (?, ?, ?)",
            (name, url, int(active)),
        )
        self._conn.commit()
        return cursor.lastrowid or None

    def _row_to_group(self, row: sqlite3.Row) -> Group:
        return Group(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            active=bool(row["active"]),
            initialized=bool(row["initialized"]),
            last_checked_at=_from_iso(row["last_checked_at"]),
            created_at=_from_iso(row["created_at"]),
        )

    def list_all(self) -> list[Group]:
        rows = self._conn.execute(
            "SELECT * FROM groups ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [self._row_to_group(row) for row in rows]

    def list_active(self) -> list[Group]:
        rows = self._conn.execute(
            "SELECT * FROM groups WHERE active = 1 ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [self._row_to_group(row) for row in rows]

    def get(self, group_id: int) -> Optional[Group]:
        row = self._conn.execute(
            "SELECT * FROM groups WHERE id = ?", (group_id,)
        ).fetchone()
        return self._row_to_group(row) if row else None

    def get_by_url(self, url: str) -> Optional[Group]:
        row = self._conn.execute(
            "SELECT * FROM groups WHERE url = ?", (url,)
        ).fetchone()
        return self._row_to_group(row) if row else None

    def update(self, group_id: int, name: str, url: str, active: bool) -> None:
        self._conn.execute(
            "UPDATE groups SET name = ?, url = ?, active = ? WHERE id = ?",
            (name, url, int(active), group_id),
        )
        self._conn.commit()

    def set_active(self, group_id: int, active: bool) -> None:
        self._conn.execute(
            "UPDATE groups SET active = ? WHERE id = ?", (int(active), group_id)
        )
        self._conn.commit()

    def set_initialized(self, group_id: int) -> None:
        self._conn.execute(
            "UPDATE groups SET initialized = 1 WHERE id = ?", (group_id,)
        )
        self._conn.commit()

    def set_last_checked_at(self, group_id: int, dt: datetime) -> None:
        self._conn.execute(
            "UPDATE groups SET last_checked_at = ? WHERE id = ?",
            (_to_iso(dt), group_id),
        )
        self._conn.commit()

    def delete(self, group_id: int) -> None:
        self._conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        self._conn.commit()


class PostRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_by_dedup_key(self, dedup_key: str) -> Optional[Post]:
        row = self._conn.execute(
            "SELECT * FROM posts WHERE dedup_key = ?", (dedup_key,)
        ).fetchone()
        return self._row_to_post(row) if row else None

    def insert_if_missing(self, post: Post) -> Optional[Post]:
        """Insere a publicação se o identificador ou dedup_key ainda não existirem.

        Retorna o Post persistido (com id e discovered_at reais) quando inserido,
        ou ``None`` caso um registro duplicado já exista.
        """
        # 1. Checagem por dedup_key canônica
        if post.dedup_key:
            existing = self.get_by_dedup_key(post.dedup_key)
            if existing is not None:
                # Se o giveaway teve seu prazo estendido, atualiza o ends_at
                if post.ends_at and (existing.ends_at is None or post.ends_at > existing.ends_at):
                    self._conn.execute(
                        "UPDATE posts SET ends_at = ? WHERE id = ?",
                        (_to_iso(post.ends_at), existing.id),
                    )
                    self._conn.commit()
                return None

        # 2. Checagem por identifier único
        existing_by_id = self.get_by_identifier(post.identifier)
        if existing_by_id is not None:
            if post.ends_at and (existing_by_id.ends_at is None or post.ends_at > existing_by_id.ends_at):
                self._conn.execute(
                    "UPDATE posts SET ends_at = ? WHERE id = ?",
                    (_to_iso(post.ends_at), existing_by_id.id),
                )
                self._conn.commit()
            return None

        discovered_at = datetime.now()
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO posts (
                group_id, identifier, identifier_source, title, publication_url,
                store_url, description, author, published_at, discovered_at, notified,
                in_library, store_app_id, price_status, price_initial_cents,
                price_final_cents, price_discount_percent, price_currency,
                price_source, price_checked_at, price_error, source, store,
                external_id, worth_usd, ends_at, claim_url, image_url, dedup_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.group_id,
                post.identifier,
                post.identifier_source,
                post.title,
                post.publication_url,
                post.store_url,
                post.description,
                post.author,
                _to_iso(post.published_at),
                _to_iso(discovered_at),
                int(post.notified),
                int(post.in_library),
                post.store_app_id,
                post.price_status,
                post.price_initial_cents,
                post.price_final_cents,
                post.price_discount_percent,
                post.price_currency,
                post.price_source,
                _to_iso(post.price_checked_at),
                post.price_error,
                post.source or "steam_group",
                post.store or "steam",
                post.external_id,
                post.worth_usd,
                _to_iso(post.ends_at),
                post.claim_url,
                post.image_url,
                post.dedup_key or post.identifier,
            ),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            return None
        identifier = post.identifier
        row = self._conn.execute(
            "SELECT * FROM posts WHERE identifier = ?", (identifier,)
        ).fetchone()
        return self._row_to_post(row)

    def get_by_identifier(self, identifier: str) -> Optional[Post]:
        row = self._conn.execute(
            "SELECT * FROM posts WHERE identifier = ?", (identifier,)
        ).fetchone()
        return self._row_to_post(row) if row else None

    def _row_to_post(self, row: sqlite3.Row) -> Post:
        keys = row.keys()
        return Post(
            id=row["id"],
            group_id=row["group_id"],
            identifier=row["identifier"],
            identifier_source=row["identifier_source"],
            title=row["title"],
            publication_url=row["publication_url"],
            store_url=row["store_url"],
            description=row["description"],
            author=row["author"],
            published_at=_from_iso(row["published_at"]),
            notified=bool(row["notified"]),
            discovered_at=_from_iso(row["discovered_at"]),
            store_app_id=row["store_app_id"],
            price_status=row["price_status"],
            price_initial_cents=row["price_initial_cents"],
            price_final_cents=row["price_final_cents"],
            price_discount_percent=row["price_discount_percent"],
            price_currency=row["price_currency"],
            price_source=row["price_source"],
            price_checked_at=_from_iso(row["price_checked_at"]),
            price_error=row["price_error"],
            in_library=bool(row["in_library"]) if "in_library" in keys else False,
            source=row["source"] if "source" in keys and row["source"] else "steam_group",
            store=row["store"] if "store" in keys and row["store"] else "steam",
            external_id=row["external_id"] if "external_id" in keys else None,
            worth_usd=row["worth_usd"] if "worth_usd" in keys else None,
            ends_at=_from_iso(row["ends_at"]) if "ends_at" in keys else None,
            claim_url=row["claim_url"] if "claim_url" in keys else None,
            image_url=row["image_url"] if "image_url" in keys else None,
            dedup_key=row["dedup_key"] if "dedup_key" in keys else None,
        )

    def set_notified(self, post_id: int, notified: bool = True) -> None:
        self._conn.execute(
            "UPDATE posts SET notified = ? WHERE id = ?", (int(notified), post_id)
        )
        self._conn.commit()

    def set_in_library(self, post_id: int, in_library: bool = True) -> None:
        self._conn.execute(
            "UPDATE posts SET in_library = ? WHERE id = ?",
            (int(in_library), post_id),
        )
        self._conn.commit()

    def list_recent(
        self,
        limit: int = 20,
        status: Optional[str] = None,
        in_library: Optional[bool] = None,
        store: Optional[str] = None,
    ) -> list[dict]:
        """Publicações recentes com o nome do grupo ou fonte, para exibição."""
        clauses: list[str] = []
        params: list[object] = []

        if status == "unchecked":
            clauses.append("(p.price_status IS NULL OR p.price_status = 'unknown')")
        elif status == "in_library":
            clauses.append("p.in_library = 1")
        elif status:
            clauses.append("p.price_status = ?")
            params.append(status)

        if in_library is not None:
            clauses.append("p.in_library = ?")
            params.append(int(in_library))

        if store:
            clauses.append("p.store = ?")
            params.append(store)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT p.*, g.name AS group_name
            FROM posts p LEFT JOIN groups g ON g.id = p.group_id
            {where}
            ORDER BY p.discovered_at DESC, p.published_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        result = []
        for row in rows:
            post = self._row_to_post(row)
            group_name = row["group_name"]
            if not group_name:
                group_name = "GamerPower" if post.source == "gamerpower" else "Global"
            result.append({"post": post, "group_name": group_name})
        return result

    def count_free_now(self, include_in_library: bool = False) -> int:
        where = "WHERE price_status = 'free'"
        if not include_in_library:
            where += " AND in_library = 0"
        row = self._conn.execute(
            f"SELECT COUNT(*) AS n FROM posts {where}"
        ).fetchone()
        return int(row["n"])

    def list_pending_notifications(self, limit: int = 20) -> list[dict]:
        """Ofertas confirmadas como grátis que ainda não foram notificadas."""
        rows = self._conn.execute(
            """
            SELECT p.*, g.name AS group_name
            FROM posts p LEFT JOIN groups g ON g.id = p.group_id
            WHERE p.notified = 0 AND p.price_status = 'free' AND p.in_library = 0
            ORDER BY p.discovered_at DESC, p.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        result = []
        for row in rows:
            post = self._row_to_post(row)
            group_name = row["group_name"]
            if not group_name:
                group_name = "GamerPower" if post.source == "gamerpower" else "Global"
            result.append({"post": post, "group_name": group_name})
        return result

    def mark_all_pending_notified(self) -> int:
        """Consome notificações pendentes sem enviá-las (preferência desligada)."""
        cursor = self._conn.execute(
            "UPDATE posts SET notified = 1 WHERE notified = 0"
        )
        self._conn.commit()
        return cursor.rowcount

    def list_for_price_refresh(
        self,
        *,
        limit: int,
        max_age_days: int,
        free_ttl_minutes: int,
        unknown_ttl_minutes: int,
        not_free_ttl_minutes: int,
        force: bool = False,
        now: Optional[datetime] = None,
    ) -> list[Post]:
        """Seleciona publicações cujo preço precisa ser verificado."""
        reference = now or datetime.now()
        age_cutoff = _to_iso(reference - timedelta(days=max_age_days))

        if force:
            where = "1 = 1"
            params: list[object] = []
        else:
            where = """
                (
                    p.price_checked_at IS NULL
                    OR (
                        COALESCE(p.published_at, p.discovered_at) >= ?
                        AND (
                            (p.price_status = 'free' AND p.price_checked_at <= ?)
                            OR (
                                p.price_status = 'unknown'
                                AND p.price_checked_at <= ?
                            )
                            OR (
                                p.price_status IN ('not_free', 'f2p')
                                AND p.price_checked_at <= ?
                            )
                        )
                    )
                )
            """
            params = [
                age_cutoff,
                _to_iso(reference - timedelta(minutes=free_ttl_minutes)),
                _to_iso(reference - timedelta(minutes=unknown_ttl_minutes)),
                _to_iso(reference - timedelta(minutes=not_free_ttl_minutes)),
            ]

        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT p.* FROM posts p
            WHERE (p.source = 'steam_group' OR (p.store = 'steam' AND p.store_app_id IS NOT NULL))
              AND ({where})
            ORDER BY
                CASE
                    WHEN p.price_checked_at IS NULL THEN 0
                    WHEN p.price_status = 'free' THEN 1
                    WHEN p.price_status = 'unknown' THEN 2
                    ELSE 3
                END,
                COALESCE(p.published_at, p.discovered_at) DESC,
                p.price_checked_at ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_post(row) for row in rows]

    def update_price_check(
        self,
        post_id: int,
        *,
        status: str,
        app_id: Optional[int] = None,
        initial_cents: Optional[int] = None,
        final_cents: Optional[int] = None,
        discount_percent: Optional[int] = None,
        currency: Optional[str] = None,
        source: Optional[str] = None,
        checked_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ) -> None:
        checked = _to_iso(checked_at or datetime.now())
        if status == "unknown":
            self._conn.execute(
                """
                UPDATE posts SET
                    store_app_id = COALESCE(?, store_app_id),
                    price_status = ?,
                    price_source = COALESCE(?, price_source),
                    price_checked_at = ?,
                    price_error = ?
                WHERE id = ?
                """,
                (app_id, status, source, checked, error, post_id),
            )
        else:
            self._conn.execute(
                """
                UPDATE posts SET
                    store_app_id = COALESCE(?, store_app_id),
                    price_status = ?,
                    price_initial_cents = ?,
                    price_final_cents = ?,
                    price_discount_percent = ?,
                    price_currency = ?,
                    price_source = COALESCE(?, price_source),
                    price_checked_at = ?,
                    price_error = NULL
                WHERE id = ?
                """,
                (
                    app_id,
                    status,
                    initial_cents,
                    final_cents,
                    discount_percent,
                    currency,
                    source,
                    checked,
                    post_id,
                ),
            )
        self._conn.commit()

    def list_for_group(self, group_id: int) -> list[Post]:
        rows = self._conn.execute(
            "SELECT * FROM posts WHERE group_id = ? ORDER BY published_at DESC",
            (group_id,),
        ).fetchall()
        return [self._row_to_post(row) for row in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM posts").fetchone()
        return int(row["n"])

    def count_for_group(self, group_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM posts WHERE group_id = ?", (group_id,)
        ).fetchone()
        return int(row["n"])


class SettingsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def get_int(self, key: str, default: int) -> int:
        value = self.get(key)
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "on")

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        self._conn.commit()


class ErrorRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, group_id: Optional[int], message: str) -> None:
        self._conn.execute(
            "INSERT INTO monitor_errors (group_id, message) VALUES (?, ?)",
            (group_id, message),
        )
        self._conn.commit()
        self._prune()

    def _prune(self) -> None:
        from ..config import MAX_KEPT_ERRORS

        self._conn.execute(
            "DELETE FROM monitor_errors WHERE id NOT IN ("
            "  SELECT id FROM monitor_errors ORDER BY id DESC LIMIT ?"
            ")",
            (MAX_KEPT_ERRORS,),
        )
        self._conn.commit()

    def recent(self, limit: int = 50) -> list[MonitorError]:
        rows = self._conn.execute(
            "SELECT * FROM monitor_errors ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            MonitorError(
                id=row["id"],
                group_id=row["group_id"],
                message=row["message"],
                created_at=_from_iso(row["created_at"]) or datetime.now(),
            )
            for row in rows
        ]


def hash_identifier(title: str, published_at: Optional[datetime]) -> str:
    """Identificador de fallback quando não há guid nem link no feed."""
    payload = f"{title}|{_to_iso(published_at) or ''}".encode("utf-8")
    return "hash:" + hashlib.sha1(payload).hexdigest()