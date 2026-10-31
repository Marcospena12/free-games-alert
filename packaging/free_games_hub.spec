# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

PACKAGING = Path(SPECPATH).resolve()
ROOT = PACKAGING.parent
APP_NAME = "FreeGamesHub"

hiddenimports = [
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

datas = collect_data_files("desktop_notifier")
assets_dir = ROOT / "src" / "free_games_hub" / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "free_games_hub/assets"))

packaging_splash = PACKAGING / "assets" / "splash.png"
if packaging_splash.exists():
    datas.append((str(packaging_splash), "free_games_hub/assets"))

a = Analysis(
    [str(PACKAGING / "entrypoint.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PACKAGING / "assets" / "app.ico"),
    version=str(ROOT / "build" / "version_info.txt"),
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
