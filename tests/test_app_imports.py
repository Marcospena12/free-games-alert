"""Garante que os módulos de entrada e da interface importam sem erros."""

from __future__ import annotations

import importlib

import pytest

MODULES = (
    "free_games_hub",
    "free_games_hub.app",
    "free_games_hub.__main__",
    "free_games_hub.services.autostart",
    "free_games_hub.services.price_checker",
    "free_games_hub.services.price_refresh",
    "free_games_hub.ui",
    "free_games_hub.ui.single_instance",
    "free_games_hub.ui.splash",
    "free_games_hub.ui.tray",
    "free_games_hub.ui.main_window",
    "free_games_hub.ui.window_theme",
    "free_games_hub.ui.controller",
    "free_games_hub.ui.views",
    "free_games_hub.ui.views.dashboard_view",
    "free_games_hub.ui.views.groups_view",
    "free_games_hub.ui.views.history_view",
    "free_games_hub.ui.views.settings_view",
)


@pytest.mark.parametrize("module_name", MODULES)
def test_import_module(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None
