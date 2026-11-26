"""Autenticação por token para a API local.

O backend sempre escuta em ``127.0.0.1``. Em modo produção (Electron) um
token aleatório é gerado a cada inicialização e o shell o passa ao
renderer; requisições sem o token são rejeitadas com 401.

Em modo desenvolvimento (sem token) só são aceitas requisições vindas do
loopback, o que evita expor a API a outras máquinas da rede local.
"""

from __future__ import annotations

import secrets

from fastapi import Request, WebSocket
from fastapi.responses import JSONResponse

TOKEN_HEADER = "X-FGH-Token"
TOKEN_QUERY = "token"

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _is_loopback(request: Request) -> bool:
    host = (request.client.host or "") if request.client else ""
    return host in _LOOPBACK_HOSTS


def check_token(request: Request, expected: str | None) -> JSONResponse | None:
    """Retorna uma resposta 401/403 quando o acesso deve ser negado."""
    if expected is None:
        # Modo dev: apenas loopback.
        if not _is_loopback(request):
            return JSONResponse({"detail": "acesso negado"}, status_code=403)
        return None
    provided = request.headers.get(TOKEN_HEADER) or request.query_params.get(TOKEN_QUERY)
    if provided is None or not secrets.compare_digest(provided, expected):
        return JSONResponse({"detail": "token inválido"}, status_code=401)
    return None


def check_ws_token(websocket: WebSocket, expected: str | None) -> bool:
    """Valida o token na query string do WebSocket (headers não chegam no upgrade)."""
    if expected is None:
        return websocket.client.host in _LOOPBACK_HOSTS if websocket.client else False
    provided = websocket.query_params.get(TOKEN_QUERY)
    return provided is not None and secrets.compare_digest(provided, expected)
