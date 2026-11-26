"""Rotas da API local.

Cada request abre a própria conexão SQLite (regra do core: conexão por
thread, nunca compartilhada). As operações de repositório são rápidas e
locais, então rodam inline no loop; o trabalho pesado (verificação de
feeds/preços) fica no ``Scheduler``/``CheckRunner`` em threads.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from typing import AsyncIterator, Optional

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .. import __version__
from ..config import data_dir
from ..database import (
    ErrorRepository,
    GroupRepository,
    PostRepository,
    SettingsRepository,
    connect_db,
    init_db,
)
from ..models import CheckResult
from ..services.filters import (
    SETTINGS_KEY_ENABLED_TYPES,
    SETTINGS_KEY_EXCLUDE_KEYWORDS,
    SETTINGS_KEY_GAMERPOWER_ENABLED,
    SETTINGS_KEY_IGNORE_NO_END_DATE,
    SETTINGS_KEY_INCLUDE_NA_WORTH,
    SETTINGS_KEY_MIN_WORTH,
    SETTINGS_KEY_STORE_FILTERS,
    StoreFilterConfig,
    StoreFilterService,
)
from ..services.scheduler import INTERVAL_KEY
from ..sources.stores import STORE_LABELS
from .auth import check_token, check_ws_token
from .serialization import _iso, error_to_dict, group_to_dict, post_to_dict

router = APIRouter()


def _db(request: Request):
    """Context manager de conexão por request."""
    return _db_session(request.app.state.db_path)


@contextmanager
def _db_session(db_path) -> AsyncIterator:
    conn = connect_db(db_path)
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def _authorized(request: Request) -> JSONResponse | None:
    return check_token(request, request.app.state.token)


def _last_check(app) -> Optional[dict]:
    return app.state.last_check


def _snapshot(conn, app=None) -> dict:
    posts = PostRepository(conn)
    groups = GroupRepository(conn)
    settings = SettingsRepository(conn)
    group_list = groups.list_all()
    last_checked = max(
        (g.last_checked_at for g in group_list if g.last_checked_at), default=None
    )
    if last_checked is None and app is not None:
        last_check = getattr(app.state, "last_check", None) or {}
        checked_at = last_check.get("at")
        if checked_at is not None:
            last_checked = datetime.fromtimestamp(float(checked_at))

    return {
        "free_now": posts.count_free_now(),
        "total_posts": posts.count(),
        "groups": {
            "total": len(group_list),
            "active": sum(1 for g in group_list if g.active),
        },
        "last_checked_at": _iso(last_checked),
        "settings": _settings_payload(settings),
        "stores_enabled": _enabled_stores(settings),
    }


def _enabled_stores(settings: SettingsRepository) -> list[str]:
    """Lojas habilitadas (config ``enabled_stores``; padrão das constantes)."""
    from ..sources.stores import DEFAULT_ENABLED_STORES

    raw = settings.get("enabled_stores")
    if not raw:
        return list(DEFAULT_ENABLED_STORES)
    try:
        values = json.loads(raw)
        if isinstance(values, list):
            return [str(v) for v in values]
    except (ValueError, TypeError):
        pass
    return list(DEFAULT_ENABLED_STORES)


def _settings_payload(settings: SettingsRepository) -> dict:
    """Configurações completas consumidas pela interface (visão única)."""
    filters = StoreFilterService(settings)
    store_filters = {
        slug: cfg.to_dict() for slug, cfg in filters.get_all_store_filters().items()
    }
    raw_keywords = settings.get(SETTINGS_KEY_EXCLUDE_KEYWORDS, "") or ""
    return {
        "check_interval_minutes": settings.get_int(INTERVAL_KEY, 5),
        "notifications_enabled": settings.get_bool("notifications_enabled", True),
        "close_to_tray": settings.get_bool("close_to_tray", True),
        "gamerpower_enabled": settings.get_bool(
            SETTINGS_KEY_GAMERPOWER_ENABLED, True
        ),
        "stores_enabled": _enabled_stores(settings),
        "enabled_types": filters.get_enabled_types(),
        "store_filters": store_filters,
        "filter_min_worth_usd": _float_or_none(settings.get(SETTINGS_KEY_MIN_WORTH)),
        "filter_include_na_worth": settings.get_bool(
            SETTINGS_KEY_INCLUDE_NA_WORTH, True
        ),
        "filter_ignore_no_end_date": settings.get_bool(
            SETTINGS_KEY_IGNORE_NO_END_DATE, False
        ),
        "filter_exclude_keywords": [
            item.strip()
            for item in raw_keywords.split(",")
            if item.strip()
        ],
    }


def _float_or_none(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_text(value: object) -> str:
    return "1" if bool(value) else "0"


def _apply_store_filters(
    settings: SettingsRepository, payload: dict
) -> None:
    """Atualiza filtros por loja de forma compatível com a UI legada."""
    filters = StoreFilterService(settings)
    configs = filters.get_all_store_filters()

    # Precedência: lista simples de lojas, tipos globais e, por fim, as
    # regras específicas de cada loja (o formato mais novo e detalhado).
    if "stores_enabled" in payload:
        stores = payload["stores_enabled"]
        if not isinstance(stores, list):
            raise HTTPException(
                status_code=400, detail="'stores_enabled' deve ser lista"
            )
        enabled = {str(slug) for slug in stores}
        for slug, config in configs.items():
            config.enabled = slug in enabled

    if "enabled_types" in payload:
        types = payload["enabled_types"]
        if not isinstance(types, list):
            raise HTTPException(
                status_code=400, detail="'enabled_types' deve ser lista"
            )
        allowed = {str(item) for item in types}
        for config in configs.values():
            config.allowed_types = set(allowed)
        settings.set(SETTINGS_KEY_ENABLED_TYPES, json.dumps(sorted(allowed)))

    raw_filters = payload.get("store_filters")
    if raw_filters is not None:
        if not isinstance(raw_filters, dict):
            raise HTTPException(status_code=400, detail="'store_filters' deve ser objeto")
        for slug, raw_config in raw_filters.items():
            if slug not in STORE_LABELS:
                continue
            if not isinstance(raw_config, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"filtro de '{slug}' deve ser objeto",
                )
            current = configs.get(slug, StoreFilterConfig())
            merged = current.to_dict()
            merged.update(raw_config)
            try:
                parsed = StoreFilterConfig.from_dict(merged)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"filtro de '{slug}' inválido",
                ) from None
            if parsed.min_worth_usd is not None and parsed.min_worth_usd < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"valor mínimo de '{slug}' não pode ser negativo",
                )
            configs[slug] = parsed

    filters.set_all_store_filters(configs)


def _app(request: Request):
    return request.app


@router.get("/health")
async def health(request: Request):
    denied = _authorized(request)
    if denied is not None:
        return denied
    return {"status": "ok"}


@router.get("/api/snapshot")
async def snapshot(request: Request):
    denied = _authorized(request)
    if denied is not None:
        return denied
    app = request.app
    with _db(request) as conn:
        data = _snapshot(conn, app)
    data["check_running"] = app.state.scheduler.is_check_running
    data["last_check"] = _last_check(app)
    return data


@router.get("/api/posts")
async def list_posts(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = Query(None),
    store: Optional[str] = Query(None),
    library: Optional[bool] = Query(None, alias="library"),
    active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    denied = _authorized(request)
    if denied is not None:
        return denied
    with _db(request) as conn:
        rows = PostRepository(conn).list_recent(
            limit=limit,
            status=status,
            in_library=library,
            store=store,
            active_only=bool(active),
            search=search,
        )
    return [post_to_dict(row["post"], row["group_name"]) for row in rows]


@router.patch("/api/posts/{post_id}")
async def patch_post(request: Request, post_id: int, payload: dict):
    denied = _authorized(request)
    if denied is not None:
        return denied
    if "in_library" not in payload:
        raise HTTPException(status_code=400, detail="campo 'in_library' obrigatório")
    in_library = bool(payload["in_library"])
    with _db(request) as conn:
        posts = PostRepository(conn)
        row = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="publicação não encontrada")
        posts.set_in_library(post_id, in_library)
        updated = conn.execute(
            """
            SELECT p.*, g.name AS group_name
            FROM posts p LEFT JOIN groups g ON g.id = p.group_id
            WHERE p.id = ?
            """,
            (post_id,),
        ).fetchone()
        post = posts._row_to_post(updated)
        group_name = updated["group_name"]
        if not group_name:
            group_name = "GamerPower" if post.source == "gamerpower" else "Global"
        result = post_to_dict(post, group_name)
    await request.app.state.bus.publish(
        {"type": "posts.updated", "data": {"updated": [result]}}
    )
    return result


@router.get("/api/groups")
async def list_groups(request: Request):
    denied = _authorized(request)
    if denied is not None:
        return denied
    with _db(request) as conn:
        groups = GroupRepository(conn).list_all()
    return [group_to_dict(g) for g in groups]


@router.post("/api/groups")
async def create_group(request: Request, payload: dict):
    denied = _authorized(request)
    if denied is not None:
        return denied
    name = (payload.get("name") or "").strip()
    url = (payload.get("url") or "").strip()
    if not name or not url:
        raise HTTPException(status_code=400, detail="'name' e 'url' são obrigatórios")
    with _db(request) as conn:
        groups = GroupRepository(conn)
        group_id = groups.add(name, url, active=payload.get("active", True))
        group = groups.get(group_id)
    result = group_to_dict(group)
    await request.app.state.bus.publish(
        {"type": "groups.updated", "data": {"updated": [result]}}
    )
    return result


@router.put("/api/groups/{group_id}")
async def update_group(request: Request, group_id: int, payload: dict):
    denied = _authorized(request)
    if denied is not None:
        return denied
    with _db(request) as conn:
        groups = GroupRepository(conn)
        existing = groups.get(group_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="grupo não encontrado")
        name = (payload.get("name") or existing.name).strip()
        url = (payload.get("url") or existing.url).strip()
        active = bool(payload.get("active", existing.active))
        if not name or not url:
            raise HTTPException(status_code=400, detail="'name' e 'url' são obrigatórios")
        groups.update(group_id, name, url, active)
        group = groups.get(group_id)
    result = group_to_dict(group)
    await request.app.state.bus.publish(
        {"type": "groups.updated", "data": {"updated": [result]}}
    )
    return result


@router.delete("/api/groups/{group_id}")
async def delete_group(request: Request, group_id: int):
    denied = _authorized(request)
    if denied is not None:
        return denied
    with _db(request) as conn:
        groups = GroupRepository(conn)
        if groups.get(group_id) is None:
            raise HTTPException(status_code=404, detail="grupo não encontrado")
        groups.delete(group_id)
    await request.app.state.bus.publish(
        {"type": "groups.updated", "data": {"removed": [group_id]}}
    )
    return {"ok": True}


@router.get("/api/settings")
async def get_settings(request: Request):
    denied = _authorized(request)
    if denied is not None:
        return denied
    with _db(request) as conn:
        return _settings_payload(SettingsRepository(conn))


@router.put("/api/settings")
async def put_settings(request: Request, payload: dict):
    denied = _authorized(request)
    if denied is not None:
        return denied

    updated: dict = {}
    with _db(request) as conn:
        settings = SettingsRepository(conn)
        if "check_interval_minutes" in payload:
            try:
                minutes = int(payload["check_interval_minutes"])
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="'check_interval_minutes' deve ser inteiro",
                ) from None
            if minutes < 1:
                raise HTTPException(status_code=400, detail="intervalo mínimo: 1 minuto")
            settings.set(INTERVAL_KEY, str(minutes))

        for key in (
            "notifications_enabled",
            "close_to_tray",
            SETTINGS_KEY_GAMERPOWER_ENABLED,
            SETTINGS_KEY_INCLUDE_NA_WORTH,
            SETTINGS_KEY_IGNORE_NO_END_DATE,
        ):
            if key in payload:
                settings.set(key, _bool_text(payload[key]))

        if SETTINGS_KEY_MIN_WORTH in payload:
            raw_min = payload[SETTINGS_KEY_MIN_WORTH]
            if raw_min is None:
                settings.set(SETTINGS_KEY_MIN_WORTH, "")
            else:
                try:
                    minimum = float(raw_min)
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail=f"'{SETTINGS_KEY_MIN_WORTH}' deve ser número",
                    ) from None
                if minimum < 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"'{SETTINGS_KEY_MIN_WORTH}' não pode ser negativo",
                    )
                settings.set(SETTINGS_KEY_MIN_WORTH, str(minimum))

        if SETTINGS_KEY_EXCLUDE_KEYWORDS in payload:
            raw_keywords = payload[SETTINGS_KEY_EXCLUDE_KEYWORDS]
            if isinstance(raw_keywords, list):
                keywords = [str(item).strip() for item in raw_keywords if str(item).strip()]
            elif isinstance(raw_keywords, str):
                keywords = [item.strip() for item in raw_keywords.split(",") if item.strip()]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{SETTINGS_KEY_EXCLUDE_KEYWORDS}' deve ser lista",
                )
            settings.set(SETTINGS_KEY_EXCLUDE_KEYWORDS, ", ".join(keywords))

        if any(
            key in payload
            for key in (
                SETTINGS_KEY_STORE_FILTERS,
                "stores_enabled",
                SETTINGS_KEY_ENABLED_TYPES,
            )
        ):
            _apply_store_filters(settings, payload)

        updated = _settings_payload(settings)

    await request.app.state.bus.publish(
        {"type": "settings.updated", "data": {"settings": updated}}
    )
    return updated


@router.get("/api/stores")
async def list_stores(request: Request):
    denied = _authorized(request)
    if denied is not None:
        return denied
    with _db(request) as conn:
        payload = _settings_payload(SettingsRepository(conn))
    filters = payload["store_filters"]
    return [
        {
            "id": key,
            "label": label,
            **filters.get(key, {"enabled": False}),
        }
        for key, label in STORE_LABELS.items()
    ]


@router.get("/api/errors")
async def list_errors(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
):
    denied = _authorized(request)
    if denied is not None:
        return denied
    with _db(request) as conn:
        groups = {g.id: g.name for g in GroupRepository(conn).list_all()}
        rows = ErrorRepository(conn).recent(limit=limit)
    return [error_to_dict(e, groups.get(e.group_id)) for e in rows]


@router.get("/api/about")
async def about(request: Request):
    denied = _authorized(request)
    if denied is not None:
        return denied
    from ..logging_setup import log_path

    db_path = request.app.state.db_path
    return {
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "data_dir": str(data_dir()),
        "db_path": str(db_path),
        "db_size_bytes": db_path.stat().st_size if db_path.exists() else 0,
        "log_path": str(log_path()),
    }


@router.post("/api/check")
async def trigger_check(request: Request, payload: dict | None = None):
    denied = _authorized(request)
    if denied is not None:
        return denied
    force_prices = bool((payload or {}).get("force_prices", False))
    started = await request.app.state.scheduler.run_now(force_prices=force_prices)
    if not started:
        raise HTTPException(status_code=409, detail="verificação já em andamento")
    return {"ok": True, "started": True}


@router.post("/api/notifications/test")
async def test_notification(request: Request):
    denied = _authorized(request)
    if denied is not None:
        return denied
    notifier = request.app.state.notifier
    notifier.notify(
        title="Free Games Hub",
        message="Notificação de teste: tudo funcionando.",
        open_url=None,
    )
    return {"ok": True}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    app = websocket.app
    if not check_ws_token(websocket, app.state.token):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    queue = app.state.bus.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        app.state.bus.unsubscribe(queue)


def _store_last_check(app, result: CheckResult | None, failed: str | None = None) -> None:
    """Atualiza o último resultado em memória (exposto no snapshot)."""
    import time

    if result is not None:
        app.state.last_check = {
            "at": time.time(),
            "new_posts": result.new_posts,
            "errors": result.errors,
            "checked_groups": result.checked_groups,
            "failed_groups": result.failed_groups,
        }
    elif failed is not None:
        app.state.last_check = {"at": time.time(), "failed": failed}


