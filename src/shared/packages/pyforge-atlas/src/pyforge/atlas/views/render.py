"""Static, self-contained Bokeh HTML fragments for the view catalog — Story 14.1 (CAP-1),
now dispatched through the pluggable widget-type registry — Story 14.2 (CAP-3).

Renders ``list[dict]`` rows (fetched via :mod:`pyforge.atlas.views.cli_bridge`, straight
from a CLI script's own ``query()``) into a ``script`` + ``div`` HTML fragment by dispatching
to the :class:`~pyforge.atlas.views.registry.View`'s declared ``widget`` type
(:func:`~pyforge.atlas.views.widgets.get_widget`) — this module never constructs a Bokeh
model type directly; that logic lives only inside a widget's ``static_renderer``. Every
widget seeded so far is a purely static rendering primitive: ``bokeh.embed.components()``
produces a self-contained fragment with no server/session/WebSocket code (never
``bokeh.embed.server_document``/``autoload_server``/any live-session API) — the Boundaries &
Constraints this story is scoped to.

Columns always come from the :class:`~pyforge.atlas.views.registry.View`'s declared
``columns`` tuple, not from whatever keys happen to be present in a given row — so the
fragment's column set is stable even when the query returns 0 rows (the EMPTY_RESULT case).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import cli_bridge
from .registry import View, get_view
from .widgets import get_widget


def render_rows(view: View, rows: list[dict[str, Any]]) -> tuple[str, str]:
    """Render already-fetched ``rows`` for ``view`` into a ``(script, div)`` HTML fragment
    pair by dispatching to ``view``'s declared widget type."""
    return get_widget(view.widget).static_renderer(view, rows)


def render_view(name: str, *, scripts_dir: Path | None = None) -> tuple[str, str]:
    """Look up ``name`` in :data:`STATIC_VIEWS <pyforge.atlas.views.registry.STATIC_VIEWS>`
    (``KeyError`` if unknown — the UNKNOWN_VIEW case), fetch its rows by dynamically
    importing and calling the matching CLI script's ``query(**view.query_kwargs)`` verbatim
    (:func:`pyforge.atlas.views.cli_bridge.call_query` — ``CfAtlasDbUnavailableError`` if
    ``cf_atlas.db`` is missing), and render the result to a static ``(script, div)`` fragment.
    """
    view = get_view(name)
    module = cli_bridge.load_cli_module(view.script, scripts_dir=scripts_dir)
    rows = cli_bridge.call_query(module, **view.query_kwargs)
    return render_rows(view, rows)
