"""Story 37.6 (CAP-69): the release-cadence counts per package.

Expected values are hand-derived from legacy ``release_cadence.py``'s query (``COUNT(*)`` versions, ``upload_unix >=
now - N * 86400`` per window, ``ORDER BY upload_unix DESC LIMIT 1`` for the latest version) -- not imported, since that
module lives in a separate tree, ``.claude/skills/conda-forge-expert/scripts/``. No network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pyforge.atlas.pipelines.derived_artifacts.release_cadence import COLUMNS, project_release_cadence
from pyforge.atlas.semantic import models
from pyforge.atlas.semantic.query_helpers import bsl_query

NOW = 1_800_000_000
DAY = 86_400


def _uploads(rows: list[tuple[str, str, int | None]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=["conda_name", "version", "upload_unix"])
    frame["upload_unix"] = frame["upload_unix"].astype("Int64")
    frame["file_count"] = 1
    return frame


def _enumerated(*names: str) -> pd.DataFrame:
    return pd.DataFrame({"conda_name": list(names), "latest_version": ["x"] * len(names)})


def _by_name(out: pd.DataFrame) -> dict[str, dict]:
    return {row["conda_name"]: row for row in out.to_dict("records")}


def test_each_window_counts_the_versions_uploaded_on_or_after_its_cutoff() -> None:
    uploads = _uploads(
        [
            ("a", "1", NOW - 30 * DAY),  # exactly the 30-day cutoff: in
            ("a", "2", NOW - 30 * DAY - 1),  # a second earlier: out of 30, in 90
            ("a", "3", NOW - 90 * DAY),  # the 90-day cutoff
            ("a", "4", NOW - 365 * DAY),  # the 365-day cutoff
            ("a", "5", NOW - 365 * DAY - 1),  # older than a year
            ("a", "6", None),  # untimed: in total_versions, in no window
        ]
    )

    (row,) = project_release_cadence(uploads, _enumerated("a"), now=NOW).to_dict("records")

    assert (row["total_versions"], row["releases_30d"], row["releases_90d"], row["releases_365d"]) == (6, 1, 3, 4)
    assert (row["first_upload"], row["last_upload"]) == (NOW - 365 * DAY - 1, NOW - 30 * DAY)


def test_the_latest_version_is_the_last_uploaded_then_the_larger_string() -> None:
    uploads = _uploads(
        [
            ("a", "1.0", NOW - 5 * DAY),
            ("a", "0.9", NOW - 1 * DAY),  # uploaded last, though a smaller version
            ("a", "2.0", None),  # untimed: never the latest while a timed one exists
            ("b", "1.0", NOW - DAY),
            ("b", "1.1", NOW - DAY),  # a tie: the larger string
            ("c", "3", None),  # only untimed versions: the larger string
            ("c", "4", None),
        ]
    )

    out = _by_name(project_release_cadence(uploads, _enumerated("a", "b", "c"), now=NOW))

    assert {n: r["latest_version"] for n, r in out.items()} == {"a": "0.9", "b": "1.1", "c": "4"}
    assert pd.isna(out["c"]["first_upload"]) and out["c"]["releases_365d"] == 0


def test_only_enumerated_packages_are_counted() -> None:
    uploads = _uploads([("a", "1", NOW), ("gone", "1", NOW)])

    out = project_release_cadence(uploads, _enumerated("a"), now=NOW)

    assert out["conda_name"].tolist() == ["a"]


def test_nothing_in_gives_a_typed_empty_frame(tmp_path: Path) -> None:
    for out in (
        project_release_cadence(None, None, now=NOW),
        project_release_cadence(_uploads([]), _enumerated("a"), now=NOW),
        project_release_cadence(_uploads([("x", "1", NOW)]), _enumerated("a"), now=NOW),
    ):
        assert out.empty and list(out.columns) == COLUMNS
        out.to_parquet(tmp_path / "e.parquet", index=False)
        back = pd.read_parquet(tmp_path / "e.parquet")
        assert str(back["releases_30d"].dtype) == "int64" and str(back["last_upload"].dtype) == "Int64"


def test_the_board_classifies_the_counts_with_legacys_trend(tmp_path: Path) -> None:
    uploads = _uploads(
        [
            ("acc", "1", NOW - DAY),
            ("acc", "2", NOW - 2 * DAY),  # 2 in 30 days, none in the 60 before: accelerating
            ("one", "1", NOW - 200 * DAY),  # one release in a year, none lately: one-version
            ("old", "1", NOW - 400 * DAY),  # nothing in a year: silent
        ]
    )
    out = project_release_cadence(uploads, _enumerated("acc", "one", "old"), now=NOW)
    path = tmp_path / "cadence.parquet"
    out.to_parquet(path, index=False)

    model = models.build_release_cadence_model(models.duckdb_table_from_parquet(str(path)))
    board = bsl_query(model, dimensions=["conda_name", "trend_label"], measures=["release_count_30d"])

    assert dict(zip(board["conda_name"], board["trend_label"], strict=True)) == {
        "acc": "accelerating",
        "one": "one-version",
        "old": "silent",
    }
