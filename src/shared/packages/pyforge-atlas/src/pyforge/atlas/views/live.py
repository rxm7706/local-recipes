"""Host-agnostic Bokeh WebSocket runtime — Story 14.3 (CAP-2).

Wraps :func:`~pyforge.atlas.views.widgets.get_widget`'s ``websocket_renderer`` factory (the
``Callable[[View], Callable[[Document], None]]`` shape Story 14.3 defined) into real Bokeh
``Application``/``Server`` objects, using the high-level ``bokeh.server.server.Server`` API
(not the low-level ``BokehTornado``/``HTTPServer``/``BaseServer`` trio — the Design Notes
record why: that assembly solves a multi-worker production-scaling concern out of this
story's scope).

This module never imports or references an ASGI host (Starlette, FastAPI, or otherwise) —
``asgi.py`` is the ONLY module that knows one exists (the story's Boundaries & Constraints),
so this module stays reusable behind any future mounting layer.
"""

from __future__ import annotations

from typing import Any

from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.server.server import Server

from .registry import STATIC_VIEWS, View
from .widgets import get_widget

# Every registered static view whose declared widget type has filled in a
# ``websocket_renderer`` — today, all 6 ``STATIC_VIEWS`` entries (all "grid"). Computed once
# at import time from the widget registry, never hardcoded, so a future widget type that
# stays static-only (chart/pivot) is excluded automatically rather than needing an edit here.
LIVE_VIEWS: tuple[View, ...] = tuple(
    view for view in STATIC_VIEWS if get_widget(view.widget).websocket_renderer is not None
)


def build_application(view: View) -> Application:
    """Wrap ``view``'s widget-declared ``websocket_renderer`` factory into a Bokeh
    ``Application`` — a ``FunctionHandler`` around the ``ModifyDoc`` callback the factory
    returns for this specific ``view``. Raises ``KeyError`` (via ``get_widget``) for an
    unregistered widget type, and ``ValueError`` if the resolved widget has no live-session
    mode (``websocket_renderer is None`` — every non-"grid" widget type today)."""
    widget = get_widget(view.widget)
    if widget.websocket_renderer is None:
        raise ValueError(
            f"view {view.name!r}'s widget {view.widget!r} has no websocket_renderer (static-only widget type)"
        )
    modify_doc = widget.websocket_renderer(view)
    return Application(FunctionHandler(modify_doc))


def build_live_server(
    views: tuple[View, ...] = LIVE_VIEWS,
    *,
    port: int = 0,
    allow_websocket_origin: list[str] | None = None,
    io_loop: Any = None,
) -> Server:
    """Build a ``bokeh.server.server.Server`` serving one ``Application`` per ``views`` entry,
    each mounted at ``/<view.name>`` (mirroring the ASGI layer's ``/live/{view_name}`` ->
    ``{base_url}/{view.name}`` embed convention in ``asgi.py``).

    ``port=0`` (the default) asks the OS for a free ephemeral port — verified empirically
    against this env's Bokeh 3.9.2: ``bokeh.server.util.bind_sockets`` resolves ``port=0`` to
    the actual bound port *before* ``Server.__init__`` computes its websocket-origin allowlist
    default, so the caller can read the real port back off ``Server.port`` and (with
    ``allow_websocket_origin`` left ``None``) the server already trusts connections addressed
    to that port — no chicken-and-egg problem binding a real socket for a test or an ad hoc
    session."""
    applications = {f"/{view.name}": build_application(view) for view in views}
    return Server(
        applications,
        port=port,
        allow_websocket_origin=allow_websocket_origin,
        io_loop=io_loop,
    )
