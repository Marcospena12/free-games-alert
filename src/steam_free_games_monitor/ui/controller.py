"""Controlador do monitoramento para a interface.

Agenda verificações periódicas com QTimer, executa cada verificação em um
QThreadPool (fora da thread da GUI) e protege contra execuções concorrentes:
uma verificação manual solicitada enquanto outra está em andamento é ignorada.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal

from ..database.repositories import SettingsRepository
from ..models import CheckResult
from ..notifications.base import Notifier, NullNotifier
from ..services.feed_fetcher import FeedFetcher
from ..services.price_checker import SteamPriceChecker
from .worker import CheckWorker

INTERVAL_KEY = "check_interval_minutes"


class MonitorController(QObject):
    check_started = Signal()
    check_finished = Signal(object)  # CheckResult
    check_failed = Signal(str)

    def __init__(
        self,
        db_path: Path,
        fetcher: FeedFetcher,
        notifier: Notifier | NullNotifier,
        settings_repo: SettingsRepository,
        price_checker: SteamPriceChecker | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db_path = db_path
        self._fetcher = fetcher
        self._notifier = notifier
        self._settings = settings_repo
        self._price_checker = price_checker
        self._pool = QThreadPool.globalInstance()
        self._current: CheckWorker | None = None
        self._running = False
        self.last_result: CheckResult | None = None
        self.last_error: str | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.trigger_check)
        self.interval_minutes = settings_repo.get_int(INTERVAL_KEY, 5)

    @property
    def interval_minutes(self) -> int:
        return self._interval_minutes

    @interval_minutes.setter
    def interval_minutes(self, value: int) -> None:
        self._interval_minutes = max(1, value)
        self._timer.start(self._interval_minutes * 60_000)

    @property
    def is_running(self) -> bool:
        return self._running

    def trigger_check(self, force_prices: bool = False) -> None:
        """Inicia uma verificação.

        Se uma verificação já estiver em andamento, a solicitação é ignorada
        (evita condições de corrida entre a verificação automática e a manual).
        ``force_prices`` ignora o cache e reconsulta todos os preços recentes.
        """
        if self._running:
            return
        self._running = True
        self._current = CheckWorker(
            self._db_path,
            self._fetcher,
            self._notifier,
            price_checker=self._price_checker,
            force_prices=force_prices,
        )
        self._current.signals.started.connect(self.check_started.emit)
        self._current.signals.finished.connect(self._on_finished)
        self._current.signals.failed.connect(self._on_failed)
        self._pool.start(self._current)

    def _on_finished(self, result: CheckResult) -> None:
        self.last_result = result
        self.last_error = None
        self._running = False
        self.check_finished.emit(result)

    def _on_failed(self, message: str) -> None:
        self.last_error = message
        self._running = False
        self.check_failed.emit(message)

    def persist_interval(self) -> None:
        """Grava o intervalo atual nas configurações."""
        self._settings.set(INTERVAL_KEY, str(self._interval_minutes))

    def test_notification(self) -> None:
        """Envia uma notificação de teste, propagando falhas para a interface."""
        self._notifier.notify(
            title="Steam Free Games Monitor",
            message="Notificações funcionando!",
            open_url=None,
        )

    def shutdown(self) -> None:
        """Para o agendamento e aguarda uma verificação em andamento."""
        self._timer.stop()
        self._pool.waitForDone(5000)