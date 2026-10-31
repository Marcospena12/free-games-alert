"""Adaptador para feeds RSS de grupos da Steam."""

from __future__ import annotations

import logging
from typing import Optional

from ..database.repositories import GroupRepository, hash_identifier
from ..models import Group, ParsedItem
from ..services.deals import extract_store_url, is_free_title
from ..services.feed_fetcher import FeedFetchError, FeedFetcher, UrlFeedFetcher
from ..services.price_checker import extract_app_id
from ..services.rss_parser import RssParseError, parse_feed
from .base import RawGiveaway, SourceAdapter
from .stores import STORE_STEAM, TYPE_GAME

logger = logging.getLogger(__name__)


def build_rss_identifier(item: ParsedItem) -> tuple[str, str]:
    """Identificador único de um item: guid, link ou hash de fallback."""
    if item.guid:
        return item.guid, "guid"
    if item.link:
        return item.link, "link"
    return hash_identifier(item.title, item.published_at), "hash"


class SteamRssSourceAdapter(SourceAdapter):
    """Adaptador que busca ofertas nos feeds RSS dos grupos cadastrados."""

    def __init__(
        self,
        groups_repo: GroupRepository,
        fetcher: Optional[FeedFetcher] = None,
    ) -> None:
        self._groups = groups_repo
        self._fetcher = fetcher or UrlFeedFetcher()

    @property
    def source_id(self) -> str:
        return "steam_rss"

    @property
    def display_name(self) -> str:
        return "Grupos da Comunidade Steam (RSS)"

    def is_enabled(self) -> bool:
        # Habilitado se houver pelo menos um grupo ativo cadastrado
        return len(self._groups.list_active()) > 0

    def fetch_giveaways_for_group(self, group: Group) -> list[RawGiveaway]:
        """Busca e normaliza itens de um grupo específico."""
        try:
            content = self._fetcher.fetch(group.url)
            items = parse_feed(content)
        except (FeedFetchError, RssParseError) as exc:
            raise RuntimeError(f"[{group.name}] {exc}") from exc

        giveaways: list[RawGiveaway] = []
        for item in items:
            if not is_free_title(item.title):
                continue

            identifier, _source = build_rss_identifier(item)
            store_url = extract_store_url(item.description)
            claim_url = store_url or item.link
            app_id = extract_app_id(store_url)

            giveaways.append(
                RawGiveaway(
                    source_id=self.source_id,
                    external_id=identifier,
                    title=item.title,
                    store=STORE_STEAM,
                    type=TYPE_GAME,
                    worth_usd=None,
                    ends_at=None,
                    published_at=item.published_at,
                    claim_url=claim_url,
                    store_url=store_url,
                    image_url=None,
                    description=item.description,
                    instructions=None,
                    supported_stores=[STORE_STEAM],
                    source_name=group.name,
                    group_id=group.id,
                    store_app_id=app_id,
                )
            )
        return giveaways

    def fetch_giveaways(self) -> list[RawGiveaway]:
        """Busca ofertas em todos os grupos ativos."""
        all_giveaways: list[RawGiveaway] = []
        for group in self._groups.list_active():
            try:
                giveaways = self.fetch_giveaways_for_group(group)
                all_giveaways.extend(giveaways)
            except Exception as exc:
                logger.warning("Falha ao buscar grupo RSS %s: %s", group.name, exc)
        return all_giveaways
