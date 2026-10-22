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
from .deals import extract_store_url, is_free_title
from .feed_fetcher import FeedFetchError, FeedFetcher, UrlFeedFetcher
from .rss_parser import RssParseError, parse_feed

LAST_CHECK_KEY = "last_check_at"


def build_identifier(item: ParsedItem) -> tuple[str, str]:
    """Identificador único de um item: guid, link ou hash de fallback."""
    if item.guid:
        return item.guid, "guid"
    if item.link:
        return item.link, "link"
    return hash_identifier(item.title, item.published_at), "hash"


class MonitorService:
    """Executa uma rodada de verificação de todos os grupos ativos."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        fetcher: Optional[FeedFetcher] = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._conn = conn
        self._fetcher = fetcher or UrlFeedFetcher(timeout)
        self._groups = GroupRepository(conn)
        self._posts = PostRepository(conn)
        self._settings = SettingsRepository(conn)
        self._errors = ErrorRepository(conn)

    def check_all(self) -> CheckResult:
        """Verifica todos os grupos ativos e retorna o resultado consolidado."""
        result = CheckResult()
        for group in self._groups.list_active():
            result.checked_groups += 1
            self._check_group(group, result)
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

    def _import_history(self, group: Group, items: list[ParsedItem]) -> None:
        """Importa publicações existentes sem gerar notificações retroativas."""
        for item in items:
            self._insert_post(group.id, item, notified=True)

    def _insert_post(
        self, group_id: int, item: ParsedItem, notified: bool
    ) -> Optional[Post]:
        identifier, identifier_source = build_identifier(item)
        post = Post(
            group_id=group_id,
            identifier=identifier,
            identifier_source=identifier_source,
            title=item.title,
            publication_url=item.link,
            store_url=extract_store_url(item.description),
            description=item.description,
            author=item.author,
            published_at=item.published_at,
            notified=notified,
        )
        return self._posts.insert_if_missing(post)