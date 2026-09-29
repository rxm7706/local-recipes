"""Story 14.1 (CAP-1) — the curated static-view catalog.

Covers the I/O matrix's UNKNOWN_VIEW row, plus two structural cross-checks against each
CLI's real ``query()``: that every curated ``View.query_kwargs`` is actually accepted as an
INPUT (catching a stale/misspelled kwarg before it becomes a runtime ``TypeError``), and that
every curated ``View.columns`` is actually present in the real OUTPUT row keys (catching a
CLI SELECT-column rename before it silently renders a blank column — ``render.py::
render_rows`` uses ``row.get(column)``, which returns ``None`` rather than failing).
"""

from __future__ import annotations

import inspect

import pytest

from pyforge.atlas.views import cli_bridge
from pyforge.atlas.views.registry import STATIC_VIEWS, View, get_view

EXPECTED_VIEW_NAMES = (
    "staleness-report",
    "feedstock-health",
    "behind-upstream",
    "cve-watcher",
    "release-cadence",
    "adoption-stage",
)


def test_static_views_is_exactly_the_six_zero_arg_clis():
    assert tuple(view.name for view in STATIC_VIEWS) == EXPECTED_VIEW_NAMES


def test_every_view_declares_stable_nonempty_columns():
    for view in STATIC_VIEWS:
        assert isinstance(view, View)
        assert isinstance(view.columns, tuple)
        assert view.columns, f"{view.name}: columns must be declared (stable even on 0 rows)"


@pytest.mark.parametrize("view", STATIC_VIEWS, ids=lambda v: v.name)
def test_query_kwargs_are_accepted_by_the_clis_real_query_signature(view):
    module = cli_bridge.load_cli_module(view.script, scripts_dir=cli_bridge.default_scripts_dir())
    accepted = set(inspect.signature(module.query).parameters)
    unknown = set(view.query_kwargs) - accepted
    assert not unknown, (
        f"{view.name}: query_kwargs {unknown} are not accepted by "
        f"{view.script}.query(){inspect.signature(module.query)}"
    )


@pytest.mark.parametrize("view", STATIC_VIEWS, ids=lambda v: v.name)
def test_view_columns_are_a_subset_of_the_clis_real_output_keys(view, atlas_db_path, monkeypatch):
    """Output-key parity — the counterpart to the query_kwargs INPUT-parity check above.
    Guards against a future CLI SELECT-column rename silently rendering a blank column."""
    module = cli_bridge.load_cli_module(view.script, scripts_dir=cli_bridge.default_scripts_dir())
    monkeypatch.setattr(module, "DB_PATH", atlas_db_path)

    rows = cli_bridge.call_query(module, **view.query_kwargs)

    assert rows, f"{view.name}: fixture must produce >=1 row to check column parity"
    missing = set(view.columns) - set(rows[0].keys())
    assert not missing, (
        f"{view.name}: declared columns {missing} are absent from {view.script}.query()'s "
        f"real output keys {set(rows[0].keys())}"
    )


def test_get_view_returns_the_named_view():
    view = get_view("staleness-report")
    assert view.name == "staleness-report"
    assert view.script == "staleness_report"


def test_get_view_unknown_name_raises_key_error_naming_the_unknown_view():
    with pytest.raises(KeyError, match="not-a-real-view"):
        get_view("not-a-real-view")
