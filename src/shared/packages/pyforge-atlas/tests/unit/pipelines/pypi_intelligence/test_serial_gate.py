"""Phase H serial-gate engineering-contract tests (Story B2, AC-5 / AD-10).

The 3-condition eligibility (never-fetched OR serial-moved OR 30-day safety re-check),
the pypi-only exclusion (the denominator never re-includes pypi_universe rows), the
``pypi_version_serial_at_fetch`` stamp, and the retained ``upload_time_iso_8601`` (for
B9) are proven against DataFrame fixtures — never a live endpoint (AD-11).
"""

from __future__ import annotations

import pandas as pd

from pyforge.atlas.pipelines.pypi_intelligence.nodes import (
    _PHASE_H_SAFETY_RECHECK_SECONDS,
    fetch_pypi_current_versions,
    phase_h_eligibility_stats,
)

_NOW = 1_800_000_000


def test_serial_gate_three_conditions():
    df = pd.DataFrame(
        {
            "pypi_name": ["never", "moved", "safety", "fresh"],
            "version": ["1", "2", "3", "4"],
            "pypi_last_serial": [10, 20, 30, 40],
            # never: serial_at_fetch NULL -> eligible
            # moved: last(20) != at_fetch(15) -> eligible
            # safety: equal serial but fetched_at is stale (>30d) -> eligible
            # fresh: equal serial AND fetched_at recent -> NOT eligible
            "pypi_version_serial_at_fetch": [pd.NA, 15, 30, 40],
            "fetched_at": [pd.NA, _NOW, _NOW - _PHASE_H_SAFETY_RECHECK_SECONDS - 1, _NOW - 10],
        }
    )
    uni = pd.DataFrame({"pypi_name": ["never", "moved", "safety", "fresh"], "last_serial": [10, 20, 30, 40]})
    out = fetch_pypi_current_versions(df, uni, now=_NOW)
    assert set(out["pypi_name"]) == {"never", "moved", "safety"}  # 'fresh' skipped


def test_serial_gate_stamps_serial_at_fetch_and_retains_upload_time():
    df = pd.DataFrame(
        {
            "pypi_name": ["pkg"],
            "version": ["9.9"],
            "pypi_last_serial": [777],
            "pypi_version_serial_at_fetch": [pd.NA],
            "fetched_at": [pd.NA],
            "upload_time_iso_8601": ["2026-07-01T00:00:00Z"],
        }
    )
    uni = pd.DataFrame({"pypi_name": ["pkg"], "last_serial": [777]})
    out = fetch_pypi_current_versions(df, uni, now=_NOW)
    row = out.iloc[0]
    assert row["pypi_version_serial_at_fetch"] == 777  # stamped to current serial on fetch
    assert row["upload_time_iso_8601"] == "2026-07-01T00:00:00Z"  # RETAINED for B9/FR-20


def test_denominator_never_re_includes_pypi_only_rows():
    # AC-5: the node iterates the ACTIONABLE pypi_json_raw slice ONLY. A pypi-only
    # project that lives in pypi_universe but is NOT in the actionable fetched slice
    # must never appear in the output (the pre-v7.9.0 cold-run bug).
    actionable = pd.DataFrame(
        {
            "pypi_name": ["mapped"],
            "version": ["1"],
            "pypi_last_serial": [5],
            "pypi_version_serial_at_fetch": [pd.NA],
            "fetched_at": [pd.NA],
        }
    )
    universe = pd.DataFrame(
        {"pypi_name": ["mapped", "pypi-only-a", "pypi-only-b"], "last_serial": [5, 1, 2]}
    )
    out = fetch_pypi_current_versions(actionable, universe, now=_NOW)
    assert set(out["pypi_name"]) == {"mapped"}  # pypi-only-* never re-included


def test_serial_moved_is_null_safe():
    # a NULL serial_at_fetch is caught by never-fetched, NOT mis-read as "moved";
    # a NULL current serial must not spuriously flag moved.
    df = pd.DataFrame(
        {
            "pypi_name": ["null-current"],
            "version": ["1"],
            "pypi_last_serial": [pd.NA],
            "pypi_version_serial_at_fetch": [10],
            "fetched_at": [_NOW - 10],  # recent -> not safety
        }
    )
    uni = pd.DataFrame({"pypi_name": ["null-current"], "last_serial": [pd.NA]})
    out = fetch_pypi_current_versions(df, uni, now=_NOW)
    # last_serial NULL, serial_at_fetch present, fetched recent -> NOT eligible
    assert out.empty


def test_eligibility_stats_split_sums_to_eligible():
    df = pd.DataFrame(
        {
            "pypi_name": ["never", "moved", "safety", "fresh"],
            "pypi_last_serial": [10, 20, 30, 40],
            "pypi_version_serial_at_fetch": [pd.NA, 15, 30, 40],
            "fetched_at": [pd.NA, _NOW, _NOW - _PHASE_H_SAFETY_RECHECK_SECONDS - 1, _NOW - 10],
        }
    )
    stats = phase_h_eligibility_stats(df, now=_NOW)
    assert stats["total"] == 4
    assert stats["eligible"] == 3
    assert stats["eligible_never_fetched"] == 1
    assert stats["eligible_serial_moved"] == 1
    assert stats["eligible_safety_recheck"] == 1
    # the three branch counts partition the eligible set
    assert (
        stats["eligible_never_fetched"]
        + stats["eligible_serial_moved"]
        + stats["eligible_safety_recheck"]
        == stats["eligible"]
    )
