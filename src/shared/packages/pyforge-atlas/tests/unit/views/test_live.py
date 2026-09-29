"""Story 14.3 (CAP-2) — Bokeh WebSocket interactivity.

Covers every row of the intent-contract's I/O & Edge-Case Matrix:

- HAPPY_PATH_FILTER / HAPPY_PATH_SORT / NO_MAINTAINER_KWARG / DB_UNAVAILABLE_AT_LOAD exercise
  ``_grid_websocket_renderer`` OFFLINE via ``Application.create_document()`` (no socket, no
  IOLoop) — the right tool per the story's Design Notes: it builds a real ``Document``
  synchronously and setting a widget's ``.value`` fires its ``on_change`` callback inline (no
  server needed to prove the callback logic).
- UNKNOWN_LIVE_VIEW exercises the real ASGI app (``asgi.py::app``) via
  ``starlette.testclient.TestClient``.
- LIVE_SESSION_ROUND_TRIP is the one test that needs an actual live ``Server`` + a genuine
  WebSocket round trip via ``pull_session()`` — skipped (not failed) if this sandbox refuses a
  localhost TCP bind, per the Design Notes' documented escape hatch.
"""

from __future__ import annotations

import threading
import time
from dataclasses import replace

import pytest
from bokeh.client.session import pull_session
from bokeh.models import DataTable, Select, TextInput
from starlette.testclient import TestClient

import pyforge.atlas.views.asgi as asgi_module
from pyforge.atlas.views import cli_bridge
from pyforge.atlas.views.asgi import app as asgi_app
from pyforge.atlas.views.live import LIVE_VIEWS, build_application, build_live_server
from pyforge.atlas.views.registry import STATIC_VIEWS, get_view
from pyforge.atlas.views.widgets import WIDGETS, Widget


def _loaded_module(view, db_path, monkeypatch):
    """Established technique (test_render.py/test_widgets.py): load the real CLI module and
    monkeypatch its DB_PATH -- load_cli_module's (name, scripts_dir) memoization means any
    later load_cli_module(view.script) call (no scripts_dir override, as live.py's code makes)
    resolves to this SAME patched module instance."""
    module = cli_bridge.load_cli_module(view.script, scripts_dir=cli_bridge.default_scripts_dir())
    monkeypatch.setattr(module, "DB_PATH", db_path)
    return module


def _select_one(doc, model_type):
    matches = list(doc.select({"type": model_type}))
    assert len(matches) == 1, f"expected exactly one {model_type.__name__}, found {matches}"
    return matches[0]


def test_live_views_is_every_static_view_since_all_six_are_grid_widgets():
    """Sanity check on the host-agnostic runtime's derivation: today every one of the 6
    STATIC_VIEWS entries is a "grid" widget and "grid" now has a websocket_renderer, so
    LIVE_VIEWS mirrors STATIC_VIEWS exactly -- computed from the widget registry, not
    hardcoded."""
    assert LIVE_VIEWS == STATIC_VIEWS


def test_maintainer_filter_narrows_rows_via_a_real_requery(atlas_db_path, monkeypatch):
    """HAPPY_PATH_FILTER: setting the maintainer TextInput's value re-queries cf_atlas.db
    (via cli_bridge, not an in-memory filter) and narrows the DataTable's ColumnDataSource to
    just the fixture package owned by that handle."""
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    doc = build_application(view).create_document()
    table = _select_one(doc, DataTable)
    assert set(table.source.data["conda_name"]) == {
        "alpha-pkg",
        "beta-pkg",
        "gamma-pkg",
        "delta-pkg",
    }

    maintainer_input = _select_one(doc, TextInput)
    maintainer_input.value = "alice"

    assert table.source.data["conda_name"] == ["alpha-pkg"]

    # a handle owning nothing narrows to zero rows -- still a real re-query, not a crash.
    maintainer_input.value = "nobody"
    assert table.source.data["conda_name"] == []


def test_sort_by_column_reorders_ascending_nulls_last(atlas_db_path, monkeypatch):
    """HAPPY_PATH_SORT: changing the sort Select re-orders the ColumnDataSource ascending by
    that column, with null values pushed to the end -- proven with two fixture columns:
    vuln_critical_affecting_current (alpha=1, the rest=0 -- a real reorder, no nulls) and
    vuln_max_epss_score (alpha=0.5, the rest=None -- proves nulls sort last)."""
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    doc = build_application(view).create_document()
    table = _select_one(doc, DataTable)
    sort_select = _select_one(doc, Select)

    sort_select.value = "vuln_critical_affecting_current"
    assert table.source.data["conda_name"] == ["beta-pkg", "gamma-pkg", "delta-pkg", "alpha-pkg"]
    assert table.source.data["vuln_critical_affecting_current"] == [0, 0, 0, 1]

    sort_select.value = "vuln_max_epss_score"
    assert table.source.data["conda_name"] == ["alpha-pkg", "beta-pkg", "gamma-pkg", "delta-pkg"]
    assert table.source.data["vuln_max_epss_score"] == [0.5, None, None, None]


