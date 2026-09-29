"""Pluggable widget-type registry — Story 14.2 (CAP-3), ``"grid"``'s live session filled in
by Story 14.3 (CAP-2).

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

This module never imports ``live.py`` or ``asgi.py`` (Story 14.3's host modules) — it builds
and returns a plain ``ModifyDoc`` callable (:data:`~bokeh.application.handlers.function.
ModifyDoc`, i.e. ``Callable[[Document], None]``) and knows nothing about ``Application``,
``Server``, or any ASGI host. That keeps the dependency direction the same one line further:
``registry.py`` → this module → (``render.py`` | ``live.py``), never the reverse.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from bokeh.document import Document
from bokeh.embed import components
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, DataTable, Select, TableColumn, TextInput

from . import cli_bridge
from .registry import View


@dataclass(frozen=True)
class Widget:
    """One entry in the pluggable widget-type registry.

    ``static_renderer`` renders already-fetched ``rows`` for a :class:`~pyforge.atlas.views.
    registry.View` into a ``(script, div)`` static HTML fragment pair. ``websocket_renderer``
    is a factory — ``Callable[[View], Callable[[Document], None]]`` — that takes the
    :class:`~pyforge.atlas.views.registry.View` and returns the actual Bokeh ``ModifyDoc``
    session callback for it (the ``func`` a ``bokeh.application.handlers.function.
    FunctionHandler`` wraps); ``None`` means the widget type has no live-session mode yet.
    Story 14.2 deliberately left this field's type unconstrained (``Callable[..., Any] |
    None``) so Story 14.3 (CAP-2) could define the concrete factory shape above without a
    second edit to this dataclass — ``"grid"`` is the first (and, as of this story, only)
    entry to fill it in, via :func:`_grid_websocket_renderer` below.
    """

    name: str
    static_renderer: Callable[[View, list[dict[str, Any]]], tuple[str, str]]
    websocket_renderer: Callable[[View], Callable[[Document], None]] | None = None


def _render_grid(view: View, rows: list[dict[str, Any]]) -> tuple[str, str]:
    """Render ``rows`` as a ``bokeh.models.DataTable`` bound to a ``ColumnDataSource``, using
    ``view.columns`` as the declared, stable column order (moved verbatim from Story 14.1's
    ``render.py::render_rows``)."""
    data = {column: [row.get(column) for row in rows] for column in view.columns}
    source = ColumnDataSource(data=data)
    table_columns = [TableColumn(field=column, title=column) for column in view.columns]
    data_table = DataTable(source=source, columns=table_columns, index_position=None)
    return components(data_table)


def _columns_data(view: View, rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Same column-projection shape as ``_render_grid``'s ``data`` — pulled out so the live
    ``ColumnDataSource`` can be re-populated by both the initial load and every ``on_change``
    callback without repeating the comprehension three times. Loop variable deliberately named
    ``col``, not ``column`` — this module now hard-imports ``bokeh.layouts.column`` at module
    level (used by ``_grid_websocket_renderer``'s ``doc.add_root(column(...))`` call), and
    shadowing it with a comprehension-local ``column`` would be a live footgun the moment either
    comprehension here were ever rewritten as a plain ``for`` loop (review-pass patch)."""
    return {col: [row.get(col) for row in rows] for col in view.columns}


def _grid_websocket_renderer(view: View) -> Callable[[Document], None]:
    """Build the live-session ``ModifyDoc`` callback for ``view`` — a maintainer-filter
    ``TextInput`` (rendered only when ``"maintainer" in view.query_kwargs``, per the story's
    Boundaries) plus a sort-by-column ``Select``, laid out above the same ``DataTable``/
    ``ColumnDataSource`` shape ``_render_grid`` uses.

    The filter's ``on_change`` re-runs ``cli_bridge.call_query`` against ``cf_atlas.db`` with
    ``maintainer`` overridden — a genuine server-side re-query (HAPPY_PATH_FILTER), never an
    in-memory filter of already-fetched rows. ``state["fetched_rows"]`` always holds that raw,
    un-sorted result; the sort ``Select``'s ``on_change`` never mutates it — ``_displayed_rows``
    derives a freshly-sorted VIEW of it on every render instead (review-pass patch: the
    original draft sorted ``state["rows"]`` in place, so picking "(unsorted)" again after a
    sort left the table showing stale sorted order under a label that claimed otherwise; deriving
    from an untouched base list makes clearing the sort a genuine no-op restoration). Re-sorting
    is still a real server-side round trip over the WebSocket session (HAPPY_PATH_SORT), just
    never a mutation of the fetched rows themselves — matching the filter/drill/sort grouping.

    Propagates ``cli_bridge.CfAtlasDbUnavailableError`` unchanged on the initial load (and on
    any later re-query) — mirrors ``render.py::render_view``'s existing propagate-don't-swallow
    behavior (DB_UNAVAILABLE_AT_LOAD); no new handling invented here.
    """

    def modify_doc(doc: Document) -> None:
        module = cli_bridge.load_cli_module(view.script)
        has_maintainer = "maintainer" in view.query_kwargs
        state: dict[str, Any] = {
            "fetched_rows": cli_bridge.call_query(module, **view.query_kwargs),
            "sort_by": "",
        }

        source = ColumnDataSource(data=_columns_data(view, state["fetched_rows"]))
        table_columns = [TableColumn(field=col, title=col) for col in view.columns]
        data_table = DataTable(source=source, columns=table_columns, index_position=None)

        def _displayed_rows() -> list[dict[str, Any]]:
            sort_by = state["sort_by"]
            if not sort_by:
                return state["fetched_rows"]
            return sorted(
                state["fetched_rows"],
                key=lambda row: (row.get(sort_by) is None, row.get(sort_by)),
            )

        def _push() -> None:
            source.data = _columns_data(view, _displayed_rows())

        controls: list[Any] = []

        if has_maintainer:
            maintainer_input = TextInput(title="Filter by maintainer", value="")

            def _on_maintainer_change(attr: str, old: str, new: str) -> None:
                # .strip() first: a whitespace-only value is visually indistinguishable from
                # empty but was previously sent straight through as a non-None filter
                # (review-pass patch).
                kwargs = dict(view.query_kwargs)
                kwargs["maintainer"] = new.strip() or None
                state["fetched_rows"] = cli_bridge.call_query(module, **kwargs)
                _push()

            maintainer_input.on_change("value", _on_maintainer_change)
            controls.append(maintainer_input)

        sort_select = Select(
            title="Sort by",
            value="",
            options=[("", "(unsorted)")] + [(c, c) for c in view.columns],
        )

        def _on_sort_change(attr: str, old: str, new: str) -> None:
            state["sort_by"] = new
            _push()

        sort_select.on_change("value", _on_sort_change)
        controls.append(sort_select)

        doc.add_root(column(*controls, data_table))

    return modify_doc


WIDGETS: dict[str, Widget] = {
    "grid": Widget(name="grid", static_renderer=_render_grid, websocket_renderer=_grid_websocket_renderer),
}


def get_widget(name: str) -> Widget:
    """Look up a :class:`Widget` by name; raises ``KeyError`` naming all known widget types
    on miss (mirrors ``registry.py::get_view``'s error style)."""
    widget = WIDGETS.get(name)
    if widget is not None:
        return widget
    raise KeyError(f"unknown widget type {name!r}; known widget types: {', '.join(WIDGETS)}")
