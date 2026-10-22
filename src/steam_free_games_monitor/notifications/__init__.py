"""Camada de notificações do sistema operacional."""

from .service import NotificationService
from .base import Notifier, NullNotifier
from .backend import DesktopNotifierBackend, build_notifier

__all__ = [
    "NotificationService",
    "Notifier",
    "NullNotifier",
    "DesktopNotifierBackend",
    "build_notifier",
]