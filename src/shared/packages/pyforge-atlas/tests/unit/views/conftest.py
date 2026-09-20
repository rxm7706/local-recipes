"""Hermetic ``cf_atlas.db``-shaped sqlite fixture for the Story 14.1/14.2/14.3 view tests.

Uses stdlib ``sqlite3`` directly (test-only — the F1 singularity gate
``tests/singularity/test_duckdb_sole_engine.py`` scans ``src/pyforge/atlas/**``, never
``tests/``) to build just enough of the live schema for each of the 6 registered CLIs'
zero-argument default ``query()`` to return a realistic, non-empty row set. Rows are shared
across all six views on purpose (one small package fixture set, not six bespoke ones) so a
single build function backs every test in this directory.

``maintainers``/``package_maintainers`` (Story 14.3, CAP-2) mirror every wrapped CLI's
identical maintainer join (``JOIN package_maintainers pm ON pm.conda_name = p.conda_name
JOIN maintainers m ON m.id = pm.maintainer_id ... WHERE LOWER(m.handle) = LOWER(?)`` — verified
against ``staleness_report.py::query``'s source) so the live maintainer-filter tests exercise
a real join, not a stub. Exactly one handle (``alice``) is assigned to exactly one fixture
package (``alpha-pkg``), so filtering by it provably narrows the result set.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

DAY = 86400
NOW = int(time.time())

_SCHEMA = """
CREATE TABLE packages (
    conda_name TEXT PRIMARY KEY,
    pypi_name TEXT,
    feedstock_name TEXT,
    latest_conda_version TEXT,
    latest_conda_upload INTEGER,
    total_downloads INTEGER,
    recipe_format TEXT,
    feedstock_archived INTEGER,
    latest_status TEXT,
    vuln_total INTEGER,
    vuln_critical_affecting_current INTEGER,
    vuln_high_affecting_current INTEGER,
    vuln_kev_affecting_current INTEGER,
    vuln_max_epss_score REAL,
    vuln_max_epss_percentile REAL,
    vuln_cwe_top TEXT,
    vdb_scanned_at INTEGER,
    bot_open_pr_count INTEGER,
    bot_last_pr_state TEXT,
    bot_last_pr_version TEXT,
    bot_version_errors_count INTEGER,
    feedstock_bad INTEGER,
    bot_status_fetched_at INTEGER,
    gh_default_branch_status TEXT,
    gh_open_issues_count INTEGER,
    gh_open_prs_count INTEGER,
    gh_pushed_at INTEGER,
    gh_status_fetched_at INTEGER,
    conda_source_registry TEXT,
    latest_version_downloads INTEGER
);
CREATE TABLE upstream_versions (
    conda_name TEXT,
    source TEXT,
    version TEXT,
    url TEXT
);
CREATE TABLE vuln_history (
    conda_name TEXT,
    snapshot_at INTEGER,
    vuln_critical_affecting_current INTEGER,
    vuln_high_affecting_current INTEGER,
    vuln_kev_affecting_current INTEGER,
    vuln_total INTEGER
);
CREATE TABLE package_version_downloads (
    conda_name TEXT,
    version TEXT,
    upload_unix INTEGER
);
CREATE TABLE maintainers (
    id INTEGER PRIMARY KEY,
    handle TEXT
);
CREATE TABLE package_maintainers (
    conda_name TEXT,
    maintainer_id INTEGER
);
"""

# One baseline row-shape shared by every packages fixture row; each package overrides only
# what its target view needs to be non-trivially exercised.
_PACKAGE_DEFAULTS = {
    "pypi_name": None,
    "feedstock_name": None,
    "latest_conda_version": "1.0.0",
    "latest_conda_upload": NOW - 100 * DAY,
    "total_downloads": 1000,
    "recipe_format": "v1",
    "feedstock_archived": 0,
    "latest_status": "active",
    "vuln_total": 0,
    "vuln_critical_affecting_current": 0,
    "vuln_high_affecting_current": 0,
    "vuln_kev_affecting_current": 0,
    "vuln_max_epss_score": None,
    "vuln_max_epss_percentile": None,
    "vuln_cwe_top": None,
    "vdb_scanned_at": None,
    "bot_open_pr_count": 0,
    "bot_last_pr_state": None,
    "bot_last_pr_version": None,
    "bot_version_errors_count": 0,
    "feedstock_bad": 0,
    "bot_status_fetched_at": None,
    "gh_default_branch_status": None,
    "gh_open_issues_count": None,
    "gh_open_prs_count": None,
    "gh_pushed_at": None,
    "gh_status_fetched_at": None,
    "conda_source_registry": None,
    "latest_version_downloads": None,
}

# conda_name -> overrides. Each targets (at least) one view's WHERE clause so all six
# registered views return non-empty results against this fixture.
_PACKAGES = {
    # staleness-report (oldest upload, on top of the ASC sort) + feedstock-health "stuck".
    "alpha-pkg": {
        "pypi_name": "alpha",
        "feedstock_name": "alpha-feedstock",
        "latest_conda_upload": NOW - 400 * DAY,
        "vuln_total": 3,
        "vuln_critical_affecting_current": 1,
        "vuln_max_epss_score": 0.5,
        "vuln_max_epss_percentile": 90.0,
        "vuln_cwe_top": "RCE",
        "vdb_scanned_at": NOW - 10 * DAY,
        "bot_open_pr_count": 1,
        "bot_last_pr_state": "open",
        "bot_last_pr_version": "1.1.0",
        "bot_version_errors_count": 2,
        "bot_status_fetched_at": NOW - 5 * DAY,
        "gh_default_branch_status": "success",
        "gh_open_issues_count": 3,
        "gh_open_prs_count": 1,
        "gh_pushed_at": NOW - 2 * DAY,
        "gh_status_fetched_at": NOW - 1 * DAY,
        "conda_source_registry": "pypi",
        "latest_version_downloads": 500,
    },
    # behind-upstream: conda_source_registry=pypi + a newer pypi upstream_versions row.
    "beta-pkg": {
        "pypi_name": "beta",
        "feedstock_name": "beta-feedstock",
        "latest_conda_upload": NOW - 90 * DAY,
        "total_downloads": 2000,
        "conda_source_registry": "pypi",
    },
    # cve-watcher: matching packages row is optional (LEFT JOIN) but included for a
    # complete rendered row.
    "gamma-pkg": {
        "pypi_name": "gamma",
        "feedstock_name": "gamma-feedstock",
        "latest_conda_version": "3.0.0",
        "latest_conda_upload": NOW - 50 * DAY,
        "total_downloads": 3000,
    },
    # release-cadence / adoption-stage: driven by package_version_downloads below.
    "delta-pkg": {
        "pypi_name": "delta",
        "feedstock_name": "delta-feedstock",
        "latest_conda_version": "1.2.0",
        "latest_conda_upload": NOW - 10 * DAY,
        "total_downloads": 4000,
        "latest_version_downloads": 400,
    },
}

_UPSTREAM_VERSIONS = [
    # beta-pkg: conda 1.0.0 vs pypi 2.0.0 -> a 'major' lag (strictly newer, PEP 440).
    ("beta-pkg", "pypi", "2.0.0", "https://pypi.org/project/beta/"),
]

_VULN_HISTORY = [
    # gamma-pkg: two snapshots >= 7 days apart, Critical count 0 -> 2 (a real delta).
    ("gamma-pkg", NOW, 2, 0, 0, 2),
    ("gamma-pkg", NOW - 10 * DAY, 0, 0, 0, 0),
]

_PACKAGE_VERSION_DOWNLOADS = [
    # delta-pkg: one release outside the 365d window, two inside it (30d + 90d).
    ("delta-pkg", "1.0.0", NOW - 400 * DAY),
    ("delta-pkg", "1.1.0", NOW - 40 * DAY),
    ("delta-pkg", "1.2.0", NOW - 10 * DAY),
]

# Story 14.3: exactly one handle, assigned to exactly one fixture package (alpha-pkg), so a
# live maintainer-filter test can prove a real narrowing join (a filter for "alice" returns
# only alpha-pkg; a filter for anyone else returns zero rows).
_MAINTAINERS = [(1, "alice")]
_PACKAGE_MAINTAINERS = [("alpha-pkg", 1)]


def _build(db_path: Path, *, with_rows: bool) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        if with_rows:
            for conda_name, overrides in _PACKAGES.items():
                row = {**_PACKAGE_DEFAULTS, **overrides, "conda_name": conda_name}
                columns = ", ".join(row)
                placeholders = ", ".join("?" for _ in row)
                conn.execute(
                    f"INSERT INTO packages ({columns}) VALUES ({placeholders})",
                    list(row.values()),
                )
            conn.executemany(
                "INSERT INTO upstream_versions (conda_name, source, version, url) VALUES (?, ?, ?, ?)",
                _UPSTREAM_VERSIONS,
            )
            conn.executemany(
                "INSERT INTO vuln_history (conda_name, snapshot_at, "
                "vuln_critical_affecting_current, vuln_high_affecting_current, "
                "vuln_kev_affecting_current, vuln_total) VALUES (?, ?, ?, ?, ?, ?)",
                _VULN_HISTORY,
            )
            conn.executemany(
                "INSERT INTO package_version_downloads (conda_name, version, upload_unix) VALUES (?, ?, ?)",
                _PACKAGE_VERSION_DOWNLOADS,
            )
            conn.executemany("INSERT INTO maintainers (id, handle) VALUES (?, ?)", _MAINTAINERS)
            conn.executemany(
                "INSERT INTO package_maintainers (conda_name, maintainer_id) VALUES (?, ?)",
                _PACKAGE_MAINTAINERS,
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def atlas_db_path(tmp_path: Path) -> Path:
    """A populated fixture db — every one of the 6 registered views returns >=1 row."""
    db_path = tmp_path / "cf_atlas.db"
    _build(db_path, with_rows=True)
    return db_path


@pytest.fixture()
def empty_atlas_db_path(tmp_path: Path) -> Path:
    """The same schema with zero rows — the EMPTY_RESULT case."""
    db_path = tmp_path / "cf_atlas_empty.db"
    _build(db_path, with_rows=False)
    return db_path
