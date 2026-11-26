"""Gera o arquivo de metadados de versão usado pelo PyInstaller.

Uso:
    make_version_info.py <versao> <destino> [nome_do_exe] [descricao]

Sem os argumentos opcionais, mantém o comportamento histórico do executável
da interface PySide6.
"""

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
        StringStruct('FileDescription', '{description}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{internal}'),
        StringStruct('OriginalFilename', '{filename}'),
        StringStruct('ProductName', 'Free Games Hub'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    if len(sys.argv) not in (3, 4, 5):
        raise SystemExit(
            "uso: make_version_info.py <versao> <destino> [nome_do_exe] [descricao]"
        )
    version = sys.argv[1]
    destination = Path(sys.argv[2])
    filename = sys.argv[3] if len(sys.argv) >= 4 else "FreeGamesHub.exe"
    description = sys.argv[4] if len(sys.argv) >= 5 else "Free Games Hub"
    internal = Path(filename).stem

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
            filename=filename,
            description=description,
            internal=internal,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
