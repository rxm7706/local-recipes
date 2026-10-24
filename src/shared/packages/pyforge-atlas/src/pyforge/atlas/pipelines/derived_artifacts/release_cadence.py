"""The release-cadence counts per package (Story 37.6, CAP-69).

A port of legacy ``release_cadence.py``'s query over ``package_version_downloads``: per package, the versions and the
ones uploaded in the last 30, 90 and 365 days (``upload_unix >= now - N days``), the first and last upload and the
version last uploaded. The trend label stays the board's: ``metrics.release_trend_label`` is legacy's ``_classify``.
PURE: every input arrives as a frame.
"""

from __future__ import annotations

import time

import pandas as pd

#: legacy's rolling windows, in days
WINDOWS = {"releases_30d": 30, "releases_90d": 90, "releases_365d": 365}
COLUMNS = [
    "conda_name",
    "total_versions",
    *WINDOWS,
    "first_upload",
    "last_upload",
    "latest_version",
]


def _typed(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(
        {
            "conda_name": object,
            "total_versions": "int64",
            **dict.fromkeys(WINDOWS, "int64"),
            "first_upload": "Int64",
            "last_upload": "Int64",
            "latest_version": object,
        }
    )


def project_release_cadence(
    core_repodata_uploads_raw: pd.DataFrame,
    core_packages_enumerated: pd.DataFrame,
    now: int | None = None,
) -> pd.DataFrame:
    # legacy: release_cadence.py::query (package_version_downloads, Phases F/I)
    """One row per enumerated package with a version in the full repodata.

    ``total_versions`` counts every version, timed or not, as legacy's ``COUNT(*)`` does; each window counts the
    versions whose ``upload_unix`` is on or after ``now`` minus its days, so an untimed version is in none. The scope is
    ``core_packages_enumerated``, as legacy's table holds only the packages its ``packages`` table lists.
    ``latest_version`` is the version with the latest upload; among equal uploads, the larger version string.
    """
    uploads = core_repodata_uploads_raw
    if (
        uploads is None
        or uploads.empty
        or core_packages_enumerated is None
        or core_packages_enumerated.empty
        or "conda_name" not in core_packages_enumerated.columns
    ):
        return _typed(pd.DataFrame(columns=COLUMNS))
    now_ts = int(time.time()) if now is None else now
    names = set(core_packages_enumerated["conda_name"].dropna().astype(str))
    rows = uploads[uploads["conda_name"].isin(names)][["conda_name", "version", "upload_unix"]].copy()
    if rows.empty:
        return _typed(pd.DataFrame(columns=COLUMNS))
    rows["upload_unix"] = rows["upload_unix"].astype("Int64")
    for column, days in WINDOWS.items():
        rows[column] = (rows["upload_unix"] >= now_ts - days * 86400).fillna(False).astype("int64")
    grouped = rows.groupby("conda_name", sort=True)
    out = grouped.agg(
        total_versions=("version", "size"),
        **{column: (column, "sum") for column in WINDOWS},
        first_upload=("upload_unix", "min"),
        last_upload=("upload_unix", "max"),
    )
    # the version last uploaded: untimed versions last, then the larger version string first among equal uploads
    latest = rows.sort_values(
        ["conda_name", "upload_unix", "version"], ascending=[True, False, False], na_position="last", kind="stable"
    ).drop_duplicates("conda_name")
    out["latest_version"] = latest.set_index("conda_name")["version"]
    return _typed(out.reset_index()[COLUMNS])
