"""
ASGI config for Python Agent Platform project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/asgi/

"""

import contextlib
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
from langflow_integration.asgi import _LifespanManager  # noqa: E402
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


async def _dispatch_lifespan(receive, send) -> None:
    """Dual-lifespan ASGI startup (Design Notes, spec-11-1; corrected
    2026-08-20 -- see the spec's Spec Change Log for the HIGH bug this
    replaces). Drives BOTH sub-apps' lifespans -- the platform FastAPI
    stub's and Langflow's (where its own Alembic bootstrap runs) -- through
    the shared, queue-driven `_LifespanManager` (`langflow_integration.asgi`)
    instead of a single-shot `receive()` replay: Starlette's lifespan
    handler calls `receive()` TWICE per invocation and never checks the
    second message's type, so a naive replay of one hardcoded message ran a
    full startup-then-shutdown cycle within a single "startup" call,
    tearing Langflow's services down immediately after boot.

    Both managers are entered into one `AsyncExitStack`, held open for the
    whole process lifetime -- the second `receive()` below blocks until the
    real ASGI server actually sends `lifespan.shutdown` -- and unwound in
    reverse order (Langflow then the platform stub) when it does, matching
    the specced startup/shutdown ordering. A startup failure on either
    sub-app is likewise rolled back automatically by that same unwind (the
    low-severity rollback gap flagged in the Review Triage Log).
    """
    event = await receive()
    if event["type"] != "lifespan.startup":
        # An ASGI server should never send anything but `lifespan.startup`
        # first, but leaving the caller with no reply at all risks a hang --
        # always send SOMETHING back.
        message = f"unexpected {event['type']}"
        await send({"type": "lifespan.startup.failed", "message": message})
        return

    started = False
    try:
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(_LifespanManager(fastapi_application))
            await stack.enter_async_context(_LifespanManager(langflow_application))
            started = True
            await send({"type": "lifespan.startup.complete"})

            event = await receive()
            if event["type"] != "lifespan.shutdown":
                message = f"unexpected {event['type']}"
                await send({"type": "lifespan.shutdown.failed", "message": message})
                return
            # Falling through here closes the AsyncExitStack, which runs the
            # real shutdown (Langflow then the platform stub, reverse order).
    except Exception as exc:  # noqa: BLE001 -- reported via the lifespan protocol, not raised to the server
        failed_event = "shutdown" if started else "startup"
        await send({"type": f"lifespan.{failed_event}.failed", "message": str(exc)})
        return

    await send({"type": "lifespan.shutdown.complete"})


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
