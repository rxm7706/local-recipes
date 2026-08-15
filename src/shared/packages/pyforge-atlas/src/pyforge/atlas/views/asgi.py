"""Minimal ASGI mounting layer for the live Bokeh sessions — Story 14.3 (CAP-2).

The ONLY module in this package that knows an ASGI host (Starlette) exists — every other
``views/*`` module (``live.py`` included) stays host-agnostic, so swapping this mounting
layer for a different one later touches only this one file (the story's Boundaries &
Constraints). One route, ``GET /live/{view_name}``, embeds the live Bokeh session for a
registered :class:`~pyforge.atlas.views.registry.View` via ``bokeh.embed.server_document()``
— the response is a small ``<script>`` fragment the BROWSER later runs to open the actual
WebSocket connection against the separately-running live Bokeh server (``live.py::
build_live_server``); rendering this route itself opens zero WebSocket connections.

Starlette, not FastAPI or Panel — the Design Notes record why (no request-validation/OpenAPI
surface needed, already a real resolved dependency, and the exact framework the community
"embed a Bokeh server behind ASGI" pattern uses).
"""

from __future__ import annotations

import os

from bokeh.embed import server_document
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.routing import Route

from .live import LIVE_VIEWS
from .registry import get_view

# Env override for the live Bokeh server's base URL (mirrors cli_bridge.py's
# PYFORGE_ATLAS_CFE_SCRIPTS_DIR env-override convention).
_LIVE_BOKEH_URL_ENV_VAR = "PYFORGE_ATLAS_LIVE_BOKEH_URL"
_DEFAULT_LIVE_BOKEH_URL = "http://localhost:5006"


def _live_bokeh_base_url() -> str:
    return os.environ.get(_LIVE_BOKEH_URL_ENV_VAR, _DEFAULT_LIVE_BOKEH_URL)


async def _live_view(request: Request) -> Response:
    """``GET /live/{view_name}``: look up ``view_name`` in ``STATIC_VIEWS``
    (``registry.py::get_view``) and embed its live session via ``server_document()``, pointed
    at ``{base_url}/{view.name}`` — the same ``/<view.name>`` mount path
    ``live.py::build_live_server`` assigns each ``Application``. An unregistered name
    translates ``get_view``'s ``KeyError`` into a plain 404 response (UNKNOWN_LIVE_VIEW) —
    never a raw traceback.

    A registered view whose widget has no ``websocket_renderer`` (not in ``LIVE_VIEWS`` — no
    such view exists today, since "grid" is the only widget type and it now has one, but a
    future chart/pivot-only static view would be exactly this case) also 404s here, rather than
    200ing with an embed script pointing at a Bokeh-server mount ``build_live_server``'s default
    construction never creates (review-pass patch — the two functions' notions of "servable"
    must agree, or a future static-only view's live route silently breaks user-facing instead of
    failing at this cheap, obvious check)."""
    name = request.path_params["view_name"]
    try:
        view = get_view(name)
    except KeyError:
        return PlainTextResponse(f"unknown view {name!r}", status_code=404)
    if view not in LIVE_VIEWS:
        return PlainTextResponse(f"view {name!r} has no live session mode", status_code=404)
    url = f"{_live_bokeh_base_url()}/{view.name}"
    return HTMLResponse(server_document(url=url))


app = Starlette(routes=[Route("/live/{view_name}", _live_view)])
