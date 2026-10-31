"""Módulo de fontes de dados e adaptadores multi-loja."""

from __future__ import annotations

from .base import RawGiveaway, SourceAdapter
from .stores import (
    DEFAULT_ENABLED_STORES,
    DEFAULT_ENABLED_TYPES,
    STORE_EPIC,
    STORE_GOG,
    STORE_ITCHIO,
    STORE_LABELS,
    STORE_STEAM,
    TYPE_BETA,
    TYPE_GAME,
    TYPE_LABELS,
    TYPE_LOOT,
    TYPE_OTHER,
    normalize_store_label,
    parse_platform_string,
)

__all__ = [
    "DEFAULT_ENABLED_STORES",
    "DEFAULT_ENABLED_TYPES",
    "RawGiveaway",
    "STORE_EPIC",
    "STORE_GOG",
    "STORE_ITCHIO",
    "STORE_LABELS",
    "STORE_STEAM",
    "SourceAdapter",
    "TYPE_BETA",
    "TYPE_GAME",
    "TYPE_LABELS",
    "TYPE_LOOT",
    "TYPE_OTHER",
    "normalize_store_label",
    "parse_platform_string",
]
