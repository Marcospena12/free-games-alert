"""Contrato base e modelo normalizado para fontes de ofertas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol


@dataclass
class RawGiveaway:
    """Modelo normalizado de oferta coletada por qualquer adaptador de fonte."""

    source_id: str  # ex.: "gamerpower" ou "steam_rss"
    external_id: str  # id original na fonte (ex.: "1546" ou GUID do RSS)
    title: str
    store: str  # slug principal (ex.: "steam", "epic-games-store", "gog")
    type: str  # "game", "loot", "beta", "other"
    worth_usd: Optional[float] = None
    ends_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    claim_url: Optional[str] = None
    store_url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    supported_stores: list[str] = field(default_factory=list)
    source_name: str = "GamerPower"
    group_id: Optional[int] = None
    store_app_id: Optional[int] = None

    @property
    def dedup_key(self) -> str:
        """Gera a chave de deduplicação canônica para persistência e verificação."""
        # Se for Steam e temos app_id identificado
        if self.store == "steam" and self.store_app_id:
            return f"steam:app:{self.store_app_id}"
        # Se tiver external_id confiável da fonte
        if self.source_id and self.external_id:
            return f"{self.source_id}:{self.external_id}"
        # Fallback para loja + título normalizado
        norm_title = "".join(c for c in self.title.lower() if c.isalnum() or c.isspace()).strip()
        norm_title = "_".join(norm_title.split())
        return f"{self.store}:{norm_title}"


class SourceAdapter(Protocol):
    """Contrato comum para qualquer adaptador de fonte de ofertas."""

    @property
    def source_id(self) -> str:
        """Identificador único da fonte (ex.: 'gamerpower', 'steam_rss')."""
        ...

    @property
    def display_name(self) -> str:
        """Nome legível para exibição e logs."""
        ...

    def is_enabled(self) -> bool:
        """Retorna True se a fonte estiver habilitada para consulta."""
        ...

    def fetch_giveaways(self) -> list[RawGiveaway]:
        """Obtém as ofertas disponíveis na fonte e as normaliza."""
        ...
