"""FR-20 release-to-availability velocity node tests (Story B9; NEW-SIGNAL, AD-14).

Two MANDATORY failure-mode fixtures (spec § 9 Story B9):
  1. the 90-day recency guard (the false "47% behind" classification cannot recur), and
  2. rebuild-inside-window invariance (MIN timestamp = first availability, so a second
     build of the same version inside the window does NOT shift the lag).

Plus matched-version-only, malformed/empty safety, ms→s boundary, tz-naive parsing, and
clock-skew (negative-lag) coverage. The population calibration numbers (median ≈ 8.9 h,
72.4% within 24 h, 83.7% within 72 h) are a CALIBRATION REFERENCE only — never asserted.
"""

from __future__ import annotations

import math

import pandas as pd

from pyforge.atlas.pipelines.vcs_health.nodes import derive_release_velocity

# Deterministic clock so the 90-day recency gate is reproducible (2023-11-14 UTC).
_NOW = 1_700_000_000
_HOUR = 3600
_DAY = 86_400


def _iso(epoch_s: int) -> str:
    """UTC ISO-8601 (Z-suffixed) for an epoch-seconds instant — the PyPI shape."""
    return pd.Timestamp(epoch_s, unit="s", tz="UTC").isoformat()


def _pcv(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["pypi_name", "version", "upload_time_iso_8601"])


def _repo(rows: list[dict]) -> pd.DataFrame:
    # repodata per-build `timestamp` is MILLISECONDS.
    return pd.DataFrame(rows, columns=["conda_name", "version", "timestamp"])


def _map(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["pypi_name", "conda_name"])


_COLS = ["pypi_name", "conda_name", "version", "release_lag_hours", "release_lag_qualifies"]


# -- happy path + ms→s boundary ---------------------------------------------

def test_matched_version_lag_and_ms_to_seconds_boundary():
    upload_s = _NOW - 2 * _DAY          # released 2 days ago (within 90 d → qualifies)
    avail_s = upload_s + 6 * _HOUR      # conda-forge published 6 h later
    pcv = _pcv([{"pypi_name": "foo", "version": "1.2.3", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "foo", "version": "1.2.3", "timestamp": avail_s * 1000}])  # ms
    mp = _map([{"pypi_name": "foo", "conda_name": "foo"}])
    out = derive_release_velocity(pcv, repo, mp, now=_NOW)
    assert list(out.columns) == _COLS
    assert len(out) == 1
    row = out.iloc[0]
    # 6 h lag — proves the ms→s conversion happened exactly once (not doubled/missing).
    assert math.isclose(row["release_lag_hours"], 6.0, abs_tol=1e-6)
    assert row["release_lag_qualifies"] is True or bool(row["release_lag_qualifies"]) is True


def test_seconds_magnitude_timestamp_is_not_divided():
    # A timestamp already below the ms threshold (epoch seconds) must pass through as-is.
    upload_s = _NOW - _DAY
    avail_s = upload_s + 3 * _HOUR
    pcv = _pcv([{"pypi_name": "foo", "version": "9.9", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "foo", "version": "9.9", "timestamp": avail_s}])  # seconds
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "foo", "conda_name": "foo"}]), now=_NOW)
    assert math.isclose(out.iloc[0]["release_lag_hours"], 3.0, abs_tol=1e-6)


# -- MANDATORY 1: the 90-day recency guard ----------------------------------