def test_clearing_sort_restores_original_fetch_order(atlas_db_path, monkeypatch):
    """Regression (review-pass patch): selecting "(unsorted)" after a sort must restore the
    original fetch order, not silently keep showing the last-sorted order under a label that
    claims otherwise -- the original bug mutated state["rows"] in place inside the sort
    callback, so clearing sort_by had nothing un-mutated left to fall back to."""
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    doc = build_application(view).create_document()
    table = _select_one(doc, DataTable)
    sort_select = _select_one(doc, Select)
    original_order = list(table.source.data["conda_name"])

    sort_select.value = "vuln_critical_affecting_current"
    assert list(table.source.data["conda_name"]) != original_order

    sort_select.value = ""
    assert list(table.source.data["conda_name"]) == original_order


def test_maintainer_filter_strips_whitespace_before_querying(atlas_db_path, monkeypatch):
    """Regression (review-pass patch): a whitespace-only or whitespace-padded filter value is
    stripped before being sent to cli_bridge.call_query -- previously sent through verbatim, so
    a value that is visually "empty" or padded produced a different query than the trimmed
    handle would."""
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    doc = build_application(view).create_document()
    table = _select_one(doc, DataTable)
    maintainer_input = _select_one(doc, TextInput)

    maintainer_input.value = "   "
    assert set(table.source.data["conda_name"]) == {
        "alpha-pkg",
        "beta-pkg",
        "gamma-pkg",
        "delta-pkg",
    }

    maintainer_input.value = "  alice  "
    assert table.source.data["conda_name"] == ["alpha-pkg"]


def test_build_application_raises_for_a_widget_without_a_websocket_renderer(monkeypatch):
    """The ValueError branch live.py::build_application documents (a registered widget type
    with no live-session mode) -- unreachable via any real STATIC_VIEWS entry today (every one
    is "grid", which now has a websocket_renderer), so exercised via a monkeypatched stub
    "static-only" widget instead."""
    monkeypatch.setitem(
        WIDGETS,
        "static-only",
        Widget(name="static-only", static_renderer=lambda view, rows: ("", "")),
    )
    view = replace(get_view("staleness-report"), widget="static-only")

    with pytest.raises(ValueError, match="static-only"):
        build_application(view)


def test_filter_and_sort_compose_a_pending_sort_survives_a_new_filter_query(atlas_db_path, monkeypatch):
    """A sort chosen before a filter change is re-applied to the freshly re-queried rows (not
    dropped) -- the two controls compose rather than fighting each other."""
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    doc = build_application(view).create_document()
    table = _select_one(doc, DataTable)
    sort_select = _select_one(doc, Select)
    maintainer_input = _select_one(doc, TextInput)

    sort_select.value = "vuln_critical_affecting_current"
    maintainer_input.value = ""  # no-op filter change, re-fetches all 4 rows
    assert table.source.data["conda_name"] == ["beta-pkg", "gamma-pkg", "delta-pkg", "alpha-pkg"]


def test_no_maintainer_kwarg_renders_the_sort_control_only(monkeypatch):
    """NO_MAINTAINER_KWARG: a View whose query_kwargs lacks "maintainer" (built via
    dataclasses.replace, never a real STATIC_VIEWS entry) renders with the sort Select but no
    maintainer TextInput. cli_bridge.call_query is monkeypatched to a canned return so this
    test needs neither a real database nor a CLI script signature that accepts the dropped
    kwarg."""
    base_view = get_view("staleness-report")
    query_kwargs = {k: v for k, v in base_view.query_kwargs.items() if k != "maintainer"}
    view = replace(base_view, query_kwargs=query_kwargs)
    assert "maintainer" not in view.query_kwargs

    monkeypatch.setattr(cli_bridge, "call_query", lambda module, **kwargs: [])

    doc = build_application(view).create_document()

    assert list(doc.select({"type": TextInput})) == []
    assert len(list(doc.select({"type": Select}))) == 1
    assert len(list(doc.select({"type": DataTable}))) == 1


