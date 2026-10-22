"""Atualização periódica do status de validade das ofertas."""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from ..config import (
    PRICE_CHECK_FREE_TTL_MINUTES,
    PRICE_CHECK_MAX_AGE_DAYS,
    PRICE_CHECK_MAX_PER_RUN,
    PRICE_CHECK_NOT_FREE_TTL_MINUTES,
    PRICE_CHECK_UNKNOWN_TTL_MINUTES,
)
from ..database.repositories import PostRepository
from .price_checker import SteamPriceChecker

logger = logging.getLogger(__name__)


class PriceRefreshService:
    """Verifica na loja Steam quais ofertas continuam com 100% de desconto."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        checker: Optional[SteamPriceChecker] = None,
        *,
        limit: int = PRICE_CHECK_MAX_PER_RUN,
        max_age_days: int = PRICE_CHECK_MAX_AGE_DAYS,
        free_ttl_minutes: int = PRICE_CHECK_FREE_TTL_MINUTES,
        unknown_ttl_minutes: int = PRICE_CHECK_UNKNOWN_TTL_MINUTES,
        not_free_ttl_minutes: int = PRICE_CHECK_NOT_FREE_TTL_MINUTES,
    ) -> None:
        self._posts = PostRepository(conn)
        self._checker = checker or SteamPriceChecker()
        self._limit = limit
        self._max_age_days = max_age_days
        self._free_ttl_minutes = free_ttl_minutes
        self._unknown_ttl_minutes = unknown_ttl_minutes
        self._not_free_ttl_minutes = not_free_ttl_minutes

    def refresh(self, force: bool = False) -> int:
        """Atualiza os posts pendentes/vencidos e retorna quantos foram vistos."""
        posts = self._posts.list_for_price_refresh(
            limit=self._limit,
            max_age_days=self._max_age_days,
            free_ttl_minutes=self._free_ttl_minutes,
            unknown_ttl_minutes=self._unknown_ttl_minutes,
            not_free_ttl_minutes=self._not_free_ttl_minutes,
            force=force,
        )

        updated = 0
        for post in posts:
            if post.id is None:
                continue
            result = self._checker.check(post.store_url, post.title)
            self._posts.update_price_check(
                post.id,
                status=result.status,
                app_id=result.app_id,
                initial_cents=result.initial_cents,
                final_cents=result.final_cents,
                discount_percent=result.discount_percent,
                currency=result.currency,
                source=result.source,
                checked_at=result.checked_at,
                error=result.error,
            )
            updated += 1
            if result.retryable:
                logger.warning(
                    "Verificação de preços interrompida nesta rodada: %s",
                    result.error,
                )
                break
        return updated
