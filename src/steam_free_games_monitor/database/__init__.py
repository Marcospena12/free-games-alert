"""Camada de persistência (banco de dados direto com sqlite3)."""

from .connection import connect_db, init_db
from .repositories import ErrorRepository, GroupRepository, PostRepository, SettingsRepository

__all__ = [
    "connect_db",
    "init_db",
    "ErrorRepository",
    "GroupRepository",
    "PostRepository",
    "SettingsRepository",
]