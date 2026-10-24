"""Story 38.1 (CAP-69): the semantic store reads its upload times and archived flag.

Expected values are hand-derived from legacy ``adoption_stage.py`` (``age_days = (now - latest_conda_upload) // 86400``,
none for a falsy upload time; ``total_versions`` / ``releases_30d`` from ``package_version_downloads``) and legacy
Phase B's ``latest_conda_upload`` -- not imported, since those modules live in
``.claude/skills/conda-forge-expert/scripts/``. No network.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.pipelines.derived_artifacts.lifecycle import (
    project_graph_archived_feedstocks,
    project_version_downloads,
)
from pyforge.atlas.pipelines.derived_artifacts.release_cadence import project_release_cadence
from pyforge.atlas.pipelines.semantic_packages import create_pipeline
from pyforge.atlas.pipelines.semantic_packages.nodes import compose_semantic_packages
from pyforge.atlas.semantic import models

NOW = 1_800_000_000
DAY = 86_400


def _uploads(rows: list[tuple[str, str, int | None, int | None]]) -> pd.DataFrame:
    """(name, version, earliest file time, latest file time)."""
    frame = pd.DataFrame(rows, columns=["conda_name", "version", "upload_unix", "last_upload_unix"])
    for col in ("upload_unix", "last_upload_unix"):
        frame[col] = frame[col].astype("Int64")
    frame["file_count"] = 1
    return frame


def _enumerated(pairs: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame({"conda_name": [n for n, _ in pairs], "latest_version": [v for _, v in pairs]})


def _compose(names: list[str], cadence=None, graph_archived=None, vcs_archived=None, attribution=None) -> pd.DataFrame:
    return compose_semantic_packages(
        pd.DataFrame({"conda_name": names}),
        pd.DataFrame({"conda_name": names, "latest_status": ["active"] * len(names)}),
        attribution if attribution is not None else pd.DataFrame({"conda_name": names, "feedstock_name": names}),
        vcs_archived if vcs_archived is not None else pd.DataFrame({"feedstock_name": [], "archived": []}),
        pd.DataFrame({"conda_name": names, "downloads_total": [1] * len(names), "downloads_30d": [1] * len(names)}),
        cadence,
        graph_archived,
        now=NOW,
    )


def _rows(out: pd.DataFrame) -> dict[str, dict]:
    return {r["conda_name"]: r for r in out.to_dict("records")}


# --------------------------------------------------------------------------- #
# latest_conda_upload in the cadence
# --------------------------------------------------------------------------- #


def test_the_latest_upload_is_the_newest_file_of_the_enumerated_latest_version() -> None:
    uploads = _uploads(
        [
            ("a", "1.0", NOW - 100 * DAY, NOW - 90 * DAY),
            ("a", "2.0", NOW - 20 * DAY, NOW - 5 * DAY),  # the latest version, rebuilt 5 days ago
            ("b", "1.0", NOW - 10 * DAY, NOW - 10 * DAY),
            ("b", "0.9", None, None),  # untimed
            ("c", "3.0", None, None),  # the latest version, untimed
            ("c", "2.0", NOW - 400 * DAY, NOW - 400 * DAY),
        ]
    )
    enumerated = _enumerated([("a", "2.0"), ("b", "1.0"), ("c", "3.0")])

    out = _rows(project_release_cadence(uploads, enumerated, now=NOW))

    assert out["a"]["latest_conda_upload"] == NOW - 5 * DAY  # the newest file, not the version's first
    assert out["b"]["latest_conda_upload"] == NOW - 10 * DAY
    assert pd.isna(out["c"]["latest_conda_upload"])  # the latest version has no timed file


def test_the_latest_upload_needs_the_latest_version_and_the_last_file_time() -> None:
    uploads = _uploads([("a", "1.0", NOW - DAY, NOW - DAY)])

    no_version = project_release_cadence(uploads, pd.DataFrame({"conda_name": ["a"]}), now=NOW)
    old_store = project_release_cadence(uploads.drop(columns="last_upload_unix"), _enumerated([("a", "1.0")]), now=NOW)

    assert pd.isna(no_version["latest_conda_upload"]).all() and pd.isna(old_store["latest_conda_upload"]).all()
    assert str(no_version["latest_conda_upload"].dtype) == "Int64"


# --------------------------------------------------------------------------- #
# the semantic store
# --------------------------------------------------------------------------- #


def test_the_store_reads_its_upload_inputs_from_the_cadence() -> None:
    cadence = pd.DataFrame(
        {
            "conda_name": ["a", "z"],
            "latest_conda_upload": pd.array([NOW - 10 * DAY - 50_000, 0], dtype="Int64"),  # 10.58 days
            "releases_30d": [2, 0],
            "total_versions": [7, 1],
        }
    )

    out = _rows(_compose(["a", "z", "x"], cadence=cadence))

    a = out["a"]
    assert (a["latest_conda_upload"], a["releases_30d"], a["total_versions"]) == (NOW - 10 * DAY - 50_000, 2, 7)
    assert a["latest_upload_age_days"] == 10  # (now - ts) // 86400: floored, never rounded
    assert pd.isna(out["z"]["latest_upload_age_days"])  # an upload time of 0 is none, as legacy reads it
    for col in ("latest_conda_upload", "latest_upload_age_days", "releases_30d", "total_versions"):
        assert pd.isna(out["x"][col]), col  # not in the cadence: NULL, never fabricated


@pytest.mark.parametrize(
    ("graph", "vcs", "archived"),
    [(["fs-a"], [], 1), ([], ["fs-a"], 1), ([], [], 0)],
    ids=["cf-graph-only", "github-only", "neither"],
)
def test_the_archived_flag_reads_either_source(graph, vcs, archived) -> None:
    attribution = pd.DataFrame({"conda_name": ["a"], "feedstock_name": ["fs-a"]})
    out = _compose(
        ["a"],
        graph_archived=pd.DataFrame({"feedstock_name": graph, "archived": [True] * len(graph)}),
        vcs_archived=pd.DataFrame({"feedstock_name": vcs, "archived": [1] * len(vcs)}),
        attribution=attribution,
    )

    assert int(out["feedstock_archived"].iloc[0]) == archived


def test_the_archived_flag_is_the_union_of_both_sources() -> None:
    attribution = pd.DataFrame({"conda_name": ["a", "b", "c"], "feedstock_name": ["fs-a", "fs-b", "fs-c"]})
    out = _compose(
        ["a", "b", "c"],
        graph_archived=pd.DataFrame({"feedstock_name": ["fs-a"], "archived": [True]}),
        vcs_archived=pd.DataFrame({"feedstock_name": ["fs-b"], "archived": [1]}),
        attribution=attribution,
    )

    assert dict(zip(out["conda_name"], out["feedstock_archived"], strict=True)) == {"a": 1, "b": 1, "c": 0}


def test_the_cadence_columns_are_nullable_integers() -> None:
    cadence = pd.DataFrame(
        {"conda_name": ["a"], "latest_conda_upload": [NOW - DAY], "releases_30d": [1], "total_versions": [2]}
    )

    out = _compose(["a", "x"], cadence=cadence)

    for col in ("latest_conda_upload", "latest_upload_age_days", "releases_30d", "total_versions"):
        assert str(out[col].dtype) == "Int64", col


def test_the_pipeline_reads_the_two_produced_inputs_and_no_raw_source() -> None:
    inputs = create_pipeline().inputs()

    assert {"derived_release_cadence", "derived_graph_archived_feedstocks"} <= inputs
    assert not any(name.endswith("_raw") for name in inputs)


def test_the_adoption_stage_classifies_the_composed_store(tmp_path: Path) -> None:
    cadence = pd.DataFrame(
        {
            "conda_name": ["fresh", "busy", "old", "gone"],
            "latest_conda_upload": pd.array(
                [NOW - 10 * DAY, NOW - DAY, NOW - 800 * DAY, NOW - 400 * DAY], dtype="Int64"
            ),
            "releases_30d": [1, 4, 0, 0],
            "total_versions": [3, 9, 2, 2],
        }
    )
    composed = _compose(["fresh", "busy", "old", "gone", "none"], cadence=cadence)
    path = tmp_path / "semantic_packages.parquet"
    composed.to_parquet(path, index=False)

    model = models.build_packages_model(models.duckdb_table_from_parquet(str(path)), now_unix=NOW)
    out = model.query(
        dimensions=["conda_name", "adoption_stage", "staleness_age_days"], measures=["package_count"]
    ).execute()

    stages = dict(zip(out["conda_name"], out["adoption_stage"], strict=True))
    assert stages == {
        "fresh": "stable",
        "busy": "bleeding-edge",
        "old": "silent",
        "gone": "declining",
        "none": "unknown",
    }
    ages = dict(zip(out["conda_name"], out["staleness_age_days"], strict=True))
    assert ages["fresh"] == 10 and pd.isna(ages["none"])


# --------------------------------------------------------------------------- #
# the two lifecycle projections
# --------------------------------------------------------------------------- #


def test_the_graph_archived_set_is_every_flagged_feedstock() -> None:
    graph = pd.DataFrame(
        {
            "feedstock_name": ["old", "old", "live", "none-flag", "nan-flag", "na-flag", None],
            "conda_name": ["old", "old-dev", "live", "x", "w", "v", "y"],
            "feedstock_archived": [True, True, False, None, float("nan"), pd.NA, True],
        }
    )

    out = project_graph_archived_feedstocks(graph)

    assert out.to_dict("records") == [{"feedstock_name": "old", "archived": True}]
    assert project_graph_archived_feedstocks(None).empty and project_graph_archived_feedstocks(graph.iloc[:0]).empty
    assert project_graph_archived_feedstocks(graph.drop(columns="feedstock_archived")).empty


def test_version_downloads_carry_the_utc_upload_date(tmp_path: Path) -> None:
    history = pd.DataFrame({"conda_name": ["a", "a", "b"], "version": ["1", "2", "1"], "downloads": [10, 20, 5]})
    uploads = _uploads([("a", "1", 1_700_000_000, 1_700_000_000), ("a", "2", None, None)])  # 2023-11-14 22:13 UTC

    out = project_version_downloads(history, uploads)

    dates = {(r["conda_name"], r["version"]): r["upload_date"] for r in out.to_dict("records")}
    assert dates == {("a", "1"): date(2023, 11, 14), ("a", "2"): None, ("b", "1"): None}
    assert out["downloads"].tolist() == [10, 20, 5]
    out.to_parquet(tmp_path / "v.parquet", index=False)  # the date column writes
    model = models.build_version_downloads_model(models.duckdb_table_from_parquet(str(tmp_path / "v.parquet")))
    q = model.query(dimensions=["conda_name", "version", "upload_date"], measures=["downloads"]).execute()
    assert len(q) == 3


def test_version_downloads_with_no_upload_store_keep_a_null_date() -> None:
    history = pd.DataFrame({"conda_name": ["a"], "version": ["1"], "downloads": [10]})

    out = project_version_downloads(history, None)

    assert out["upload_date"].isna().all() and list(out.columns) == [
        "conda_name",
        "version",
        "downloads",
        "upload_date",
    ]
    assert project_version_downloads(None, None).empty and project_version_downloads(history.iloc[:0], None).empty
    assert project_version_downloads(history.drop(columns="downloads"), None).empty