def test_db_unavailable_at_load_propagates_not_swallowed(tmp_path, monkeypatch):
    """DB_UNAVAILABLE_AT_LOAD: a missing cf_atlas.db at session-load time raises
    CfAtlasDbUnavailableError out of modify_doc -- matches render_view's existing
    propagate-don't-swallow behavior; create_document() itself is what runs modify_doc, so the
    exception surfaces there."""
    view = get_view("staleness-report")
    _loaded_module(view, tmp_path / "does-not-exist.db", monkeypatch)

    application = build_application(view)
    with pytest.raises(cli_bridge.CfAtlasDbUnavailableError):
        application.create_document()


def test_asgi_unknown_view_returns_404_not_a_raw_traceback():
    """UNKNOWN_LIVE_VIEW: GET /live/{unregistered name} on the real ASGI app translates
    registry.py::get_view's KeyError into a plain 404 -- never a raw traceback / 500."""
    client = TestClient(asgi_app)

    response = client.get("/live/totally-unknown-view")

    assert response.status_code == 404
    assert "Traceback" not in response.text


def test_asgi_registered_view_embeds_a_server_document_script():
    """The AC: a registered view's /live/{view_name} response HTML contains a
    server_document-shaped embed script referencing the configured live-server URL, and that
    response itself is just markup -- no ws://scheme, no live server contacted to build it."""
    client = TestClient(asgi_app)

    response = client.get("/live/staleness-report")

    assert response.status_code == 200
    body = response.text
    assert "<script" in body
    assert "http://localhost:5006/staleness-report" in body
    assert "ws://" not in body
    assert "wss://" not in body


def test_asgi_live_bokeh_url_env_override(monkeypatch):
    """PYFORGE_ATLAS_LIVE_BOKEH_URL overrides the default http://localhost:5006 base URL the
    embed script points at (mirrors cli_bridge.py's PYFORGE_ATLAS_CFE_SCRIPTS_DIR
    env-override convention -- previously untested)."""
    monkeypatch.setenv("PYFORGE_ATLAS_LIVE_BOKEH_URL", "http://bokeh-live.internal:9000")
    client = TestClient(asgi_app)

    response = client.get("/live/staleness-report")

    assert "http://bokeh-live.internal:9000/staleness-report" in response.text


def test_asgi_registered_but_static_only_view_returns_404(monkeypatch):
    """Review-pass patch: a registered view whose widget has no websocket_renderer (not in
    LIVE_VIEWS -- no such view exists today, since "grid" is the only widget type and it now
    has one) 404s rather than 200ing with an embed script pointing at a Bokeh-server mount
    build_live_server's default construction never creates."""
    monkeypatch.setattr(asgi_module, "LIVE_VIEWS", ())
    client = TestClient(asgi_app)

    response = client.get("/live/staleness-report")

    assert response.status_code == 404


def test_live_session_round_trip_via_a_real_websocket_connection(atlas_db_path, monkeypatch):
    """LIVE_SESSION_ROUND_TRIP: a real bokeh.server.server.Server on an OS-assigned ephemeral
    port; pull_session() performs a genuine WebSocket round trip and the resulting
    ClientSession's .document contains the expected DataTable/TextInput/Select models.

    If this sandbox forbids binding a localhost TCP socket, the specific OSError/
    PermissionError from the bind attempt is caught and the test is skipped (not failed) --
    the offline tests above already fully exercise the callback logic without any socket, so
    this narrows only the one test that specifically needs a live connection."""
    view = get_view("staleness-report")
    _loaded_module(view, atlas_db_path, monkeypatch)

    try:
        server = build_live_server(views=(view,), port=0)
    except (OSError, PermissionError) as exc:
        pytest.skip(f"sandbox forbids binding a localhost TCP socket: {exc}")

    server.start()
    thread = threading.Thread(target=server.io_loop.start, daemon=True)
    thread.start()
    try:
        session = None
        last_exc: Exception | None = None
        deadline = time.monotonic() + 5.0
        while session is None and time.monotonic() < deadline:
            try:
                session = pull_session(
                    session_id="test-round-trip",
                    url=f"http://localhost:{server.port}/{view.name}",
                )
            except Exception as exc:  # server not accepting connections yet
                last_exc = exc
                time.sleep(0.1)
        assert session is not None, f"could not connect to the live server: {last_exc}"
        try:
            assert list(session.document.select({"type": DataTable}))
            assert list(session.document.select({"type": TextInput}))
            assert list(session.document.select({"type": Select}))
        finally:
            session.close()
    finally:
        server.io_loop.add_callback(server.io_loop.stop)
        thread.join(timeout=5)
        server.stop()
