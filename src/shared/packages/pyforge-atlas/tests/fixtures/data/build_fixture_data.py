"""Regenerate the static fixture data root beside this file (Story 27.3).

``tests/fixtures/data/`` mirrors the catalog's own ``data/`` layout: every path
below is exactly the relpath the matching constant in
``pyforge.atlas.dashboard.data`` names, so a test materializes a data root by
copying this tree wholesale. ``tests/integration/dashboard/test_dashboard_e2e.py``
is the consumer — it drives the real dashboard against real rows rather than
against an empty data root.

The rows are hand-authored and tiny: enough that every grounded page has
something to render, that the ``semantic_packages``-backed pages light up, and
that the two pages whose ``PageDef`` declares a chart or a filter can build it.
Nothing here is a capture of production data.

Run from the repo root::

    pixi run -e pyforge-atlas python \\
        src/shared/packages/pyforge-atlas/tests/fixtures/data/build_fixture_data.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent

# `now` the dashboard tests pin (tests/integration/dashboard/conftest.py::NOW),
# so the staleness/adoption metrics over the packages store are deterministic.
NOW = 1_700_000_000

FIXTURES: dict[str, pd.DataFrame] = {
    "primary/core_feedstock_health/core_feedstock_health.parquet": pd.DataFrame(
        {
            "feedstock_name": ["alpha", "beta", "gamma"],
            "ci_status": ["failure", "success", "error"],
            "open_prs": pd.array([0, 3, 1], dtype="Int64"),
            "open_issues": pd.array([2, 0, 0], dtype="Int64"),
        }
    ),
    "intermediate/vcs_package_maintainers/vcs_package_maintainers.parquet": pd.DataFrame(
        {
            "conda_name": ["a", "a", "b", "c"],
            "maintainer": ["alice", "bob", "alice", "carol"],
        }
    ),
    "primary/query_plane_estate/query_plane_estate.parquet": pd.DataFrame(
        {
            "sku": ["sku-alpha", "sku-beta", "sku-gamma"],
            "units": pd.array([12, 34, 56], dtype="Int64"),
        }
    ),
    "primary/semantic_packages/semantic_packages.parquet": pd.DataFrame(
        {
            "conda_name": ["a", "b", "c"],
            "latest_status": ["active", "active", "inactive"],
            "feedstock_archived": pd.array([0, 0, 0], dtype="Int64"),
            "latest_conda_upload": pd.array([NOW - 86400, NOW - 8 * 86400, NOW], dtype="Int64"),
            "downloads_total": pd.array([100, 200, 300], dtype="Int64"),
            "downloads_30d": pd.array([1, 2, 3], dtype="Int64"),
            "latest_upload_age_days": pd.array([1, 8, 0], dtype="Int64"),
            "releases_30d": pd.array([0, 1, 0], dtype="Int64"),
            "total_versions": pd.array([2, 5, 1], dtype="Int64"),
        }
    ),
    # version-downloads declares a chart (DESIGN.md § 3.2).
    "primary/version_downloads/version_downloads.parquet": pd.DataFrame(
        {
            "conda_name": ["a", "a", "b"],
            "version": ["1.0.0", "1.1.0", "2.0.0"],
            "upload_date": ["2026-01-02", "2026-03-04", "2026-02-02"],
            "downloads": pd.array([10, 25, 40], dtype="Int64"),
        }
    ),
    # distribution-breakdown declares BOTH a filter and a chart (DESIGN.md § 3.8).
    "primary/distribution_breakdown/distribution_breakdown.parquet": pd.DataFrame(
        {
            "conda_name": ["a", "a", "b", "b"],
            "facet": ["platform", "python-version", "platform", "python-version"],
            "bucket": ["linux-64", "3.12", "osx-arm64", "3.11"],
            "downloads_90d": pd.array([90, 45, 30, 15], dtype="Int64"),
            "declared_python_min": [None, "3.11", None, "3.12"],
            "empirical_floor": [None, "3.12", None, "3.11"],
        }
    ),
}


def main() -> int:
    for relpath, frame in FIXTURES.items():
        target = ROOT / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(target, index=False)
        print(f"wrote {relpath} ({len(frame)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
