"""Regras de negócio para identificação de ofertas gratuitas."""

from __future__ import annotations

import re

FREE_TAG_RE = re.compile(r"\[free\]", re.IGNORECASE)
STORE_URL_RE = re.compile(
    r"https?://store\.steampowered\.com/(?:app|sub|bundle|sale)/[^\"'<>\s]+"
)


def is_free_title(title: str) -> bool:
    """Retorna True quando o título contém ``[FREE]`` (sem diferenciar caixa)."""
    return bool(FREE_TAG_RE.search(title or ""))


def clean_title(title: str) -> str:
    """Remove a marca ``[FREE]`` e espaços extras do título do post."""
    text = FREE_TAG_RE.sub(" ", title or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -–—|:")


def extract_store_url(html: str | None) -> str | None:
    """Extrai o primeiro link da loja Steam presente no HTML da descrição.

    Retorna ``None`` quando não houver link de loja disponível.
    """
    if not html:
        return None
    match = STORE_URL_RE.search(html)
    return match.group(0) if match else None