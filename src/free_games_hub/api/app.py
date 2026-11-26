"""Aplicação FastAPI local que alimenta o shell Electron.

``create_app`` monta o servidor com:

- rotas da API (``/health``, ``/api/*``, ``/ws``);
- scheduler headless de verificações periódicas;
- barramento de eventos (WebSocket) para atualizações em tempo real;
- serviço estático da SPA construída (produção) — mesma origem, sem CORS.

Em desenvolvimento (``python -m free_games_hub.api --dev``) o app roda sem
token e sem diretório de SPA, apenas com as rotas da API.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..bootstrap import ensure_defaults
from ..database import connect_db, init_db
from ..notifications import build_notifier
from ..services.feed_fetcher import UrlFeedFetcher
from ..services.price_checker import SteamPriceChecker
from ..services.scheduler import Scheduler
from .events import EventBus
from .routes import _store_last_check, router

logger = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    """Serve a SPA e devolve ``index.html`` para rotas do cliente.

    O app não usa roteador no cliente hoje, mas o fallback evita 404 caso uma
    rota seja adicionada no futuro. Caminhos de API nunca caem no fallback.
    """

    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # No Windows, ``StaticFiles.get_path`` normaliza para ``\``.
            normalized = path.replace("\\", "/").lstrip("/")
            is_api = (
                normalized == "api"
                or normalized.startswith("api/")
                or normalized == "ws"
                or normalized.startswith("ws/")
                or normalized == "health"
            )
            if exc.status_code == 404 and not is_api:
                return await super().get_response("index.html", scope)
            raise


def create_app(
    db_path: Path,
    *,
    token: Optional[str] = None,
    spa_dir: Optional[Path] = None,
    notifier: Optional[object] = None,
    scheduler_enabled: bool = True,
    dev_cors: bool = False,
    app_icon: Optional[Path] = None,
) -> FastAPI:
    """Cria a aplicação FastAPI com estado compartilhado no ``app.state``.

    ``dev_cors`` habilita o middleware CORS apenas em desenvolvimento,
    quando o renderer é servido pelo Vite (``localhost:5173``) e a API
    roda em outra porta. Em produção a SPA é servida pela própria API
    (mesma origem) e o middleware fica desativado.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Garante que o banco existe, está na versão atual e tem os padrões.
    conn = connect_db(db_path)
    init_db(conn)
    ensure_defaults(conn)
    conn.close()

    bus = EventBus()
    notifier = notifier if notifier is not None else build_notifier(
        on_error=lambda msg: logger.warning("notificador: %s", msg),
        app_icon_path=app_icon,
    )

    # O app é criado depois do scheduler; usa-se um holder para os callbacks.
    app_ref: dict = {}

    def _store_result(result) -> None:
        _store_last_check(app_ref["app"], result)

    def _store_failed(message: str) -> None:
        _store_last_check(app_ref["app"], None, message)

    scheduler = Scheduler(
        db_path,
        UrlFeedFetcher(),
        notifier=notifier,
        price_checker=SteamPriceChecker(),
        event_bus=bus,
        on_check_result=_store_result,
        on_check_failed=_store_failed,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if scheduler_enabled:
            await scheduler.start()
        logger.info(
            "API Free Games Hub v%s pronta (db=%s, token=%s)",
            __version__,
            db_path,
            "sim" if token else "desativado",
        )
        yield
        await scheduler.stop()
        logger.info("API encerrada")

    docs_enabled = token is None
    app = FastAPI(
        title="Free Games Hub API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app_ref["app"] = app
    app.state.db_path = db_path
    app.state.token = token
    app.state.bus = bus
    app.state.scheduler = scheduler
    app.state.notifier = notifier
    app.state.last_check = None

    app.include_router(router)

    # CORS apenas em desenvolvimento: o Vite serve o renderer em
    # ``localhost:5173`` (ou a próxima porta livre) e a API em outra porta.
    # Em produção, SPA e API compartilham a mesma origem — sem CORS.
    if dev_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # SPA construída (produção): servida na raiz, com fallback para index.html.
    if spa_dir is not None and Path(spa_dir).is_dir():
        app.mount(
            "/",
            SPAStaticFiles(directory=str(spa_dir), html=True),
            name="spa",
        )

    return app