def test_ninety_day_guard_stale_release_does_not_qualify():
    # A version-unchanged package whose UPSTREAM release is >90 days old: the row still
    # exists (matched version) and a lag is computed, but qualifies MUST be False — the
    # rebuild-cadence artifact that produced the false "47% behind" cannot recur.
    upload_s = _NOW - 200 * _DAY        # released 200 days ago (> 90 d)
    avail_s = upload_s + 5 * _HOUR
    pcv = _pcv([{"pypi_name": "old", "version": "1.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "old", "version": "1.0", "timestamp": avail_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "old", "conda_name": "old"}]), now=_NOW)
    assert len(out) == 1
    assert bool(out.iloc[0]["release_lag_qualifies"]) is False


def test_ninety_day_boundary_recent_release_qualifies():
    # A release exactly inside the window (89 days) qualifies — guards an off-by-one /
    # inverted gate.
    upload_s = _NOW - 89 * _DAY
    avail_s = upload_s + 2 * _HOUR
    pcv = _pcv([{"pypi_name": "recent", "version": "2.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "recent", "version": "2.0", "timestamp": avail_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "recent", "conda_name": "recent"}]), now=_NOW)
    assert bool(out.iloc[0]["release_lag_qualifies"]) is True


# -- MANDATORY 2: rebuild-inside-window invariance (MIN = first availability) ---

def test_rebuild_inside_window_does_not_shift_lag():
    # Two builds of the SAME (conda_name, version): the first is the true first
    # availability; a later rebuild lands INSIDE the 90-day window. The lag MUST use the
    # EARLIER build (MIN timestamp), never the latest upload — otherwise a migration/ABI
    # rebuild would inflate the lag exactly as `latest_conda_upload` did.
    upload_s = _NOW - 10 * _DAY
    first_avail = upload_s + 4 * _HOUR       # first build: 4 h after upstream
    rebuild = upload_s + 40 * _DAY           # rebuild: 40 days later, still inside window
    pcv = _pcv([{"pypi_name": "pkg", "version": "3.1", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo(
        [
            {"conda_name": "pkg", "version": "3.1", "timestamp": rebuild * 1000},       # later row first
            {"conda_name": "pkg", "version": "3.1", "timestamp": first_avail * 1000},
        ]
    )
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "pkg", "conda_name": "pkg"}]), now=_NOW)
    assert len(out) == 1
    # 4 h — the FIRST-availability lag, unmoved by the 40-day rebuild.
    assert math.isclose(out.iloc[0]["release_lag_hours"], 4.0, abs_tol=1e-6)


# -- matched-version-only ----------------------------------------------------

def test_unmatched_version_produces_no_row():
    # conda side carries a DIFFERENT version than the current PyPI release → no match,
    # no lag row (lag computed ONLY for the matched version).
    upload_s = _NOW - _DAY
    pcv = _pcv([{"pypi_name": "foo", "version": "2.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": upload_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "foo", "conda_name": "foo"}]), now=_NOW)
    assert out.empty
    assert list(out.columns) == _COLS


def test_unmapped_pypi_name_produces_no_row():
    upload_s = _NOW - _DAY
    pcv = _pcv([{"pypi_name": "foo", "version": "1.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": upload_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([]), now=_NOW)  # empty mapping
    assert out.empty


def test_pypi_conda_name_differ_via_mapping():
    # The two sides key on DIFFERENT name columns; the mapping bridges them.
    upload_s = _NOW - _DAY
    avail_s = upload_s + _HOUR
    pcv = _pcv([{"pypi_name": "Pillow", "version": "10.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "pillow", "version": "10.0", "timestamp": avail_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "Pillow", "conda_name": "pillow"}]), now=_NOW)
    assert len(out) == 1
    assert out.iloc[0]["conda_name"] == "pillow"
    assert math.isclose(out.iloc[0]["release_lag_hours"], 1.0, abs_tol=1e-6)


# -- AD-13 safety: malformed / missing / empty ------------------------------

def test_malformed_upload_time_yields_nan_lag_and_false_qualifies():
    avail_s = _NOW - _DAY
    pcv = _pcv([{"pypi_name": "foo", "version": "1.0", "upload_time_iso_8601": "not-a-date"}])
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": avail_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "foo", "conda_name": "foo"}]), now=_NOW)
    assert len(out) == 1
    assert math.isnan(out.iloc[0]["release_lag_hours"])
    assert bool(out.iloc[0]["release_lag_qualifies"]) is False


def test_tz_naive_upload_time_parses_as_utc():
    upload_s = _NOW - _DAY
    avail_s = upload_s + 2 * _HOUR
    # tz-NAIVE ISO (no Z / offset) — must be assumed UTC, not raise.
    naive = pd.Timestamp(upload_s, unit="s").isoformat()  # no tz
    pcv = _pcv([{"pypi_name": "foo", "version": "1.0", "upload_time_iso_8601": naive}])
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": avail_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "foo", "conda_name": "foo"}]), now=_NOW)
    assert math.isclose(out.iloc[0]["release_lag_hours"], 2.0, abs_tol=1e-6)
    assert bool(out.iloc[0]["release_lag_qualifies"]) is True


def test_negative_lag_on_clock_skew_is_reported_not_dropped():
    # conda build predating the PyPI upload (clock skew / backport): a negative lag is a
    # data-quality SIGNAL, reported raw — the row is not dropped and does not crash.
    upload_s = _NOW - _DAY
    avail_s = upload_s - 2 * _HOUR      # conda "available" 2 h BEFORE upstream upload
    pcv = _pcv([{"pypi_name": "foo", "version": "1.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": avail_s * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "foo", "conda_name": "foo"}]), now=_NOW)
    assert math.isclose(out.iloc[0]["release_lag_hours"], -2.0, abs_tol=1e-6)


def test_empty_inputs_return_columned_empty_frame():
    empty = pd.DataFrame()
    out = derive_release_velocity(empty, empty, empty, now=_NOW)
    assert out.empty
    assert list(out.columns) == _COLS


def test_missing_columns_return_columned_empty_frame():
    # A non-empty but mis-shaped input (missing upload_time_iso_8601) degrades cleanly.
    pcv = pd.DataFrame({"pypi_name": ["foo"], "version": ["1.0"]})
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": _NOW * 1000}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "foo", "conda_name": "foo"}]), now=_NOW)
    assert out.empty and list(out.columns) == _COLS


def test_malformed_conda_timestamp_yields_nan_lag_and_false_qualifies():
    # A recent, valid upstream upload but an UNPARSEABLE conda `timestamp`: the lag can't
    # be computed (NaN), so the row must NOT qualify. A qualifying row that carries a NaN
    # lag would pollute any downstream aggregation over the qualifying population
    # (AD-13 "malformed → qualifies False"; B9 Edge-Case-Hunter review).
    upload_s = _NOW - _DAY  # 1 day old -> well within the 90-day gate
    pcv = _pcv([{"pypi_name": "foo", "version": "1.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": "not-a-number"}])
    out = derive_release_velocity(pcv, repo, _map([{"pypi_name": "foo", "conda_name": "foo"}]), now=_NOW)
    assert len(out) == 1
    assert math.isnan(out.iloc[0]["release_lag_hours"])
    assert out.iloc[0]["release_lag_qualifies"] is False or out.iloc[0]["release_lag_qualifies"] == False  # noqa: E712


def test_empty_frame_has_bool_and_float_dtypes():
    # the empty return must match the non-empty path's dtypes (bool / float64), else a
    # schema-typed parquet sink or a concat with a populated result mismatches (B9 review).
    out = derive_release_velocity(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), now=_NOW)
    assert out.empty and list(out.columns) == _COLS
    assert out["release_lag_qualifies"].dtype == bool
    assert str(out["release_lag_hours"].dtype) == "float64"


def test_duplicate_name_version_rows_deduped():
    upload_s = _NOW - _DAY
    avail_s = upload_s + _HOUR
    pcv = _pcv([{"pypi_name": "foo", "version": "1.0", "upload_time_iso_8601": _iso(upload_s)}])
    repo = _repo([{"conda_name": "foo", "version": "1.0", "timestamp": avail_s * 1000}])
    # duplicate mapping rows must not fan out to duplicate output rows.
    mp = _map([{"pypi_name": "foo", "conda_name": "foo"}, {"pypi_name": "foo", "conda_name": "foo"}])
    out = derive_release_velocity(pcv, repo, mp, now=_NOW)
    assert len(out) == 1


# -- AD-14 parity boundary (new-signal, never parity-gated) ------------------

def test_output_dataset_is_in_the_frozen_new_signal_exclusion_set():
    from pyforge.atlas.parity import EXCLUDED_NEW_SIGNAL_DATASETS
    from pyforge.atlas.parity.legacy_surface import parity_scoped_kedro_datasets

    assert "vcs_release_velocity" in EXCLUDED_NEW_SIGNAL_DATASETS
    # the frozen set stays len==3 (B9 aligned to an ALREADY-present name; added none).
    assert len(EXCLUDED_NEW_SIGNAL_DATASETS) == 3
    # never a legacy-surface parity dataset.
    assert parity_scoped_kedro_datasets() & EXCLUDED_NEW_SIGNAL_DATASETS == set()
