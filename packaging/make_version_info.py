"""Gera o arquivo de metadados de versão usado pelo PyInstaller."""

from __future__ import annotations

import sys
from pathlib import Path

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={filevers},
    prodvers={prodvers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'Marcos'),
        StringStruct('FileDescription', 'Steam Free Games Monitor'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'SteamFreeGamesMonitor'),
        StringStruct('OriginalFilename', 'SteamFreeGamesMonitor.exe'),
        StringStruct('ProductName', 'Steam Free Games Monitor'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("uso: make_version_info.py <versao> <destino>")
    version = sys.argv[1]
    destination = Path(sys.argv[2])
    parts = [int(part) for part in version.split(".")]
    if len(parts) > 4 or not parts:
        raise SystemExit(f"versão inválida: {version}")
    numbers = (parts + [0, 0, 0, 0])[:4]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        TEMPLATE.format(
            filevers=tuple(numbers),
            prodvers=tuple(numbers),
            version=version,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
