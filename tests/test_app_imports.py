"""Garante que os módulos de entrada e da interface importam sem erros."""

from __future__ import annotations

import importlib

import pytest

MODULES = (
    "steam_free_games_monitor",
    "steam_free_games_monitor.app",
    "steam_free_games_monitor.__main__",
    "steam_free_games_monitor.services.autostart",
    "steam_free_games_monitor.services.price_checker",
    "steam_free_games_monitor.services.price_refresh",
    "steam_free_games_monitor.ui",
    "steam_free_games_monitor.ui.single_instance",
    "steam_free_games_monitor.ui.tray",
    "steam_free_games_monitor.ui.main_window",
    "steam_free_games_monitor.ui.controller",
    "steam_free_games_monitor.ui.views",
    "steam_free_games_monitor.ui.views.dashboard_view",
    "steam_free_games_monitor.ui.views.groups_view",
    "steam_free_games_monitor.ui.views.history_view",
    "steam_free_games_monitor.ui.views.settings_view",
)


@pytest.mark.parametrize("module_name", MODULES)
def test_import_module(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None
