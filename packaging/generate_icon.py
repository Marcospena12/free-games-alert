"""Gera os ícones do app a partir de ``packaging/assets/app.png``.

Saídas: ``app.ico``, ``src/free_games_hub/assets/app.ico`` e ``app.png``.
A logo é recortada nas bordas transparentes e centralizada em um quadrado,
mantendo a proporção e aproveitando melhor os tamanhos pequenos do ícone.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtGui import QGuiApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from free_games_hub.ui.tray import build_app_icon
from image_assets import save_png, squared_logo

SIZES = (16, 24, 32, 48, 64, 128, 256)
ICON_CANVAS = 1024


def main() -> None:
    pkg_assets = Path(__file__).resolve().parent / "assets"
    src_assets = ROOT / "src" / "free_games_hub" / "assets"
    pkg_assets.mkdir(parents=True, exist_ok=True)
    src_assets.mkdir(parents=True, exist_ok=True)

    png_src = pkg_assets / "app.png"
    output_pkg_ico = pkg_assets / "app.ico"
    output_src_ico = src_assets / "app.ico"
    output_src_png = src_assets / "app.png"

    if png_src.exists():
        with Image.open(png_src) as img:
            icon = squared_logo(img, ICON_CANVAS)
            icon.save(output_pkg_ico, format="ICO", sizes=[(s, s) for s in SIZES])
            icon.save(output_src_ico, format="ICO", sizes=[(s, s) for s in SIZES])
            save_png(icon, output_src_png)
        print(f"Ícone gerado a partir de {png_src}")
        return

    app = QGuiApplication([])
    output = output_pkg_ico
    icon = build_app_icon()
    images: list[Image.Image] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        for size in SIZES:
            png_path = Path(temp_dir) / f"app-{size}.png"
            if not icon.pixmap(size, size).save(str(png_path), "PNG"):
                raise RuntimeError(f"Não foi possível gerar o ícone {size}px")
            with Image.open(png_path) as image:
                images.append(image.convert("RGBA").copy())

    images[-1].save(output, format="ICO", sizes=[(size, size) for size in SIZES])
    app.quit()
    print(f"Ícone gerado: {output}")


if __name__ == "__main__":
    main()
