#!/usr/bin/env python3
"""Gera os assets do Electron a partir da logo oficial do projeto.

Fonte: ``packaging/assets/app.png`` (e ``app.ico`` já gerado).
Saída: ``desktop/assets/icon.png``, ``icon.ico`` e ``tray.png``.

A logo é recortada nas bordas transparentes e centralizada em um quadrado,
para que imagens não quadradas continuem legíveis em tamanhos pequenos.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

from image_assets import save_png, squared_logo

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PNG = ROOT / "packaging" / "assets" / "app.png"
SOURCE_ICO = ROOT / "packaging" / "assets" / "app.ico"
TARGET = ROOT / "desktop" / "assets"
ICON_SIZE = 512
TRAY_SIZE = 32
TRAY_MARGIN = 0.02


def main() -> None:
    if not SOURCE_PNG.is_file():
        raise SystemExit(f"Logo fonte não encontrada: {SOURCE_PNG}")
    TARGET.mkdir(parents=True, exist_ok=True)

    with Image.open(SOURCE_PNG) as image:
        save_png(squared_logo(image, ICON_SIZE), TARGET / "icon.png")
        save_png(
            squared_logo(image, TRAY_SIZE, margin=TRAY_MARGIN), TARGET / "tray.png"
        )

    if SOURCE_ICO.is_file():
        shutil.copy2(SOURCE_ICO, TARGET / "icon.ico")
    else:
        raise SystemExit(f"Ícone .ico não encontrado: {SOURCE_ICO}")

    print(f"Assets gerados em {TARGET}")


if __name__ == "__main__":
    main()
