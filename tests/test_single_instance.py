"""Testes das mensagens de instância única."""

from __future__ import annotations

from typing import Any

from steam_free_games_monitor.ui.single_instance import SingleInstance


class FakeSocket:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def readAll(self) -> bytes:
        return self._data


def _instance() -> SingleInstance:
    return SingleInstance("SteamFreeGamesMonitorTest")


def test_mensagem_show_emite_ativacao() -> None:
    guard = _instance()
    calls: list[Any] = []
    guard.activation_requested.connect(lambda: calls.append("show"))

    guard._on_ready_read(FakeSocket(b"show"))  # type: ignore[arg-type]

    assert calls == ["show"]


def test_mensagem_quit_emite_encerramento() -> None:
    guard = _instance()
    calls: list[Any] = []
    guard.quit_requested.connect(lambda: calls.append("quit"))

    guard._on_ready_read(FakeSocket(b"quit"))  # type: ignore[arg-type]

    assert calls == ["quit"]


def test_mensagem_desconhecida_e_ignorada() -> None:
    guard = _instance()
    calls: list[Any] = []
    guard.activation_requested.connect(lambda: calls.append("show"))
    guard.quit_requested.connect(lambda: calls.append("quit"))

    guard._on_ready_read(FakeSocket(b"noop"))  # type: ignore[arg-type]

    assert calls == []
