"""Testes do serviço de inicialização automática com o Windows."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from steam_free_games_monitor.services.autostart import (
    AUTOSTART_ARG,
    AutostartError,
    WindowsAutostart,
    build_launch_argv,
    start_hidden_requested,
)


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def read(self, value_name: str) -> Optional[str]:
        return self.values.get(value_name)

    def write(self, value_name: str, value: str) -> None:
        self.values[value_name] = value

    def delete(self, value_name: str) -> None:
        if value_name not in self.values:
            raise FileNotFoundError(value_name)
        del self.values[value_name]


class FailingRegistry(FakeRegistry):
    def read(self, value_name: str) -> Optional[str]:
        raise OSError("acesso negado")


def test_comando_usa_pythonw_no_modo_fonte() -> None:
    argv = build_launch_argv(
        executable=r"C:\venv\Scripts\python.exe",
        frozen=False,
        pythonw_path=r"C:\venv\Scripts\pythonw.exe",
    )

    assert argv == [
        r"C:\venv\Scripts\pythonw.exe",
        "-m",
        "steam_free_games_monitor",
        AUTOSTART_ARG,
    ]


def test_comando_usa_executavel_quando_congelado() -> None:
    argv = build_launch_argv(
        executable=r"C:\Apps\SteamFreeGamesMonitor.exe",
        frozen=True,
    )

    assert argv == [r"C:\Apps\SteamFreeGamesMonitor.exe", AUTOSTART_ARG]


def test_comando_cai_para_python_quando_pythonw_nao_existe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "exists", lambda _self: False)

    argv = build_launch_argv(
        executable=r"C:\venv\Scripts\python.exe",
        frozen=False,
    )

    assert argv[0] == r"C:\venv\Scripts\python.exe"
    assert argv[1:] == ["-m", "steam_free_games_monitor", AUTOSTART_ARG]


def test_detecta_argumento_hidden() -> None:
    assert start_hidden_requested(["--hidden"]) is True
    assert start_hidden_requested(["--outro"]) is False
    assert start_hidden_requested([]) is False


def test_habilitar_e_desabilitar_com_registro_falso() -> None:
    registry = FakeRegistry()
    manager = WindowsAutostart(
        registry,
        value_name="Teste",
        command="comando --hidden",
        platform="win32",
    )

    assert manager.supported is True
    assert manager.is_enabled() is False

    manager.enable()
    assert registry.values["Teste"] == "comando --hidden"
    assert manager.is_enabled() is True

    manager.disable()
    assert registry.values == {}
    assert manager.is_enabled() is False

    manager.disable()


def test_atualiza_comando_de_entrada_existente() -> None:
    registry = FakeRegistry()
    registry.values["Teste"] = "comando antigo"
    manager = WindowsAutostart(
        registry,
        value_name="Teste",
        command="comando novo",
        platform="win32",
    )

    assert manager.refresh_command() is True
    assert registry.values["Teste"] == "comando novo"
    assert manager.refresh_command() is False


def test_nao_cria_entrada_ausente_ao_atualizar_comando() -> None:
    registry = FakeRegistry()
    manager = WindowsAutostart(
        registry,
        value_name="Teste",
        command="comando novo",
        platform="win32",
    )

    assert manager.refresh_command() is False
    assert registry.values == {}


def test_desabilitado_fora_do_windows() -> None:
    manager = WindowsAutostart(
        FakeRegistry(),
        value_name="Teste",
        command="comando",
        platform="linux",
    )

    assert manager.supported is False
    assert manager.is_enabled() is False
    with pytest.raises(AutostartError):
        manager.enable()


def test_erro_de_leitura_vira_autostart_error() -> None:
    manager = WindowsAutostart(
        FailingRegistry(),
        value_name="Teste",
        command="comando",
        platform="win32",
    )

    with pytest.raises(AutostartError):
        manager.is_enabled()
