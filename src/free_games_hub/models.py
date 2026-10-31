"""Modelos de domínio da aplicação."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Group:
    """Um grupo RSS cadastrado para monitoramento."""

    name: str
    url: str
    active: bool = True
    initialized: bool = False
    id: Optional[int] = None
    last_checked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class ParsedItem:
    """Um item extraído de um feed RSS, antes da filtragem/persistência."""

    title: str
    guid: Optional[str] = None
    link: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    author: Optional[str] = None

    @property
    def identifier_source(self) -> str:
        if self.guid:
            return "guid"
        if self.link:
            return "link"
        return "hash"


@dataclass
class Post:
    """Uma publicação relevante persistida no banco de dados."""

    group_id: Optional[int]
    identifier: str
    identifier_source: str
    title: str
    publication_url: Optional[str] = None
    store_url: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    notified: bool = False
    id: Optional[int] = None
    discovered_at: Optional[datetime] = None
    store_app_id: Optional[int] = None
    price_status: Optional[str] = None
    price_initial_cents: Optional[int] = None
    price_final_cents: Optional[int] = None
    price_discount_percent: Optional[int] = None
    price_currency: Optional[str] = None
    price_source: Optional[str] = None
    price_checked_at: Optional[datetime] = None
    price_error: Optional[str] = None
    in_library: bool = False
    source: str = "steam_group"
    store: str = "steam"
    external_id: Optional[str] = None
    worth_usd: Optional[float] = None
    ends_at: Optional[datetime] = None
    claim_url: Optional[str] = None
    image_url: Optional[str] = None
    dedup_key: Optional[str] = None


@dataclass
class MonitorError:
    """Erro registrado durante o monitoramento de um feed."""

    message: str
    created_at: datetime = field(default_factory=datetime.now)
    group_id: Optional[int] = None
    id: Optional[int] = None


@dataclass
class CheckResult:
    """Resultado consolidado de uma rodada de verificação."""

    new_posts: list[Post] = field(default_factory=list)
    errors: list[MonitorError] = field(default_factory=list)
    checked_groups: int = 0
    failed_groups: int = 0