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
# CAP-3 locality: ASGI's default leaf is local. Production images must set
# DJANGO_SETTINGS_MODULE=config.settings.production (and leave
# COMPONENT_RUNTIME unset / non-local) so stage-1/2 refusals stay armed.
if os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings.local":
    os.environ.setdefault("COMPONENT_RUNTIME", "local")

# CAP-2: configure before get_asgi_application so DjangoInstrumentor can insert
# middleware into MIDDLEWARE before the handler stack is built.
from config.observability import configure_observability  # noqa: E402

configure_observability()

# This application object is used by any ASGI server configured to use this file.
django_application = get_asgi_application()

# Import websocket application here, so apps from django_application are loaded first
# FastAPI seam (Story 10.1): owns the /api/ namespace. Story 43.2 moved
# Langflow off bare /api/v1 — Langflow stays at /langflow/api/v1/... and
# bare /health paths (see below). Versioned station APIs live at
# /stations/<name>/api/v<N>/ on the station FastAPI sub-apps (station_api).
# DB-GPT
# (Story 11.2) never gets an ASGI mount at all -- AD-14/AD-17 moved it to
# Pattern B (its own sidecar container, reached over Celery/REST) before this
# module would have needed one; see the registry-consult touchpoint below.
from django_pyforge.mcp_http import dispatch_station_mcp  # noqa: E402
from django_pyforge.mcp_http import loaded_station_mcp_apps  # noqa: E402

from config.engine_patterns import ENGINE_PATTERNS  # noqa: E402
from config.fastapi_app import fastapi_application  # noqa: E402
from config.station_api import parse_station_api_path  # noqa: E402
from config.station_api import station_application  # noqa: E402
from config.websocket import websocket_application  # noqa: E402

# Station MCP faces (canopy AD-5) are discovered via django_pyforge.mcp_http.
# Story 11.1 (spec-python-agent-platform CAP-2, AD-14 Pattern A): Langflow's
# own FastAPI app, built once at import time. Imported only after Django's
# settings have executed (via django_application above), which is what
# exports the derived LANGFLOW_DATABASE_URL/LANGFLOW_CACHE_TYPE/... env vars
# langflow_integration.asgi's create_app() call reads.
from langflow_integration.asgi import _LifespanManager  # noqa: E402
from langflow_integration.asgi import langflow_application  # noqa: E402

# Story 11.2 (spec-python-agent-platform CAP-3, AD-17): the registry-consult
# touchpoint for DB-GPT. DB-GPT is configured to Pattern B (its own sidecar
# container, reached over Celery/REST -- `dbgpt_integration/tasks.py`), never
# an ASGI mount, so there is nothing Pattern-A to build here. This assertion
# IS the touchpoint AD-17 requires -- not hardcoded absence: flipping
# `ENGINE_PATTERNS["dbgpt"]` to "A" fails it loudly, the moment a future
# revert lands here without also adding the ASGI sub-app Pattern A would
# need (mirroring `langflow_integration/asgi.py`'s own `create_app()` +
# `_LifespanManager` shape), rather than silently mounting nothing.
if ENGINE_PATTERNS["dbgpt"] == "A":
    # A plain `if`/`raise`, not `assert` -- this check must survive
    # `python -O`/`PYTHONOPTIMIZE`, which strips `assert` statements, and
    # this IS the touchpoint AD-17 requires (see the comment above).
    msg = (
        "dbgpt is configured as Pattern A (config/engine_patterns.py) but "
        "config/asgi.py builds no DB-GPT ASGI sub-app -- add one (mirroring "
        "langflow_integration/asgi.py) before flipping ENGINE_PATTERNS['dbgpt']"
    )
    raise RuntimeError(msg)

# I/O & Edge-Case Matrix (spec-11-1): these three routes match Langflow's own
# native route prefixes, so they forward with the ASGI scope UNCHANGED --
# no path rewriting, unlike the /langflow/ prefix-strip below.
_LANGFLOW_BARE_HEALTH_PATHS = frozenset({"/health", "/health_check"})


def _is_langflow_bare_health_path(path: str) -> bool:
    return path in _LANGFLOW_BARE_HEALTH_PATHS


def _is_langflow_prefixed_path(path: str) -> bool:
    return path == "/langflow" or path.startswith("/langflow/")


def _strip_langflow_prefix(scope: dict) -> dict:
    """Route `/langflow/...` to Langflow as `/...`, mirroring real Starlette
    `Mount` semantics -- verified against this env's own installed
    `starlette.routing.Mount.matches`/`starlette._utils.get_route_path`, not
    assumed. A real `Mount` does NOT rewrite `scope["path"]`/`raw_path"]` at
    all: it only extends `root_path` (`root_path + matched_path`), and every
    internal route-matching call computes the route-relative path via
    `get_route_path(scope)` (`path` minus the leading `root_path`) instead of
    reading `path` directly. Leaving `path`/`raw_path` untouched is what
    keeps `/langflow` in a redirect Location: Starlette's own trailing-slash
    redirect builds its URL from the copied scope's (unstripped) `path` via
    `starlette.datastructures.URL(scope=...)`, which never consults
    `root_path` -- so physically slicing `/langflow` off `path` (an earlier
    version of this function did) makes routing work but silently loses the
    prefix from any redirect Langflow's own router issues, proven by this
    story's own test (`test_langflow_prefixed_path_forwards_with_prefix_
    stripped`): the Location carried no `/langflow` segment until this
    function stopped touching `path`.
    """
    new_scope = dict(scope)
    new_scope["root_path"] = scope.get("root_path", "") + "/langflow"
    return new_scope


def _is_api_path(path: str) -> bool:
    return path == "/api" or path.startswith("/api/")


async def _dispatch_http(scope, receive, send) -> None:
    path = scope["path"]
    if await dispatch_station_mcp(scope, receive, send):
        return
    station_api = parse_station_api_path(path)
    if station_api is not None:
        station, version = station_api
        try:
            app = station_application(station, version)
        except KeyError:
            from starlette.responses import JSONResponse

            response = JSONResponse({"detail": "Not Found"}, status_code=404)
            await response(scope, receive, send)
            return
        await app(scope, receive, send)
    elif _is_langflow_bare_health_path(path):
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
            for mcp_app in list(loaded_station_mcp_apps().values()):
                await stack.enter_async_context(_LifespanManager(mcp_app))
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
