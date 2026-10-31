"""Motor de regras e filtros de ofertas por loja e preferências."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

from ..database.repositories import SettingsRepository
from ..sources.base import RawGiveaway
from ..sources.stores import (
    DEFAULT_ENABLED_STORES,
    DEFAULT_ENABLED_TYPES,
    STORE_LABELS,
    TYPE_BETA,
    TYPE_GAME,
    TYPE_LOOT,
)

SETTINGS_KEY_GAMERPOWER_ENABLED = "gamerpower_enabled"
SETTINGS_KEY_ENABLED_STORES = "enabled_stores"
SETTINGS_KEY_ENABLED_TYPES = "enabled_types"
SETTINGS_KEY_STORE_FILTERS = "store_filters"
SETTINGS_KEY_MIN_WORTH = "filter_min_worth_usd"
SETTINGS_KEY_INCLUDE_NA_WORTH = "filter_include_na_worth"
SETTINGS_KEY_IGNORE_NO_END_DATE = "filter_ignore_no_end_date"
SETTINGS_KEY_EXCLUDE_KEYWORDS = "filter_exclude_keywords"


@dataclass
class StoreFilterConfig:
    """Configurações de filtro independentes para uma loja ou perfil global."""

    enabled: bool = True
    allowed_types: set[str] = field(default_factory=lambda: {TYPE_GAME})
    min_worth_usd: Optional[float] = None
    include_na_worth: bool = True
    title_include_keywords: list[str] = field(default_factory=list)
    title_exclude_keywords: list[str] = field(default_factory=list)
    ignore_no_end_date: bool = False
    min_hours_before_expiration: Optional[int] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["allowed_types"] = sorted(list(self.allowed_types))
        return data

    @classmethod
    def from_dict(cls, data: dict) -> StoreFilterConfig:
        return cls(
            enabled=bool(data.get("enabled", True)),
            allowed_types=set(data.get("allowed_types", [TYPE_GAME])),
            min_worth_usd=float(data["min_worth_usd"]) if data.get("min_worth_usd") is not None else None,
            include_na_worth=bool(data.get("include_na_worth", True)),
            title_include_keywords=list(data.get("title_include_keywords", [])),
            title_exclude_keywords=list(data.get("title_exclude_keywords", [])),
            ignore_no_end_date=bool(data.get("ignore_no_end_date", False)),
            min_hours_before_expiration=int(data["min_hours_before_expiration"]) if data.get("min_hours_before_expiration") is not None else None,
        )


class StoreFilterService:
    """Carrega preferências e aplica regras de filtragem às ofertas brutas."""

    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def is_gamerpower_enabled(self) -> bool:
        return self._settings.get_bool(SETTINGS_KEY_GAMERPOWER_ENABLED, False)

    def set_gamerpower_enabled(self, enabled: bool) -> None:
        self._settings.set(SETTINGS_KEY_GAMERPOWER_ENABLED, "1" if enabled else "0")

    # ----- Filtros independentes por loja ---------------------------------
    def get_all_store_filters(self) -> dict[str, StoreFilterConfig]:
        """Retorna as configurações de filtros para todas as lojas registradas."""
        raw_val = self._settings.get(SETTINGS_KEY_STORE_FILTERS)
        saved_filters: dict[str, dict] = {}
        if raw_val:
            try:
                parsed = json.loads(raw_val)
                if isinstance(parsed, dict):
                    saved_filters = parsed
            except Exception:
                pass

        # Lojas atualmente habilitadas na configuração simples
        legacy_enabled = self.get_enabled_stores()

        result: dict[str, StoreFilterConfig] = {}
        for slug in STORE_LABELS.keys():
            if slug in saved_filters:
                result[slug] = StoreFilterConfig.from_dict(saved_filters[slug])
            else:
                # Inicializar com valores padrão sensatos
                is_enabled = slug in legacy_enabled if legacy_enabled else slug in DEFAULT_ENABLED_STORES
                result[slug] = StoreFilterConfig(
                    enabled=is_enabled,
                    allowed_types=set(self.get_enabled_types()),
                    min_worth_usd=None,
                    include_na_worth=True,
                    ignore_no_end_date=False,
                )
        return result

    def get_store_filter(self, store_slug: str) -> StoreFilterConfig:
        """Retorna o filtro específico de uma loja."""
        all_filters = self.get_all_store_filters()
        return all_filters.get(
            store_slug,
            StoreFilterConfig(enabled=False, allowed_types={TYPE_GAME}),
        )

    def set_store_filter(self, store_slug: str, config: StoreFilterConfig) -> None:
        """Atualiza a configuração de uma loja e persiste."""
        all_filters = self.get_all_store_filters()
        all_filters[store_slug] = config
        self.set_all_store_filters(all_filters)

    def set_all_store_filters(self, configs: dict[str, StoreFilterConfig]) -> None:
        """Salva todas as configurações de lojas no repositório."""
        serialized = {slug: cfg.to_dict() for slug, cfg in configs.items()}
        self._settings.set(SETTINGS_KEY_STORE_FILTERS, json.dumps(serialized))

        # Sincronizar enabled_stores legado para manter compatibilidade
        enabled_list = [slug for slug, cfg in configs.items() if cfg.enabled]
        self._settings.set(SETTINGS_KEY_ENABLED_STORES, json.dumps(enabled_list))

    def copy_store_filter_to_all(self, source_slug: str) -> None:
        """Copia os critérios (tipos, valor mínimo, prazos, palavras) de uma loja para todas as outras."""
        all_filters = self.get_all_store_filters()
        source = all_filters.get(source_slug)
        if not source:
            return

        for slug, cfg in all_filters.items():
            if slug == source_slug:
                continue
            cfg.allowed_types = set(source.allowed_types)
            cfg.min_worth_usd = source.min_worth_usd
            cfg.include_na_worth = source.include_na_worth
            cfg.title_include_keywords = list(source.title_include_keywords)
            cfg.title_exclude_keywords = list(source.title_exclude_keywords)
            cfg.ignore_no_end_date = source.ignore_no_end_date
            cfg.min_hours_before_expiration = source.min_hours_before_expiration

        self.set_all_store_filters(all_filters)

    def get_effective_enabled_stores(self) -> list[str]:
        """Retorna os slugs de todas as lojas que estão ativas."""
        all_filters = self.get_all_store_filters()
        return [slug for slug, cfg in all_filters.items() if cfg.enabled]

    def get_effective_query_types(self) -> list[str]:
        """Retorna a união de tipos requeridos por todas as lojas ativas para consulta HTTP otimizada."""
        all_filters = self.get_all_store_filters()
        union_types: set[str] = set()
        for cfg in all_filters.values():
            if cfg.enabled:
                union_types.update(cfg.allowed_types)
        return sorted(list(union_types)) if union_types else list(DEFAULT_ENABLED_TYPES)

    # ----- Métodos Legados / Compatibilidade -------------------------------
    def get_enabled_stores(self) -> list[str]:
        val = self._settings.get(SETTINGS_KEY_ENABLED_STORES)
        if not val:
            return list(DEFAULT_ENABLED_STORES)
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return list(DEFAULT_ENABLED_STORES)

    def set_enabled_stores(self, stores: list[str]) -> None:
        self._settings.set(SETTINGS_KEY_ENABLED_STORES, json.dumps(stores))

    def get_enabled_types(self) -> list[str]:
        val = self._settings.get(SETTINGS_KEY_ENABLED_TYPES)
        if not val:
            return list(DEFAULT_ENABLED_TYPES)
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return list(DEFAULT_ENABLED_TYPES)

    def set_enabled_types(self, types: list[str]) -> None:
        self._settings.set(SETTINGS_KEY_ENABLED_TYPES, json.dumps(types))
        raw_val = self._settings.get(SETTINGS_KEY_STORE_FILTERS)
        if raw_val:
            try:
                parsed = json.loads(raw_val)
                if isinstance(parsed, dict):
                    for cfg_dict in parsed.values():
                        cfg_dict["allowed_types"] = types
                    self._settings.set(SETTINGS_KEY_STORE_FILTERS, json.dumps(parsed))
            except Exception:
                pass

    def get_global_filter_config(self) -> StoreFilterConfig:
        min_worth = None
        raw_min = self._settings.get(SETTINGS_KEY_MIN_WORTH)
        if raw_min:
            try:
                min_worth = float(raw_min)
            except ValueError:
                pass

        include_na = self._settings.get_bool(SETTINGS_KEY_INCLUDE_NA_WORTH, True)
        ignore_no_end = self._settings.get_bool(SETTINGS_KEY_IGNORE_NO_END_DATE, False)
        exclude_kw_str = self._settings.get(SETTINGS_KEY_EXCLUDE_KEYWORDS, "")
        exclude_kw = [k.strip().lower() for k in exclude_kw_str.split(",") if k.strip()]

        return StoreFilterConfig(
            enabled=True,
            allowed_types=set(self.get_enabled_types()),
            min_worth_usd=min_worth,
            include_na_worth=include_na,
            title_exclude_keywords=exclude_kw,
            ignore_no_end_date=ignore_no_end,
        )

    # ----- Avaliação de Ofertas --------------------------------------------
    def matches(self, deal: RawGiveaway, override_config: Optional[StoreFilterConfig] = None) -> bool:
        """Avalia se uma oferta atende aos critérios configurados para as lojas suportadas."""
        if override_config is not None:
            return self._matches_single_config(deal, override_config)

        all_filters = self.get_all_store_filters()

        # Reunir lojas candidatas da oferta (lojas suportadas + loja primária)
        candidate_stores: list[str] = []
        for s in deal.supported_stores:
            if s not in candidate_stores:
                candidate_stores.append(s)
        if deal.store and deal.store not in candidate_stores:
            candidate_stores.append(deal.store)

        for store_slug in candidate_stores:
            cfg = all_filters.get(store_slug)
            if cfg is None or not cfg.enabled:
                continue

            if self._matches_single_config(deal, cfg):
                # Se a loja primária atual não estava habilitada ou não atendeu aos critérios,
                # ajusta o deal.store para a loja que aprovou a oferta
                primary_cfg = all_filters.get(deal.store)
                if (
                    primary_cfg is None
                    or not primary_cfg.enabled
                    or not self._matches_single_config(deal, primary_cfg)
                ):
                    deal.store = store_slug
                return True

        return False

    @staticmethod
    def _matches_single_config(deal: RawGiveaway, config: StoreFilterConfig) -> bool:
        """Verifica se um deal atende a uma configuração de filtro específica."""
        # 1. Checagem de tipo (Game, Loot/DLC, Beta)
        if config.allowed_types and deal.type not in config.allowed_types:
            return False

        # 2. Checagem de preço em USD
        if config.min_worth_usd is not None:
            if deal.worth_usd is None:
                if not config.include_na_worth:
                    return False
            elif deal.worth_usd < config.min_worth_usd:
                return False

        # 3. Checagem de palavras-chave no título
        title_lower = deal.title.lower()
        if config.title_include_keywords:
            if not any(kw in title_lower for kw in config.title_include_keywords):
                return False
        if config.title_exclude_keywords:
            if any(kw in title_lower for kw in config.title_exclude_keywords):
                return False

        # 4. Checagem de prazo de expiração
        if config.ignore_no_end_date and deal.ends_at is None:
            return False

        if config.min_hours_before_expiration is not None and deal.ends_at is not None:
            now = datetime.now()
            if deal.ends_at > now:
                remaining_hours = (deal.ends_at - now).total_seconds() / 3600
                if remaining_hours < config.min_hours_before_expiration:
                    return False

        return True
