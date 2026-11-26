#!/usr/bin/env python3
"""Build completo do desktop 0.3+ (SPA, backend headless e instalador).

Etapas:
1. (opcional) roda os testes Python;
2. compila a SPA com electron-vite;
3. empacota o backend FastAPI com PyInstaller (onedir, console);
4. monta ``backend-dist/`` com backend + SPA + assets de runtime;
5. chama o electron-builder para gerar o instalador da plataforma atual.

Exemplos:
    .venv\\Scripts\\python.exe scripts/build_desktop.py
    .venv\\Scripts\\python.exe scripts/build_desktop.py --skip-tests --skip-installer

O build de Linux (AppImage/deb) deve rodar em Linux; o workflow do GitHub
Actions faz isso em ``ubuntu-22.04``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / "desktop"
PACKAGING = ROOT / "packaging"
BACKEND_DIST = ROOT / "backend-dist"
PYINSTALLER_DIST = ROOT / "build" / "pyinstaller-dist"
PYINSTALLER_WORK = ROOT / "build" / "pyinstaller-work"
RUNTIME_ASSETS = ("icon.png", "icon.ico", "tray.png")


def log(message: str) -> None:
    print(f"\n==> {message}", flush=True)


def run(args: list[str], cwd: Path = ROOT) -> None:
    printable = subprocess.list2cmdline(args) if os.name == "nt" else " ".join(args)
    print(f"$ {printable}", flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Ferramenta não encontrada no PATH: {name}")
    return path


def app_version() -> str:
    output = subprocess.check_output(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'src'); "
            "from free_games_hub import __version__; print(__version__)",
        ],
        cwd=ROOT,
        text=True,
    )
    return output.strip()


def validate_versions() -> str:
    version = app_version()
    package = json.loads((DESKTOP / "package.json").read_text(encoding="utf-8"))
    if package.get("version") != version:
        raise SystemExit(
            "Versões divergentes: "
            f"pyproject/__init__={version} e desktop/package.json={package.get('version')}"
        )
    return version


def check_build_dependencies() -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit(
            "PyInstaller não está instalado. Rode: pip install -e \".[dev,build]\""
        )


def stage_runtime(version: str) -> None:
    log("Montando backend-dist")
    if BACKEND_DIST.exists():
        shutil.rmtree(BACKEND_DIST)
    BACKEND_DIST.mkdir(parents=True)

    spa_src = DESKTOP / "out" / "renderer"
    if not (spa_src / "index.html").is_file():
        raise SystemExit(f"SPA não encontrada em {spa_src}; rode o build do renderer.")
    shutil.copytree(spa_src, BACKEND_DIST / "spa")

    assets_dest = BACKEND_DIST / "assets"
    assets_dest.mkdir()
    assets_src = DESKTOP / "assets"
    for name in RUNTIME_ASSETS:
        source = assets_src / name
        if not source.is_file():
            raise SystemExit(f"Asset de runtime ausente: {source}")
        shutil.copy2(source, assets_dest / name)

    version_file = ROOT / "build" / "version_info_backend.txt"
    build_version = ROOT / "build" / "version_info.txt"
    run(
        [
            sys.executable,
            str(PACKAGING / "make_version_info.py"),
            version,
            str(version_file),
            "free-games-hub-backend.exe",
            "Free Games Hub Backend",
        ]
    )
    # Mantém o arquivo histórico usado pelo build legado.
    build_version.write_text(version_file.read_text(encoding="utf-8"), encoding="utf-8")


def build_backend() -> None:
    log("Empacotando backend com PyInstaller")
    if PYINSTALLER_DIST.exists():
        shutil.rmtree(PYINSTALLER_DIST)
    if PYINSTALLER_WORK.exists():
        shutil.rmtree(PYINSTALLER_WORK)
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(PYINSTALLER_DIST),
            "--workpath",
            str(PYINSTALLER_WORK),
            str(PACKAGING / "backend.spec"),
        ]
    )

    output = PYINSTALLER_DIST / "free-games-hub-backend"
    exe = output / ("free-games-hub-backend.exe" if os.name == "nt" else "free-games-hub-backend")
    if not exe.is_file():
        raise SystemExit(f"Backend não encontrado após o PyInstaller: {exe}")

    for entry in output.iterdir():
        destination = BACKEND_DIST / entry.name
        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if entry.is_dir():
            shutil.copytree(entry, destination)
        else:
            shutil.copy2(entry, destination)


def build_installer(target: str) -> None:
    log(f"Gerando instalador ({target})")
    npx = tool("npx")
    args = [npx, "electron-builder", "--publish", "never"]
    if target == "win":
        args += ["--win", "nsis"]
    elif target == "linux":
        args += ["--linux", "AppImage", "deb"]
    else:
        raise SystemExit(f"Alvo inválido: {target}")
    run(args, cwd=DESKTOP)


def show_artifacts() -> None:
    dist = DESKTOP / "dist"
    patterns = ("*.exe", "*.AppImage", "*.deb", "*.blockmap", "*.yml")
    found = sorted({path for pattern in patterns for path in dist.glob(pattern)})
    if not found:
        print("\nNenhum artefato de instalador encontrado em desktop/dist.")
        return
    log("Artefatos gerados")
    for path in found:
        print(f" - {path} ({path.stat().st_size / (1024 * 1024):.1f} MB)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="não rodar pytest")
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="parar depois de montar backend-dist (sem electron-builder)",
    )
    args = parser.parse_args()

    if sys.platform not in ("win32", "linux"):
        raise SystemExit("Esta versão suporta build apenas em Windows e Linux (x64).")

    version = validate_versions()
    log(f"Free Games Hub {version} — build desktop")
    check_build_dependencies()

    if not args.skip_tests:
        log("Rodando testes Python")
        run([sys.executable, "-m", "pytest"])

    log("Compilando SPA (electron-vite)")
    npm = tool("npm")
    run([npm, "run", "build"], cwd=DESKTOP)

    stage_runtime(version)
    build_backend()

    if args.skip_installer:
        log("Build do backend concluído (instalador ignorado)")
        print(f"Conteúdo pronto em: {BACKEND_DIST}")
        return 0

    build_installer("win" if sys.platform == "win32" else "linux")
    show_artifacts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
