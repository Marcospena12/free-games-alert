"""Serviço de download assíncrono e cache em disco de capas e banners de jogos."""

from __future__ import annotations

import hashlib
import logging
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QPixmap

from ..config import data_dir

logger = logging.getLogger(__name__)


def get_cover_url_for_post(post) -> Optional[str]:
    """Retorna a melhor URL de imagem disponível para a publicação."""
    if getattr(post, "image_url", None):
        return post.image_url
    if getattr(post, "store_app_id", None):
        # Arte oficial de cabeçalho da loja Steam
        return f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{post.store_app_id}/header.jpg"
    return None


class _ImageFetchSignals(QObject):
    loaded = Signal(str, object)  # (url, QPixmap)
    failed = Signal(str)


class _ImageFetchWorker(QRunnable):
    def __init__(self, url: str, cache_path: Path, signals: _ImageFetchSignals) -> None:
        super().__init__()
        self.url = url
        self.cache_path = cache_path
        self.signals = signals

    @Slot()
    def run(self) -> None:
        try:
            # Se não estiver em disco, faz o download com timeout curto
            if not self.cache_path.exists():
                req = urllib.request.Request(
                    self.url,
                    headers={"User-Agent": "FreeGamesHub/0.1 (+https://github.com/)"},
                )
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    if resp.status == 200:
                        content = resp.read()
                        self.cache_path.write_bytes(content)
                    else:
                        self.signals.failed.emit(self.url)
                        return

            pixmap = QPixmap()
            if pixmap.load(str(self.cache_path)):
                self.signals.loaded.emit(self.url, pixmap)
            else:
                self.signals.failed.emit(self.url)
        except Exception as exc:
            logger.debug("Falha ao baixar imagem %s: %s", self.url, exc)
            self.signals.failed.emit(self.url)


class CoverCacheService(QObject):
    """Gerencia o cache em memória e em disco das capas dos jogos."""

    cover_loaded = Signal(str, object)  # (url, QPixmap)

    def __init__(self, cache_dir: Optional[Path] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cache_dir = cache_dir or (data_dir() / "cache" / "covers")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, QPixmap] = {}
        self._pending: set[str] = set()
        self._failed: set[str] = set()
        self._pool = QThreadPool.globalInstance()

    def get_cached(self, url: Optional[str]) -> Optional[QPixmap]:
        """Retorna o QPixmap da memória se já estiver disponível."""
        if not url:
            return None
        return self._memory_cache.get(url)

    def request_cover(self, url: Optional[str]) -> Optional[QPixmap]:
        """Solicita a imagem. Retorna o QPixmap imediatamente se em cache, ou dispara o download."""
        if not url:
            return None

        # 1. Checa memória
        if url in self._memory_cache:
            return self._memory_cache[url]

        if url in self._failed:
            return None

        # 2. Checa disco
        cache_file = self._cache_path_for_url(url)
        if cache_file.exists():
            pixmap = QPixmap()
            if pixmap.load(str(cache_file)):
                self._memory_cache[url] = pixmap
                return pixmap

        # 3. Dispara em segundo plano se ainda não estiver pendente
        if url not in self._pending:
            self._pending.add(url)
            signals = _ImageFetchSignals()
            signals.loaded.connect(self._on_worker_loaded)
            signals.failed.connect(self._on_worker_failed)
            worker = _ImageFetchWorker(url, cache_file, signals)
            self._pool.start(worker)

        return None

    def _cache_path_for_url(self, url: str) -> Path:
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self._cache_dir / f"cover_{h}.jpg"

    def _on_worker_loaded(self, url: str, pixmap: QPixmap) -> None:
        self._pending.discard(url)
        self._memory_cache[url] = pixmap
        self.cover_loaded.emit(url, pixmap)

    def _on_worker_failed(self, url: str) -> None:
        self._pending.discard(url)
        self._failed.add(url)
