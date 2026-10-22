"""Gera packaging/assets/app.ico a partir do ícone usado pela bandeja."""

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

from steam_free_games_monitor.ui.tray import build_app_icon

SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> None:
    app = QGuiApplication([])
    output = Path(__file__).resolve().parent / "assets" / "app.ico"
    output.parent.mkdir(parents=True, exist_ok=True)

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
