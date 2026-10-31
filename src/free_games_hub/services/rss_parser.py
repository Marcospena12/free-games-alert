"""Interpretação de feeds RSS/Atom com feedparser."""

from __future__ import annotations

import calendar
from datetime import datetime, timezone

import feedparser

from ..models import ParsedItem


class RssParseError(RuntimeError):
    """O conteúdo recebido não pôde ser interpretado como um feed RSS/Atom."""


def _to_datetime(parsed) -> datetime | None:
    if parsed is None:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    except (OverflowError, ValueError, OSError):
        return None


def _to_author(entry) -> str | None:
    author = entry.get("author")
    if author:
        return author
    detail = entry.get("author_detail") or {}
    return detail.get("name")


def parse_feed(content: bytes) -> list[ParsedItem]:
    """Analisa o XML e retorna os itens encontrados.

    ``content`` deve ser ``bytes`` (o conteúdo efetivamente baixado) para que o
    feedparser não tente interpretar strings como URLs.
    """
    feed = feedparser.parse(content)

    if feed.bozo:
        raise RssParseError(f"XML inválido: {feed.bozo_exception}")

    if not getattr(feed, "version", None) and not feed.entries:
        raise RssParseError("A resposta não parece ser um feed RSS/Atom válido")

    items: list[ParsedItem] = []
    for entry in feed.entries:
        published = _to_datetime(entry.get("published_parsed")) or _to_datetime(
            entry.get("updated_parsed")
        )
        items.append(
            ParsedItem(
                title=entry.get("title") or "",
                guid=entry.get("guid") or entry.get("id"),
                link=entry.get("link"),
                description=entry.get("summary") or entry.get("description"),
                published_at=published,
                author=_to_author(entry),
            )
        )
    return items