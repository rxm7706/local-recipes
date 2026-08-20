"""
ASGI config for Python Agent Platform project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/asgi/

"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

# This allows easy placement of apps within the interior
# platformapp directory.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(BASE_DIR / "platformapp"))

# If DJANGO_SETTINGS_MODULE is unset, default to the local settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# This application object is used by any ASGI server configured to use this file.
django_application = get_asgi_application()

# Import websocket application here, so apps from django_application are loaded first
# FastAPI seam (Story 10.1): owns the whole /api/ namespace except /api/v1/,
# which Story 11.1 routes to Langflow's own app instead (see below). Epic 11
# also attaches DB-GPT's /api/dbgpt/ mount; this module never builds either.
from config.fastapi_app import fastapi_application  # noqa: E402
from config.websocket import websocket_application  # noqa: E402

# Story 11.1 (spec-python-agent-platform CAP-2, AD-14 Pattern A): Langflow's
# own FastAPI app, built once at import time. Imported only after Django's
# settings have executed (via django_application above), which is what
# exports the derived LANGFLOW_DATABASE_URL/LANGFLOW_CACHE_TYPE/... env vars
# langflow_integration.asgi's create_app() call reads.
from langflow_integration.asgi import langflow_application  # noqa: E402

# I/O & Edge-Case Matrix (spec-11-1): these three routes match Langflow's own
# native route prefixes, so they forward with the ASGI scope UNCHANGED --
# no path rewriting, unlike the /langflow/ prefix-strip below.
_LANGFLOW_BARE_HEALTH_PATHS = frozenset({"/health", "/health_check"})


def _is_langflow_api_v1_path(path: str) -> bool:
    return path == "/api/v1" or path.startswith("/api/v1/")


def _is_langflow_bare_health_path(path: str) -> bool:
    return path in _LANGFLOW_BARE_HEALTH_PATHS


def _is_langflow_prefixed_path(path: str) -> bool:
    return path == "/langflow" or path.startswith("/langflow/")


def _strip_langflow_prefix(scope: dict) -> dict:
    """Rewrite `/langflow/...` -> `/...`, mirroring Starlette `Mount` semantics.

    Langflow has no native `/langflow` route of its own (unlike `/api/v1/` and
    bare `/health`), so this alias needs an actual scope rewrite rather than
    an unchanged forward -- a plain dict copy is enough since ASGI scopes are
    just dicts and Langflow's app never sees the original `/langflow` prefix.
    """
    new_scope = dict(scope)
    prefix = "/langflow"
    new_scope["path"] = scope["path"][len(prefix) :] or "/"
    raw_path = scope.get("raw_path")
    if raw_path is not None:
        new_scope["raw_path"] = raw_path[len(prefix.encode()) :] or b"/"
    return new_scope


def _is_api_path(path: str) -> bool:
    return path == "/api" or path.startswith("/api/")


async def _run_lifespan(app, event: str) -> None:
    """Replay a single lifespan event (startup or shutdown) into `app`.

    `config.asgi.application` is the one ASGI callable the server invokes, so
    it owns the `lifespan` scope for BOTH sub-apps that implement it (the
    platform's own FastAPI stub and Langflow's) -- there is no third-party
    ASGI router doing this fan-out. Each call opens an isolated in-memory
    receive/send pair carrying just the one event, matching the ASGI lifespan
    protocol's single-event-per-message shape.
    """
    sent = []

    async def receive():
        return {"type": f"lifespan.{event}"}

    async def send(message):
        sent.append(message)

    await app({"type": "lifespan"}, receive, send)
    if sent and sent[-1]["type"].endswith(".failed"):
        raise RuntimeError(sent[-1].get("message", f"{event} failed"))


async def _dispatch_http(scope, receive, send) -> None:
    path = scope["path"]
    if _is_langflow_api_v1_path(path) or _is_langflow_bare_health_path(path):
        await langflow_application(scope, receive, send)
    elif _is_langflow_prefixed_path(path):
        await langflow_application(_strip_langflow_prefix(scope), receive, send)
    elif _is_api_path(path):
        await fastapi_application(scope, receive, send)
    else:
        await django_application(scope, receive, send)


async def _run_startup_or_failed(send) -> None:
    try:
        await _run_lifespan(fastapi_application, "startup")
        await _run_lifespan(langflow_application, "startup")
    except Exception as exc:  # noqa: BLE001 -- reported via the lifespan protocol, not raised to the server
        await send({"type": "lifespan.startup.failed", "message": str(exc)})
    else:
        await send({"type": "lifespan.startup.complete"})


async def _run_shutdown_or_failed(send) -> None:
    try:
        await _run_lifespan(langflow_application, "shutdown")
        await _run_lifespan(fastapi_application, "shutdown")
    except Exception as exc:  # noqa: BLE001 -- reported via the lifespan protocol, not raised to the server
        await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
    else:
        await send({"type": "lifespan.shutdown.complete"})


async def _dispatch_lifespan(receive, send) -> None:
    """Dual-lifespan ASGI startup (Design Notes, spec-11-1): drive BOTH
    sub-apps' startup/shutdown, not just the platform stub's -- this is where
    Langflow's own Alembic bootstrap runs. Startup order: platform stub then
    Langflow; shutdown is the reverse.
    """
    event = await receive()
    if event["type"] == "lifespan.startup":
        await _run_startup_or_failed(send)
        # Consume the eventual shutdown message from the real server so this
        # coroutine doesn't return before the process actually stops.
        event = await receive()
    if event["type"] == "lifespan.shutdown":
        await _run_shutdown_or_failed(send)


async def application(scope, receive, send):
    if scope["type"] == "http":
        await _dispatch_http(scope, receive, send)
    elif scope["type"] == "websocket":
        await websocket_application(scope, receive, send)
    elif scope["type"] == "lifespan":
        await _dispatch_lifespan(receive, send)
    else:
        msg = f"Unknown scope type {scope['type']}"
        raise NotImplementedError(msg)
