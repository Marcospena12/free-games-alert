"""Funções utilitárias da interface."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from ..models import Post
from ..services.steam import is_steam_running, resolve_game_open_target

EMPTY = "—"


def fmt_datetime(value: Optional[datetime]) -> str:
    if value is None:
        return EMPTY
    return value.strftime("%d/%m/%Y %H:%M")


def fmt_date(value: Optional[date]) -> str:
    if value is None:
        return EMPTY
    return value.strftime("%d/%m/%Y")


def open_url(
    url: Optional[str],
    app_id: Optional[int] = None,
    prefer_steam: bool = True,
) -> None:
    """Abre uma oferta no cliente Steam (caso em execução) ou no navegador padrão."""
    if not url and not app_id:
        return
    target, _is_steam = resolve_game_open_target(url, app_id, prefer_steam=prefer_steam)
    if not target:
        target = url
    if target:
        QDesktopServices.openUrl(QUrl(target))


def fmt_price(cents: Optional[int], currency: Optional[str] = None) -> str:
    """Formata um preço em centavos, usando o padrão brasileiro para BRL."""
    if cents is None:
        return EMPTY
    formatted = f"{cents / 100:,.2f}".replace(",", "X")
    formatted = formatted.replace(".", ",").replace("X", ".")
    if not currency or currency == "BRL":
        return f"R$ {formatted}"
    return f"{formatted} {currency}"


def fmt_post_status(post: Post) -> str:
    """Texto curto do status de validade da oferta."""
    status = post.price_status
    if status == "free":
        text = "Grátis (-100%)"
    elif status == "not_free":
        text = "Expirado"
        if post.price_final_cents is not None:
            text += f" · {fmt_price(post.price_final_cents, post.price_currency)}"
        if post.price_discount_percent:
            text += f" (-{post.price_discount_percent}%)"
    elif status == "f2p":
        text = "F2P (não é promoção)"
    elif status == "unknown":
        text = "Não verificado"
    else:
        text = "Pendente"

    if post.in_library:
        text += " · Na biblioteca"
    return text


def fmt_price_tooltip(post: Post) -> str:
    """Detalhes da última verificação de preço para exibir em tooltip."""
    lines: list[str] = []
    if post.price_initial_cents is not None:
        lines.append(
            f"Preço original: {fmt_price(post.price_initial_cents, post.price_currency)}"
        )
    if post.price_final_cents is not None:
        lines.append(
            f"Preço atual: {fmt_price(post.price_final_cents, post.price_currency)}"
        )
    if post.price_discount_percent:
        lines.append(f"Desconto: {post.price_discount_percent}%")
    if post.price_source == "search":
        lines.append("Jogo localizado pela busca da Steam.")
    if post.price_checked_at is not None:
        lines.append(f"Verificado em: {fmt_datetime(post.price_checked_at)}")
    if post.price_error:
        lines.append(f"Erro: {post.price_error}")
    return "\n".join(lines)