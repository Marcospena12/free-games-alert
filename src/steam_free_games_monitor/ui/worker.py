"""Execução da verificação fora da thread principal (QThreadPool)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ..models import CheckResult
from ..notifications.base import Notifier, NullNotifier
from ..notifications.service import NotificationService
from ..services.feed_fetcher import FeedFetcher
from ..services.monitor import MonitorService
from ..services.price_checker import SteamPriceChecker
from ..services.price_refresh import PriceRefreshService

logger = logging.getLogger(__name__)


class CheckSignals(QObject):
    started = Signal()
    finished = Signal(object)  # CheckResult
    failed = Signal(str)


class CheckWorker(QRunnable):
    """Roda uma verificação completa, abrindo sua própria conexão SQLite.

    Cada thread usa uma conexão própria para o mesmo arquivo de banco,
    evitando as limitações de SQLite quanto a uso de conexão entre threads.
    """

    def __init__(
        self,
        db_path: Path,
        fetcher: FeedFetcher,
        notifier: Optional[Notifier | NullNotifier] = None,
        price_checker: Optional[SteamPriceChecker] = None,
        force_prices: bool = False,
    ) -> None:
        super().__init__()
        self.signals = CheckSignals()
        self._db_path = db_path
        self._fetcher = fetcher
        self._notifier = notifier or NullNotifier()
        self._price_checker = price_checker
        self._force_prices = force_prices

    @Slot()
    def run(self) -> None:  # noqa: C901 - fluxo de erro explícito
        from ..database import connect_db, init_db

        self.signals.started.emit()
        conn = None
        try:
            conn = connect_db(self._db_path)
            init_db(conn)

            result: CheckResult = MonitorService(conn, self._fetcher).check_all()
            try:
                PriceRefreshService(conn, self._price_checker).refresh(
                    force=self._force_prices
                )
            except Exception:  # noqa: BLE001 - preço não pode derrubar a checagem
                logger.exception("Falha ao atualizar o status das ofertas")
            try:
                NotificationService(conn, self._notifier).process_pending()
            except Exception:  # noqa: BLE001 - notificação não derruba a checagem
                logger.exception("Falha ao processar notificações")
            self.signals.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - nunca derrubar o aplicativo
            self.signals.failed.emit(str(exc))
        finally:
            if conn is not None:
                conn.close()