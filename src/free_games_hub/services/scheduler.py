"""Agendador headless de verificações (substitui o QTimer do PySide6).

O ``Scheduler`` roda em um loop asyncio (o mesmo da API FastAPI) e agenda
verificações periódicas usando o ``CheckRunner`` em threads. O intervalo é
lido do banco a cada ciclo (chave ``check_interval_minutes``), então mudar a
configuração na interface reflete na próxima rodada sem reiniciar o app.

Proteção contra execuções concorrentes é a mesma do ``MonitorController``:
uma verificação manual solicitada enquanto outra está em andamento é
ignorada (``run_now`` retorna ``False``).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

from ..config import DEFAULT_CHECK_INTERVAL_MINUTES, database_path
from ..database import connect_db, init_db
from ..database.repositories import SettingsRepository
from ..models import CheckResult
from ..notifications.base import Notifier, NullNotifier
from .check_runner import CheckRunner
from .feed_fetcher import FeedFetcher
from .price_checker import SteamPriceChecker

logger = logging.getLogger(__name__)

INTERVAL_KEY = "check_interval_minutes"
MIN_INTERVAL_MINUTES = 1


def _read_interval_minutes(db_path: Path) -> int:
    """Lê o intervalo configurado, com saneamento (mínimo de 1 minuto)."""
    conn = None
    try:
        conn = connect_db(db_path)
        init_db(conn)
        minutes = SettingsRepository(conn).get_int(
            INTERVAL_KEY, DEFAULT_CHECK_INTERVAL_MINUTES
        )
    except Exception:  # noqa: BLE001 - banco indisponível não para o scheduler
        logger.exception("Falha ao ler o intervalo de verificação")
        return DEFAULT_CHECK_INTERVAL_MINUTES
    finally:
        if conn is not None:
            conn.close()
    return max(MIN_INTERVAL_MINUTES, minutes)


class Scheduler:
    """Agenda e executa verificações periódicas em um loop asyncio."""

    def __init__(
        self,
        db_path: Path,
        fetcher: FeedFetcher,
        notifier: Optional[Notifier | NullNotifier] = None,
        price_checker: Optional[SteamPriceChecker] = None,
        event_bus: Optional[object] = None,
        on_check_result: Optional[Callable[[CheckResult], None]] = None,
        on_check_failed: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._db_path = db_path
        self._fetcher = fetcher
        self._notifier = notifier
        self._price_checker = price_checker
        self._bus = event_bus
        self._on_check_result = on_check_result
        self._on_check_failed = on_check_failed
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None
        self._running_check = False
        self._stopping = False

    @property
    def is_check_running(self) -> bool:
        return self._running_check

    async def start(self) -> None:
        """Inicia o loop de agendamento. Seguro chamar mais de uma vez."""
        if self._task is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._stopping = False
        self._task = asyncio.create_task(self._loop_forever(), name="scheduler")

    async def stop(self) -> None:
        """Encerra o loop. Verificação em andamento termina de forma natural."""
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    async def run_now(self, force_prices: bool = False) -> bool:
        """Solicita uma verificação imediata.

        Retorna ``False`` quando já há uma verificação em andamento
        (solicitação ignorada, mesma regra da interface antiga).
        """
        if self._running_check:
            return False
        self._running_check = True
        try:
            runner = CheckRunner(
                self._db_path,
                self._fetcher,
                notifier=self._notifier,
                price_checker=self._price_checker,
                force_prices=force_prices,
                on_started=self._on_started,
                on_finished=self._on_finished,
                on_failed=self._on_failed,
            )
            await asyncio.to_thread(runner.run_blocking)
        finally:
            self._running_check = False
        return True

    async def _loop_forever(self) -> None:
        while not self._stopping:
            interval = _read_interval_minutes(self._db_path)
            try:
                await self.run_now()
            except Exception:  # noqa: BLE001 - o loop nunca deve morrer
                logger.exception("Falha agendada na verificação")
            try:
                await asyncio.sleep(interval * 60)
            except asyncio.CancelledError:
                raise

    # -- callbacks do CheckRunner (rodam em thread; fazem o hop para o loop) --

    def _publish(self, event: dict) -> None:
        if self._bus is None or self._loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._bus.publish(event), self._loop)
        except Exception:  # noqa: BLE001 - publicar não pode derrubar o check
            logger.exception("Falha ao publicar evento")

    def _on_started(self) -> None:
        self._publish({"type": "check.started", "data": {}})

    def _on_finished(self, result: CheckResult) -> None:
        self._publish(
            {
                "type": "check.finished",
                "data": {
                    "new_posts": result.new_posts,
                    "errors": result.errors,
                    "checked_groups": result.checked_groups,
                    "failed_groups": result.failed_groups,
                },
            }
        )
        if self._on_check_result is not None:
            try:
                self._on_check_result(result)
            except Exception:  # noqa: BLE001 - callback extra não derruba o check
                logger.exception("Falha no callback de resultado de verificação")

    def _on_failed(self, message: str) -> None:
        self._publish({"type": "check.failed", "data": {"message": message}})
        if self._on_check_failed is not None:
            try:
                self._on_check_failed(message)
            except Exception:  # noqa: BLE001 - callback extra não derruba o check
                logger.exception("Falha no callback de falha de verificação")
