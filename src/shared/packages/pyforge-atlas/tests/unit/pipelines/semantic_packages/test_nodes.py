"""``semantic_packages`` pipeline node unit tests (Story 20.3, CAP-6).

Pure-pandas join correctness + the honesty constraint the spec's Block-If clause
names: the 4 ``metrics.METRIC_PROVENANCE`` deferred-input columns must be NULL,
never fabricated, in every branch (real data, empty inputs, partial inputs).
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.semantic_packages.nodes import (
    _DEFERRED_INPUT_COLUMNS,
    _OUTPUT_COLUMNS,
    compose_semantic_packages,
)


def _by_key(df: pd.DataFrame, key: str) -> dict:
    return dict(zip(df[key], df.to_dict("records")))


def test_composes_the_declared_shape_with_real_joins():
    core_packages_enumerated = pd.DataFrame({"conda_name": ["a", "b", "c", "d"]})
    core_latest_status = pd.DataFrame(
        {"conda_name": ["a", "b", "c"], "latest_status": ["active", "active", "inactive"]}
    )
    # a -> alpha (not archived); b, c -> beta (archived); d has no attribution.
    core_feedstock_attribution = pd.DataFrame(
        {"conda_name": ["a", "b", "c"], "feedstock_name": ["alpha", "beta", "beta"]}
    )
    vcs_archived_feedstocks = pd.DataFrame({"feedstock_name": ["beta"], "archived": pd.array([1], dtype="Int64")})
    core_downloads = pd.DataFrame(
        {
            "conda_name": ["a", "b"],
            "downloads_total": pd.array([100, 200], dtype="Int64"),
            "downloads_30d": pd.array([1, 2], dtype="Int64"),
        }
    )

    out = compose_semantic_packages(
        core_packages_enumerated,
        core_latest_status,
        core_feedstock_attribution,
        vcs_archived_feedstocks,
        core_downloads,
    )

    assert list(out.columns) == list(_OUTPUT_COLUMNS)
    assert sorted(out["conda_name"]) == ["a", "b", "c", "d"]

    by_name = _by_key(out, "conda_name")

    assert by_name["a"]["latest_status"] == "active"
    assert int(by_name["a"]["feedstock_archived"]) == 0  # alpha not in the skip-set
    assert int(by_name["a"]["downloads_total"]) == 100
    assert int(by_name["a"]["downloads_30d"]) == 1

    assert int(by_name["b"]["feedstock_archived"]) == 1  # beta IS in the skip-set
    assert int(by_name["c"]["feedstock_archived"]) == 1  # shares beta with b
    assert by_name["c"]["latest_status"] == "inactive"
    assert pd.isna(by_name["c"]["downloads_total"])  # no core_downloads row for c

    # d: unattributed + unstatused + undownloaded -> honest defaults, never fabricated.
    assert pd.isna(by_name["d"]["latest_status"])
    assert int(by_name["d"]["feedstock_archived"]) == 0  # no attribution -> not archived
    assert pd.isna(by_name["d"]["downloads_total"])

    # the 4 deferred-input columns are NULL for every row, regardless of the rest of
    # the frame being populated -- the Block-If honesty constraint.
    for col in _DEFERRED_INPUT_COLUMNS:
        assert out[col].isna().all(), col


def test_never_fabricates_deferred_inputs_even_with_full_upstream_data():
    """Even when every OTHER upstream input is fully populated, the 4 deferred-input
    columns stay NULL -- no sealed-seven output carries them, so there is nothing to
    join them from, and the node must not invent a value."""
    core_packages_enumerated = pd.DataFrame({"conda_name": ["a"]})
    core_latest_status = pd.DataFrame({"conda_name": ["a"], "latest_status": ["active"]})
    core_feedstock_attribution = pd.DataFrame({"conda_name": ["a"], "feedstock_name": ["alpha"]})
    vcs_archived_feedstocks = pd.DataFrame({"feedstock_name": [], "archived": pd.array([], dtype="Int64")})
    core_downloads = pd.DataFrame(
        {
            "conda_name": ["a"],
            "downloads_total": pd.array([1], dtype="Int64"),
            "downloads_30d": pd.array([1], dtype="Int64"),
        }
    )
    out = compose_semantic_packages(
        core_packages_enumerated,
        core_latest_status,
        core_feedstock_attribution,
        vcs_archived_feedstocks,
        core_downloads,
    )
    for col in _DEFERRED_INPUT_COLUMNS:
        assert out[col].isna().all(), col
        assert out[col].dtype == "Int64", col


def test_duplicate_conda_name_across_joined_inputs_does_not_fan_out_the_population():
    """A conda_name matched more than once in an upstream table (e.g. a stale
    duplicate row) must not multiply the composed population -- one row per
    ``conda_name`` in, one row per ``conda_name`` out."""
    core_packages_enumerated = pd.DataFrame({"conda_name": ["a", "a"]})  # dup in the population itself
    core_latest_status = pd.DataFrame({"conda_name": ["a", "a"], "latest_status": ["active", "active"]})
    out = compose_semantic_packages(
        core_packages_enumerated, core_latest_status, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    assert len(out) == 1
    assert out.iloc[0]["conda_name"] == "a"


def test_empty_population_returns_the_declared_empty_shape():
    empty = pd.DataFrame()
    out = compose_semantic_packages(empty, empty, empty, empty, empty)
    assert out.empty
    assert list(out.columns) == list(_OUTPUT_COLUMNS)


def test_null_conda_name_in_population_is_dropped_not_carried_as_a_row():
    """A null conda_name in the population input (identity column) must not survive into
    the composed store as a NaN-keyed row -- there is no honest way to render a package
    with no name, so it is dropped rather than fabricated a placeholder identity."""
    core_packages_enumerated = pd.DataFrame({"conda_name": ["a", None, "b"]})
    out = compose_semantic_packages(
        core_packages_enumerated, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    assert sorted(out["conda_name"]) == ["a", "b"]
    assert not out["conda_name"].isna().any()


def test_missing_optional_upstream_frames_degrade_not_crash():
    """Every join besides the population is optional -- an absent/empty
    core_feedstock_attribution, vcs_archived_feedstocks, or core_downloads must not
    raise; the population still comes through with honest (never-fabricated) gaps."""
    core_packages_enumerated = pd.DataFrame({"conda_name": ["a", "b"]})
    out = compose_semantic_packages(
        core_packages_enumerated, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    assert sorted(out["conda_name"]) == ["a", "b"]
    assert out["latest_status"].isna().all()
    assert (out["feedstock_archived"] == 0).all()
    assert out["downloads_total"].isna().all()
    assert out["downloads_30d"].isna().all()
    for col in _DEFERRED_INPUT_COLUMNS:
        assert out[col].isna().all(), col
