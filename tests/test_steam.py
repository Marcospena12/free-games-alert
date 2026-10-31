"""Testes da integração com o cliente desktop da Steam e URLs steam://."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from free_games_hub.services.steam import (
    get_steam_protocol_url,
    is_steam_running,
    resolve_game_open_target,
)


class TestSteamProtocolUrl:
    def test_com_app_id_direto(self):
        assert get_steam_protocol_url(app_id=730) == "steam://store/730"

    def test_com_store_url_padrao(self):
        url = "https://store.steampowered.com/app/2990600/Fireside_Feelings/"
        assert get_steam_protocol_url(url=url) == "steam://store/2990600"

    def test_com_store_url_sub(self):
        url = "https://store.steampowered.com/sub/12345/"
        assert get_steam_protocol_url(url=url) == "steam://openurl/https://store.steampowered.com/sub/12345/"

    def test_com_community_url(self):
        url = "https://steamcommunity.com/groups/jogosbra/announcements/detail/123"
        assert get_steam_protocol_url(url=url) == f"steam://openurl/{url}"

    def test_url_externa_retorna_none(self):
        assert get_steam_protocol_url(url="https://epicgames.com/store") is None

    def test_url_vazia_retorna_none(self):
        assert get_steam_protocol_url(url=None, app_id=None) is None
        assert get_steam_protocol_url(url="", app_id=None) is None


class TestIsSteamRunning:
    def test_windows_steam_running_mock(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        with patch("free_games_hub.services.steam._is_steam_running_win", return_value=True):
            assert is_steam_running() is True

    def test_windows_steam_not_running_mock(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        with patch("free_games_hub.services.steam._is_steam_running_win", return_value=False):
            assert is_steam_running() is False

    def test_linux_steam_running_mock(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        with patch("free_games_hub.services.steam._is_steam_running_linux", return_value=True):
            assert is_steam_running() is True

    def test_linux_steam_not_running_mock(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        with patch("free_games_hub.services.steam._is_steam_running_linux", return_value=False):
            assert is_steam_running() is False

    def test_outro_sistema_retorna_false(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        assert is_steam_running() is False


class TestResolveGameOpenTarget:
    def test_steam_aberta_direciona_para_steam_protocol(self):
        with patch("free_games_hub.services.steam.is_steam_running", return_value=True):
            target, is_steam = resolve_game_open_target(
                url="https://store.steampowered.com/app/730/CS2/",
                app_id=730,
            )
            assert is_steam is True
            assert target == "steam://store/730"

    def test_steam_fechada_direciona_para_navegador(self):
        with patch("free_games_hub.services.steam.is_steam_running", return_value=False):
            url = "https://store.steampowered.com/app/730/CS2/"
            target, is_steam = resolve_game_open_target(url=url, app_id=730)
            assert is_steam is False
            assert target == url

    def test_prefer_steam_false_retorna_url_web(self):
        with patch("free_games_hub.services.steam.is_steam_running", return_value=True):
            url = "https://store.steampowered.com/app/730/CS2/"
            target, is_steam = resolve_game_open_target(
                url=url, app_id=730, prefer_steam=False
            )
            assert is_steam is False
            assert target == url
