"""Story 37.10 — the bootstrap-index-health table: tiers, floors and status."""

from __future__ import annotations

import pandas as pd
import pytest
from kedro.framework.project import configure_project

from pyforge.atlas.pipeline_registry import AFTER_RUN_PIPELINES, register_pipelines
from pyforge.atlas.pipelines.catalog_index.nodes import CATALOG_INDEX_HEALTH_COLUMNS, report_catalog_index_health

WRITTEN = pd.Timestamp("2026-10-23T00:00:00Z")
PARAMS = {
    "tiers": {"core_packages_enumerated": "Tier 0", "discovery_homebrew_packages_raw": "Tier 3"},
    "floors": {"core_packages_enumerated": 30000},
}


def _index(rows: list[tuple]) -> pd.DataFrame:
    """``(entry, written, rows, stale, reason)`` as the catalog index."""
    return pd.DataFrame(
        [
            {
                "catalog_entry": entry,
                "layer": "primary",
                "relpath": f"primary/{entry}",
                "regenerated_at": written,
                "row_count": count,
                "stale": stale,
                "stale_reason": reason,
            }
            for entry, written, count, stale, reason in rows
        ]
    )


def _health(rows: list[tuple], params=PARAMS) -> dict[str, dict]:
    out = report_catalog_index_health(_index(rows), params)
    assert list(out.columns) == CATALOG_INDEX_HEALTH_COLUMNS
    return {row["catalog_entry"]: row for row in out.to_dict("records")}


@pytest.mark.parametrize(
    ("written", "count", "stale", "status"),
    [
        (None, None, False, "missing"),
        (WRITTEN, 40000, True, "stale"),
        (WRITTEN, 0, False, "empty"),
        (WRITTEN, 29999, False, "below_floor"),
        (WRITTEN, 30000, False, "ok"),
        (WRITTEN, None, False, "ok"),
    ],
)
def test_the_status(written, count, stale, status):
    row = _health([("core_packages_enumerated", written, count, stale, "r" if stale else None)])[
        "core_packages_enumerated"
    ]
    assert row["status"] == status


def test_missing_wins_over_a_stale_marker():
    assert _health([("x", None, None, True, "absent")])["x"]["status"] == "missing"


def test_tiers_and_floors_come_from_the_params():
    got = _health([("core_packages_enumerated", WRITTEN, 40000, False, None), ("other", WRITTEN, 1, False, None)])
    assert got["core_packages_enumerated"]["tier"] == "Tier 0"
    assert got["core_packages_enumerated"]["floor"] == 30000
    assert got["other"]["tier"] == "untiered"
    assert pd.isna(got["other"]["floor"])


def test_the_index_leaves_out_its_own_output():
    got = _health([("catalog_index_health", WRITTEN, 3, False, None), ("x", WRITTEN, 1, False, None)])
    assert set(got) == {"x"}


def test_tiered_entries_sort_first_by_tier():
    out = report_catalog_index_health(
        _index(
            [
                ("aaa_untiered", WRITTEN, 1, False, None),
                ("discovery_homebrew_packages_raw", WRITTEN, 1, False, None),
                ("core_packages_enumerated", WRITTEN, 40000, False, None),
            ]
        ),
        PARAMS,
    )
    assert list(out["catalog_entry"]) == ["core_packages_enumerated", "discovery_homebrew_packages_raw", "aaa_untiered"]


@pytest.mark.parametrize("index", [None, pd.DataFrame()])
def test_an_empty_index_gives_an_empty_typed_table(index):
    out = report_catalog_index_health(index, PARAMS)
    assert out.empty and list(out.columns) == CATALOG_INDEX_HEALTH_COLUMNS
    assert str(out["row_count"].dtype) == "Int64"


def test_the_board_reads_the_table(tmp_path):
    from pyforge.atlas.dashboard import data as dash_data

    out = report_catalog_index_health(
        _index([("core_packages_enumerated", WRITTEN, 10, False, None), ("never", None, None, False, None)]), PARAMS
    )
    path = tmp_path / "catalog_index_health.parquet"
    out.to_parquet(path, index=False)
    board = dash_data.load_bootstrap_index_health(path)
    assert set(board["status"]) == {"below_floor", "missing"}


def test_catalog_index_runs_after_the_build_never_inside_default():
    configure_project("pyforge.atlas")
    pipelines = register_pipelines()
    assert "catalog_index" in AFTER_RUN_PIPELINES
    assert "catalog_index" in pipelines
    default = {n.name for n in pipelines["__default__"].nodes}
    assert "report_catalog_index_health" not in default
    assert {n.name for n in pipelines["catalog_index"].nodes} == {"report_catalog_index_health"}
