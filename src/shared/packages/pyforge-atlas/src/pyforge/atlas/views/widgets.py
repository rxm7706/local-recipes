"""Pluggable widget-type registry — Story 14.2 (CAP-3).

Story 14.1's ``render.py::render_rows`` hardcoded one Bokeh shape
(``ColumnDataSource``→``DataTable``) directly. This module extracts that shape into a
named, pluggable :class:`Widget` entry so a future widget type (chart, pivot) can be added as
"one registry entry plus one renderer" without editing any existing :class:`~pyforge.atlas.
views.registry.View` or ``render.py`` itself.

Layering order (bottom to top, matching dependency direction): ``registry.py`` (no
intra-package deps) → this module (imports :class:`~pyforge.atlas.views.registry.View` from
``registry.py`` only) → ``render.py`` (imports :func:`get_widget` from here). ``View``
construction never validates its ``widget`` name against :data:`WIDGETS` (that would make
``registry.py`` depend on this module, reversing the layering into a cycle) —
:func:`get_widget` raises ``KeyError`` at render time instead, mirroring this repo's existing
"name-only, validated at dispatch" convention (``a2a/schema.py``'s ``_KIND_TO_MODEL``,
``orchestration/definitions.py``'s profile lookup).

Only one widget type, ``"grid"``, is seeded here. A survey of all 11 conda-forge-expert skill
CLIs' query shapes (not just the 6 already in ``STATIC_VIEWS``) found 8 flat-grid-shaped, 1
chart-shaped, and 2 pivot/hierarchical-shaped — and, separately, every one of today's 6
``STATIC_VIEWS`` entries happens to fall in the grid bucket. "chart"/"pivot" are each a
future one-entry-plus-one-renderer addition when a story actually introduces a view needing
one, not built here speculatively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from bokeh.embed import components
from bokeh.models import ColumnDataSource, DataTable, TableColumn

from .registry import View


@dataclass(frozen=True)
class Widget:
    """One entry in the pluggable widget-type registry.

    ``static_renderer`` renders already-fetched ``rows`` for a :class:`~pyforge.atlas.views.
    registry.View` into a ``(script, div)`` static HTML fragment pair. ``websocket_renderer``
    is a Story 14.3 slot for live-session rendering — every entry seeded by this story leaves
    it ``None``.
    """

    name: str
    static_renderer: Callable[[View, list[dict[str, Any]]], tuple[str, str]]
    websocket_renderer: Callable[..., Any] | None = None


def _render_grid(view: View, rows: list[dict[str, Any]]) -> tuple[str, str]:
    """Render ``rows`` as a ``bokeh.models.DataTable`` bound to a ``ColumnDataSource``, using
    ``view.columns`` as the declared, stable column order (moved verbatim from Story 14.1's
    ``render.py::render_rows``)."""
    data = {column: [row.get(column) for row in rows] for column in view.columns}
    source = ColumnDataSource(data=data)
    table_columns = [TableColumn(field=column, title=column) for column in view.columns]
    data_table = DataTable(source=source, columns=table_columns, index_position=None)
    return components(data_table)


WIDGETS: dict[str, Widget] = {
    "grid": Widget(name="grid", static_renderer=_render_grid),
}


def get_widget(name: str) -> Widget:
    """Look up a :class:`Widget` by name; raises ``KeyError`` naming all known widget types
    on miss (mirrors ``registry.py::get_view``'s error style)."""
    widget = WIDGETS.get(name)
    if widget is not None:
        return widget
    raise KeyError(
        f"unknown widget type {name!r}; known widget types: {', '.join(WIDGETS)}"
    )
