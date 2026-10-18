"""The row-level classifiers in ``semantic.metrics`` agree with the legacy code they port.

Each expression runs on DuckDB over a Parquet round-trip (the ``parquet_table`` fixture), and
the expected value comes from an independent Python port of the legacy function, never from
the Ibis layer. Until Story 34.3 these were exercised only by the dashboard integration tests.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.semantic import metrics


def _legacy_classify(r30: int, r90: int, r365: int) -> str:
    """``release_cadence.py::_classify``, verbatim."""
    if r365 == 0:
        return "silent"
    older_60 = max(0, r90 - r30)
    if r30 == 0 and older_60 == 0:
        return "one-version" if r365 == 1 else "decelerating"
    if older_60 == 0:
        return "accelerating"
    ratio = r30 / older_60
    if ratio >= 1.5:
        return "accelerating"
    if ratio <= 0.7:
        return "decelerating"
    return "stable"


def _legacy_policy(declared: str | None, empirical: str | None) -> str:
    """``pyver_breakdown.py::policy_check_status``, verbatim."""
    if declared is None or empirical is None:
        return "unknown"

    def _key(s: str) -> tuple[int, int]:
        parts = s.split(".")
        try:
            return (int(parts[0]), int(parts[1]))
        except IndexError, ValueError:
            return (99, 99)

    d = _key(declared)
    e = _key(empirical)
    if e > d:
        return "bump-safe"
    if e < d:
        return "aggressive"
    return "aligned"


def _column(parquet_table, frame: pd.DataFrame, expr) -> list:
    t = parquet_table(frame)
    return list(t.mutate(out=expr(t)).order_by("i").execute()["out"])


RELEASES = [
    (0, 0, 0),  # silent
    (0, 0, 1),  # one-version
    (0, 0, 4),  # decelerating: nothing in 90 days
    (2, 2, 5),  # accelerating: older_60 == 0
    (3, 4, 9),  # ratio 3.0
    (1, 5, 9),  # ratio 0.25
    (2, 4, 9),  # ratio 1.0: stable
    (1, 0, 3),  # r90 < r30: older_60 clamps to 0
]


def test_release_trend_label_matches_legacy_classify(parquet_table) -> None:
    frame = pd.DataFrame(
        {
            "i": range(len(RELEASES) + 1),
            "releases_30d": pd.array([r[0] for r in RELEASES] + [None], dtype="Int64"),
            "releases_90d": pd.array([r[1] for r in RELEASES] + [None], dtype="Int64"),
            "releases_365d": pd.array([r[2] for r in RELEASES] + [None], dtype="Int64"),
        }
    )

    got = _column(parquet_table, frame, metrics.release_trend_label)

    assert got == [_legacy_classify(*r) for r in RELEASES] + ["silent"]  # a NULL count is 0


PYVERS = [
    ("3.9", "3.11"),
    ("3.11", "3.9"),
    ("3.10", "3.10"),
    (None, "3.10"),
    ("3.10", None),
]


def test_python_min_bump_status_matches_legacy_policy_check(parquet_table) -> None:
    frame = pd.DataFrame(
        {
            "i": range(len(PYVERS)),
            "declared_python_min": [d for d, _ in PYVERS],
            "empirical_floor": [e for _, e in PYVERS],
        }
    )

    got = _column(parquet_table, frame, metrics.python_min_bump_status)

    assert got == [_legacy_policy(d, e) for d, e in PYVERS]


def test_python_min_bump_status_calls_a_malformed_version_unknown(parquet_table) -> None:
    """A deliberate departure: legacy keys a malformed value as ``(99, 99)`` (``"garbage"`` reads
    as aggressive, ``"3.9.1"`` as aligned); the metric folds it to NULL and says ``unknown``."""
    frame = pd.DataFrame({"i": [0, 1], "declared_python_min": ["garbage", "3.9"], "empirical_floor": ["3.10", "3.9.1"]})

    assert _column(parquet_table, frame, metrics.python_min_bump_status) == ["unknown", "unknown"]


@pytest.mark.parametrize(
    ("column", "fn"),
    [
        ("OpenTeams_Issue_URL", metrics.has_open_teams_issue),
        ("Conda-Forge_FeedStock_URL", metrics.has_feedstock),
        ("Staged_Recipes_PR_URL", metrics.has_staged_pr),
        ("Local_Recipes_URL", metrics.has_local_recipe),
    ],
)
def test_identity_presence_flags_treat_blank_and_null_as_absent(parquet_table, column, fn) -> None:
    frame = pd.DataFrame({"i": [0, 1, 2], column: ["https://example.invalid/x", "", None]})

    assert _column(parquet_table, frame, fn) == [True, False, False]


def test_identity_local_build_status_names_a_blank_status(parquet_table) -> None:
    frame = pd.DataFrame({"i": [0, 1, 2], "Local_Build_Status": ["built", "", None]})

    assert _column(parquet_table, frame, metrics.identity_local_build_status) == ["built", "blank", "blank"]
