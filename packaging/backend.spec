# -*- mode: python ; coding: utf-8 -*-
"""Backend headless (FastAPI + uvicorn) distribuído com o app Electron.

Saída: ``build/pyinstaller-dist/free-games-hub-backend/`` (onedir, console).
O script ``scripts/build_desktop.py`` copia o conteúdo para ``backend-dist``
junto com a SPA construída e os ícones usados em runtime.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PACKAGING = Path(SPECPATH).resolve()
ROOT = PACKAGING.parent
APP_NAME = "free-games-hub-backend"

hiddenimports = collect_submodules("uvicorn")
hiddenimports += [
    "anyio._backends._asyncio",
    "desktop_notifier.backends.winrt",
    "winrt.system",
    "winrt.windows.applicationmodel.core",
    "winrt.windows.data.xml.dom",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.ui.notifications",
    "winrt._winrt_windows_applicationmodel_core",
    "winrt._winrt_windows_data_xml_dom",
    "winrt._winrt_windows_foundation",
    "winrt._winrt_windows_foundation_collections",
    "winrt._winrt_windows_ui_notifications",
]

if sys.platform.startswith("linux"):
    hiddenimports += collect_submodules("dbus_next")
    hiddenimports += collect_submodules("desktop_notifier")

datas = collect_data_files("desktop_notifier")
assets_dir = ROOT / "src" / "free_games_hub" / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "free_games_hub/assets"))

version_file = ROOT / "build" / "version_info_backend.txt"
icon_file = ROOT / "packaging" / "assets" / "app.ico"
windows_metadata = sys.platform == "win32"

a = Analysis(
    [str(PACKAGING / "backend_entrypoint.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # A UI PySide6 não faz parte do backend headless.
    excludes=["PySide6", "shiboken6", "PyQt5", "PyQt6", "tkinter", "tests"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if windows_metadata and icon_file.exists() else None,
    version=str(version_file)
    if windows_metadata and version_file.exists()
    else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
