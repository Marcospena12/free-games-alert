"""Barramento de eventos para broadcast em WebSocket.

Cada cliente WebSocket recebe uma fila própria. Publicação é não
bloqueante: clientes lentos (fila cheia) são descartados, nunca
bloqueando o scheduler nem o loop principal.
"""

from __future__ import annotations

import asyncio
from typing import Any

MAX_QUEUED_PER_CLIENT = 256


class EventBus:
    """Broadcast de eventos para clientes WebSocket."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUED_PER_CLIENT)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    @property
    def client_count(self) -> int:
        return len(self._subscribers)

    async def publish(self, event: dict[str, Any]) -> None:
        """Envia o evento a todos os clientes sem bloquear."""
        if not self._subscribers:
            return
        slow: list[asyncio.Queue] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                slow.append(queue)
        for queue in slow:
            self._subscribers.discard(queue)
