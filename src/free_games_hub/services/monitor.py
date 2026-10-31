"""Orquestração do monitoramento de feeds RSS.

Responsável por consultar todos os grupos ativos, interpretar cada feed,
filtrar publicações relevantes, persistir os dados e registrar erros.

Estratégia de inicialização e duplicação de alertas:

* Cada grupo possui a flag ``initialized`` (booleano, inicia em ``0``).
* Na **primeira leitura bem-sucedida** de um feed, todas as publicações que
  correspondem ao filtro ``[FREE]`` são importadas com ``notified = 1``
  (histórico) e o grupo é marcado como inicializado. Nenhuma notificação
  retroativa é gerada.
* Nas leituras seguintes, cada item é inserido com ``INSERT OR IGNORE`` usando
  o identificador único. Somente os itens efetivamente novos (linha inserida)
  retornam em ``CheckResult.new_posts`` e podem gerar notificação.
* Se uma consulta falhar (rede, HTTP inválido ou XML quebrado), o grupo **não**
  é marcado como inicializado e o erro é registrado. O histórico existente é
  preservado e a verificação é retomada na próxima rodada.

Um grupo com falha nunca impede o monitoramento dos demais.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Optional

from ..config import REQUEST_TIMEOUT_SECONDS
from ..database.repositories import (
    ErrorRepository,
    GroupRepository,
    PostRepository,
    SettingsRepository,
    hash_identifier,
)
from ..models import CheckResult, Group, MonitorError, ParsedItem, Post
from ..sources.base import RawGiveaway
from ..sources.gamerpower import GamerPowerApiAdapter
from ..sources.stores import STORE_STEAM
from .deals import extract_store_url, is_free_title
from .feed_fetcher import FeedFetchError, FeedFetcher, UrlFeedFetcher
from .filters import StoreFilterService
from .price_checker import extract_app_id
from .rss_parser import RssParseError, parse_feed

logger = logging.getLogger(__name__)

LAST_CHECK_KEY = "last_check_at"
GAMERPOWER_INITIALIZED_KEY = "gamerpower_initialized"


def build_identifier(item: ParsedItem) -> tuple[str, str]:
    """Identificador único de um item: guid, link ou hash de fallback."""
    if item.guid:
        return item.guid, "guid"
    if item.link:
        return item.link, "link"
    return hash_identifier(item.title, item.published_at), "hash"


class MonitorService:
    """Executa uma rodada de verificação de todas as fontes ativas (Grupos RSS e GamerPower)."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        fetcher: Optional[FeedFetcher] = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        gamerpower_adapter: Optional[GamerPowerApiAdapter] = None,
        filter_service: Optional[StoreFilterService] = None,
    ) -> None:
        self._conn = conn
        self._fetcher = fetcher or UrlFeedFetcher(timeout)
        self._groups = GroupRepository(conn)
        self._posts = PostRepository(conn)
        self._settings = SettingsRepository(conn)
        self._errors = ErrorRepository(conn)
        self._filters = filter_service or StoreFilterService(self._settings)

        self._gp_adapter = gamerpower_adapter or GamerPowerApiAdapter(
            get_enabled_stores=self._filters.get_effective_enabled_stores,
            get_enabled_types=self._filters.get_effective_query_types,
            is_enabled_callback=self._filters.is_gamerpower_enabled,
        )

    def check_all(self) -> CheckResult:
        """Verifica todos os grupos ativos e fontes globais, retornando o resultado consolidado."""
        result = CheckResult()

        # 1. Consulta grupos RSS existentes
        for group in self._groups.list_active():
            result.checked_groups += 1
            self._check_group(group, result)

        # 2. Consulta GamerPower API (se habilitada)
        if self._filters.is_gamerpower_enabled():
            self._check_gamerpower(result)

        self._settings.set(
            LAST_CHECK_KEY, datetime.now().isoformat(timespec="seconds")
        )
        return result

    def check_group(self, group: Group) -> CheckResult:
        """Verifica um único grupo, útil para testes direcionados."""
        result = CheckResult(checked_groups=1)
        self._check_group(group, result)
        return result

    def _check_group(self, group: Group, result: CheckResult) -> None:
        try:
            content = self._fetcher.fetch(group.url)
            items = parse_feed(content)
        except (FeedFetchError, RssParseError) as exc:
            message = f"[{group.name}] {exc}"
            result.failed_groups += 1
            result.errors.append(
                MonitorError(group_id=group.id, message=message)
            )
            self._errors.add(group.id, message)
            return

        matching = [item for item in items if is_free_title(item.title)]

        if not group.initialized:
            self._import_history(group, matching)
            self._groups.set_initialized(group.id)
        else:
            for item in matching:
                inserted = self._insert_post(group.id, item, notified=False)
                if inserted is not None:
                    result.new_posts.append(inserted)

        self._groups.set_last_checked_at(group.id, datetime.now())

    def _check_gamerpower(self, result: CheckResult) -> None:
        """Consulta ofertas na GamerPower API e aplica os filtros configurados."""
        is_initialized = self._settings.get_bool(GAMERPOWER_INITIALIZED_KEY, False)
        try:
            giveaways = self._gp_adapter.fetch_giveaways()
        except Exception as exc:
            message = f"[GamerPower API] Falha na consulta: {exc}"
            logger.warning(message)
            result.errors.append(MonitorError(group_id=None, message=message))
            self._errors.add(group_id=None, message=message)
            return

        # Aplicar motor de filtros por loja e regras do usuário
        filtered_giveaways = [g for g in giveaways if self._filters.matches(g)]

        if not is_initialized:
            # Primeira execução: semear silenciosamente o histórico para evitar flood de notificações
            for g in filtered_giveaways:
                self._insert_gamerpower_post(g, notified=True)
            self._settings.set(GAMERPOWER_INITIALIZED_KEY, "1")
        else:
            for g in filtered_giveaways:
                inserted = self._insert_gamerpower_post(g, notified=False)
                if inserted is not None:
                    result.new_posts.append(inserted)

    def _insert_gamerpower_post(self, giveaway: RawGiveaway, notified: bool) -> Optional[Post]:
        post = Post(
            group_id=None,
            identifier=f"gp-{giveaway.external_id}",
            identifier_source="gamerpower",
            title=giveaway.title,
            publication_url=giveaway.store_url,
            store_url=giveaway.store_url,
            description=giveaway.description,
            author="GamerPower",
            published_at=giveaway.published_at,
            notified=notified,
            store_app_id=giveaway.store_app_id,
            price_status="free",
            source="gamerpower",
            store=giveaway.store,
            external_id=giveaway.external_id,
            worth_usd=giveaway.worth_usd,
            ends_at=giveaway.ends_at,
            claim_url=giveaway.claim_url,
            image_url=giveaway.image_url,
            dedup_key=giveaway.dedup_key,
        )
        return self._posts.insert_if_missing(post)

    def _import_history(self, group: Group, items: list[ParsedItem]) -> None:
        """Importa publicações existentes sem gerar notificações retroativas."""
        for item in items:
            self._insert_post(group.id, item, notified=True)

    def _insert_post(
        self, group_id: int, item: ParsedItem, notified: bool
    ) -> Optional[Post]:
        identifier, identifier_source = build_identifier(item)
        store_url = extract_store_url(item.description)
        app_id = extract_app_id(store_url)
        dedup_key = f"steam:app:{app_id}" if app_id else identifier

        post = Post(
            group_id=group_id,
            identifier=identifier,
            identifier_source=identifier_source,
            title=item.title,
            publication_url=item.link,
            store_url=store_url,
            description=item.description,
            author=item.author,
            published_at=item.published_at,
            notified=notified,
            store_app_id=app_id,
            source="steam_group",
            store=STORE_STEAM,
            claim_url=store_url or item.link,
            dedup_key=dedup_key,
        )
        return self._posts.insert_if_missing(post)