#!/usr/bin/env python3
"""Utilitários de imagem compartilhados pelos geradores de assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

DEFAULT_MARGIN = 0.04


def trim_transparent(image: Image.Image) -> Image.Image:
    """Recorta as bordas totalmente transparentes da imagem."""
    rgba = image.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("a imagem de origem é totalmente transparente")
    return rgba.crop(bbox)


def squared_logo(
    source: Image.Image, canvas: int, margin: float = DEFAULT_MARGIN
) -> Image.Image:
    """Ajusta a logo em um quadrado transparente, preservando a proporção.

    A logo é recortada nas bordas transparentes e redimensionada para caber
    com ``margin`` em cada lado. Assim, logos não quadradas aproveitam melhor
    ícones pequenos (bandeja, por exemplo) em vez de virarem uma faixa fina.
    """
    logo = trim_transparent(source)
    usable = max(1, round(canvas * (1 - 2 * margin)))
    logo.thumbnail((usable, usable), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    result.alpha_composite(logo, ((canvas - logo.width) // 2, (canvas - logo.height) // 2))
    return result


def save_png(image: Image.Image, destination: Path | str) -> None:
    """Salva PNG com compressão máxima."""
    image.save(destination, "PNG", optimize=True, compress_level=9)
