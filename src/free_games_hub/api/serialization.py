"""Conversão dos modelos de domínio em dicionários JSON-serializáveis.

Os formatos são estáveis e consumidos pelo front-end; campos novos podem
ser adicionados, mas existentes não devem ser renomeados sem migração.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ..models import Group, MonitorError, Post


def _iso(dt: Optional[datetime]) -> Optional[str]:
    """Serializa datas com offset explícito.

    O banco guarda parte das datas como ``datetime`` ingênuo no horário local
    (ex.: ``discovered_at``). Sem offset, o JavaScript interpreta o valor como
    horário local, mas APIs externas podem enviar UTC. Anexar o offset local
    remove a ambiguidade sem exigir migração de schema.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.isoformat(timespec="seconds")


def post_to_dict(post: Post, group_name: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": post.id,
        "group_id": post.group_id,
        "group_name": group_name,
        "title": post.title,
        "description": post.description,
        "author": post.author,
        "publication_url": post.publication_url,
        "store_url": post.store_url,
        "claim_url": post.claim_url,
        "image_url": post.image_url,
        "store": post.store,
        "source": post.source,
        "store_app_id": post.store_app_id,
        "external_id": post.external_id,
        "in_library": post.in_library,
        "notified": post.notified,
        "published_at": _iso(post.published_at),
        "discovered_at": _iso(post.discovered_at),
        "ends_at": _iso(post.ends_at),
        "worth_usd": post.worth_usd,
        "price_status": post.price_status,
        "price_initial_cents": post.price_initial_cents,
        "price_final_cents": post.price_final_cents,
        "price_discount_percent": post.price_discount_percent,
        "price_currency": post.price_currency,
        "price_source": post.price_source,
        "price_checked_at": _iso(post.price_checked_at),
        "price_error": post.price_error,
    }


def group_to_dict(group: Group) -> dict[str, Any]:
    return {
        "id": group.id,
        "name": group.name,
        "url": group.url,
        "active": group.active,
        "initialized": group.initialized,
        "last_checked_at": _iso(group.last_checked_at),
        "created_at": _iso(group.created_at),
    }


def error_to_dict(error: MonitorError, group_name: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": error.id,
        "group_id": error.group_id,
        "group_name": group_name,
        "message": error.message,
        "created_at": _iso(error.created_at),
    }
