"""Adaptador de fonte da GamerPower API normalizando para RawGiveaway."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Callable, Optional

from .base import RawGiveaway, SourceAdapter
from .gamerpower_client import GamerPowerClient
from .stores import (
    DEFAULT_ENABLED_STORES,
    DEFAULT_ENABLED_TYPES,
    STORE_PC,
    STORE_STEAM,
    TYPE_BETA,
    TYPE_GAME,
    TYPE_LOOT,
    TYPE_OTHER,
    parse_platform_string,
)

logger = logging.getLogger(__name__)

STEAM_APP_ID_RE = re.compile(r"store\.steampowered\.com/app/(\d+)", re.IGNORECASE)
WORTH_RE = re.compile(r"\$?([0-9]+(?:\.[0-9]+)?)")


def _parse_worth(worth_str: Optional[str]) -> Optional[float]:
    if not worth_str or worth_str.upper() == "N/A":
        return None
    match = WORTH_RE.search(worth_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str or dt_str.upper() == "N/A":
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _normalize_type(raw_type: Optional[str]) -> str:
    if not raw_type:
        return TYPE_GAME
    t = raw_type.lower().strip()
    if "game" in t:
        return TYPE_GAME
    if "dlc" in t or "loot" in t:
        return TYPE_LOOT
    if "beta" in t or "early access" in t:
        return TYPE_BETA
    return TYPE_OTHER


def _extract_steam_app_id(*candidates: Optional[str]) -> Optional[int]:
    for cand in candidates:
        if not cand:
            continue
        match = STEAM_APP_ID_RE.search(cand)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


class GamerPowerApiAdapter(SourceAdapter):
    """Adaptador de fonte que busca ofertas via GamerPower API e as normaliza."""

    def __init__(
        self,
        client: Optional[GamerPowerClient] = None,
        get_enabled_stores: Optional[Callable[[], list[str]]] = None,
        get_enabled_types: Optional[Callable[[], list[str]]] = None,
        is_enabled_callback: Optional[Callable[[], bool]] = None,
    ) -> None:
        self.client = client or GamerPowerClient()
        self._get_enabled_stores = get_enabled_stores or (lambda: DEFAULT_ENABLED_STORES)
        self._get_enabled_types = get_enabled_types or (lambda: DEFAULT_ENABLED_TYPES)
        self._is_enabled_callback = is_enabled_callback or (lambda: True)

    @property
    def source_id(self) -> str:
        return "gamerpower"

    @property
    def display_name(self) -> str:
        return "GamerPower API (Multi-lojas)"

    def is_enabled(self) -> bool:
        return bool(self._is_enabled_callback())

    def fetch_giveaways(self) -> list[RawGiveaway]:
        """Consulta a GamerPower e converte cada giveaway para o modelo normalizado."""
        stores = self._get_enabled_stores()
        types = self._get_enabled_types()

        # Mapeia tipos internos para os parâmetros da GamerPower API (game, loot, beta)
        api_types: list[str] = []
        for t in types:
            if t in (TYPE_GAME, TYPE_LOOT, TYPE_BETA):
                api_types.append(t)

        raw_items = self.client.get_giveaways(
            platforms=stores if stores else None,
            types=api_types if api_types else None,
        )

        giveaways: list[RawGiveaway] = []
        for item in raw_items:
            try:
                giveaway = self._to_raw_giveaway(item, stores)
                giveaways.append(giveaway)
            except Exception as exc:
                logger.warning("Falha ao normalizar giveaway da GamerPower (%s): %s", item.get("id"), exc)

        return giveaways

    def _to_raw_giveaway(self, item: dict[str, Any], enabled_stores: list[str]) -> RawGiveaway:
        external_id = str(item.get("id", ""))
        title = item.get("title", "").strip()
        raw_type = item.get("type", "")
        norm_type = _normalize_type(raw_type)

        claim_url = item.get("open_giveaway_url") or item.get("open_giveaway")
        store_url = item.get("open_giveaway_url") or item.get("gamerpower_url")
        platforms_str = item.get("platforms", "")
        supported_stores = parse_platform_string(platforms_str, title=title, url=claim_url)

        # Determinar a loja principal: primeira loja suportada que estiver habilitada pelo usuário
        primary_store = STORE_PC
        for s in supported_stores:
            if s in enabled_stores:
                primary_store = s
                break
        else:
            if supported_stores:
                primary_store = supported_stores[0]

        worth_usd = _parse_worth(item.get("worth"))
        published_at = _parse_datetime(item.get("published_date"))
        ends_at = _parse_datetime(item.get("end_date"))
        image_url = item.get("image") or item.get("thumbnail")
        description = item.get("description")
        instructions = item.get("instructions")

        store_app_id = None
        if primary_store == STORE_STEAM:
            store_app_id = _extract_steam_app_id(claim_url, store_url, description, instructions)

        return RawGiveaway(
            source_id=self.source_id,
            external_id=external_id,
            title=title,
            store=primary_store,
            type=norm_type,
            worth_usd=worth_usd,
            ends_at=ends_at,
            published_at=published_at,
            claim_url=claim_url,
            store_url=store_url,
            image_url=image_url,
            description=description,
            instructions=instructions,
            supported_stores=supported_stores,
            source_name="GamerPower",
            store_app_id=store_app_id,
        )
