#!/usr/bin/env python3
"""Gera os assets do Electron a partir do ícone oficial do projeto.

Fonte: ``packaging/assets/app.png`` (e ``app.ico`` já gerado).
Saída: ``desktop/assets/icon.png``, ``icon.ico`` e ``tray.png``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PNG = ROOT / "packaging" / "assets" / "app.png"
SOURCE_ICO = ROOT / "packaging" / "assets" / "app.ico"
TARGET = ROOT / "desktop" / "assets"


def main() -> None:
    if not SOURCE_PNG.is_file():
        raise SystemExit(f"Ícone fonte não encontrado: {SOURCE_PNG}")
    TARGET.mkdir(parents=True, exist_ok=True)

    with Image.open(SOURCE_PNG) as image:
        icon = image.convert("RGBA")
        icon.thumbnail((512, 512), Image.Resampling.LANCZOS)
        icon.save(TARGET / "icon.png", "PNG", optimize=True)

        tray = image.convert("RGBA")
        tray.thumbnail((32, 32), Image.Resampling.LANCZOS)
        tray.save(TARGET / "tray.png", "PNG", optimize=True)

    if SOURCE_ICO.is_file():
        shutil.copy2(SOURCE_ICO, TARGET / "icon.ico")
    else:
        raise SystemExit(f"Ícone .ico não encontrado: {SOURCE_ICO}")

    print(f"Assets gerados em {TARGET}")


if __name__ == "__main__":
    main()
