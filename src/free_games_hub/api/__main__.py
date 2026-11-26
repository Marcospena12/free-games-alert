"""Ponto de entrada da API local.

Uso:

- desenvolvimento::

      python -m free_games_hub.api --dev

- produção (iniciado pelo shell Electron)::

      python -m free_games_hub.api --port 48213 --token <token> --spa-dir <dir>

Quando ``--port 0`` é usado, a porta efetiva é impressa na primeira linha
de saída como ``FGH_PORT=<n>`` para o processo pai (Electron) capturar.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .. import __version__
from ..config import database_path
from ..logging_setup import configure_logging
from .app import create_app


def _resolve_spa_dir(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.is_dir() else None
    # Produção empacotada: o Electron passa o diretório explicitamente.
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="free_games_hub.api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 = porta aleatória")
    parser.add_argument("--token", default=None, help="token de autenticação")
    parser.add_argument("--db", default=None, help="caminho do banco (padrão: dados do usuário)")
    parser.add_argument("--spa-dir", default=None, help="diretório da SPA construída")
    parser.add_argument("--dev", action="store_true", help="modo desenvolvimento (sem token)")
    parser.add_argument("--no-scheduler", action="store_true", help="não iniciar agendador")
    parser.add_argument("--app-icon", default=None, help="ícone das notificações")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    log_file = configure_logging()
    logger = logging.getLogger(__name__)
    logger.info(
        "Free Games Hub API %s iniciando (log=%s)", __version__, log_file or "stderr"
    )

    token = None if args.dev else args.token
    db_path = Path(args.db) if args.db else database_path()
    app_icon = Path(args.app_icon) if args.app_icon else None
    if app_icon is not None and not app_icon.is_file():
        logger.warning("Ícone de notificação não encontrado: %s", app_icon)
        app_icon = None
    app = create_app(
        db_path,
        token=token,
        spa_dir=_resolve_spa_dir(args.spa_dir),
        scheduler_enabled=not args.no_scheduler,
        dev_cors=args.dev,
        app_icon=app_icon,
    )

    import socket

    import uvicorn

    # Pré-ligamos o socket para descobrir a porta efetiva antes de o
    # servidor bloquear. O socket é entregue ao uvicorn, que o reutiliza.
    bind_sock = socket.socket()
    bind_sock.bind((args.host, args.port))
    bind_sock.listen(128)
    bind_sock.set_inheritable(True)
    actual_port = bind_sock.getsockname()[1]

    if args.port == 0:
        # Impresso antes de rodar o servidor (que bloqueia), para o processo
        # pai (Electron) descobrir a porta.
        print(f"FGH_PORT={actual_port}", flush=True)

    config = uvicorn.Config(
        app,
        host=args.host,
        port=actual_port,
        log_level="warning",
        log_config=None,
        access_log=False,
        lifespan="on",
    )
    server = uvicorn.Server(config)
    # ``run`` aplica os handlers de sinal (SIGINT/SIGTERM/SIGBREAK)
    # internamente e roda até o shutdown.
    server.run(sockets=[bind_sock])
    return 0


if __name__ == "__main__":
    sys.exit(main())
