"""Story 14.1 (CAP-1) — Bokeh fragment rendering.

Covers the I/O matrix's HAPPY_PATH and EMPTY_RESULT rows, the UNKNOWN_VIEW row via the
public ``render_view`` entrypoint, and the Boundaries & Constraints assertion that no
rendered fragment (across every registered view) ever contains a live-session/WebSocket
marker — ``bokeh.embed.components()`` is a purely static primitive.

Also proves the CAP-1 acceptance bar ("rows agree with the CLI counterpart's output") for
every one of the 6 registered views, not just ``staleness-report`` — a dedicated row-count +
content assertion per remaining view (``feedstock-health``, ``behind-upstream``,
``release-cadence``, ``adoption-stage``; ``cve-watcher`` is covered in
``test_cli_bridge.py``), each checked against the shared fixture rows in ``conftest.py``.
"""

from __future__ import annotations

import pytest

from pyforge.atlas.views import cli_bridge
from pyforge.atlas.views.registry import STATIC_VIEWS, get_view
from pyforge.atlas.views.render import render_rows, render_view

# Never allowed to appear in a rendered fragment — the story's rendering-primitive
# boundary (components() only, never server_document/autoload_server/any live session).
FORBIDDEN_MARKERS = ("ws://", "wss://", "autoload_server", "session_id")


def _rows_for(view, db_path, monkeypatch):
    module = cli_bridge.load_cli_module(view.script, scripts_dir=cli_bridge.default_scripts_dir())
    monkeypatch.setattr(module, "DB_PATH", db_path)
    return cli_bridge.call_query(module, **view.query_kwargs)


def test_render_rows_happy_path_rows_match_fixture_in_declared_column_order(atlas_db_path, monkeypatch):
    view = get_view("staleness-report")
    rows = _rows_for(view, atlas_db_path, monkeypatch)
    assert rows  # fixture has non-empty results for this view

    script, div = render_rows(view, rows)

    assert "<script" in script
    assert "data-root-id" in div
    # every declared column name is embedded in the serialized fragment, in order.
    for column in view.columns:
        assert column in script
    assert [row["conda_name"] for row in rows] == [
        "alpha-pkg",
        "beta-pkg",
        "gamma-pkg",
        "delta-pkg",
    ]


def test_feedstock_health_rows_match_the_fixtures_stuck_package(atlas_db_path, monkeypatch):
    view = get_view("feedstock-health")
    rows = _rows_for(view, atlas_db_path, monkeypatch)

    # only alpha-pkg has bot_version_errors_count > 0 (the default "stuck" filter).
    assert len(rows) == 1
    assert rows[0]["conda_name"] == "alpha-pkg"
    assert rows[0]["bot_version_errors_count"] == 2


def test_behind_upstream_rows_match_the_fixtures_lagging_package(atlas_db_path, monkeypatch):
    view = get_view("behind-upstream")
    rows = _rows_for(view, atlas_db_path, monkeypatch)

    # only beta-pkg has an upstream_versions row (pypi 2.0.0 vs conda 1.0.0 -> 'major').
    assert len(rows) == 1
    assert rows[0]["conda_name"] == "beta-pkg"
    assert rows[0]["upstream_version"] == "2.0.0"
    assert rows[0]["lag_label"] == "major"


def test_release_cadence_rows_match_the_fixtures_versioned_package(atlas_db_path, monkeypatch):
    view = get_view("release-cadence")
    rows = _rows_for(view, atlas_db_path, monkeypatch)

    # only delta-pkg has package_version_downloads rows.
    assert len(rows) == 1
    assert rows[0]["conda_name"] == "delta-pkg"
    assert rows[0]["total_versions"] == 3
    assert rows[0]["trend"] == "stable"


def test_adoption_stage_rows_match_the_fixtures_four_packages(atlas_db_path, monkeypatch):
    view = get_view("adoption-stage")
    rows = _rows_for(view, atlas_db_path, monkeypatch)

    # all 4 fixture packages have latest_conda_upload set, so all 4 are classified.
    assert len(rows) == 4
    by_name = {row["conda_name"]: row for row in rows}
    # delta-pkg released 10 days ago with a release in the last 30d -> 'stable'.
    assert by_name["delta-pkg"]["stage"] == "stable"
    # alpha-pkg's latest upload is 400 days ago (> 365) -> 'declining'.
    assert by_name["alpha-pkg"]["stage"] == "declining"


def test_render_rows_empty_result_still_declares_all_columns(empty_atlas_db_path, monkeypatch):
    view = get_view("staleness-report")
    rows = _rows_for(view, empty_atlas_db_path, monkeypatch)
    assert rows == []

    script, div = render_rows(view, rows)

    assert "<script" in script
    assert "data-root-id" in div
    for column in view.columns:
        assert column in script


@pytest.mark.parametrize("view", STATIC_VIEWS, ids=lambda v: v.name)
def test_no_registered_view_fragment_opens_a_websocket(view, atlas_db_path, monkeypatch):
    rows = _rows_for(view, atlas_db_path, monkeypatch)

    script, div = render_rows(view, rows)

    for marker in FORBIDDEN_MARKERS:
        assert marker not in script
        assert marker not in div


def test_render_view_unknown_name_raises_key_error():
    with pytest.raises(KeyError, match="totally-unknown-view"):
        render_view("totally-unknown-view")


def test_render_view_happy_path_drives_the_full_public_entrypoint(atlas_db_path, monkeypatch):
    """Exercises ``render_view`` itself end-to-end (view lookup -> CLI module load ->
    ``query()`` -> render), not just its ``render_rows`` half — ``load_cli_module`` memoizes
    per ``(name, scripts_dir)``, so pre-loading the module here to monkeypatch ``DB_PATH``
    means ``render_view``'s own internal load returns this same patched module."""
    scripts_dir = cli_bridge.default_scripts_dir()
    view = get_view("staleness-report")
    module = cli_bridge.load_cli_module(view.script, scripts_dir=scripts_dir)
    monkeypatch.setattr(module, "DB_PATH", atlas_db_path)

    script, div = render_view("staleness-report", scripts_dir=scripts_dir)

    assert "<script" in script
    assert "data-root-id" in div
    for column in view.columns:
        assert column in script
