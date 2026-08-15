"""Story 14.2 (CAP-3) — pluggable widget-type registry.

Covers the I/O matrix's HAPPY_PATH, UNKNOWN_WIDGET, EXTENSIBILITY, and WEBSOCKET_UNSET rows.

HAPPY_PATH is split into two independent checks, deliberately avoiding a byte-identical
comparison of Bokeh's own HTML output (which would require monkeypatching Bokeh's private,
non-deterministic id-generation internals — a maintenance liability with no real payoff, since
Story 14.1's unmodified ``test_render.py`` already exercises every registered view's actual
rendered content):

- ``test_render_rows_dispatches_through_the_registry_...`` proves ``render_rows``'s dispatch
  logic itself (``get_widget(view.widget).static_renderer(view, rows)``) via a spy widget —
  independent of any real Bokeh rendering.
- ``test_get_widget_grid_static_renderer_produces_a_valid_static_fragment`` proves the "grid"
  widget's real renderer produces a well-formed fragment, using the same structural assertions
  (declared columns present, no byte-for-byte comparison) ``test_render.py`` already uses.
"""

from __future__ import annotations

import pytest

from pyforge.atlas.views import cli_bridge
from pyforge.atlas.views.registry import STATIC_VIEWS, get_view
from pyforge.atlas.views.render import render_rows
from pyforge.atlas.views.widgets import WIDGETS, Widget, get_widget


def _rows_for(view, db_path, monkeypatch):
    module = cli_bridge.load_cli_module(
        view.script, scripts_dir=cli_bridge.default_scripts_dir()
    )
    monkeypatch.setattr(module, "DB_PATH", db_path)
    return cli_bridge.call_query(module, **view.query_kwargs)


def test_render_rows_dispatches_through_the_registry_with_exact_args_and_return_value(
    monkeypatch,
):
    """render_rows's one-line dispatch (get_widget(view.widget).static_renderer(view, rows))
    calls the registered widget's renderer with exactly (view, rows) and returns its result
    unchanged -- a pure dispatch-correctness check, independent of Bokeh's own rendering."""
    view = get_view("staleness-report")
    rows = [{"conda_name": "alpha-pkg"}]
    calls = []

    def _spy_static_renderer(v, r):
        calls.append((v, r))
        return ("<script>spy</script>", "<div>spy</div>")

    monkeypatch.setitem(
        WIDGETS, "grid", Widget(name="grid", static_renderer=_spy_static_renderer)
    )

    result = render_rows(view, rows)

    assert calls == [(view, rows)]
    assert result == ("<script>spy</script>", "<div>spy</div>")


def test_get_widget_grid_static_renderer_produces_a_valid_static_fragment(
    atlas_db_path, monkeypatch
):
    """HAPPY_PATH: get_widget("grid") returns the registered Widget; calling its
    static_renderer directly (not just through render_rows) produces a real, well-formed
    Bokeh fragment whose declared columns are present."""
    view = get_view("staleness-report")
    rows = _rows_for(view, atlas_db_path, monkeypatch)

    widget = get_widget("grid")
    assert isinstance(widget, Widget)
    assert widget.name == "grid"

    script, div = widget.static_renderer(view, rows)

    assert "<script" in script
    assert "data-root-id" in div
    for column in view.columns:
        assert column in script


def test_get_widget_unknown_name_raises_key_error_naming_known_widget_types():
    """UNKNOWN_WIDGET: get_widget("bogus") raises KeyError naming all known widget-type
    names, mirroring registry.py::get_view's error style."""
    with pytest.raises(KeyError, match="bogus") as exc_info:
        get_widget("bogus")
    assert "grid" in str(exc_info.value)


def test_get_widget_extensibility_via_monkeypatch_needs_no_registry_edit(monkeypatch):
    """EXTENSIBILITY: a throwaway widget type registered only inside the test leaves the 6
    existing STATIC_VIEWS/View entries unmodified — no edit to registry.py was needed."""

    def _fake_static_renderer(view, rows):
        return ("<script>fake</script>", "<div>fake</div>")

    fake_widget = Widget(name="fake", static_renderer=_fake_static_renderer)
    monkeypatch.setitem(WIDGETS, "fake", fake_widget)

    assert get_widget("fake") is fake_widget
    assert len(STATIC_VIEWS) == 6
    assert all(view.widget == "grid" for view in STATIC_VIEWS)


def test_get_widget_grid_websocket_renderer_is_unset():
    """WEBSOCKET_UNSET: get_widget("grid").websocket_renderer is None — Story 14.3 fills
    this in."""
    assert get_widget("grid").websocket_renderer is None


def test_views_package_reexports_widget_registry_symbols():
    """The pyforge.atlas.views package root re-exports Widget/WIDGETS/get_widget (not just
    the widgets submodule) — proves __init__.py's new export lines actually work."""
    import pyforge.atlas.views as views_pkg

    assert views_pkg.Widget is Widget
    assert views_pkg.WIDGETS is WIDGETS
    assert views_pkg.get_widget is get_widget
