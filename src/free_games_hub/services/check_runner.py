"""Execução headless de uma rodada de verificação.

Extraída de ``ui/worker.py`` (que permanece até a paridade das interfaces).
O ``CheckRunner`` roda a verificação completa em uma thread própria, abrindo
sua própria conexão SQLite — mesma estratégia usada pelo ``CheckWorker`` do
PySide6, evitando as limitações de SQLite quanto a uso de conexão entre
threads.

O runner é agnóstico de interface: emite eventos por callbacks (``on_started``,
``on_finished``, ``on_failed``), o que permite usá-lo tanto pelo scheduler
headless da API quanto por qualquer shell futuro.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from ..models import CheckResult
from ..notifications.base import Notifier, NullNotifier
from ..notifications.service import NotificationService
from .feed_fetcher import FeedFetcher
from .monitor import MonitorService
from .price_checker import SteamPriceChecker
from .price_refresh import PriceRefreshService

logger = logging.getLogger(__name__)


class CheckRunner:
    """Roda uma verificação completa em uma thread, com conexão própria.

    Parâmetros:
    - ``db_path``: arquivo SQLite compartilhado; uma conexão é aberta por
      execução e fechada ao final.
    - ``fetcher``: busca de feeds (injetável em testes).
    - ``notifier``: backend de notificações; ``None`` usa ``NullNotifier``.
    - ``price_checker``: checker de preços Steam; ``None`` usa o padrão.
    - ``force_prices``: ignora o cache e reconsulta todos os preços recentes.

    Os callbacks recebem o ``CheckResult`` (``on_finished``) ou a mensagem
    de erro (``on_failed``) sempre na thread de execução — quem quiser
    publicar em outro loop (ex.: asyncio) deve fazer o *hop* no callback.
    """

    def __init__(
        self,
        db_path: Path,
        fetcher: FeedFetcher,
        notifier: Optional[Notifier | NullNotifier] = None,
        price_checker: Optional[SteamPriceChecker] = None,
        force_prices: bool = False,
        on_started: Optional[Callable[[], None]] = None,
        on_finished: Optional[Callable[[CheckResult], None]] = None,
        on_failed: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._db_path = db_path
        self._fetcher = fetcher
        self._notifier = notifier or NullNotifier()
        self._price_checker = price_checker
        self._force_prices = force_prices
        self._on_started = on_started
        self._on_finished = on_finished
        self._on_failed = on_failed

    def start(self) -> threading.Thread:
        """Inicia a verificação em uma thread nova e a retorna."""
        thread = threading.Thread(target=self._run, name="check-runner", daemon=True)
        thread.start()
        return thread

    def run_blocking(self) -> None:
        """Executa a verificação na thread atual (útil em testes)."""
        self._run()

    def _run(self) -> None:  # noqa: C901 - fluxo de erro explícito
        from ..database import connect_db, init_db

        if self._on_started is not None:
            self._on_started()

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
            if self._on_finished is not None:
                self._on_finished(result)
        except Exception as exc:  # noqa: BLE001 - nunca derrubar o aplicativo
            logger.exception("Falha na verificação")
            if self._on_failed is not None:
                self._on_failed(str(exc))
        finally:
            if conn is not None:
                conn.close()
