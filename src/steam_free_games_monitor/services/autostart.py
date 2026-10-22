"""Inicialização automática do aplicativo com o Windows.

A entrada é criada no registro do usuário atual (``HKCU``), sem exigir
privilégios administrativos. O comando inclui ``--hidden`` para que o app
suba direto na bandeja.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, Protocol

from .. import APP_ID_WINDOWS

AUTOSTART_ARG = "--hidden"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class AutostartError(RuntimeError):
    """Falha ao consultar ou alterar a inicialização automática."""


class AutostartRegistry(Protocol):
    """Acesso mínimo ao registro usado para o autostart."""

    def read(self, value_name: str) -> Optional[str]: ...

    def write(self, value_name: str, value: str) -> None: ...

    def delete(self, value_name: str) -> None: ...


class WindowsRegistry:
    """Implementação real baseada em ``winreg`` (somente Windows)."""

    def read(self, value_name: str) -> Optional[str]:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE
        ) as key:
            value, _kind = winreg.QueryValueEx(key, value_name)
            return str(value)

    def write(self, value_name: str, value: str) -> None:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value)

    def delete(self, value_name: str) -> None:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, value_name)


def build_launch_argv(
    *,
    executable: Optional[str] = None,
    frozen: Optional[bool] = None,
    pythonw_path: Optional[str] = None,
) -> list[str]:
    """Monta o comando usado na entrada de inicialização do Windows."""
    exe = executable or sys.executable
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return [exe, AUTOSTART_ARG]

    interpreter = pythonw_path
    if interpreter is None:
        candidate = Path(exe).with_name("pythonw.exe")
        interpreter = str(candidate) if candidate.exists() else exe
    return [interpreter, "-m", "steam_free_games_monitor", AUTOSTART_ARG]


def start_hidden_requested(argv: Optional[list[str]] = None) -> bool:
    """Retorna True quando ``--hidden`` foi passado na linha de comando."""
    args = sys.argv[1:] if argv is None else argv
    return AUTOSTART_ARG in args


class WindowsAutostart:
    """Gerencia a entrada ``Run`` do usuário atual no Windows."""

    def __init__(
        self,
        registry: Optional[AutostartRegistry] = None,
        *,
        value_name: str = APP_ID_WINDOWS,
        command: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> None:
        self._platform = platform or sys.platform
        self._registry = registry
        self._value_name = value_name
        if command is None:
            command = subprocess.list2cmdline(
                build_launch_argv(executable=sys.executable)
            )
        self._command = command

    @property
    def supported(self) -> bool:
        return self._platform == "win32" and (
            self._registry is not None or self._platform == sys.platform
        )

    @property
    def command(self) -> str:
        return self._command

    def _backend(self) -> AutostartRegistry:
        if not self.supported:
            raise AutostartError(
                "Inicialização automática disponível apenas no Windows."
            )
        if self._registry is None:
            self._registry = WindowsRegistry()
        return self._registry

    def is_enabled(self) -> bool:
        if not self.supported:
            return False
        try:
            return bool(self._backend().read(self._value_name))
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise AutostartError(
                f"Não foi possível ler a inicialização automática: {exc}"
            ) from exc

    def refresh_command(self) -> bool:
        """Aponta uma entrada já existente para o executável atual."""
        if not self.supported:
            return False
        try:
            current = self._backend().read(self._value_name)
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise AutostartError(
                f"Não foi possível ler a inicialização automática: {exc}"
            ) from exc
        if not current or current == self._command:
            return False
        try:
            self._backend().write(self._value_name, self._command)
        except OSError as exc:
            raise AutostartError(
                f"Não foi possível atualizar a inicialização automática: {exc}"
            ) from exc
        return True

    def enable(self) -> None:
        try:
            self._backend().write(self._value_name, self._command)
        except OSError as exc:
            raise AutostartError(
                f"Não foi possível ativar a inicialização automática: {exc}"
            ) from exc

    def disable(self) -> None:
        try:
            self._backend().delete(self._value_name)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise AutostartError(
                f"Não foi possível desativar a inicialização automática: {exc}"
            ) from exc
