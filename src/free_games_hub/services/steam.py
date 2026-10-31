"""Integração com o cliente desktop da Steam e resolução de URLs do protocolo steam://."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)

APP_ID_RE = re.compile(r"store\.steampowered\.com/app/(\d+)", re.IGNORECASE)


def _is_steam_running_win() -> bool:
    """Verifica se steam.exe está em execução no Windows usando ctypes (sem dependências)."""
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    try:
        CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
        Process32First = ctypes.windll.kernel32.Process32First
        Process32Next = ctypes.windll.kernel32.Process32Next
        CloseHandle = ctypes.windll.kernel32.CloseHandle

        h_snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h_snap in (-1, 0):
            return False

        pe32 = PROCESSENTRY32()
        pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
        try:
            if Process32First(h_snap, ctypes.byref(pe32)):
                while True:
                    name = pe32.szExeFile.decode("utf-8", errors="ignore").lower()
                    if name == "steam.exe":
                        return True
                    if not Process32Next(h_snap, ctypes.byref(pe32)):
                        break
        finally:
            CloseHandle(h_snap)
    except Exception as exc:  # noqa: BLE001 - falha não quebra a aplicação
        logger.debug("Falha ao verificar processo da Steam no Windows: %s", exc)
        return False
    return False


def _is_steam_running_linux() -> bool:
    """Verifica se o processo steam está em execução no Linux."""
    try:
        res = subprocess.run(
            ["pgrep", "-x", "steam"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return res.returncode == 0
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao verificar processo da Steam no Linux: %s", exc)
        return False


def is_steam_running() -> bool:
    """Verifica se o cliente desktop da Steam está em execução."""
    if sys.platform == "win32":
        return _is_steam_running_win()
    if sys.platform.startswith("linux"):
        return _is_steam_running_linux()
    return False


def get_steam_protocol_url(
    url: Optional[str] = None, app_id: Optional[int] = None
) -> Optional[str]:
    """Retorna uma URL do protocolo steam:// para a publicação/loja ou None se incompatível."""
    if app_id:
        return f"steam://store/{app_id}"
    if not url:
        return None

    match = APP_ID_RE.search(url)
    if match:
        return f"steam://store/{match.group(1)}"

    if "steampowered.com" in url or "steamcommunity.com" in url:
        return f"steam://openurl/{url}"

    return None


def resolve_game_open_target(
    url: Optional[str] = None,
    app_id: Optional[int] = None,
    *,
    prefer_steam: bool = True,
) -> tuple[Optional[str], bool]:
    """Determina a URL de destino e se usará o protocolo Steam.

    Retorna uma tupla ``(url_final, is_steam)``. Se a Steam estiver rodando e a
    URL for compatível, retorna a URL com esquema ``steam://`` e ``True``.
    Caso contrário, retorna a URL web original e ``False``.
    """
    if prefer_steam and is_steam_running():
        steam_target = get_steam_protocol_url(url=url, app_id=app_id)
        if steam_target:
            return steam_target, True

    return url, False
