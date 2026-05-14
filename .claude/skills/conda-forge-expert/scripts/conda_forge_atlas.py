#!/usr/bin/env python3
"""
Conda-Forge Atlas — Cross-Channel Package Map.

Builds a SQLite-based aggregation of conda-forge ↔ PyPI ↔ npm/CRAN/CPAN/LuaRocks
package metadata, with cross-channel relationship tracking. Conda-forge-centric:
every conda-forge package is captured with full metadata; cross-channel matches
identify PyPI / npm / etc. counterparts where they exist; the PyPI universe is
captured as names-only baseline for "is this PyPI package on conda-forge?"
queries.

Replaces the flat `pypi_conda_map.json` produced by `mapping_manager.py` with a
queryable single source of truth that captures:

  - Identity & cross-channel match (parselmouth + recipe source.url + name match)
  - conda-forge metadata (license, summary, homepage, repo, maintainers, …)
  - Active vs inactive status (presence in current_repodata vs feedstock-outputs)
  - Source registry detection (pypi/npm/cran/cpan/luarocks/github)
  - Archived feedstock detection (GraphQL)
  - PyPI universe (names + freshness serial)

Output:
  - .claude/data/conda-forge-expert/cf_atlas.db          -- SQLite, primary
  - .claude/data/conda-forge-expert/cf_atlas_meta.json   -- build provenance sidecar
  - .claude/data/conda-forge-expert/cf_atlas_export.json -- optional full table dump

CLI:
  python conda_forge_atlas.py build [--dry-run] [--export-json]
  python conda_forge_atlas.py query <name>
  python conda_forge_atlas.py stats

Pixi tasks:
  pixi run -e local-recipes build-cf-atlas
  pixi run -e local-recipes query-cf-atlas -- <name>
  pixi run -e local-recipes stats-cf-atlas
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Enterprise HTTP helpers (truststore + .netrc auth + URL resolvers)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from _http import (  # type: ignore[import-not-found]
        inject_ssl_truststore,
        make_request as _http_make_request,
        resolve_conda_forge_urls as _resolve_conda_forge_urls,
        resolve_pypi_simple_urls as _resolve_pypi_simple_urls,
        resolve_github_urls as _resolve_github_urls,
        resolve_github_api_urls as _resolve_github_api_urls,
        resolve_gitlab_api_urls as _resolve_gitlab_api_urls,
        resolve_codeberg_api_urls as _resolve_codeberg_api_urls,
        resolve_npm_urls as _resolve_npm_urls,
        resolve_cran_urls as _resolve_cran_urls,
        resolve_cpan_urls as _resolve_cpan_urls,
        resolve_luarocks_urls as _resolve_luarocks_urls,
        resolve_crates_urls as _resolve_crates_urls,
        resolve_rubygems_urls as _resolve_rubygems_urls,
        resolve_maven_urls as _resolve_maven_urls,
        resolve_nuget_urls as _resolve_nuget_urls,
        fetch_with_fallback as _fetch_with_fallback,
    )
    inject_ssl_truststore()
    _HTTP_AVAILABLE = True
except ImportError:
    _http_make_request = None  # type: ignore[assignment]
    _resolve_conda_forge_urls = None  # type: ignore[assignment]
    _resolve_pypi_simple_urls = None  # type: ignore[assignment]
    _resolve_github_urls = None  # type: ignore[assignment]
    _resolve_github_api_urls = None  # type: ignore[assignment]
    _resolve_gitlab_api_urls = None  # type: ignore[assignment]
    _resolve_codeberg_api_urls = None  # type: ignore[assignment]
    _resolve_npm_urls = None  # type: ignore[assignment]
    _resolve_cran_urls = None  # type: ignore[assignment]
    _resolve_cpan_urls = None  # type: ignore[assignment]
    _resolve_luarocks_urls = None  # type: ignore[assignment]
    _resolve_crates_urls = None  # type: ignore[assignment]
    _resolve_rubygems_urls = None  # type: ignore[assignment]
    _resolve_maven_urls = None  # type: ignore[assignment]
    _resolve_nuget_urls = None  # type: ignore[assignment]
    _fetch_with_fallback = None  # type: ignore[assignment]
    _HTTP_AVAILABLE = False


def _iso_to_unix_safe(iso: str | None) -> int | None:
    """Parse RFC 3339 / ISO 8601 to UNIX seconds; returns None on bad input."""
    if not iso:
        return None
    import datetime as _dt
    try:
        return int(_dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _make_req(url: str, extra_headers: dict | None = None) -> urllib.request.Request:
    """Build an enterprise-safe Request; falls back to bare urllib if _http unavailable."""
    if _HTTP_AVAILABLE and _http_make_request is not None:
        return _http_make_request(url, extra_headers=extra_headers, user_agent="unified-map-builder/1.0")
    headers: dict = {"User-Agent": "unified-map-builder/1.0"}
    if extra_headers:
        headers.update(extra_headers)
    return urllib.request.Request(url, headers=headers)


# Conda-forge subdirs we enumerate. Order doesn't matter; they're aggregated
# per package_name into the conda_subdirs JSON list column.
CONDA_FORGE_SUBDIRS = [
    "noarch",
    "linux-64",
    "linux-aarch64",
    "linux-ppc64le",
    "osx-64",
    "osx-arm64",
    "win-64",
]
CONDA_FORGE_CHANNEL = "conda-forge"

# URL resolvers (`_resolve_conda_forge_urls`, `_resolve_pypi_simple_urls`,
# `_resolve_github_urls`) and `_fetch_with_fallback` are imported from
# `_http.py` above — see docstrings there for the priority chain logic.
# Air-gapped JFrog routing is configured via env vars or pixi config; no
# enterprise URLs live in this script.

SCHEMA_VERSION = 21


def _get_data_dir() -> Path:
    """Get skill-scoped data directory: .claude/data/conda-forge-expert/"""
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DATA_DIR = _get_data_dir()
DB_PATH = DATA_DIR / "cf_atlas.db"
META_PATH = DATA_DIR / "cf_atlas_meta.json"
EXPORT_PATH = DATA_DIR / "cf_atlas_export.json"

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS packages (
    conda_name             TEXT,
    pypi_name              TEXT,
    feedstock_name         TEXT,
    feedstock_archived     INTEGER,
    archived_at            INTEGER,
    relationship           TEXT NOT NULL,
    match_source           TEXT NOT NULL,
    match_confidence       TEXT NOT NULL,
    conda_subdirs          TEXT,
    conda_noarch           INTEGER,
    latest_conda_version   TEXT,
    latest_conda_upload    INTEGER,
    latest_status          TEXT,
    conda_summary          TEXT,
    conda_license          TEXT,
    conda_license_family   TEXT,
    conda_homepage         TEXT,
    conda_dev_url          TEXT,
    conda_doc_url          TEXT,
    conda_repo_url         TEXT,
    conda_keywords         TEXT,
    recipe_format          TEXT,
    conda_source_registry  TEXT,
    npm_name               TEXT,
    cran_name              TEXT,
    cpan_name              TEXT,
    luarocks_name          TEXT,
    maven_coord            TEXT,
    pypi_last_serial       INTEGER,
    total_downloads          INTEGER,
    latest_version_downloads INTEGER,
    downloads_fetched_at     INTEGER,
    downloads_fetch_attempts INTEGER,
    downloads_last_error     TEXT,
    downloads_source         TEXT,
    vuln_total                       INTEGER,
    vuln_critical_affecting_current  INTEGER,
    vuln_high_affecting_current      INTEGER,
    vuln_kev_affecting_current       INTEGER,
    vdb_scanned_at                   INTEGER,
    vdb_last_error                   TEXT,
    pypi_current_version             TEXT,
    pypi_current_version_yanked      INTEGER,
    pypi_version_fetched_at          INTEGER,
    pypi_version_last_error          TEXT,
    pypi_version_source              TEXT,
    pypi_version_serial_at_fetch     INTEGER,  -- v21: serial-gate for Phase H
    github_current_version           TEXT,
    github_version_fetched_at        INTEGER,
    github_version_last_error        TEXT,
    bot_open_pr_count                INTEGER,
    bot_last_pr_state                TEXT,
    bot_last_pr_version              TEXT,
    bot_version_errors_count         INTEGER,
    feedstock_bad                    INTEGER,
    bot_status_fetched_at            INTEGER,
    gh_default_branch_status         TEXT,
    gh_open_issues_count             INTEGER,
    gh_open_prs_count                INTEGER,
    gh_pushed_at                     INTEGER,
    gh_status_fetched_at             INTEGER,
    gh_status_last_error             TEXT,
    notes                  TEXT
);

CREATE TABLE IF NOT EXISTS maintainers (
    id     INTEGER PRIMARY KEY,
    handle TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS package_maintainers (
    conda_name    TEXT NOT NULL,
    maintainer_id INTEGER NOT NULL,
    PRIMARY KEY (conda_name, maintainer_id)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Phase progress checkpoints. Long-running phases (currently Phase N) write
-- one row per run with the last-processed feedstock; a subsequent run can
-- read this row and resume from where the previous run died. The cursor is
-- the feedstock_name space ordered alphabetically — Phase N's SQL already
-- uses `ORDER BY p.feedstock_name` so the cursor is stable across runs.
CREATE TABLE IF NOT EXISTS phase_state (
    phase_name               TEXT PRIMARY KEY,
    run_started_at           INTEGER,
    last_completed_cursor    TEXT,     -- e.g. feedstock_name for Phase N
    items_completed          INTEGER,
    items_total              INTEGER,
    run_completed_at         INTEGER,  -- non-NULL iff the run finished cleanly
    status                   TEXT,     -- 'in_progress' | 'completed' | 'failed'
    last_error               TEXT
);

-- Phase J: dependency graph extracted from cf-graph node_attrs.
-- One row per (source, target, requirement_type) triple.
CREATE TABLE IF NOT EXISTS dependencies (
    source_conda_name TEXT NOT NULL,
    target_conda_name TEXT NOT NULL,
    requirement_type  TEXT NOT NULL,  -- 'build' | 'host' | 'run' | 'test'
    pin_spec          TEXT,
    PRIMARY KEY (source_conda_name, target_conda_name, requirement_type)
);
CREATE INDEX IF NOT EXISTS idx_deps_source ON dependencies(source_conda_name);
CREATE INDEX IF NOT EXISTS idx_deps_target ON dependencies(target_conda_name);

-- Phase G snapshot history: one row per (snapshot_at, conda_name) capturing
-- the four affecting-current counts. Lets cve-watcher diff between any
-- two snapshots and surface "new this week."
CREATE TABLE IF NOT EXISTS vuln_history (
    snapshot_at INTEGER NOT NULL,
    conda_name  TEXT NOT NULL,
    vuln_total                       INTEGER,
    vuln_critical_affecting_current  INTEGER,
    vuln_high_affecting_current      INTEGER,
    vuln_kev_affecting_current       INTEGER,
    PRIMARY KEY (snapshot_at, conda_name)
);
CREATE INDEX IF NOT EXISTS idx_vuln_history_name ON vuln_history(conda_name);
CREATE INDEX IF NOT EXISTS idx_vuln_history_snap ON vuln_history(snapshot_at);

-- Phase I: per-version download history. One row per (conda_name, version);
-- written by Phase F as a side effect when fetching the anaconda.org payload
-- (already contains per-file ndownloads + upload_time). Enables release-
-- cadence and adoption-curve analysis without extra HTTP calls.
CREATE TABLE IF NOT EXISTS package_version_downloads (
    conda_name TEXT NOT NULL,
    version    TEXT NOT NULL,
    upload_unix INTEGER,        -- min upload_time across files of this version
    file_count INTEGER,
    total_downloads INTEGER,
    fetched_at INTEGER,
    source     TEXT,
    PRIMARY KEY (conda_name, version)
);
CREATE INDEX IF NOT EXISTS idx_pvd_conda_name ON package_version_downloads(conda_name);
CREATE INDEX IF NOT EXISTS idx_pvd_upload ON package_version_downloads(upload_unix);

-- Phase K/L+: unified upstream version cache. One row per
-- (conda_name, source). The source column distinguishes registries —
-- 'pypi', 'github', 'gitlab', 'codeberg', 'npm', 'cran', 'cpan',
-- 'luarocks', 'maven', 'crates', 'rubygems', 'nuget', etc. Adding new
-- registries means adding a new resolver, not new columns. The dedicated
-- pypi_current_version / github_current_version columns are kept for
-- backward-compat with v6.7+ tooling but are also mirrored here so
-- queries that need cross-source comparison can use one place.
CREATE TABLE IF NOT EXISTS upstream_versions (
    conda_name TEXT NOT NULL,
    source     TEXT NOT NULL,
    version    TEXT,
    url        TEXT,
    fetched_at INTEGER,
    last_error TEXT,
    PRIMARY KEY (conda_name, source)
);
CREATE INDEX IF NOT EXISTS idx_upstream_name ON upstream_versions(conda_name);
CREATE INDEX IF NOT EXISTS idx_upstream_source ON upstream_versions(source);

-- Phase D side table (schema v20): the PyPI universe directory. One row
-- per public PyPI project — separated from `packages` so the working set
-- stays conda-actionable. Refreshed on its own TTL via
-- PHASE_D_UNIVERSE_TTL_DAYS (default 7); the daily Phase D run updates
-- `packages.pypi_last_serial` on conda-linked rows without touching this
-- table. Read by the `pypi-only-candidates` CLI via LEFT JOIN to
-- `packages.pypi_name`. The v20 migration block in init_schema migrates
-- existing `relationship='pypi_only'` rows here and DELETEs them from
-- `packages`.
CREATE TABLE IF NOT EXISTS pypi_universe (
    pypi_name   TEXT PRIMARY KEY,
    last_serial INTEGER,
    fetched_at  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_pypi_universe_serial ON pypi_universe(last_serial);
CREATE INDEX IF NOT EXISTS idx_pypi_universe_fetched ON pypi_universe(fetched_at);

-- Canonical persona-filter triplet, encoded as a view (schema v21+) so
-- phase authors can't drift. Every selector that wants "the conda-
-- actionable working set" reads FROM v_actionable_packages instead of
-- repeating the triplet inline. The drift-prevention meta-test
-- `tests/meta/test_actionable_scope.py` asserts every `SELECT ... FROM
-- packages WHERE ...` in `conda_forge_atlas.py` either uses this view
-- OR has an inline `# scope: ...` justification comment within 3 lines
-- above. Phases that legitimately need a broader scope (B, B.5, B.6,
-- C, D, E, E.5, J, M — writes / cross-cutting) read packages directly
-- with such a comment.
CREATE VIEW IF NOT EXISTS v_actionable_packages AS
SELECT *
FROM packages
WHERE conda_name IS NOT NULL
  AND COALESCE(latest_status, 'active') = 'active'
  AND COALESCE(feedstock_archived, 0) = 0;

-- Upstream-version drift history. Captures one row per (snapshot_at,
-- conda_name, source) tuple at the end of each Phase H/K/L run. Lets
-- consumers track upstream-velocity trends and compute per-package
-- "behind for N days" durations.
CREATE TABLE IF NOT EXISTS upstream_versions_history (
    snapshot_at INTEGER NOT NULL,
    conda_name  TEXT NOT NULL,
    source      TEXT NOT NULL,
    version     TEXT,
    PRIMARY KEY (snapshot_at, conda_name, source)
);
CREATE INDEX IF NOT EXISTS idx_uvh_name   ON upstream_versions_history(conda_name);
CREATE INDEX IF NOT EXISTS idx_uvh_source ON upstream_versions_history(source);
CREATE INDEX IF NOT EXISTS idx_uvh_snap   ON upstream_versions_history(snapshot_at);

-- Per-version vuln scoring. Phase G writes only the latest_conda_version's
-- counts to `packages`; Phase G' (per-version) iterates package_version_
-- downloads and scores each version separately. Lets users find "the
-- most recent version with 0 critical CVEs" for env-lockdown.
CREATE TABLE IF NOT EXISTS package_version_vulns (
    conda_name TEXT NOT NULL,
    version    TEXT NOT NULL,
    vuln_total                       INTEGER,
    vuln_critical_affecting_version  INTEGER,
    vuln_high_affecting_version      INTEGER,
    vuln_kev_affecting_version       INTEGER,
    scanned_at                       INTEGER,
    PRIMARY KEY (conda_name, version)
);
CREATE INDEX IF NOT EXISTS idx_pvv_conda_name ON package_version_vulns(conda_name);
CREATE INDEX IF NOT EXISTS idx_pvv_critical ON package_version_vulns(vuln_critical_affecting_version);

CREATE INDEX IF NOT EXISTS idx_relationship ON packages(relationship);
CREATE INDEX IF NOT EXISTS idx_match_source ON packages(match_source);
CREATE INDEX IF NOT EXISTS idx_pypi_name    ON packages(pypi_name);
CREATE INDEX IF NOT EXISTS idx_conda_name   ON packages(conda_name);
CREATE INDEX IF NOT EXISTS idx_feedstock    ON packages(feedstock_name);
CREATE INDEX IF NOT EXISTS idx_license      ON packages(conda_license);
CREATE INDEX IF NOT EXISTS idx_status       ON packages(latest_status);
CREATE INDEX IF NOT EXISTS idx_archived     ON packages(feedstock_archived);
CREATE INDEX IF NOT EXISTS idx_handle       ON maintainers(handle);
-- Conda packages get a unique row keyed on conda_name. PyPI-only rows have
-- conda_name NULL; SQLite treats NULLs as distinct under UNIQUE, so they
-- coexist freely. Phase B uses ON CONFLICT(conda_name) DO UPDATE for
-- rebuild idempotency.
CREATE UNIQUE INDEX IF NOT EXISTS uq_conda_name ON packages(conda_name);

CREATE VIEW IF NOT EXISTS v_packages_enriched AS
SELECT
    p.*,
    CASE WHEN pypi_name IS NOT NULL
         THEN 'https://pypi.org/project/' || pypi_name || '/' END AS pypi_url,
    CASE WHEN feedstock_name IS NOT NULL
         THEN 'https://github.com/conda-forge/' || feedstock_name END AS feedstock_url,
    CASE WHEN conda_name IS NOT NULL
         THEN 'https://anaconda.org/conda-forge/' || conda_name END AS conda_anaconda_url,
    CASE WHEN conda_name IS NOT NULL
         THEN 'https://prefix.dev/channels/conda-forge/packages/' || conda_name END AS prefix_dev_url,
    CASE WHEN npm_name IS NOT NULL
         THEN 'https://www.npmjs.com/package/' || npm_name END AS npm_url,
    CASE WHEN cran_name IS NOT NULL
         THEN 'https://cran.r-project.org/package=' || cran_name END AS cran_url,
    CASE WHEN cpan_name IS NOT NULL
         THEN 'https://metacpan.org/pod/' || cpan_name END AS cpan_url,
    CASE WHEN luarocks_name IS NOT NULL
         THEN 'https://luarocks.org/modules/' || luarocks_name END AS luarocks_url
FROM packages p;
"""


def open_db(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the SQLite DB with performance pragmas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.row_factory = sqlite3.Row
    return conn


def _dedupe_packages_by_conda_name(conn: sqlite3.Connection) -> int:
    """v2→v3 migration: collapse duplicate rows that share a conda_name.

    Pre-v3 rebuilds appended a new row to `packages` instead of upserting,
    so each rebuild after the first one created a duplicate per conda
    package. Duplicates are ~bit-identical apart from `pypi_last_serial`
    (Phase D only updates the originally-inserted row). Resolution:
      - keep the row with non-NULL pypi_last_serial when it differs;
      - tiebreak by lowest rowid (= oldest, with the most history);
      - delete the rest.

    Returns the number of rows deleted.
    """
    # scope: v2→v3 dedupe migration; intentionally scans ALL packages rows
    # (including archived/inactive) to find duplicates before the UNIQUE
    # index is created. The view's actionable-filter would miss duplicates
    # that exist only in archived/inactive rows.
    cur = conn.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM packages "
        "WHERE conda_name IS NOT NULL "
        "GROUP BY conda_name HAVING COUNT(*) > 1)"
    )
    n_dup_names = cur.fetchone()[0]
    if not n_dup_names:
        return 0
    cur = conn.execute(
        """
        DELETE FROM packages WHERE rowid IN (
            SELECT rowid FROM (
                SELECT rowid,
                       ROW_NUMBER() OVER (
                           PARTITION BY conda_name
                           ORDER BY (pypi_last_serial IS NULL), rowid
                       ) AS rn
                FROM packages
                WHERE conda_name IS NOT NULL
            ) WHERE rn > 1
        )
        """
    )
    deleted = cur.rowcount
    conn.commit()
    return deleted


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables, indexes, and views if not present.

    On a fresh DB the SCHEMA_DDL block alone produces the current schema;
    the ALTER TABLE / dedup migrations below only fire when carrying an
    older DB forward (they touch `packages` before SCHEMA_DDL runs, so
    they must be guarded behind a packages-exists check).
    """
    have_packages = bool(list(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='packages'"
    )))

    if have_packages:
        # v1 → v2 → v4: column additions via ALTER TABLE. v3 was the dedup +
        # UNIQUE INDEX migration handled below; v4 adds Phase F failure-tracking
        # columns. Run ADD COLUMN before executescript so the columns exist
        # before any later DDL references them.
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(packages)")}
        for col, ddl in (
            ("total_downloads",          "ALTER TABLE packages ADD COLUMN total_downloads INTEGER"),
            ("latest_version_downloads", "ALTER TABLE packages ADD COLUMN latest_version_downloads INTEGER"),
            ("downloads_fetched_at",     "ALTER TABLE packages ADD COLUMN downloads_fetched_at INTEGER"),
            ("downloads_fetch_attempts", "ALTER TABLE packages ADD COLUMN downloads_fetch_attempts INTEGER"),
            ("downloads_last_error",     "ALTER TABLE packages ADD COLUMN downloads_last_error TEXT"),
            ("archived_at",              "ALTER TABLE packages ADD COLUMN archived_at INTEGER"),
            ("vuln_total",                       "ALTER TABLE packages ADD COLUMN vuln_total INTEGER"),
            ("vuln_critical_affecting_current",  "ALTER TABLE packages ADD COLUMN vuln_critical_affecting_current INTEGER"),
            ("vuln_high_affecting_current",      "ALTER TABLE packages ADD COLUMN vuln_high_affecting_current INTEGER"),
            ("vuln_kev_affecting_current",       "ALTER TABLE packages ADD COLUMN vuln_kev_affecting_current INTEGER"),
            ("vdb_scanned_at",                   "ALTER TABLE packages ADD COLUMN vdb_scanned_at INTEGER"),
            ("vdb_last_error",                   "ALTER TABLE packages ADD COLUMN vdb_last_error TEXT"),
            ("pypi_current_version",             "ALTER TABLE packages ADD COLUMN pypi_current_version TEXT"),
            ("pypi_version_fetched_at",          "ALTER TABLE packages ADD COLUMN pypi_version_fetched_at INTEGER"),
            ("pypi_version_last_error",          "ALTER TABLE packages ADD COLUMN pypi_version_last_error TEXT"),
            ("pypi_current_version_yanked",      "ALTER TABLE packages ADD COLUMN pypi_current_version_yanked INTEGER"),
            ("github_current_version",           "ALTER TABLE packages ADD COLUMN github_current_version TEXT"),
            ("github_version_fetched_at",        "ALTER TABLE packages ADD COLUMN github_version_fetched_at INTEGER"),
            ("github_version_last_error",        "ALTER TABLE packages ADD COLUMN github_version_last_error TEXT"),
            ("bot_open_pr_count",                "ALTER TABLE packages ADD COLUMN bot_open_pr_count INTEGER"),
            ("bot_last_pr_state",                "ALTER TABLE packages ADD COLUMN bot_last_pr_state TEXT"),
            ("bot_last_pr_version",              "ALTER TABLE packages ADD COLUMN bot_last_pr_version TEXT"),
            ("bot_version_errors_count",         "ALTER TABLE packages ADD COLUMN bot_version_errors_count INTEGER"),
            ("feedstock_bad",                    "ALTER TABLE packages ADD COLUMN feedstock_bad INTEGER"),
            ("bot_status_fetched_at",            "ALTER TABLE packages ADD COLUMN bot_status_fetched_at INTEGER"),
            ("gh_default_branch_status",         "ALTER TABLE packages ADD COLUMN gh_default_branch_status TEXT"),
            ("gh_open_issues_count",             "ALTER TABLE packages ADD COLUMN gh_open_issues_count INTEGER"),
            ("gh_open_prs_count",                "ALTER TABLE packages ADD COLUMN gh_open_prs_count INTEGER"),
            ("gh_pushed_at",                     "ALTER TABLE packages ADD COLUMN gh_pushed_at INTEGER"),
            ("gh_status_fetched_at",             "ALTER TABLE packages ADD COLUMN gh_status_fetched_at INTEGER"),
            ("gh_status_last_error",             "ALTER TABLE packages ADD COLUMN gh_status_last_error TEXT"),
            ("maven_coord",                      "ALTER TABLE packages ADD COLUMN maven_coord TEXT"),
            ("downloads_source",                 "ALTER TABLE packages ADD COLUMN downloads_source TEXT"),
            ("pypi_version_source",              "ALTER TABLE packages ADD COLUMN pypi_version_source TEXT"),
        ):
            if col not in existing_cols:
                conn.execute(ddl)

        # v17 → v18: package_version_downloads gains a `source` discriminator
        # so consumers can tell anaconda-api rows (upload_unix populated) from
        # s3-parquet rows (upload_unix NULL) apart.
        pvd_exists = bool(list(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='package_version_downloads'"
        )))
        if pvd_exists:
            pvd_cols = {row["name"] for row in conn.execute(
                "PRAGMA table_info(package_version_downloads)"
            )}
            if "source" not in pvd_cols:
                conn.execute("ALTER TABLE package_version_downloads ADD COLUMN source TEXT")

        # v19 → v20: extract the ~660k `relationship='pypi_only'` rows from
        # `packages` into the new `pypi_universe` side table. Working-set
        # queries (Phase F/G/G'/H/K/L/N + every CLI) stop seeing pypi-only
        # rows; the `pypi-only-candidates` CLI reads them via LEFT JOIN.
        # Self-healing: INSERT OR IGNORE + DELETE is idempotent; re-running
        # after success is a no-op because the SELECT returns 0 rows.
        # Wrapped in its own transaction so a crash mid-migration doesn't
        # leave half-state.
        # scope: v19→v20 migration probe; reads ALL packages rows to count
        # pypi_only rows before they migrate to pypi_universe. View would
        # exclude them (relationship != actionable triplet) — wrong scope.
        v20_pre_count = conn.execute(
            "SELECT COUNT(*) FROM packages WHERE relationship = 'pypi_only'"
        ).fetchone()[0]
        if v20_pre_count > 0:
            # The pypi_universe table is in SCHEMA_DDL (created below) but
            # the migration runs first, so create it inline here. Repeats
            # are harmless under IF NOT EXISTS.
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pypi_universe ("
                "  pypi_name TEXT PRIMARY KEY,"
                "  last_serial INTEGER,"
                "  fetched_at INTEGER"
                ")"
            )
            print(f"  v20 migration: moving {v20_pre_count:,} pypi_only rows "
                  f"to pypi_universe...")
            conn.execute("BEGIN TRANSACTION")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO pypi_universe "
                    "(pypi_name, last_serial, fetched_at) "
                    "SELECT pypi_name, pypi_last_serial, "
                    "       COALESCE(downloads_fetched_at, 0) "
                    "FROM packages "
                    "WHERE relationship = 'pypi_only' "
                    "  AND pypi_name IS NOT NULL"
                )
                deleted = conn.execute(
                    "DELETE FROM packages WHERE relationship = 'pypi_only'"
                ).rowcount
                conn.commit()
                print(f"  v20 migration: deleted {deleted:,} pypi_only rows "
                      f"from packages")
            except Exception:
                conn.rollback()
                raise

        # v20 → v21: two changes packaged together.
        #
        # (A) Add `pypi_version_serial_at_fetch INTEGER` column to
        #     `packages`. Stamped by Phase H on each successful fetch
        #     (alongside `pypi_version_fetched_at`); compared against
        #     `pypi_last_serial` (populated by Phase D's daily-lean path)
        #     to gate Phase H's eligible-rows selector. Idempotent.
        #
        # (B) The `v_actionable_packages` view is in SCHEMA_DDL below
        #     (CREATE VIEW IF NOT EXISTS) so no migration step is needed
        #     here. The executescript at the end of init_schema creates it.
        #
        # Wave C (drop vuln_total) deferred from v8.0.0 — discovered
        # 4 consumers (detail_cf_atlas, cve_watcher, staleness_report,
        # scan_project) that the original audit missed; needs a re-spec.
        if "pypi_version_serial_at_fetch" not in existing_cols:
            conn.execute(
                "ALTER TABLE packages ADD COLUMN pypi_version_serial_at_fetch INTEGER"
            )

        # v2 → v3: dedupe before the unique index in SCHEMA_DDL is created, or
        # the CREATE UNIQUE INDEX would fail on the duplicates.
        have_uq = bool(list(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='uq_conda_name'"
        )))
        if not have_uq:
            n_deleted = _dedupe_packages_by_conda_name(conn)
            if n_deleted:
                print(f"  Migration v2→v3: deleted {n_deleted:,} duplicate rows")

    conn.executescript(SCHEMA_DDL)
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                 ("schema_version", str(SCHEMA_VERSION)))
    conn.commit()


# --- Pipeline phases (skeleton; populated incrementally) ---

def _fetch_current_repodata(subdir: str, retries: int = 2) -> dict:
    """Fetch current_repodata.json (latest active version per package) for one subdir.

    Tries each base URL in `_resolve_conda_forge_urls()` in order:
    JFrog (env var or pixi config) → prefix.dev → conda.anaconda.org. Within
    each base URL, retries `retries` times with exponential backoff for
    transient errors (5xx, timeouts, network resets). 4xx errors (404/403)
    skip immediately to the next URL — they signal the URL is wrong, not
    that the request is transiently flaky.

    Single-file JSON fetch — avoids the sharded msgpack protocol that's
    prone to transient 502s. ~15MB per subdir vs ~170MB for full repodata.
    """
    if _HTTP_AVAILABLE and _resolve_conda_forge_urls is not None:
        base_urls = _resolve_conda_forge_urls()
    else:
        # Bare-urllib fallback when _http isn't importable. Public defaults only.
        base_urls = [
            "https://repo.prefix.dev/conda-forge",
            "https://conda.anaconda.org/conda-forge",
        ]
    last_err: Exception | None = None
    for base_url in base_urls:
        url = f"{base_url}/{subdir}/current_repodata.json"
        for attempt in range(retries):
            try:
                req = _make_req(url)
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                last_err = e
                # 4xx (except 408 timeout / 429 rate-limit) means this URL
                # is wrong — fall through to next base URL immediately.
                if 400 <= e.code < 500 and e.code not in (408, 429):
                    print(f"    {subdir} via {base_url}: HTTP {e.code}; trying next source")
                    break
                print(f"    {subdir} via {base_url} attempt {attempt + 1} failed: {e}; retrying...")
                time.sleep(2 ** attempt)
            except Exception as e:
                last_err = e
                print(f"    {subdir} via {base_url} attempt {attempt + 1} failed: {e}; retrying...")
                time.sleep(2 ** attempt)
    assert last_err is not None
    raise RuntimeError(
        f"Failed to fetch {subdir}/current_repodata.json from any of "
        f"{len(base_urls)} source(s); last error: {last_err}"
    )


def _aggregate_repodata_records(repodata_by_subdir: dict[str, dict]) -> dict[str, dict[str, Any]]:
    """Reduce per-subdir repodata into one aggregated record per package_name.

    Picks the latest version (then build_number, then timestamp). Aggregates
    subdirs across platforms. Marks noarch if any record in any subdir is noarch.
    """
    from packaging.version import InvalidVersion, parse as parse_version

    def version_sort_key(version_str: str) -> Any:
        try:
            return (0, parse_version(version_str))  # 0 = real version
        except InvalidVersion:
            return (1, version_str)  # 1 = fallback to string for non-PEP-440 versions

    aggregated: dict[str, dict[str, Any]] = {}
    for subdir, repodata in repodata_by_subdir.items():
        for source_dict in (repodata.get("packages.conda", {}), repodata.get("packages", {})):
            for rec in source_dict.values():
                name = rec.get("name")
                if not name:
                    continue
                version = rec.get("version", "")
                build_number = rec.get("build_number", 0) or 0
                timestamp = rec.get("timestamp", 0) or 0
                noarch = rec.get("noarch")  # str like "python", "generic", or absent
                key = version_sort_key(version)
                # Track latest by (version, build_number, timestamp); always merge subdirs
                agg = aggregated.get(name)
                if agg is None:
                    aggregated[name] = {
                        "conda_name": name,
                        "conda_subdirs": {subdir},
                        "conda_noarch": 1 if noarch else 0,
                        "latest_conda_version": version,
                        "_latest_key": key,
                        "_latest_build_number": build_number,
                        "_latest_timestamp": timestamp,
                        "latest_conda_upload": int(timestamp / 1000) if timestamp else None,
                        "conda_license": rec.get("license"),
                        "conda_license_family": rec.get("license_family"),
                    }
                else:
                    agg["conda_subdirs"].add(subdir)
                    if noarch:
                        agg["conda_noarch"] = 1
                    candidate = (key, build_number, timestamp)
                    current = (agg["_latest_key"], agg["_latest_build_number"], agg["_latest_timestamp"])
                    if candidate > current:
                        agg["latest_conda_version"] = version
                        agg["_latest_key"] = key
                        agg["_latest_build_number"] = build_number
                        agg["_latest_timestamp"] = timestamp
                        agg["latest_conda_upload"] = int(timestamp / 1000) if timestamp else None
                        agg["conda_license"] = rec.get("license")
                        agg["conda_license_family"] = rec.get("license_family")
    # Drop internal sort keys; freeze subdirs to a sorted list
    for agg in aggregated.values():
        agg["conda_subdirs"] = sorted(agg["conda_subdirs"])
        del agg["_latest_key"]
        del agg["_latest_build_number"]
        del agg["_latest_timestamp"]
    return aggregated


def phase_b_conda_enumeration(conn: sqlite3.Connection) -> dict:
    """Phase B: enumerate conda-forge packages via per-subdir current_repodata.json.

    Populates one row per conda package with: conda_name, conda_subdirs,
    conda_noarch, latest_conda_version, latest_conda_upload, conda_license,
    conda_license_family. Sets relationship='conda_only' (refined in later phases
    by parselmouth join, source.url match, and PyPI overlap).

    Uses plain urllib + json parsing rather than rattler's sharded protocol —
    py-rattler's Gateway hit transient anaconda.org 502s on the sharded
    msgpack endpoint during testing; current_repodata.json is a single-file
    fetch per subdir and much more reliable.

    Returns: stats dict (subdirs scanned, package count, insert duration).
    """
    t0 = time.monotonic()
    print(f"  Fetching current_repodata.json for {len(CONDA_FORGE_SUBDIRS)} subdirs...")
    repodata_by_subdir: dict[str, dict] = {}
    for subdir in CONDA_FORGE_SUBDIRS:
        repodata_by_subdir[subdir] = _fetch_current_repodata(subdir)
        n_pkgs = len(repodata_by_subdir[subdir].get("packages.conda", {}))
        print(f"    {subdir}: {n_pkgs:,} packages")

    print("  Aggregating across subdirs...")
    aggregated = _aggregate_repodata_records(repodata_by_subdir)
    print(f"  Aggregated to {len(aggregated):,} unique packages")

    print(f"  Upserting into SQLite (batched commits every 1k rows)...")
    # Upsert on conda_name. On conflict refresh the conda_* fields and reset
    # relationship/match_* to the conda_only baseline; later phases (C, C.5
    # via E, D) will refine the relationship and source classification. PyPI
    # serial, feedstock_*, downloads, and other non-Phase-B columns are left
    # untouched so a rebuild doesn't trash work from later phases.
    #
    # Batched commit (v7.7+): every 1k rows. UPSERT on conda_name is
    # idempotent, so an interrupt mid-run just leaves a partial set of rows
    # that the next run will overwrite. The phase_state cursor records the
    # alphabetically-largest conda_name written so an operator can see how
    # far the prior run got. The current_repodata_names temp table is filled
    # FIRST (single statement, fast) so Phase B.6's demotion logic stays
    # correct even on a partial Phase B.
    save_phase_checkpoint(
        conn, "B", cursor=None, items_completed=0,
        items_total=len(aggregated), status="in_progress",
    )
    conn.execute("DROP TABLE IF EXISTS current_repodata_names")
    conn.execute("CREATE TEMP TABLE current_repodata_names(name TEXT PRIMARY KEY)")
    conn.executemany(
        "INSERT INTO current_repodata_names(name) VALUES (?)",
        [(rec["conda_name"],) for rec in aggregated.values()],
    )
    conn.commit()

    commit_every = 1000
    sorted_recs = sorted(aggregated.values(), key=lambda r: r["conda_name"])
    written = 0
    last_name = ""
    for rec in sorted_recs:
        conn.execute(
            """
            INSERT INTO packages (
                conda_name, conda_subdirs, conda_noarch,
                latest_conda_version, latest_conda_upload,
                conda_license, conda_license_family,
                relationship, match_source, match_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'conda_only', 'none', 'n/a')
            ON CONFLICT(conda_name) DO UPDATE SET
                conda_subdirs        = excluded.conda_subdirs,
                conda_noarch         = excluded.conda_noarch,
                latest_conda_version = excluded.latest_conda_version,
                latest_conda_upload  = excluded.latest_conda_upload,
                conda_license        = excluded.conda_license,
                conda_license_family = excluded.conda_license_family,
                relationship         = 'conda_only',
                match_source         = 'none',
                match_confidence     = 'n/a'
            """,
            (
                rec["conda_name"],
                json.dumps(rec["conda_subdirs"]),
                rec["conda_noarch"],
                rec["latest_conda_version"],
                rec["latest_conda_upload"],
                rec["conda_license"],
                rec["conda_license_family"],
            ),
        )
        written += 1
        last_name = rec["conda_name"]
        if written % commit_every == 0:
            conn.commit()
            save_phase_checkpoint(
                conn, "B", cursor=last_name,
                items_completed=written, items_total=len(aggregated),
                status="in_progress",
            )

    conn.commit()
    save_phase_checkpoint(
        conn, "B", cursor=last_name,
        items_completed=written, items_total=len(aggregated),
        status="completed",
    )

    elapsed = time.monotonic() - t0
    print(f"  Phase B done in {elapsed:.1f}s")
    return {
        "subdirs_scanned": CONDA_FORGE_SUBDIRS,
        "package_count": len(aggregated),
        "duration_seconds": round(elapsed, 1),
    }


def _download_feedstock_outputs_archive() -> dict[str, list[str]]:
    """Download conda-forge/feedstock-outputs main.zip and parse the sharded
    outputs/*/*.json files into a {package_name: [feedstocks...]} map.

    feedstock-outputs is the canonical 1:N source for "which feedstock(s) publish
    this package name." Multi-output feedstocks like pytorch-feedstock map many
    package names back to one feedstock.
    """
    import io
    import zipfile

    # Phase B.5 GitHub fetch — uses _http resolver chain when available so
    # JFrog Generic Remote / GITHUB_BASE_URL can redirect github.com.
    if _HTTP_AVAILABLE and _resolve_github_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_github_urls(
            "conda-forge/feedstock-outputs",
            "/archive/refs/heads/main.zip",
        )
        print(f"  Downloading feedstock-outputs zip ({len(urls)} source(s) tried)...")
        zip_bytes = _fetch_with_fallback(urls, timeout=300, user_agent="unified-map-builder/1.0")
    else:
        url = "https://github.com/conda-forge/feedstock-outputs/archive/refs/heads/main.zip"
        print(f"  Downloading {url}...")
        req = _make_req(url)
        with urllib.request.urlopen(req, timeout=300) as resp:
            zip_bytes = resp.read()
    print(f"  Got {len(zip_bytes):,} bytes; parsing sharded outputs/*/*.json...")

    # Per config.json, feedstock-outputs uses shard_level=3 with shard_fill='z'.
    # Paths look like: feedstock-outputs-main/outputs/2/1/c/21cmfast.json
    # We don't depend on a specific depth — accept any .json under outputs/.
    mapping: dict[str, list[str]] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            if "/outputs/" not in name:
                continue
            package_name = name.rsplit("/", 1)[-1][:-5]  # basename minus .json
            if not package_name:  # directory entries have empty basename
                continue
            try:
                payload = json.loads(zf.read(name))
                feedstocks = payload.get("feedstocks", [])
                if feedstocks:
                    mapping[package_name] = feedstocks
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return mapping


def phase_b5_feedstock_outputs(conn: sqlite3.Connection) -> dict:
    """Phase B.5: download feedstock-outputs archive; populate feedstock_name.

    For multi-output feedstocks, takes the first feedstock listed (typical
    case is 1:1; multi-feedstock listings are rare and usually indicate a
    package transition).

    Also inserts placeholder rows for packages registered in feedstock-outputs
    but absent from current_repodata.json — these are likely yanked, deprecated,
    or never built. Sets relationship='conda_only', latest_status='inactive'
    on those rows.

    Returns: stats dict.
    """
    t0 = time.monotonic()
    mapping = _download_feedstock_outputs_archive()
    print(f"  Loaded {len(mapping):,} package→feedstock mappings")

    # scope: Phase B.5 inserts inactive placeholder rows for outputs in
    # feedstock-outputs but not in current_repodata; needs ALL existing
    # conda_names (including archived/inactive) to decide INSERT vs UPDATE.
    existing = {row[0] for row in conn.execute("SELECT conda_name FROM packages WHERE conda_name IS NOT NULL")}
    print(f"  Existing conda_name rows: {len(existing):,}")

    # Incremental commits every 500 rows: a mid-phase interrupt on a 30k-row
    # mapping previously rolled back the entire phase under a single BEGIN/
    # COMMIT. The (conda_name, ...) UPDATEs and the conda_only INSERTs are
    # both idempotent (UPDATE-by-PK, INSERT with no UNIQUE that we'd violate
    # on retry beyond the ones already present in `existing`), so partial
    # progress survives across runs.
    updated = 0
    inserted_inactive = 0
    processed = 0
    commit_every = 500
    for pkg_name, feedstocks in mapping.items():
        feedstock_name = feedstocks[0] if feedstocks else None
        if pkg_name in existing:
            conn.execute(
                "UPDATE packages SET feedstock_name = ? WHERE conda_name = ?",
                (feedstock_name, pkg_name),
            )
            updated += 1
        else:
            conn.execute(
                """
                INSERT OR IGNORE INTO packages (
                    conda_name, feedstock_name,
                    relationship, match_source, match_confidence, latest_status
                ) VALUES (?, ?, 'conda_only', 'none', 'n/a', 'inactive')
                """,
                (pkg_name, feedstock_name),
            )
            inserted_inactive += 1
        processed += 1
        if processed % commit_every == 0:
            conn.commit()
    conn.commit()

    elapsed = time.monotonic() - t0
    print(f"  Phase B.5 done in {elapsed:.1f}s — updated {updated:,}, inserted {inserted_inactive:,} inactive")
    return {
        "feedstock_outputs_count": len(mapping),
        "updated_existing": updated,
        "inserted_inactive": inserted_inactive,
        "duration_seconds": round(elapsed, 1),
    }


def phase_b6_yanked_detection(conn: sqlite3.Connection) -> dict:
    """Phase B.6: assign latest_status based on current_repodata presence.

    Lite version (cheap): packages WITH a latest_conda_version → 'active';
    packages without (added in Phase B.5 from feedstock-outputs) → 'inactive'.

    Full per-version yanked detection (diff patched vs unpatched repodata)
    would add ~1GB of downloads and ~10 min build time. Deferred to true v2;
    the lite signal already covers "fully yanked / no current release" which
    is the most actionable case.
    """
    t0 = time.monotonic()
    # Intentional monolithic transaction: this phase issues 3 bulk UPDATEs
    # (no per-row loop) and runs in <1s. An interrupt mid-statement is
    # virtually impossible to hit and re-running is free. Don't refactor
    # to incremental commits — there's nothing to checkpoint.
    conn.execute("BEGIN TRANSACTION")
    try:
        # Definition: a row is 'active' iff its conda_name appears in
        # current_repodata. This handles all three transitions in one pass:
        #   - first-time activation (Phase B insert, no prior status)
        #   - re-activation (Phase B.5 row that reappeared in repodata)
        #   - demotion (was 'active', no longer in repodata)
        # Phase B populates the temp table; if it didn't run we fall back to
        # the lite "has-version → active" rule for partial-pipeline runs.
        have_temp = conn.execute(
            "SELECT 1 FROM sqlite_temp_master "
            "WHERE type='table' AND name='current_repodata_names'"
        ).fetchone()
        promoted = 0
        demoted = 0
        if have_temp:
            promoted = conn.execute(
                "UPDATE packages SET latest_status = 'active' "
                "WHERE conda_name IN (SELECT name FROM current_repodata_names) "
                "  AND COALESCE(latest_status, '') != 'active'"
            ).rowcount
            demoted = conn.execute(
                "UPDATE packages SET latest_status = 'inactive' "
                "WHERE conda_name IS NOT NULL "
                "  AND latest_status = 'active' "
                "  AND conda_name NOT IN (SELECT name FROM current_repodata_names)"
            ).rowcount
        else:
            promoted = conn.execute(
                "UPDATE packages SET latest_status = 'active' "
                "WHERE latest_conda_version IS NOT NULL AND latest_status IS NULL"
            ).rowcount
        # scope: Phase B.6 reports the active/inactive distribution as
        # cross-cutting stats; needs to count BOTH classes (the view excludes
        # inactive by definition).
        active_total = conn.execute(
            "SELECT COUNT(*) FROM packages WHERE latest_status = 'active'"
        ).fetchone()[0]
        # scope: same — counts the OPPOSITE side of the active/inactive split.
        inactive_total = conn.execute(
            "SELECT COUNT(*) FROM packages WHERE latest_status = 'inactive'"
        ).fetchone()[0]
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    elapsed = time.monotonic() - t0
    print(
        f"  Phase B.6 done in {elapsed:.1f}s — promoted: {promoted:,}, "
        f"demoted: {demoted:,}, totals active/inactive: "
        f"{active_total:,}/{inactive_total:,}"
    )
    return {
        "promoted_count": promoted,
        "demoted_count": demoted,
        "active_count": active_total,
        "inactive_count": inactive_total,
        "duration_seconds": round(elapsed, 2),
        "note": "lite mode; per-version yanked diff deferred to true v2",
    }


def phase_c_parselmouth_join(conn: sqlite3.Connection) -> dict:
    """Phase C: join via parselmouth's PyPI ↔ conda mapping (verified matches).

    Pulls from `conda_forge_metadata.autotick_bot.pypi_to_conda.get_pypi_name_mapping()`
    which wraps prefix-dev/parselmouth's hourly bot output. ~12k entries.
    """
    t0 = time.monotonic()
    try:
        from conda_forge_metadata.autotick_bot.pypi_to_conda import get_pypi_name_mapping
    except ImportError as e:
        raise RuntimeError("conda-forge-metadata required for Phase C") from e

    print("  Fetching parselmouth mapping via conda-forge-metadata...")
    entries = get_pypi_name_mapping()
    print(f"  Got {len(entries):,} mapping entries")

    # Incremental commits every 500 entries: a mid-loop interrupt previously
    # rolled back the whole ~12k-entry parselmouth merge. UPDATEs are
    # idempotent (UPDATE-by-conda_name, no UNIQUE violations on re-run).
    updated = 0
    processed = 0
    commit_every = 500
    for entry in entries:
        pypi_name = (entry.get("pypi_name") or "").lower()
        conda_name = entry.get("conda_name")
        if not pypi_name or not conda_name:
            continue
        relationship = "both_same_name" if pypi_name == conda_name else "both_renamed"
        cursor = conn.execute(
            """
            UPDATE packages
               SET pypi_name = ?, relationship = ?,
                   match_source = 'parselmouth', match_confidence = 'verified'
             WHERE conda_name = ?
            """,
            (pypi_name, relationship, conda_name),
        )
        updated += cursor.rowcount
        processed += 1
        if processed % commit_every == 0:
            conn.commit()
    conn.commit()

    elapsed = time.monotonic() - t0
    print(f"  Phase C done in {elapsed:.1f}s — matched {updated:,} conda rows to PyPI")
    return {
        "parselmouth_entries": len(entries),
        "matched_rows": updated,
        "duration_seconds": round(elapsed, 1),
    }


def phase_c5_source_url_match(conn: sqlite3.Connection) -> dict:
    """Phase C.5 — deferred. Recipe source.url match requires cf-graph data
    fetched in Phase E. Implemented inline within Phase E to avoid double-fetch.
    """
    _ = conn  # signature required by phases-list dispatcher; logic folded into E
    print("  Phase C.5 folded into Phase E (needs cf-graph data); skipping standalone")
    return {"folded_into": "E"}


def _fetch_pypi_simple() -> list[dict]:
    """Fetch the PyPI Simple v1 catalog (~40 MB, ~800k projects).

    Shared by Phase D's working-set update and universe upsert paths.
    Honors `_http.py` resolver fallback for enterprise mirroring via
    `PYPI_BASE_URL`.
    """
    if _HTTP_AVAILABLE and _resolve_pypi_simple_urls is not None and _fetch_with_fallback is not None:
        urls = [f"{base}/" for base in _resolve_pypi_simple_urls()]
        simple = _fetch_with_fallback(
            urls,
            extra_headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            user_agent="unified-map-builder/1.0",
            timeout=300,
            return_json=True,
        )
    else:
        req = _make_req(
            "https://pypi.org/simple/",
            extra_headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            simple = json.load(resp)
    return simple.get("projects", [])


def _phase_d_update_working_set(
    conn: sqlite3.Connection, projects: list[dict]
) -> tuple[int, int]:
    """Phase D's always-on lean path: update conda-linked serials + discover
    name-coincidence matches.

    Returns (serial_updates, name_coincidence_upgrades). Touches only rows
    already in `packages` — never inserts. The pypi-only corpus lives in
    `pypi_universe` (see `_phase_d_upsert_universe`).
    """
    # scope: Phase D name-coincidence discovery needs to match PyPI projects
    # against EVERY existing conda row (including archived/inactive — a
    # later "rebuild from archive" may rely on the cross-ecosystem mapping
    # being recorded). The view's actionable triplet would miss those.
    existing_conda = {row[0].lower(): row[0] for row in
                      conn.execute("SELECT conda_name FROM packages WHERE conda_name IS NOT NULL")
                      if row[0]}
    # scope: same — Phase D needs ALL existing pypi_names to decide UPDATE
    # vs name-coincidence promotion; archived rows must be considered.
    existing_pypi = {row[0] for row in
                     conn.execute("SELECT pypi_name FROM packages WHERE pypi_name IS NOT NULL")
                     if row[0]}

    commit_every = 5000
    updated_serial = 0
    upgraded_to_coincidence = 0
    written = 0
    for proj in projects:
        pypi_name = proj.get("name", "").lower()
        serial = proj.get("_last-serial")
        if not pypi_name:
            continue
        if pypi_name in existing_pypi:
            conn.execute(
                "UPDATE packages SET pypi_last_serial = ? WHERE pypi_name = ?",
                (serial, pypi_name),
            )
            updated_serial += 1
            written += 1
        elif pypi_name in existing_conda:
            conn.execute(
                """
                UPDATE packages
                   SET pypi_name = ?, pypi_last_serial = ?,
                       relationship = 'both_same_name',
                       match_source = 'name_coincidence',
                       match_confidence = 'likely'
                 WHERE conda_name = ? AND pypi_name IS NULL
                """,
                (pypi_name, serial, existing_conda[pypi_name]),
            )
            upgraded_to_coincidence += 1
            existing_pypi.add(pypi_name)
            written += 1
        # else: pypi-only project. NOT inserted into `packages` (v20+).
        # The pypi_universe upsert handles it.
        if written and written % commit_every == 0:
            conn.commit()
    conn.commit()
    return updated_serial, upgraded_to_coincidence


def _phase_d_universe_is_fresh(
    conn: sqlite3.Connection, ttl_days: float
) -> bool:
    """Probe `pypi_universe` freshness: True iff MAX(fetched_at) is within
    `ttl_days` of now. Empty table → False (forces first-time upsert).
    """
    row = conn.execute(
        "SELECT MAX(fetched_at) FROM pypi_universe"
    ).fetchone()
    if row is None or row[0] is None:
        return False
    cutoff = int(time.time()) - int(ttl_days * 86400)
    return row[0] > cutoff


def _phase_d_upsert_universe(
    conn: sqlite3.Connection, projects: list[dict]
) -> int:
    """TTL-gated bulk-write of the PyPI universe directory.

    Each call refreshes every project's `(pypi_name, last_serial, fetched_at)`
    row. Idempotent via INSERT OR REPLACE; safe to re-run after a partial
    crash. Incremental commits every 5k rows so a mid-run interrupt leaves
    a partial-but-coherent snapshot the next run will complete.
    """
    now = int(time.time())
    commit_every = 5000
    written = 0
    for proj in projects:
        pypi_name = proj.get("name", "").lower()
        serial = proj.get("_last-serial")
        if not pypi_name:
            continue
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(pypi_name) DO UPDATE SET "
            "  last_serial = excluded.last_serial, "
            "  fetched_at = excluded.fetched_at",
            (pypi_name, serial, now),
        )
        written += 1
        if written % commit_every == 0:
            conn.commit()
    conn.commit()
    return written


def phase_d_pypi_enumeration(conn: sqlite3.Connection) -> dict:
    """Phase D: enumerate PyPI universe via Simple API v1 (schema v20+).

    Two-tier write strategy:
      - **Always-on** (every build): update `packages.pypi_last_serial` on
        conda-linked rows + discover name-coincidence matches. Drives the
        working-set freshness signal. Cheap; no row inserts.
      - **TTL-gated** (default 7d via PHASE_D_UNIVERSE_TTL_DAYS): refresh
        the `pypi_universe` side table with the full ~800k-project
        catalog. Read by the `pypi-only-candidates` CLI via LEFT JOIN to
        `packages.pypi_name`.

    The legacy v19 `INSERT INTO packages ... 'pypi_only'` branch was
    removed in v20; pypi-only projects live in `pypi_universe`, never in
    `packages`. The v20 schema migration moves any pre-existing
    `relationship='pypi_only'` rows over and DELETEs them from `packages`
    so existing atlases self-heal on next `init_schema`.

    Tunables (env vars):
      - PHASE_D_DISABLED           : "1" to skip the entire phase
      - PHASE_D_UNIVERSE_DISABLED  : "1" to skip the universe upsert branch
                                     (keep the lean per-row work). Useful
                                     for consumer/maintainer profiles that
                                     never query the universe directly.
      - PHASE_D_UNIVERSE_TTL_DAYS  : days the universe table stays fresh
                                     before re-upserting (default 7).
                                     Lower for admin shops that query the
                                     candidate list daily.
    """
    t0 = time.monotonic()

    if os.environ.get("PHASE_D_DISABLED"):
        return {
            "skipped": True,
            "reason": "PHASE_D_DISABLED=1 set; skipping Phase D.",
            "duration_seconds": 0.0,
        }

    print("  Fetching PyPI Simple v1 JSON (~40MB)...")
    projects = _fetch_pypi_simple()
    print(f"  Got {len(projects):,} PyPI projects")

    save_phase_checkpoint(
        conn, "D", cursor=None, items_completed=0,
        items_total=len(projects), status="in_progress",
    )

    # Branch (a) + (b): always run.
    updated_serial, upgraded_to_coincidence = _phase_d_update_working_set(
        conn, projects
    )

    # Branch (c): TTL-gated universe upsert.
    universe_upserts = 0
    universe_skipped_reason: str | None = None
    if os.environ.get("PHASE_D_UNIVERSE_DISABLED"):
        universe_skipped_reason = "PHASE_D_UNIVERSE_DISABLED=1"
    else:
        try:
            ttl_days = float(os.environ.get("PHASE_D_UNIVERSE_TTL_DAYS", "7"))
        except ValueError:
            ttl_days = 7.0
        if _phase_d_universe_is_fresh(conn, ttl_days):
            universe_skipped_reason = f"universe TTL fresh (< {ttl_days}d)"
        else:
            universe_upserts = _phase_d_upsert_universe(conn, projects)

    save_phase_checkpoint(
        conn, "D", cursor="", items_completed=len(projects),
        items_total=len(projects), status="completed",
    )

    elapsed = time.monotonic() - t0
    print(f"  Phase D done in {elapsed:.1f}s")
    print(f"    parselmouth-matched serial updates: {updated_serial:,}")
    print(f"    upgraded to name_coincidence:        {upgraded_to_coincidence:,}")
    if universe_skipped_reason:
        print(f"    pypi_universe:                       skipped ({universe_skipped_reason})")
    else:
        print(f"    pypi_universe upserts:               {universe_upserts:,}")
    return {
        "pypi_projects": len(projects),
        "serial_updates": updated_serial,
        "name_coincidence_upgrades": upgraded_to_coincidence,
        "universe_upserts": universe_upserts,
        "universe_skipped_reason": universe_skipped_reason,
        "duration_seconds": round(elapsed, 1),
    }


# Regex patterns for source.url registry detection
_SRC_REGEX_PATTERNS = [
    ("pypi", r"(?:pypi\.io|pypi\.org|files\.pythonhosted\.org)/packages/"),
    ("npm", r"registry\.npmjs\.org/"),
    ("cran", r"cran[.-]r-project\.org/"),
    ("cpan", r"(?:cpan\.org|metacpan\.org)/"),
    ("luarocks", r"luarocks\.org/"),
    ("github", r"github\.com/.+/(?:archive|releases)"),
    ("maven", r"(?:repo\.maven\.apache\.org|repo1\.maven\.org|search\.maven\.org|"
              r"central\.sonatype\.com)/"),
]
# Specific extractors for cross-channel name within source.url
_NPM_NAME_RE = r"registry\.npmjs\.org/(@[^/]+/[^/]+|[^/]+)/-/"
_PYPI_NAME_RE = r"(?:pypi\.io|pypi\.org)/packages/source/[^/]/([^/]+)/"
# Maven jar URL: https://repo.maven.apache.org/maven2/<group/path>/<artifact>/<version>/<artifact>-<version>.jar
# Coords are derived as <group-with-slashes-as-dots>:<artifact>
_MAVEN_SOURCE_RE = re.compile(
    r"(?:repo\.maven\.apache\.org/maven2|repo1\.maven\.org/maven2)/"
    r"([^?#]+?)/([^/]+)/[^/]+/[^/]+\.(?:jar|pom|aar)"
)


def _classify_source_url(source_url: Any) -> tuple[str | None, str | None]:
    """Return (registry, extracted_name) tuple from a source URL.

    Coerces non-string inputs (lists, dicts, None) to a sane string by walking
    nested 'url' keys — meta.yaml sometimes stores source.url as a list of dicts.
    """
    if not source_url:
        return (None, None)
    if isinstance(source_url, list):
        # Take first non-empty url-like element
        for item in source_url:
            reg, name = _classify_source_url(item)
            if reg:
                return (reg, name)
        return (None, None)
    if isinstance(source_url, dict):
        return _classify_source_url(source_url.get("url"))
    if not isinstance(source_url, str):
        return (None, None)
    matched_registries = [reg for reg, pat in _SRC_REGEX_PATTERNS if re.search(pat, source_url)]
    if not matched_registries:
        return ("other", None)
    if len(matched_registries) > 1:
        return ("multiple", None)
    registry = matched_registries[0]
    if registry == "npm":
        m = re.search(_NPM_NAME_RE, source_url)
        return ("npm", m.group(1) if m else None)
    if registry == "pypi":
        m = re.search(_PYPI_NAME_RE, source_url)
        return ("pypi", m.group(1).lower() if m else None)
    return (registry, None)


def phase_e_enrichment(conn: sqlite3.Connection) -> dict:
    """Phase E: per-package enrichment via cf-graph-countyfair node_attrs.

    cf-graph-countyfair stores per-feedstock metadata as sharded JSON files
    at node_attrs/<letter>/<letter>/<letter>/<feedstock_name>.json. Each file
    contains the rendered recipe + about.json fields + extra.recipe-maintainers.

    Strategy: bulk download the cf-graph repo as a tarball (compressed ~250MB
    but only the node_attrs/ subset needed). For each conda package row with
    a feedstock_name, look up the corresponding node_attrs JSON and extract:
    summary, license_family (if not in repodata), homepage, dev_url, doc_url,
    repo_url, keywords, maintainers, recipe_format, source registry +
    cross-channel names (npm/cran/cpan/luarocks).

    Implementation note: cf-graph is large. For practical v1 we use a
    shallow strategy: clone only node_attrs/ via git sparse-checkout, OR
    fetch individual files on demand for our subset. The full archive is
    ~250MB compressed; node_attrs/ alone is ~150MB.

    Tunables (env vars):
      - PHASE_E_ENABLED          : "1" to enable Phase E (off by default).
      - ATLAS_CFGRAPH_TTL_DAYS   : days the cached cf-graph tarball stays
                                   fresh (default 1.0). Weekly-cron users
                                   should set ``ATLAS_CFGRAPH_TTL_DAYS=7``
                                   to skip the ~150MB re-download per run.
                                   Phases J and M reuse the same cache
                                   file, so the TTL is shared across them.
    """
    t0 = time.monotonic()
    print("  Phase E: per-package enrichment via cf-graph-countyfair")
    print("  WARNING: cf-graph bulk download is ~150MB; this takes ~3-5 min")
    print("  Skipping for v1-checkpoint. Implementation deferred — schema columns")
    print("  remain nullable. Re-run with PHASE_E_ENABLED=1 to fetch.")

    import os
    if not os.environ.get("PHASE_E_ENABLED"):
        return {
            "skipped": True,
            "reason": "Heavy fetch deferred. Set PHASE_E_ENABLED=1 to enable.",
            "duration_seconds": 0.0,
        }

    # Bulk download cf-graph node_attrs via tarball — cache to disk so retries
    # don't re-download the 139MB archive. We stream the parse from the cached
    # file (no in-memory ~150MB BytesIO buffer); only the download path needs
    # to materialize bytes in RAM.
    import tarfile
    cache_path = DATA_DIR / "cf-graph-countyfair.tar.gz"
    cache_age = (time.time() - cache_path.stat().st_mtime) / 86400 if cache_path.exists() else 999
    # TTL was hardcoded at 1 day; weekly-cron users were re-downloading the
    # ~150MB archive every run for no information gain. Override via env.
    try:
        cache_ttl_days = float(os.environ.get("ATLAS_CFGRAPH_TTL_DAYS", "1"))
    except ValueError:
        cache_ttl_days = 1.0
    if cache_path.exists() and cache_age < cache_ttl_days:
        print(f"  Using cached cf-graph archive ({cache_path.stat().st_size:,} bytes, "
              f"{cache_age:.2f}d old, TTL {cache_ttl_days}d)")
    else:
        # Multi-URL fallback chain via _http resolver when available; honors
        # GITHUB_BASE_URL for JFrog Generic Remote setups.
        if _HTTP_AVAILABLE and _resolve_github_urls is not None and _fetch_with_fallback is not None:
            urls = _resolve_github_urls(
                "regro/cf-graph-countyfair",
                "/archive/refs/heads/master.tar.gz",
            )
            print(f"  Downloading cf-graph archive ({len(urls)} source(s) tried, ~150 MB)...")
            tar_bytes = _fetch_with_fallback(urls, timeout=600, user_agent="unified-map-builder/1.0")
        else:
            cf_graph_url = "https://github.com/regro/cf-graph-countyfair/archive/refs/heads/master.tar.gz"
            print(f"  Downloading {cf_graph_url} (large)...")
            req = _make_req(cf_graph_url)
            with urllib.request.urlopen(req, timeout=600) as resp:
                tar_bytes = resp.read()
        # Atomic write: tmp + rename so an interrupt during write doesn't
        # leave a corrupt cache file that fails to open next run.
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        tmp_path.write_bytes(tar_bytes)
        os.replace(tmp_path, cache_path)
        print(f"  Cached to {cache_path}")
    print(f"  Streaming node_attrs/ from {cache_path.stat().st_size:,}-byte cache...")

    # scope: Phase E enrichment needs reverse-lookup map for ALL feedstocks
    # (including archived) since cf-graph may carry metadata for archived
    # feedstocks that we still want recorded.
    # Build feedstock_name → conda_name map for reverse-lookup
    feedstock_to_conda: dict[str, list[str]] = {}
    for row in conn.execute(
        "SELECT conda_name, feedstock_name FROM packages WHERE feedstock_name IS NOT NULL"
    ):
        feedstock_to_conda.setdefault(row[1], []).append(row[0])

    enriched = 0
    pypi_url_matched = 0
    commit_every = 200
    # Previously: monolithic BEGIN TRANSACTION around the entire ~25k-row
    # parse loop. A mid-parse interrupt (OOM, Ctrl-C, network blip during
    # subsequent phases) rolled the whole phase back. Now we commit every
    # `commit_every` enrichments so progress survives across runs — the
    # UPDATE SET ... COALESCE(?, col) statements below are idempotent.
    with tarfile.open(cache_path, "r:gz") as tf:
        for member in tf:
            if not member.isfile():
                continue
            # Match: cf-graph-countyfair-master/node_attrs/<l>/<l>/<l>/<feedstock>.json
            if "/node_attrs/" not in member.name or not member.name.endswith(".json"):
                continue
            feedstock_basename = member.name.rsplit("/", 1)[-1][:-5]
            conda_names = feedstock_to_conda.get(feedstock_basename, [])
            if not conda_names:
                continue
            f = tf.extractfile(member)
            if f is None:
                continue
            try:
                payload = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            # Extract about.json fields
            meta_yaml = payload.get("meta_yaml") or {}
            about = meta_yaml.get("about") or {}
            extra = meta_yaml.get("extra") or {}
            source = meta_yaml.get("source") or {}
            source_url = None
            if isinstance(source, dict):
                source_url = source.get("url")
            elif isinstance(source, list) and source:
                first = source[0]
                if isinstance(first, dict):
                    source_url = first.get("url")
            summary = about.get("summary")
            homepage = about.get("home")
            dev_url = about.get("dev_url")
            doc_url = about.get("doc_url")
            repo_url = about.get("repository") or about.get("dev_url")
            license_family = about.get("license_family")
            keywords = about.get("keywords") or []
            maintainers = extra.get("recipe-maintainers") or []
            # recipe_format detection from cf-graph node_attrs.
            # cf-graph stores meta_yaml.schema_version: 0 = v0 (meta.yaml,
            # Jinja-templated), 1 = v1 (recipe.yaml, native YAML context).
            # Earlier classifier looked for `rendered_recipes` which
            # cf-graph does not emit — left every row at "unknown".
            #
            # The full ladder:
            #   1. meta_yaml.schema_version explicit (1 → recipe.yaml,
            #      0 → meta.yaml).
            #   2. raw_meta_yaml head bytes ({% set → v0, context: → v1).
            #   3. meta_yaml structural shape (top-level `package` +
            #      `source`/`build` is v0; top-level `context` is v1).
            #      Catches CDT packages (~116 globally) which are auto-
            #      generated v0 without any Jinja templating.
            recipe_format = None
            sv = meta_yaml.get("schema_version") if isinstance(meta_yaml, dict) else None
            if sv == 1:
                recipe_format = "recipe.yaml"
            elif sv == 0:
                recipe_format = "meta.yaml"
            else:
                raw = payload.get("raw_meta_yaml") or ""
                head = raw[:500]
                if "{% set" in head or head.lstrip().startswith("{%"):
                    recipe_format = "meta.yaml"
                elif "context:" in head:
                    recipe_format = "recipe.yaml"
                elif isinstance(meta_yaml, dict):
                    # Structural-shape fallback. v1 recipes ALWAYS have a
                    # top-level `context` key in meta_yaml (the parsed
                    # YAML reflects this). v0 has package + source/build.
                    if "context" in meta_yaml:
                        recipe_format = "recipe.yaml"
                    elif "package" in meta_yaml and (
                        "source" in meta_yaml or "build" in meta_yaml
                    ):
                        recipe_format = "meta.yaml"
            if recipe_format is None:
                recipe_format = "unknown"
            # Source registry classification
            registry, extracted = _classify_source_url(source_url)

            # Coerce list-typed metadata fields to strings to avoid SQLite errors
            def _str(v: Any) -> str | None:
                if v is None:
                    return None
                if isinstance(v, str):
                    return v
                if isinstance(v, list):
                    return ", ".join(str(x) for x in v if x)
                return str(v)
            keywords_str = json.dumps(keywords) if keywords else None
            for conda_name in conda_names:
                conn.execute(
                    """
                    UPDATE packages SET
                        conda_summary = COALESCE(?, conda_summary),
                        conda_homepage = COALESCE(?, conda_homepage),
                        conda_dev_url = COALESCE(?, conda_dev_url),
                        conda_doc_url = COALESCE(?, conda_doc_url),
                        conda_repo_url = COALESCE(?, conda_repo_url),
                        conda_license_family = COALESCE(?, conda_license_family),
                        recipe_format = COALESCE(?, recipe_format),
                        conda_source_registry = COALESCE(?, conda_source_registry),
                        conda_keywords = COALESCE(?, conda_keywords)
                    WHERE conda_name = ?
                    """,
                    (
                        _str(summary), _str(homepage), _str(dev_url), _str(doc_url),
                        _str(repo_url), _str(license_family), recipe_format, registry,
                        keywords_str, conda_name,
                    ),
                )
                # C.5 fold-in: deterministic source.url → pypi match
                if registry == "pypi" and extracted:
                    cursor = conn.execute(
                        """
                        UPDATE packages SET
                            pypi_name = COALESCE(pypi_name, ?),
                            relationship = CASE WHEN ? = conda_name THEN 'both_same_name' ELSE 'both_renamed' END,
                            match_source = 'recipe_source_url',
                            match_confidence = 'verified'
                        WHERE conda_name = ?
                          AND match_source != 'parselmouth'
                        """,
                        (extracted, extracted, conda_name),
                    )
                    if cursor.rowcount:
                        pypi_url_matched += 1
                if registry == "npm" and extracted:
                    conn.execute(
                        "UPDATE packages SET npm_name = COALESCE(npm_name, ?) WHERE conda_name = ?",
                        (extracted, conda_name),
                    )
                if registry == "maven":
                    # Pull groupId:artifactId from the source URL when
                    # the recipe sources a jar/pom/aar from Maven Central.
                    m_match = _MAVEN_SOURCE_RE.search(source_url) if isinstance(source_url, str) else None
                    if m_match:
                        group_path = m_match.group(1).strip("/")
                        artifact = m_match.group(2)
                        group_id = group_path.replace("/", ".")
                        coord = f"{group_id}:{artifact}"
                        conn.execute(
                            "UPDATE packages SET maven_coord = COALESCE(maven_coord, ?) WHERE conda_name = ?",
                            (coord, conda_name),
                        )
                # Maintainers: insert into junction table
                for m in maintainers:
                    if not isinstance(m, str):
                        continue
                    conn.execute(
                        "INSERT OR IGNORE INTO maintainers(handle) VALUES (?)", (m,)
                    )
                    mid = conn.execute(
                        "SELECT id FROM maintainers WHERE handle = ?", (m,)
                    ).fetchone()[0]
                    conn.execute(
                        "INSERT OR IGNORE INTO package_maintainers(conda_name, maintainer_id) VALUES (?, ?)",
                        (conda_name, mid),
                    )
                enriched += 1
                if enriched % commit_every == 0:
                    conn.commit()
    conn.commit()

    elapsed = time.monotonic() - t0
    print(f"  Phase E done in {elapsed:.1f}s — enriched {enriched:,} rows; pypi_url matches {pypi_url_matched:,}")
    return {
        "enriched_rows": enriched,
        "pypi_url_matches": pypi_url_matched,
        "duration_seconds": round(elapsed, 1),
    }


def phase_e5_archived_feedstocks(conn: sqlite3.Connection) -> dict:
    """Phase E.5: GraphQL query for archived feedstocks in conda-forge org.

    Uses gh CLI's GraphQL access (no API token management needed). Sets
    feedstock_archived=1 and archived_at (UNIX seconds) on rows whose
    feedstock_name appears in the archived list, 0/NULL on the rest.

    Note: GitHub's GraphQL Repository type does not expose an "archived
    reason" field — that's a manual operator decision not stored on the
    repo. If that signal becomes useful, the `notes` column on `packages`
    is the right place for hand-curated annotations.
    """
    import datetime as dt
    import subprocess
    t0 = time.monotonic()
    print("  Phase E.5: querying conda-forge org for archived feedstock repos...")

    # Paginated GraphQL — conda-forge has thousands of feedstocks; we filter to archived only.
    # Page-level checkpoints land in `phase_state` so observers can see the
    # pagination progress mid-run (status='in_progress', items_completed=
    # accumulated repo count, last_completed_cursor=GraphQL endCursor). A
    # mid-pagination interrupt still restarts pagination from scratch — the
    # GraphQL call has no side effects, so re-running is safe and the
    # archived set rarely shifts more than a handful of repos between runs.
    archived: dict[str, str | None] = {}
    cursor = None
    page = 0
    while True:
        page += 1
        cursor_arg = f', after: "{cursor}"' if cursor else ""
        query = (
            "{ organization(login: \"conda-forge\") { "
            f"  repositories(first: 100, isArchived: true{cursor_arg}) {{ "
            "    nodes { name archivedAt } "
            "    pageInfo { hasNextPage endCursor } "
            "  } "
            "} }"
        )
        try:
            result = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True, text=True, check=True, timeout=60,
            )
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            err_msg = f"GraphQL failed on page {page}: {e.stderr[:200]}"
            print(f"  {err_msg}")
            save_phase_checkpoint(
                conn, "phase_e5",
                cursor=cursor,
                items_completed=len(archived),
                status="failed",
                last_error=err_msg,
            )
            conn.commit()
            break
        repos = data["data"]["organization"]["repositories"]
        for node in repos["nodes"]:
            archived[node["name"]] = node.get("archivedAt")
        cursor = repos["pageInfo"]["endCursor"]
        save_phase_checkpoint(
            conn, "phase_e5",
            cursor=cursor,
            items_completed=len(archived),
            status="in_progress",
        )
        conn.commit()
        if not repos["pageInfo"]["hasNextPage"]:
            break
    print(f"  Found {len(archived):,} archived repos in conda-forge org (across {page} pages)")

    def _iso_to_unix(s: str | None) -> int | None:
        if not s:
            return None
        try:
            # GitHub returns RFC 3339 / ISO 8601 with trailing 'Z'.
            return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return None

    # Filter to *-feedstock repos and apply
    archived_feedstocks = {
        name: ts for name, ts in archived.items() if name.endswith("-feedstock")
    }
    print(f"  {len(archived_feedstocks):,} are *-feedstock repos")

    # Default everyone to not-archived first; clears stale archived_at on
    # rows that were unarchived since last run. Then apply the per-feedstock
    # marks with periodic commits so a mid-apply interrupt still leaves the
    # DB in a coherent state (all UPDATEs are idempotent on re-run).
    conn.execute(
        "UPDATE packages SET feedstock_archived = 0, archived_at = NULL "
        "WHERE feedstock_name IS NOT NULL"
    )
    conn.commit()
    # Strip "-feedstock" suffix from GitHub repo names — feedstock-outputs
    # stores them WITHOUT the suffix (e.g., "numpy" not "numpy-feedstock"),
    # but GraphQL returns the full repo name.
    marked = 0
    with_timestamp = 0
    applied = 0
    commit_every = 500
    for fs_repo_name, archived_iso in archived_feedstocks.items():
        fs_short = fs_repo_name[:-len("-feedstock")]  # strip suffix
        ts_unix = _iso_to_unix(archived_iso)
        if ts_unix is not None:
            with_timestamp += 1
        update_cursor = conn.execute(
            "UPDATE packages SET feedstock_archived = 1, archived_at = ? "
            "WHERE feedstock_name = ?",
            (ts_unix, fs_short),
        )
        marked += update_cursor.rowcount
        applied += 1
        if applied % commit_every == 0:
            conn.commit()
    conn.commit()
    save_phase_checkpoint(
        conn, "phase_e5",
        cursor=None,
        items_completed=len(archived_feedstocks),
        items_total=len(archived_feedstocks),
        status="completed",
    )
    conn.commit()

    elapsed = time.monotonic() - t0
    print(
        f"  Phase E.5 done in {elapsed:.1f}s — marked {marked:,} rows as archived "
        f"({with_timestamp:,} with archivedAt timestamp)"
    )
    return {
        "archived_repos_total": len(archived),
        "archived_feedstocks": len(archived_feedstocks),
        "marked_rows": marked,
        "rows_with_archived_at": with_timestamp,
        "duration_seconds": round(elapsed, 1),
    }


_ANACONDA_API_FALLBACK = "https://api.anaconda.org"


def _anaconda_api_base() -> str:
    """Resolve the api.anaconda.org base URL.

    Priority:
      1. ANACONDA_API_BASE_URL env var (project convention)
      2. ANACONDA_API_BASE        env var (legacy, used by detail_cf_atlas.py)
      3. https://api.anaconda.org

    Air-gapped enterprise users can point this at a JFrog Artifactory or
    similar generic-HTTP mirror that proxies api.anaconda.org responses.
    """
    return (
        os.environ.get("ANACONDA_API_BASE_URL")
        or os.environ.get("ANACONDA_API_BASE")
        or _ANACONDA_API_FALLBACK
    ).rstrip("/")


_RETRY_AFTER_HARD_CAP_SECONDS = 60


def _parse_retry_after(value: str | None, *, fallback: float) -> float:
    """Parse an HTTP `Retry-After` header into a sleep duration in seconds.

    RFC 9110 allows either a delta-seconds integer (`Retry-After: 30`) or
    an HTTP-date (`Retry-After: Wed, 12 Nov 2025 14:00:00 GMT`). We accept
    the integer form precisely; for the HTTP-date form we compute the
    delta against `now`. Anything unparseable falls back to `fallback`.

    Hard-capped at `_RETRY_AFTER_HARD_CAP_SECONDS` (60s) — a buggy or
    hostile origin can otherwise stall a worker indefinitely. Treat
    longer Retry-After values as "give up, let TTL re-pick this row next
    run." Always returns ≥ 0.
    """
    if not value:
        return max(0.0, fallback)
    s = value.strip()
    try:
        secs = float(s)
    except ValueError:
        # HTTP-date form. Use email.utils.parsedate_to_datetime — handles
        # the RFC 5322 / RFC 7231 IMF-fixdate format.
        try:
            from email.utils import parsedate_to_datetime
            import datetime as _dt
            when = parsedate_to_datetime(s)
            now = _dt.datetime.now(when.tzinfo or _dt.timezone.utc)
            secs = (when - now).total_seconds()
        except Exception:
            return max(0.0, fallback)
    return max(0.0, min(secs, float(_RETRY_AFTER_HARD_CAP_SECONDS)))


def _phase_f_fetch_one(
    name: str, latest: str | None
) -> tuple[str, str | None, dict | None, str, str | None]:
    """Worker for Phase F. Returns (name, latest, payload, status, err_msg).

    status ∈ {'ok', '404', 'fail'}. err_msg is None on success, otherwise a
    short string suitable for `downloads_last_error`. On 429 retries up to 3x
    honoring the server's `Retry-After` header (capped at 60s); on 503
    similarly. On other 4xx returns 'fail' with the HTTP status; on network
    errors retries with exponential backoff + jitter.
    """
    import random as _random
    url = f"{_anaconda_api_base()}/package/conda-forge/{name}"
    last_err: str | None = None
    for attempt in range(3):
        try:
            req = _make_req(url)
            # 120s timeout: awscli's response is ~120MB / ~55s. With 8 workers,
            # one slow row doesn't gate the others.
            with urllib.request.urlopen(req, timeout=120) as resp:
                return (name, latest, json.load(resp), "ok", None)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 404:
                return (name, latest, None, "404", last_err)
            if e.code in (429, 503) and attempt < 2:
                # Prefer server-stated Retry-After when present; otherwise
                # fall back to exponential + ±25% jitter so synchronized
                # workers don't all wake up and re-request together.
                retry_after = e.headers.get("Retry-After") if e.headers else None
                base = 2.0 ** attempt + 1.0
                jitter = base * (0.75 + 0.5 * _random.random())
                sleep_for = _parse_retry_after(retry_after, fallback=jitter)
                time.sleep(sleep_for)
                continue
            return (name, latest, None, "fail", last_err)
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"
            if attempt < 2:
                # ±25% jitter on transient network failures too.
                base = 1.0 + attempt
                time.sleep(base * (0.75 + 0.5 * _random.random()))
                continue
            return (name, latest, None, "fail", last_err)
    return (name, latest, None, "fail", last_err or "exhausted retries")


def _phase_f_eligible_rows(conn: sqlite3.Connection) -> tuple[list, int, int, int]:
    """Resolve the TTL gate + LIMIT cap and return (rows, ttl_days, concurrency, limit)."""
    ttl_days = int(os.environ.get("PHASE_F_TTL_DAYS", "7"))
    # Default concurrency is 3 (was 8). api.anaconda.org has a soft per-IP
    # secondary rate limit; 8 workers on a 32k-row backfill reliably tripped
    # 429s. 3 workers stay well under the threshold while still parallelizing.
    # Override via PHASE_F_CONCURRENCY when you know the limit is higher
    # (e.g., authenticated requests, or a JFrog mirror with no rate cap).
    concurrency = max(1, int(os.environ.get("PHASE_F_CONCURRENCY", "3")))
    limit = int(os.environ.get("PHASE_F_LIMIT", "0"))
    cutoff = int(time.time()) - ttl_days * 86400

    # Reads from v_actionable_packages (schema v21+) — encodes the
    # canonical persona-filter triplet (conda_name + active + !archived).
    sql = (
        "SELECT DISTINCT conda_name, latest_conda_version "
        "FROM v_actionable_packages "
        "WHERE COALESCE(downloads_fetched_at, 0) < ?"
    )
    params: tuple = (cutoff,)
    if limit > 0:
        sql += " LIMIT ?"
        params = (cutoff, limit)
    rows = list(conn.execute(sql, params))
    return rows, ttl_days, concurrency, limit


def _phase_f_probe_api() -> tuple[bool, str | None]:
    """Reachability check for the anaconda API via one GET against `pip`.

    Honors ANACONDA_API_BASE_URL so probes against a JFrog mirror don't
    misclassify the public endpoint as unreachable.

    Returns (ok, reason). On success, reason is None. On failure, reason
    is a short tag suitable for logging.
    """
    url = f"{_anaconda_api_base()}/package/conda-forge/pip"
    try:
        req = _make_req(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read(1)
        return (True, None)
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            return (False, f"HTTP {e.code}")
        return (True, None)
    except Exception as e:  # noqa: BLE001
        return (False, f"{type(e).__name__}: {str(e)[:120]}")


def _phase_f_via_api(
    conn: sqlite3.Connection,
    *,
    rows: list | None = None,
    ttl_days: int | None = None,
    concurrency: int | None = None,
    abort_on_high_failure: bool = False,
) -> dict:
    """Original Phase F path: per-row HTTP fetches against `api.anaconda.org`.

    When `abort_on_high_failure` is True, the dispatcher will cancel
    pending futures once >25% of the first 1,000 completed rows have
    failed; the names of the rows that never got written are returned in
    `unwritten` so the caller can fall through to S3 for them.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    t0 = time.monotonic()
    if rows is None:
        rows, ttl_days, concurrency, _ = _phase_f_eligible_rows(conn)
    if ttl_days is None:
        ttl_days = int(os.environ.get("PHASE_F_TTL_DAYS", "7"))
    if concurrency is None:
        concurrency = max(1, int(os.environ.get("PHASE_F_CONCURRENCY", "3")))
    print(f"  {len(rows):,} rows to refresh (TTL {ttl_days}d, concurrency {concurrency})")

    fetched = 0
    failed = 0
    not_found = 0
    # Cap at 2,500 so multi-100k-row runs still emit a line every ~30-60s
    # instead of going silent for many minutes (the historical "Phase H is
    # hung" misdiagnosis — workers were churning, the formula just buried
    # the signal under a 20k-row gap).
    progress_every = min(max(500, len(rows) // 40), 2500) if rows else 1
    commit_every = 500
    completed = 0
    aborted = False
    unwritten: list[tuple[str, str | None]] = []
    unwritten_seen: set[str] = set()

    def _mark_unwritten(row_id: tuple[str, str | None] | None) -> None:
        if row_id and row_id[0] and row_id[0] not in unwritten_seen:
            unwritten.append(row_id)
            unwritten_seen.add(row_id[0])

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        future_to_row = {
            ex.submit(_phase_f_fetch_one, r["conda_name"], r["latest_conda_version"]): (
                r["conda_name"], r["latest_conda_version"]
            )
            for r in rows
        }
        for fut in as_completed(future_to_row):
            if aborted:
                _mark_unwritten(future_to_row.get(fut))
                continue
            name, latest, payload, status, err_msg = fut.result()
            now = int(time.time())
            if status == "ok":
                files = (payload or {}).get("files") or []
                total = sum(int(f.get("ndownloads") or 0) for f in files)
                latest_dl = sum(
                    int(f.get("ndownloads") or 0)
                    for f in files
                    if f.get("version") == latest
                )
                by_version: dict[str, dict[str, Any]] = {}
                for f in files:
                    fver = f.get("version")
                    if not fver:
                        continue
                    bucket = by_version.setdefault(
                        fver, {"downloads": 0, "files": 0, "upload": None}
                    )
                    bucket["downloads"] += int(f.get("ndownloads") or 0)
                    bucket["files"] += 1
                    upload_str = f.get("upload_time")
                    if upload_str:
                        try:
                            ts = int(_iso_to_unix_safe(upload_str) or 0)
                        except (TypeError, ValueError):
                            ts = 0
                        if ts and (bucket["upload"] is None or ts < bucket["upload"]):
                            bucket["upload"] = ts
                conn.execute(
                    "UPDATE packages SET total_downloads = ?, "
                    "latest_version_downloads = ?, downloads_fetched_at = ?, "
                    "downloads_fetch_attempts = COALESCE(downloads_fetch_attempts, 0) + 1, "
                    "downloads_last_error = NULL, "
                    "downloads_source = 'anaconda-api' "
                    "WHERE conda_name = ?",
                    (total, latest_dl, now, name),
                )
                for fver, info in by_version.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO package_version_downloads "
                        "(conda_name, version, upload_unix, file_count, "
                        "total_downloads, fetched_at, source) "
                        "VALUES (?, ?, ?, ?, ?, ?, 'anaconda-api')",
                        (name, fver, info["upload"], info["files"],
                         info["downloads"], now),
                    )
                fetched += 1
            elif status == "404":
                conn.execute(
                    "UPDATE packages SET total_downloads = 0, "
                    "latest_version_downloads = 0, downloads_fetched_at = ?, "
                    "downloads_fetch_attempts = COALESCE(downloads_fetch_attempts, 0) + 1, "
                    "downloads_last_error = ?, "
                    "downloads_source = 'anaconda-api' "
                    "WHERE conda_name = ?",
                    (now, err_msg, name),
                )
                not_found += 1
            else:
                conn.execute(
                    "UPDATE packages SET "
                    "downloads_fetch_attempts = COALESCE(downloads_fetch_attempts, 0) + 1, "
                    "downloads_last_error = ? "
                    "WHERE conda_name = ?",
                    (err_msg, name),
                )
                failed += 1

            completed += 1
            if completed % commit_every == 0:
                conn.commit()

            # Abort guard runs on EVERY iteration after the first 1,000 rows,
            # not just inside the failure branch — a long success streak
            # followed by a late failure burst must still trigger fallback.
            if abort_on_high_failure and not aborted and completed >= 1000:
                if failed / completed > 0.25:
                    aborted = True
                    for pending_fut, row_id in future_to_row.items():
                        if not pending_fut.done():
                            pending_fut.cancel()
                            _mark_unwritten(row_id)
                    print(
                        f"  Phase F: aborting API pool — {failed}/{completed} "
                        f"failed (>25%); falling back to S3 for unwritten rows"
                    )

            if completed % progress_every == 0:
                elapsed = time.monotonic() - t0
                rate = completed / elapsed if elapsed else 0
                eta_min = (len(rows) - completed) / rate / 60 if rate else 0
                print(
                    f"    [{completed:,}/{len(rows):,}] fetched={fetched:,} "
                    f"failed={failed:,} 404={not_found:,}  "
                    f"rate={rate:.1f}/s  ETA={eta_min:.1f}min"
                )

    conn.commit()
    elapsed = time.monotonic() - t0
    print(
        f"  Phase F (api) done in {elapsed:.1f}s — fetched {fetched:,}, "
        f"failed {failed:,}, 404 {not_found:,}"
    )
    return {
        "rows_eligible": len(rows),
        "fetched": fetched,
        "failed": failed,
        "not_found_404": not_found,
        "ttl_days": ttl_days,
        "concurrency": concurrency,
        "duration_seconds": round(elapsed, 1),
        "source": "anaconda-api",
        "aborted": aborted,
        "unwritten": unwritten,
    }


def _phase_f_via_s3(
    conn: sqlite3.Connection,
    *,
    rows: list | None = None,
    only_names: set[str] | None = None,
) -> dict:
    """S3-parquet Phase F path: bulk-read monthly parquet, aggregate, batch-write.

    Reads months from `_parquet_cache.list_s3_parquet_months()` (or the last
    N months when `PHASE_F_S3_MONTHS` is set), filters to `data_source =
    'conda-forge'`, and aggregates with pyarrow. Writes use the same
    500-row batched-commit pattern as the API path. `only_names`, when
    set, restricts the write back to those rows (used by the auto-mode
    fallback to fill only the rows the API pool didn't manage to write).
    """
    sys.path.insert(0, str(Path(__file__).parent))
    import _parquet_cache  # type: ignore[import-not-found]
    import pyarrow.compute as pc

    t0 = time.monotonic()
    print("  Phase F: per-package download counts via S3 parquet")

    if rows is None:
        rows, ttl_days, _, _ = _phase_f_eligible_rows(conn)
    else:
        ttl_days = int(os.environ.get("PHASE_F_TTL_DAYS", "7"))

    eligible_names = {r["conda_name"] for r in rows}
    latest_version_by_name = {r["conda_name"]: r["latest_conda_version"] for r in rows}
    if only_names is not None:
        eligible_names &= only_names
    print(f"  {len(eligible_names):,} rows eligible from S3")

    if not eligible_names:
        elapsed = time.monotonic() - t0
        return {
            "rows_eligible": 0, "fetched": 0, "failed": 0, "not_found_404": 0,
            "ttl_days": ttl_days, "months_loaded": 0,
            "duration_seconds": round(elapsed, 1), "source": "s3-parquet",
        }

    all_months = _parquet_cache.list_s3_parquet_months()
    if not all_months:
        raise RuntimeError("Phase F S3: bucket listing returned no months")
    raw = os.environ.get("PHASE_F_S3_MONTHS", "0")
    try:
        trailing = max(0, int(raw))
    except ValueError:
        print(f"  ignoring invalid PHASE_F_S3_MONTHS={raw!r}; loading all months")
        trailing = 0
    months = all_months[-trailing:] if trailing > 0 else all_months
    current_month = all_months[-1]
    print(f"  loading {len(months)} months (current={current_month})")
    for m in months:
        _parquet_cache.ensure_month(m, current_month=current_month)

    table = _parquet_cache.read_filtered(
        months, pkg_names=eligible_names, data_source="conda-forge"
    )
    print(f"  parquet rows after filter: {table.num_rows:,}")

    nz_table = table.filter(pc.field("counts") > 0)
    by_pkg = nz_table.group_by("pkg_name").aggregate([("counts", "sum")])
    totals: dict[str, int] = {
        pkg: int(s or 0)
        for pkg, s in zip(by_pkg["pkg_name"].to_pylist(), by_pkg["counts_sum"].to_pylist())
        if pkg
    }

    # Aggregate 2: per (pkg_name, pkg_version) → downloads.
    by_ver = table.group_by(["pkg_name", "pkg_version"]).aggregate([
        ("counts", "sum"),
    ])
    per_version: dict[str, dict[str, int]] = {}
    pkg_v = by_ver["pkg_name"].to_pylist()
    ver_v = by_ver["pkg_version"].to_pylist()
    sum_v = by_ver["counts_sum"].to_pylist()
    for i, pkg in enumerate(pkg_v):
        ver = ver_v[i]
        if not pkg or not ver:
            continue
        per_version.setdefault(pkg, {})[ver] = int(sum_v[i] or 0)

    fetched = 0
    not_found = 0
    completed = 0
    commit_every = 500
    now = int(time.time())

    for name in eligible_names:
        total = totals.get(name)
        latest = latest_version_by_name.get(name)
        if total is None:
            # Package had no rows in the parquet sweep. Leave any prior
            # downloads_last_error in place (don't mask a real error with NULL).
            conn.execute(
                "UPDATE packages SET total_downloads = 0, "
                "latest_version_downloads = 0, downloads_fetched_at = ?, "
                "downloads_fetch_attempts = COALESCE(downloads_fetch_attempts, 0) + 1, "
                "downloads_source = 's3-parquet' "
                "WHERE conda_name = ?",
                (now, name),
            )
            not_found += 1
        else:
            latest_dl = per_version.get(name, {}).get(latest, 0) if latest else 0
            conn.execute(
                "UPDATE packages SET total_downloads = ?, "
                "latest_version_downloads = ?, downloads_fetched_at = ?, "
                "downloads_fetch_attempts = COALESCE(downloads_fetch_attempts, 0) + 1, "
                "downloads_last_error = NULL, "
                "downloads_source = 's3-parquet' "
                "WHERE conda_name = ?",
                (total, latest_dl, now, name),
            )
            # UPSERT preserves upload_unix/file_count from any prior API
            # write — S3 has neither column. Without this, an auto-mode run
            # that mixes API and S3 would clobber real file counts with NULL.
            for ver, dl in per_version.get(name, {}).items():
                conn.execute(
                    "INSERT INTO package_version_downloads "
                    "(conda_name, version, upload_unix, file_count, "
                    "total_downloads, fetched_at, source) "
                    "VALUES (?, ?, NULL, NULL, ?, ?, 's3-parquet') "
                    "ON CONFLICT(conda_name, version) DO UPDATE SET "
                    "  total_downloads = excluded.total_downloads, "
                    "  fetched_at = excluded.fetched_at, "
                    "  source = excluded.source",
                    (name, ver, dl, now),
                )
            fetched += 1
        completed += 1
        if completed % commit_every == 0:
            conn.commit()

    conn.commit()
    elapsed = time.monotonic() - t0
    print(
        f"  Phase F (s3) done in {elapsed:.1f}s — fetched {fetched:,}, "
        f"no_data {not_found:,}"
    )
    return {
        "rows_eligible": len(eligible_names),
        "fetched": fetched,
        "failed": 0,
        "not_found_404": not_found,
        "ttl_days": ttl_days,
        "months_loaded": len(months),
        "duration_seconds": round(elapsed, 1),
        "source": "s3-parquet",
    }


def _phase_f_via_auto(conn: sqlite3.Connection) -> dict:
    """Probe `api.anaconda.org`; on success run the API path with mid-run
    failure-rate guard, on failure fall through to S3 for the whole set.

    If the API path aborts mid-run on >25% failures, the dispatcher
    invokes the S3 path for the unwritten subset and marks any row that
    received writes from both paths as `'merged'`.
    """
    t0 = time.monotonic()
    ok, reason = _phase_f_probe_api()
    if not ok:
        print(f"  Phase F: api probe failed ({reason}); falling back to S3")
        result = _phase_f_via_s3(conn)
        result["probe"] = reason
        result["duration_seconds"] = round(time.monotonic() - t0, 1)
        return result

    rows, ttl_days, concurrency, _ = _phase_f_eligible_rows(conn)
    api_result = _phase_f_via_api(
        conn, rows=rows, ttl_days=ttl_days, concurrency=concurrency,
        abort_on_high_failure=True,
    )
    if not api_result.get("aborted"):
        api_result["duration_seconds"] = round(time.monotonic() - t0, 1)
        return api_result

    unwritten = {name for name, _ in api_result.get("unwritten", []) if name}
    s3_result = _phase_f_via_s3(conn, rows=rows, only_names=unwritten)
    # Per-row tags stay accurate ('anaconda-api' or 's3-parquet'); only the
    # run-summary `source` is 'merged'. Overwriting per-row tags would hide
    # which dataset actually populated each row.
    conn.commit()
    return {
        "rows_eligible": api_result["rows_eligible"],
        "fetched": api_result["fetched"] + s3_result["fetched"],
        "failed": api_result["failed"],
        "not_found_404": api_result["not_found_404"] + s3_result["not_found_404"],
        "ttl_days": ttl_days,
        "concurrency": concurrency,
        "duration_seconds": round(time.monotonic() - t0, 1),
        "source": "merged",
    }


def phase_f_downloads(conn: sqlite3.Connection) -> dict:
    """Phase F: per-package download counts.

    Dispatches on `PHASE_F_SOURCE` (default `auto`):
      - `anaconda-api`  → existing per-row HTTP path against api.anaconda.org
      - `s3-parquet`    → bulk read of `anaconda-package-data` S3 monthly parquets
      - `auto`          → probe API once; on success run API (with >25% failure
                          guard that falls through to S3 for unwritten rows);
                          on failure run S3 for the whole eligible set.

    Tunables (env vars):
      - PHASE_F_DISABLED       : "1" to skip entirely (opt-out)
      - PHASE_F_SOURCE         : auto | anaconda-api | s3-parquet (default
                                 auto). Large orgs (>30k rows) that
                                 reliably hit api.anaconda.org's 429 wall
                                 should set ``PHASE_F_SOURCE=s3-parquet``
                                 to skip the API path entirely.
      - PHASE_F_TTL_DAYS       : skip rows refreshed within N days (default 7)
      - PHASE_F_CONCURRENCY    : API worker pool size (default 3). The
                                 default was 8 until we observed 25%+
                                 429-rate failures on 32k-row backfills;
                                 3 stays under api.anaconda.org's per-IP
                                 secondary limit. Raise only when you know
                                 your link tolerates higher load
                                 (authenticated requests, JFrog mirror).
      - PHASE_F_LIMIT          : cap rows processed (debug; 0 = no cap)
      - PHASE_F_S3_MONTHS      : trailing months to load from S3 (0 = all)
      - S3_PARQUET_BASE_URL    : enterprise mirror for the parquet bucket
      - ANACONDA_API_BASE_URL  : enterprise mirror for api.anaconda.org
                                 (e.g. a JFrog generic-HTTP remote). Falls
                                 back to ANACONDA_API_BASE (legacy) then
                                 the public host.

    Every populated row carries a non-NULL `downloads_source` discriminator
    (`'anaconda-api'` | `'s3-parquet'` | `'merged'`) so consumers can
    surface which dataset produced the number.

    Rate-limit handling: the API path retries on 429 / 503 honoring the
    server's ``Retry-After`` header (capped at 60s); on other transient
    failures, it backs off exponentially with ±25% jitter to avoid
    synchronized retry storms across the worker pool.
    """
    print("  Phase F: per-package download counts")

    if os.environ.get("PHASE_F_DISABLED"):
        return {
            "skipped": True,
            "reason": "PHASE_F_DISABLED=1 set; skipping Phase F.",
            "duration_seconds": 0.0,
        }

    source = os.environ.get("PHASE_F_SOURCE", "auto").lower()
    if source == "anaconda-api":
        return _phase_f_via_api(conn)
    if source == "s3-parquet":
        return _phase_f_via_s3(conn)
    if source == "auto":
        return _phase_f_via_auto(conn)
    raise ValueError(
        f"PHASE_F_SOURCE={source!r} is not one of auto, anaconda-api, s3-parquet"
    )


def phase_g_vdb_summary(conn: sqlite3.Connection) -> dict:
    """Phase G: cache vdb risk summary into the packages table.

    For each active conda-forge row, derives purls and queries the AppThreat
    multi-source vdb to populate four count columns + a scan timestamp:
      - vuln_total                       — total CVEs across all purls
      - vuln_critical_affecting_current  — Critical hits on latest_conda_version
      - vuln_high_affecting_current      — High hits on latest_conda_version
      - vuln_kev_affecting_current       — KEV-flagged hits on latest_conda_version
      - vdb_scanned_at                   — UNIX seconds of this run
      - vdb_last_error                   — error string on failure, NULL on success

    Mirrors the *counts* — not the full vuln rows. The full data still requires
    `--vdb` against the live vdb library (which only the `vuln-db` pixi env
    has). The cache lets `local-recipes` env callers and offline tooling
    (staleness-report, dashboards, batch queries) rank by risk without
    spinning up the heavy env.

    Auto-skip when the vdb library isn't importable — graceful degradation in
    `local-recipes` env. Opt-out via PHASE_G_DISABLED=1 even in vuln-db env.

    Tunables (env vars):
      - PHASE_G_DISABLED  : "1" to skip entirely (e.g., CI smoke builds)
      - PHASE_G_TTL_DAYS  : skip rows scanned within N days (default 7)
      - PHASE_G_LIMIT     : cap rows processed (debug; 0 = no cap)

    Concurrency: default serial. vdb's on-disk index reader is not documented
    as thread-safe; running serial keeps the result deterministic. Future
    PHASE_G_CONCURRENCY tunable may be added once thread-safety is confirmed.
    """
    t0 = time.monotonic()
    print("  Phase G: vdb risk-summary cache")

    if os.environ.get("PHASE_G_DISABLED"):
        return {
            "skipped": True,
            "reason": "PHASE_G_DISABLED=1 set; skipping vdb scan.",
            "duration_seconds": 0.0,
        }

    # Auto-skip when vdb library isn't installed (i.e., not in vuln-db env).
    # `find_spec` raises ModuleNotFoundError when the top-level package is
    # missing, so wrap defensively rather than relying on a None return.
    import importlib.util
    try:
        spec = importlib.util.find_spec("vdb.lib.search")
    except (ModuleNotFoundError, ValueError):
        spec = None
    if spec is None:
        return {
            "skipped": True,
            "reason": "vdb library not installed (run from `vuln-db` env).",
            "duration_seconds": 0.0,
        }

    # Reuse the canonical purl-derivation + scoring logic from
    # detail_cf_atlas. Both live in this same scripts/ directory.
    sys.path.insert(0, str(Path(__file__).parent))
    from detail_cf_atlas import fetch_vdb_data  # type: ignore[import-not-found]

    ttl_days = int(os.environ.get("PHASE_G_TTL_DAYS", "7"))
    limit = int(os.environ.get("PHASE_G_LIMIT", "0"))
    cutoff = int(time.time()) - ttl_days * 86400

    # Reads from v_actionable_packages (schema v21+) — canonical triplet.
    sql = (
        "SELECT conda_name, pypi_name, npm_name, latest_conda_version, "
        "       conda_repo_url, conda_dev_url "
        "FROM v_actionable_packages "
        "WHERE COALESCE(vdb_scanned_at, 0) < ?"
    )
    params: tuple = (cutoff,)
    if limit > 0:
        sql += " LIMIT ?"
        params = (cutoff, limit)
    rows = list(conn.execute(sql, params))
    print(f"  {len(rows):,} rows to scan (TTL {ttl_days}d)")

    scanned = 0
    failed = 0
    no_purls = 0
    progress_every = min(max(200, len(rows) // 40), 2500) if rows else 1
    commit_every = 200

    for i, row in enumerate(rows):
        record = {
            "conda_name":           row["conda_name"],
            "pypi_name":            row["pypi_name"],
            "npm_name":             row["npm_name"],
            "latest_conda_version": row["latest_conda_version"],
            "conda_repo_url":       row["conda_repo_url"],
            "conda_dev_url":        row["conda_dev_url"],
        }
        data, err = fetch_vdb_data(record)
        now = int(time.time())
        if data is None:
            if err and "no purls derivable" in err:
                no_purls += 1
                conn.execute(
                    "UPDATE packages SET vuln_total = 0, "
                    "vuln_critical_affecting_current = 0, "
                    "vuln_high_affecting_current = 0, "
                    "vuln_kev_affecting_current = 0, "
                    "vdb_scanned_at = ?, vdb_last_error = NULL "
                    "WHERE conda_name = ?",
                    (now, row["conda_name"]),
                )
            else:
                failed += 1
                conn.execute(
                    "UPDATE packages SET vdb_last_error = ? "
                    "WHERE conda_name = ?",
                    (err[:200] if err else "unknown error", row["conda_name"]),
                )
            continue

        affecting = data.get("affecting_latest_version", []) or []
        crit = sum(1 for v in affecting if v.get("severity") == "Critical")
        high = sum(1 for v in affecting if v.get("severity") == "High")
        kev = sum(1 for v in affecting if v.get("kev"))
        total = len(data.get("all_vulns") or [])
        conn.execute(
            "UPDATE packages SET "
            "vuln_total = ?, "
            "vuln_critical_affecting_current = ?, "
            "vuln_high_affecting_current = ?, "
            "vuln_kev_affecting_current = ?, "
            "vdb_scanned_at = ?, vdb_last_error = NULL "
            "WHERE conda_name = ?",
            (total, crit, high, kev, now, row["conda_name"]),
        )
        scanned += 1

        if (scanned + failed + no_purls) % commit_every == 0:
            conn.commit()
        if (i + 1) % progress_every == 0:
            elapsed = time.monotonic() - t0
            rate = (i + 1) / elapsed if elapsed else 0
            eta_min = (len(rows) - i - 1) / rate / 60 if rate else 0
            print(
                f"    [{i+1:,}/{len(rows):,}] scanned={scanned:,} "
                f"no_purls={no_purls:,} failed={failed:,}  "
                f"rate={rate:.1f}/s  ETA={eta_min:.1f}min"
            )

    conn.commit()
    # Snapshot history: insert one row per package whose vdb_scanned_at is
    # current (i.e., scanned in this run OR within the TTL window from prior
    # runs). Rows where Phase G hasn't run yet are excluded — they'd skew
    # the trend with NULL vs 0.
    snapshot_at = int(time.time())
    snap = conn.execute(
        "INSERT INTO vuln_history (snapshot_at, conda_name, vuln_total, "
        "vuln_critical_affecting_current, vuln_high_affecting_current, "
        "vuln_kev_affecting_current) "
        "SELECT ?, conda_name, vuln_total, "
        "vuln_critical_affecting_current, vuln_high_affecting_current, "
        "vuln_kev_affecting_current "
        "FROM packages "
        "WHERE conda_name IS NOT NULL AND vdb_scanned_at IS NOT NULL",
        (snapshot_at,),
    )
    snapshot_rows = snap.rowcount
    conn.commit()
    elapsed = time.monotonic() - t0
    print(
        f"  Phase G done in {elapsed:.1f}s — scanned: {scanned:,}, "
        f"no_purls: {no_purls:,}, failed: {failed:,}, "
        f"snapshot rows: {snapshot_rows:,}"
    )
    return {
        "rows_eligible": len(rows),
        "scanned": scanned,
        "no_purls": no_purls,
        "failed": failed,
        "snapshot_rows": snapshot_rows,
        "snapshot_at": snapshot_at,
        "ttl_days": ttl_days,
        "duration_seconds": round(elapsed, 1),
    }


def load_phase_checkpoint(conn: sqlite3.Connection, phase_name: str) -> dict | None:
    """Return the most recent `phase_state` row for `phase_name`, or None.

    Phases use this on entry to decide whether to skip already-processed
    cursor values. Callers should treat a row with `status='completed'`
    as "no resume needed" — that run finished cleanly.
    """
    row = conn.execute(
        "SELECT phase_name, run_started_at, last_completed_cursor, "
        "items_completed, items_total, run_completed_at, status, last_error "
        "FROM phase_state WHERE phase_name = ?",
        (phase_name,),
    ).fetchone()
    return dict(row) if row else None


def save_phase_checkpoint(
    conn: sqlite3.Connection,
    phase_name: str,
    *,
    cursor: str | None = None,
    items_completed: int | None = None,
    items_total: int | None = None,
    status: str = "in_progress",
    last_error: str | None = None,
) -> None:
    """UPSERT a `phase_state` row. `run_started_at` is preserved across
    incremental updates; `run_completed_at` is set when status is 'completed'.
    Auto-commits so the checkpoint survives an interrupt right after this call.
    """
    now = int(time.time())
    existing = load_phase_checkpoint(conn, phase_name)
    run_started_at = existing["run_started_at"] if existing and existing.get("status") == "in_progress" else now
    run_completed_at = now if status == "completed" else None
    conn.execute(
        "INSERT INTO phase_state "
        "(phase_name, run_started_at, last_completed_cursor, items_completed, "
        " items_total, run_completed_at, status, last_error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(phase_name) DO UPDATE SET "
        "  run_started_at = excluded.run_started_at, "
        "  last_completed_cursor = excluded.last_completed_cursor, "
        "  items_completed = excluded.items_completed, "
        "  items_total = excluded.items_total, "
        "  run_completed_at = excluded.run_completed_at, "
        "  status = excluded.status, "
        "  last_error = excluded.last_error",
        (phase_name, run_started_at, cursor, items_completed, items_total,
         run_completed_at, status, last_error),
    )
    conn.commit()


def _snapshot_upstream_versions(conn: sqlite3.Connection,
                                  source_filter: str | None = None) -> int:
    """Append a snapshot of `upstream_versions` into the history table.

    Called at the end of Phase H / K / L. `source_filter` restricts the
    snapshot to one source (e.g., 'pypi' for Phase H, 'github'/'gitlab'/
    'codeberg' for Phase K). When None, snapshots all sources — used by
    Phase L which writes multiple sources in one run.
    """
    snapshot_at = int(time.time())
    if source_filter:
        sql = (
            "INSERT OR IGNORE INTO upstream_versions_history "
            "(snapshot_at, conda_name, source, version) "
            "SELECT ?, conda_name, source, version FROM upstream_versions "
            "WHERE source = ? AND version IS NOT NULL"
        )
        params = (snapshot_at, source_filter)
    else:
        sql = (
            "INSERT OR IGNORE INTO upstream_versions_history "
            "(snapshot_at, conda_name, source, version) "
            "SELECT ?, conda_name, source, version FROM upstream_versions "
            "WHERE version IS NOT NULL"
        )
        params = (snapshot_at,)
    cursor = conn.execute(sql, params)
    conn.commit()
    return cursor.rowcount


def _phase_h_fetch_one(pypi_name: str
                       ) -> tuple[str, str | None, bool | None, str | None]:
    """Worker for Phase H. Returns (pypi_name, current_version, yanked, err).

    Hits https://pypi.org/pypi/<name>/json. Reads `info.version` and the
    matching release entry's `yanked` flag (PEP 592). Yanked-but-still-
    visible versions appear in `info.version` but should NOT be used as
    upstream-of-record; the boolean is surfaced so behind-upstream and
    consumers can warn / pick the next-newest non-yanked version.

    On 429/503: honors the server's `Retry-After` header (delta-seconds
    or HTTP-date), capped at 60s via `_parse_retry_after`. On other
    transient failures: exponential backoff + ±25% jitter so a
    synchronized worker pool doesn't re-hit pypi.org in lockstep.
    """
    import random as _random
    url = f"https://pypi.org/pypi/{pypi_name}/json"
    last_err: str | None = None
    for attempt in range(3):
        try:
            req = _make_req(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
            info = payload.get("info") or {}
            version = info.get("version")
            # `info.yanked` (top-level) is sometimes set; the canonical signal
            # is `releases[<version>][i].yanked` for any sdist/wheel entry
            # of the version. We treat the version as yanked iff EVERY file
            # of that version is yanked (PEP 592 semantics).
            yanked: bool | None = None
            if version:
                rel = (payload.get("releases") or {}).get(version) or []
                if isinstance(rel, list) and rel:
                    yanked = all(
                        bool(f.get("yanked")) for f in rel
                        if isinstance(f, dict)
                    )
                elif isinstance(info.get("yanked"), bool):
                    yanked = info["yanked"]
            return (pypi_name, version, yanked, None)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 404:
                return (pypi_name, None, None, "HTTP 404")
            if e.code in (429, 503) and attempt < 2:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                base = 2.0 ** attempt + 1.0
                jitter = base * (0.75 + 0.5 * _random.random())
                sleep_for = _parse_retry_after(retry_after, fallback=jitter)
                time.sleep(sleep_for)
                continue
            return (pypi_name, None, None, last_err)
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"
            if attempt < 2:
                base = 1.0 + attempt
                time.sleep(base * (0.75 + 0.5 * _random.random()))
                continue
            return (pypi_name, None, None, last_err)
    return (pypi_name, None, None, last_err or "exhausted retries")


def _phase_h_eligibility_stats(conn: sqlite3.Connection) -> dict[str, int]:
    """Branch-by-branch counts for Phase H eligible-rows (v21+).

    Returns a dict with three keys mirroring the SQL OR clauses in
    `_phase_h_eligible_pypi_names`:

    - `eligible_never_fetched`     — `pypi_version_fetched_at IS NULL`
    - `eligible_serial_moved`      — fetched_at populated AND
                                      `pypi_last_serial IS NOT
                                      pypi_version_serial_at_fetch`
    - `eligible_safety_recheck`    — fetched_at populated AND serial
                                      unchanged AND fetched_at past 30 d

    Buckets are mutually exclusive (the SQL OR is short-circuited by
    each branch's preconditions). Sum equals the eligible-rows count.
    """
    safety_cutoff = int(time.time()) - 30 * 86400
    base = (
        "SELECT COUNT(DISTINCT pypi_name) FROM v_actionable_packages "
        "WHERE pypi_name IS NOT NULL "
    )
    never = conn.execute(base + "AND pypi_version_fetched_at IS NULL").fetchone()[0]
    moved = conn.execute(
        base + "AND pypi_version_fetched_at IS NOT NULL "
               "AND pypi_last_serial IS NOT pypi_version_serial_at_fetch"
    ).fetchone()[0]
    safety = conn.execute(
        base + "AND pypi_version_fetched_at IS NOT NULL "
               "AND pypi_last_serial IS pypi_version_serial_at_fetch "
               "AND pypi_version_fetched_at < ?",
        (safety_cutoff,),
    ).fetchone()[0]
    return {
        "eligible_never_fetched":  never,
        "eligible_serial_moved":   moved,
        "eligible_safety_recheck": safety,
    }


def _phase_h_eligible_pypi_names(conn: sqlite3.Connection) -> tuple[list, int, int, int]:
    """Return (rows, ttl_days, concurrency, limit) shared by all Phase H paths.

    Schema v21+ adds serial-aware gating (Layer 2). A row is eligible
    when ANY of three conditions hold:

    1. **Never fetched** — `pypi_version_fetched_at IS NULL`. Cold-start
       case; always fetch.
    2. **Serial moved** — `pypi_last_serial != pypi_version_serial_at_fetch`.
       Phase D's daily-lean path writes `pypi_last_serial` from the
       PyPI Simple API; if it doesn't match what Phase H stamped on
       the last successful fetch, upstream has had at least one new
       release / yank since.
    3. **30d safety re-check** — `pypi_version_fetched_at < (now - 30d)`.
       Even if the serial appears unchanged, periodic re-fetches catch
       missed events (Phase D outage, serial-wraparound edge cases).

    Result on typical daily runs: only the ~30-100 packages whose
    upstream actually moved get re-fetched, instead of all ~12k TTL-stale
    rows. Phase H warm-daily wall-clock drops from ~5 min (TTL boundary)
    to ~30 s (typical day).
    """
    ttl_days = int(os.environ.get("PHASE_H_TTL_DAYS", "7"))
    # Default concurrency is 3 (was 8). pypi.org documents a ~30 req/s per-IP
    # ceiling for the JSON API; 8 workers on a 100k-row backfill could trip
    # secondary 429s. 3 stays comfortably under the limit and the cf-graph
    # backend (PHASE_H_SOURCE=cf-graph) is the right choice anyway for
    # full backfills. Override via PHASE_H_CONCURRENCY for trusted setups
    # (authenticated mirrors, JFrog proxy with no rate cap).
    concurrency = max(1, int(os.environ.get("PHASE_H_CONCURRENCY", "3")))
    limit = int(os.environ.get("PHASE_H_LIMIT", "0"))
    safety_cutoff = int(time.time()) - 30 * 86400  # 30d safety re-check

    # Reads from v_actionable_packages (schema v21+) — encodes the
    # canonical triplet (conda_name + active + !archived). The
    # AND pypi_name IS NOT NULL clause stays here because the view
    # doesn't filter on pypi_name (Phase H is the only consumer that
    # needs that extra narrowing). 3-condition serial-gate (v8.0.0+).
    #
    # `IS NOT` is the NULL-safe form of `!=` — required because
    # `pypi_version_serial_at_fetch` is NULL for every row in the
    # post-schema-v21-migration state (the column was just added).
    # Plain `pypi_last_serial != NULL` evaluates to NULL (falsy in
    # WHERE), which would silently exclude the entire post-migration
    # working set from condition 2. `IS NOT` correctly returns TRUE
    # when one side is NULL and the other isn't, so post-migration
    # rows with a populated `pypi_last_serial` get re-fetched once
    # to stamp `pypi_version_serial_at_fetch`. Caught by live-DB
    # verification on 2026-05-13 (retro D2).
    sql = (
        "SELECT DISTINCT pypi_name FROM v_actionable_packages "
        "WHERE pypi_name IS NOT NULL "
        "  AND ("
        "       pypi_version_fetched_at IS NULL "
        "    OR pypi_last_serial IS NOT pypi_version_serial_at_fetch "
        "    OR pypi_version_fetched_at < ? "
        "  )"
    )
    params: tuple = (safety_cutoff,)
    if limit > 0:
        sql += " LIMIT ?"
        params = (safety_cutoff, limit)
    rows = list(conn.execute(sql, params))
    return rows, ttl_days, concurrency, limit


def _phase_h_via_pypi_json(conn: sqlite3.Connection) -> dict:
    """Original per-row fan-out against `pypi.org/pypi/<name>/json`.

    Real-time, carries PEP 592 yanked status, but throughput is gated by
    pypi.org throttling and ThreadPool concurrency. Marks every populated
    row with `pypi_version_source='pypi-json'`.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    t0 = time.monotonic()
    print("  Phase H: PyPI current-version via pypi.org JSON")

    rows, ttl_days, concurrency, _ = _phase_h_eligible_pypi_names(conn)
    stats = _phase_h_eligibility_stats(conn)
    print(
        f"  {len(rows):,} pypi names to refresh "
        f"(TTL {ttl_days}d, concurrency {concurrency})"
    )
    print(
        f"    breakdown: never_fetched={stats['eligible_never_fetched']:,}, "
        f"serial_moved={stats['eligible_serial_moved']:,}, "
        f"safety_recheck={stats['eligible_safety_recheck']:,}"
    )

    fetched = 0
    failed = 0
    not_found = 0
    # Cap at 2,500 so multi-100k-row runs still emit a line every ~30-60s
    # instead of going silent for many minutes (the historical "Phase H is
    # hung" misdiagnosis — workers were churning, the formula just buried
    # the signal under a 20k-row gap).
    progress_every = min(max(500, len(rows) // 40), 2500) if rows else 1
    commit_every = 500
    completed = 0
    last_heartbeat = time.monotonic()
    HEARTBEAT_S = 60.0

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(_phase_h_fetch_one, r["pypi_name"]) for r in rows]
        for fut in as_completed(futures):
            pypi_name, version, yanked, err = fut.result()
            now = int(time.time())
            if version is not None:
                yanked_int = 1 if yanked is True else (0 if yanked is False else None)
                # Stamp pypi_version_serial_at_fetch = pypi_last_serial so the
                # next eligible-rows gate (v21+) recognizes this row as
                # "fetched at the current serial" and skips re-fetch until
                # Phase D bumps pypi_last_serial.
                conn.execute(
                    "UPDATE packages SET pypi_current_version = ?, "
                    "pypi_current_version_yanked = ?, "
                    "pypi_version_fetched_at = ?, pypi_version_last_error = NULL, "
                    "pypi_version_source = 'pypi-json', "
                    "pypi_version_serial_at_fetch = pypi_last_serial "
                    "WHERE pypi_name = ?",
                    (version, yanked_int, now, pypi_name),
                )
                # Mirror to unified upstream_versions side table — one row per
                # (conda_name, 'pypi'). For multi-conda names sharing one pypi
                # name (rare), both rows get the same upstream version.
                # scope: write-side mirror to upstream_versions. Already
                # filtered on `pypi_name = ? AND conda_name IS NOT NULL`
                # below; the actionable view would additionally require
                # active+!archived but historical mirror writes should
                # land regardless of current archive state.
                conn.execute(
                    "INSERT OR REPLACE INTO upstream_versions "
                    "(conda_name, source, version, url, fetched_at, last_error) "
                    "SELECT conda_name, 'pypi', ?, ?, ?, NULL FROM packages "
                    "WHERE pypi_name = ? AND conda_name IS NOT NULL",
                    (version, f"https://pypi.org/project/{pypi_name}/", now, pypi_name),
                )
                fetched += 1
            elif err == "HTTP 404":
                # Stamp serial-at-fetch on 404 too — prevents immediate re-fetch
                # of a deleted-from-PyPI package; eligibility returns on the
                # next Phase D bump (which won't happen for truly deleted
                # packages — the row stays in "404 known" state).
                conn.execute(
                    "UPDATE packages SET pypi_version_fetched_at = ?, "
                    "pypi_version_last_error = ?, pypi_version_source = 'pypi-json', "
                    "pypi_version_serial_at_fetch = pypi_last_serial "
                    "WHERE pypi_name = ?",
                    (now, err, pypi_name),
                )
                not_found += 1
            else:
                conn.execute(
                    "UPDATE packages SET pypi_version_last_error = ? WHERE pypi_name = ?",
                    (err, pypi_name),
                )
                failed += 1

            completed += 1
            if completed % commit_every == 0:
                conn.commit()
            now_mono = time.monotonic()
            # Print on progress_every count OR on heartbeat timer, whichever
            # fires first. Heartbeat covers the case where progress_every is
            # huge for a big-row run but the user expects a "still alive"
            # signal at human cadence.
            if (completed % progress_every == 0
                    or now_mono - last_heartbeat >= HEARTBEAT_S):
                elapsed = now_mono - t0
                rate = completed / elapsed if elapsed else 0
                eta_min = (len(rows) - completed) / rate / 60 if rate else 0
                print(
                    f"    [{completed:,}/{len(rows):,}] fetched={fetched:,} "
                    f"failed={failed:,} 404={not_found:,}  "
                    f"rate={rate:.1f}/s  ETA={eta_min:.1f}min"
                )
                last_heartbeat = now_mono

    conn.commit()
    snap_rows = _snapshot_upstream_versions(conn, source_filter="pypi")
    elapsed = time.monotonic() - t0
    print(
        f"  Phase H (pypi-json) done in {elapsed:.1f}s — fetched {fetched:,}, "
        f"failed {failed:,}, 404 {not_found:,}, "
        f"history snapshot rows: {snap_rows:,}"
    )
    return {
        "rows_eligible": len(rows),
        "eligible_never_fetched":  stats["eligible_never_fetched"],
        "eligible_serial_moved":   stats["eligible_serial_moved"],
        "eligible_safety_recheck": stats["eligible_safety_recheck"],
        "fetched": fetched,
        "failed": failed,
        "not_found_404": not_found,
        "history_snapshot_rows": snap_rows,
        "ttl_days": ttl_days,
        "concurrency": concurrency,
        "duration_seconds": round(elapsed, 1),
        "source": "pypi-json",
    }


def _phase_h_via_cf_graph(conn: sqlite3.Connection) -> dict:
    """Bulk Phase H path backed by the locally-cached cf-graph tarball.

    Reads `version_pr_info/<sharded>/<feedstock>.json` shards (already on
    disk after Phase E) and projects `new_version` onto `packages.pypi_name`
    via `feedstock_name`. Cold-start friendly: zero network, zero auth.

    Yanked status is not carried by cf-graph; rows populated by this path
    leave `pypi_current_version_yanked = NULL` so consumers know the source
    can't speak to PEP 592. Re-run with `PHASE_H_SOURCE=pypi-json` to backfill
    yanked precisely when needed.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    import _cf_graph_versions  # type: ignore[import-not-found]

    t0 = time.monotonic()
    print("  Phase H: PyPI current-version via cf-graph (offline)")

    tarball = _cf_graph_versions.default_tarball_path()
    if not _cf_graph_versions.tarball_available(tarball):
        elapsed = time.monotonic() - t0
        print(f"  cf-graph cache missing at {tarball}; run Phase E first")
        return {
            "skipped": True,
            "reason": "cf-graph cache missing; run Phase E first.",
            "rows_eligible": 0, "fetched": 0, "failed": 0, "not_found_404": 0,
            "duration_seconds": round(elapsed, 1),
            "source": "cf-graph",
        }

    rows, ttl_days, _, _ = _phase_h_eligible_pypi_names(conn)
    stats = _phase_h_eligibility_stats(conn)
    eligible_pypi_names = {r["pypi_name"] for r in rows}
    print(f"  {len(eligible_pypi_names):,} pypi names eligible (TTL {ttl_days}d)")
    print(
        f"    breakdown: never_fetched={stats['eligible_never_fetched']:,}, "
        f"serial_moved={stats['eligible_serial_moved']:,}, "
        f"safety_recheck={stats['eligible_safety_recheck']:,}"
    )

    if not eligible_pypi_names:
        elapsed = time.monotonic() - t0
        return {
            "rows_eligible": 0,
            "eligible_never_fetched":  stats["eligible_never_fetched"],
            "eligible_serial_moved":   stats["eligible_serial_moved"],
            "eligible_safety_recheck": stats["eligible_safety_recheck"],
            "fetched": 0, "failed": 0, "not_found_404": 0,
            "history_snapshot_rows": 0,
            "ttl_days": ttl_days,
            "duration_seconds": round(elapsed, 1),
            "source": "cf-graph",
        }

    # scope: Phase H cf-graph reverse-lookup needs the feedstock_name →
    # pypi_name map for ALL rows; the `eligible_pypi_names` set (already
    # filtered through v_actionable_packages above) narrows what gets
    # written, so this just builds the lookup index.
    pypi_by_feedstock: dict[str, str] = {}
    for row in conn.execute(
        "SELECT feedstock_name, pypi_name FROM packages "
        "WHERE feedstock_name IS NOT NULL AND pypi_name IS NOT NULL"
    ):
        fs = row["feedstock_name"]
        pn = row["pypi_name"]
        if fs and pn and pn in eligible_pypi_names:
            pypi_by_feedstock.setdefault(fs, pn)

    version_map = _cf_graph_versions.build_pypi_version_map(
        pypi_by_feedstock, path=tarball
    )
    print(f"  cf-graph yielded {len(version_map):,} version mappings")

    fetched = 0
    not_found = 0
    completed = 0
    commit_every = 500
    now = int(time.time())

    for pypi_name in eligible_pypi_names:
        version = version_map.get(pypi_name)
        if version is None:
            # cf-graph had no version_pr_info shard for the matching feedstock,
            # or new_version was null/false (bot found no upstream). Mark the
            # source but leave the row available for a future pypi-json pass.
            conn.execute(
                "UPDATE packages SET pypi_version_source = 'cf-graph' "
                "WHERE pypi_name = ? AND pypi_version_fetched_at IS NULL",
                (pypi_name,),
            )
            not_found += 1
        else:
            # cf-graph path: stamp pypi_version_serial_at_fetch = pypi_last_serial
            # so this fetch satisfies the v21+ serial-gate.
            conn.execute(
                "UPDATE packages SET pypi_current_version = ?, "
                "pypi_current_version_yanked = NULL, "
                "pypi_version_fetched_at = ?, pypi_version_last_error = NULL, "
                "pypi_version_source = 'cf-graph', "
                "pypi_version_serial_at_fetch = pypi_last_serial "
                "WHERE pypi_name = ?",
                (version, now, pypi_name),
            )
            # scope: write-side mirror to upstream_versions (cf-graph path).
            # Same rationale as the pypi-json mirror above — `pypi_name = ?
            # AND conda_name IS NOT NULL` is sufficient for the write.
            conn.execute(
                "INSERT OR REPLACE INTO upstream_versions "
                "(conda_name, source, version, url, fetched_at, last_error) "
                "SELECT conda_name, 'pypi', ?, ?, ?, NULL FROM packages "
                "WHERE pypi_name = ? AND conda_name IS NOT NULL",
                (version, f"https://pypi.org/project/{pypi_name}/", now, pypi_name),
            )
            fetched += 1
        completed += 1
        if completed % commit_every == 0:
            conn.commit()

    conn.commit()
    snap_rows = _snapshot_upstream_versions(conn, source_filter="pypi")
    elapsed = time.monotonic() - t0
    print(
        f"  Phase H (cf-graph) done in {elapsed:.1f}s — fetched {fetched:,}, "
        f"no_data {not_found:,}, history snapshot rows: {snap_rows:,}"
    )
    return {
        "rows_eligible": len(eligible_pypi_names),
        "eligible_never_fetched":  stats["eligible_never_fetched"],
        "eligible_serial_moved":   stats["eligible_serial_moved"],
        "eligible_safety_recheck": stats["eligible_safety_recheck"],
        "fetched": fetched,
        "failed": 0,
        "not_found_404": not_found,
        "history_snapshot_rows": snap_rows,
        "ttl_days": ttl_days,
        "duration_seconds": round(elapsed, 1),
        "source": "cf-graph",
    }


def phase_h_pypi_versions(conn: sqlite3.Connection) -> dict:
    """Phase H: cache each pypi-linked package's current upstream version.

    Dispatches on `PHASE_H_SOURCE` (default `pypi-json`):
      - `pypi-json` → original per-row HTTP path against pypi.org. Real-time,
                      carries PEP 592 yanked status.
      - `cf-graph`  → bulk offline read of the cf-graph tarball populated by
                      Phase E. Zero network, no yanked status, ~hours lag.

    Combined with `latest_conda_version`, this enables behind-upstream
    detection: a feedstock whose conda version lags its PyPI counterpart.
    TTL-gated like Phase F so warm runs are cheap.

    Tunables (env vars):
      - PHASE_H_DISABLED     : "1" to skip entirely
      - PHASE_H_SOURCE       : pypi-json | cf-graph (default pypi-json).
                               Large org / cold-start backfills should
                               prefer ``cf-graph`` to skip pypi.org entirely;
                               see v7.7.0 entry in CHANGELOG.md for the
                               yanked / freshness trade-off.
      - PHASE_H_TTL_DAYS     : skip rows refreshed within N days (default 7)
      - PHASE_H_CONCURRENCY  : pypi-json worker pool size (default 3). The
                               default was 8 until the v7.8.1 audit
                               highlighted pypi.org's documented ~30 req/s
                               per-IP ceiling; 3 stays under the secondary
                               limit. Raise only when you know your link
                               tolerates higher load.
      - PHASE_H_LIMIT        : cap rows processed (debug; 0 = no cap)

    Rate-limit handling (pypi-json path): retries on 429 / 503 honoring
    the server's ``Retry-After`` header (capped at 60s); on other
    transient failures, backs off exponentially with ±25% jitter to
    avoid synchronized retry storms across the worker pool. Same
    pattern as Phase F — see ``_phase_f_fetch_one``.

    Every populated row carries a non-NULL `pypi_version_source` discriminator
    (`'pypi-json'` | `'cf-graph'`) so consumers can surface which dataset
    produced the version.
    """
    print("  Phase H: PyPI current-version cache")

    if os.environ.get("PHASE_H_DISABLED"):
        return {
            "skipped": True,
            "reason": "PHASE_H_DISABLED=1 set; skipping PyPI fetch.",
            "duration_seconds": 0.0,
        }

    source = os.environ.get("PHASE_H_SOURCE", "pypi-json").lower()
    if source == "pypi-json":
        return _phase_h_via_pypi_json(conn)
    if source == "cf-graph":
        return _phase_h_via_cf_graph(conn)
    raise ValueError(
        f"PHASE_H_SOURCE={source!r} is not one of pypi-json, cf-graph"
    )


_GITHUB_REPO_RE = re.compile(r"github\.com/([^/\s,]+)/([^/?#.\s,()<>\"']+)")
_GITLAB_REPO_RE = re.compile(r"gitlab\.com/([^?#\s,]+?)(?:/-/|/?(?:$|[?#\s,]))")
_CODEBERG_REPO_RE = re.compile(r"codeberg\.org/([^/\s,]+)/([^/?#.\s,()<>\"']+)")


def _extract_vcs_repo(*urls: str | None) -> tuple[str, str, str] | None:
    """Detect a VCS-host repo from any of the URLs.

    Returns (host, owner_or_path, repo) where host ∈ {'github','gitlab','codeberg'}.
    For GitLab, `owner_or_path` is the full project path (may contain slashes
    for sub-groups, e.g., 'group/sub/project'); `repo` is the trailing leaf
    used for display. For GitHub/Codeberg, `owner_or_path` is the username.
    """
    for u in urls:
        if not u:
            continue
        m = _GITHUB_REPO_RE.search(u)
        if m:
            return ("github", m.group(1), m.group(2).rstrip("/"))
        m = _CODEBERG_REPO_RE.search(u)
        if m:
            return ("codeberg", m.group(1), m.group(2).rstrip("/"))
        m = _GITLAB_REPO_RE.search(u)
        if m:
            path = m.group(1).rstrip("/")
            # Strip trailing .git if present (gitlab clone URLs sometimes)
            if path.endswith(".git"):
                path = path[:-4]
            leaf = path.rsplit("/", 1)[-1]
            return ("gitlab", path, leaf)
    return None


def _normalize_release_tag(tag: str | None) -> str | None:
    """Normalize a release tag to a version string. Case-insensitive prefix
    stripping handles `v3.0.44`, `Release_1_6_15`, `rel-2.0`, `RELEASE-1`,
    etc. Returns None if input is empty.
    """
    if not tag:
        return None
    s = tag.strip()
    for prefix in ("release-", "release_", "rel-", "rel_", "v"):
        if s.lower().startswith(prefix):
            s = s[len(prefix):]
            break
    return s or None


def _gh_token() -> str | None:
    """Resolve a GitHub token: GITHUB_TOKEN env var first, then `gh auth token`."""
    import subprocess
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _phase_k_github_graphql_batch(
    repos: list[tuple[str, str]],
    gh_token: str,
    *,
    batch_size: int = 100,
) -> dict[tuple[str, str], tuple[str | None, str | None]]:
    """Resolve latest release/tag for a list of GitHub repos via GraphQL.

    Returns ``{(owner, repo): (version_or_None, err_or_None)}`` with one
    entry per input repo. The REST fanout in `_phase_k_fetch_one` does
    one GET per repo (often two — releases/latest then tags fallback);
    a 4k-row Phase K can hit GitHub's secondary rate limit even with a
    PAT. This issues one HTTP POST per `batch_size` (default 100) repos
    using aliased queries, so a 4k-row run is ~40 requests instead of
    ~14k. Each repo's subquery asks for both `releases(first:1)` and
    `refs(refPrefix:"refs/tags/", first:1)` so release+tag fallback is
    resolved server-side in the same round-trip.

    Error handling:
      - Network / 5xx errors: retry up to 3x with exponential backoff,
        then mark every repo in that batch as failed.
      - Per-alias errors (NOT_FOUND, SUSPENDED, etc.) come back as
        `data[alias] = null` plus an entry in the response's `errors`
        array with `path: ["<alias>"]`. We map them to per-repo errors.
      - Repos with neither a release nor a tag get `(None, "no tags")`
        to match the REST path's behavior.

    GraphQL is auth-only (anonymous queries return 401), so callers
    must pass a non-empty `gh_token`. The Phase K dispatcher already
    enforces that.
    """
    results: dict[tuple[str, str], tuple[str | None, str | None]] = {}
    if not repos:
        return results

    # Honor GITHUB_API_BASE_URL for GitHub Enterprise Server. GHES exposes
    # GraphQL at `<base>/graphql` under the same `/api` root used for REST,
    # so a single env var redirects both.
    if _HTTP_AVAILABLE and _resolve_github_api_urls is not None:
        endpoint = _resolve_github_api_urls("graphql")[0]
    else:
        endpoint = "https://api.github.com/graphql"

    def _build_query(batch: list[tuple[str, str]]) -> str:
        parts = ["query {"]
        for i, (owner, repo) in enumerate(batch):
            owner_lit = json.dumps(owner)
            repo_lit = json.dumps(repo)
            parts.append(
                f"  r{i}: repository(owner: {owner_lit}, name: {repo_lit}) {{\n"
                f"    releases(first: 1, orderBy: {{field: CREATED_AT, direction: DESC}}) {{\n"
                f"      nodes {{ tagName }}\n"
                f"    }}\n"
                f"    refs(refPrefix: \"refs/tags/\", first: 1, "
                f"orderBy: {{field: TAG_COMMIT_DATE, direction: DESC}}) {{\n"
                f"      nodes {{ name }}\n"
                f"    }}\n"
                f"  }}"
            )
        parts.append("  rateLimit { cost remaining resetAt }")
        parts.append("}")
        return "\n".join(parts)

    headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "cf-atlas/phase-k-graphql",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    for batch_start in range(0, len(repos), batch_size):
        batch = repos[batch_start:batch_start + batch_size]
        query = _build_query(batch)
        body = json.dumps({"query": query}).encode("utf-8")

        payload: dict | None = None
        batch_err: str | None = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    endpoint, data=body, headers=headers, method="POST",
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                batch_err = f"HTTP {e.code}"
                if e.code in (403, 429, 502, 503, 504) and attempt < 2:
                    time.sleep(2 ** attempt + 2)
                    continue
                break
            except Exception as e:
                batch_err = f"{type(e).__name__}: {str(e)[:120]}"
                if attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                break

        if payload is None:
            for owner, repo in batch:
                results[(owner, repo)] = (None, batch_err or "graphql batch failed")
            continue

        data = payload.get("data") or {}
        errors_by_alias: dict[str, str] = {}
        for err in (payload.get("errors") or []):
            path = err.get("path") or []
            alias = path[0] if path else None
            etype = err.get("type") or ""
            msg = err.get("message") or ""
            if not alias:
                continue
            if etype == "NOT_FOUND" or "Could not resolve" in msg:
                errors_by_alias[alias] = "HTTP 404"
            else:
                errors_by_alias[alias] = f"{etype or 'GraphQLError'}: {msg[:80]}"

        for i, (owner, repo) in enumerate(batch):
            alias = f"r{i}"
            repo_data = data.get(alias)
            if repo_data is None:
                err = errors_by_alias.get(alias, "HTTP 404")
                results[(owner, repo)] = (None, err)
                continue
            release_nodes = (((repo_data.get("releases") or {}).get("nodes")) or [])
            tag_nodes = (((repo_data.get("refs") or {}).get("nodes")) or [])
            tag: str | None = None
            if release_nodes:
                tag = (release_nodes[0] or {}).get("tagName")
            if not tag and tag_nodes:
                tag = (tag_nodes[0] or {}).get("name")
            if tag:
                results[(owner, repo)] = (_normalize_release_tag(tag), None)
            else:
                results[(owner, repo)] = (None, "no tags")

    return results


def _phase_k_fetch_one(host: str, owner_or_path: str, repo: str,
                       gh_token: str | None, gl_token: str | None
                       ) -> tuple[str, str, str, str | None, str | None]:
    """Worker for Phase K. Returns (host, owner_or_path, repo, version, err).

    Dispatches by host:
      - 'github'   → GET /repos/<o>/<r>/releases/latest, fallback to /tags
      - 'codeberg' → same Gitea-compatible API as GitHub
      - 'gitlab'   → GET /api/v4/projects/<urlencoded>/releases?per_page=1
                     fallback to /repository/tags?per_page=1
    """
    if host in ("github", "codeberg"):
        # GitHub Enterprise Server / self-hosted Gitea: honor
        # GITHUB_API_BASE_URL / CODEBERG_API_BASE_URL respectively. Both
        # use the same `/repos/<o>/<r>` path layout.
        if host == "github":
            if _HTTP_AVAILABLE and _resolve_github_api_urls is not None:
                api_root = _resolve_github_api_urls()[0]
            else:
                api_root = "https://api.github.com"
        else:
            if _HTTP_AVAILABLE and _resolve_codeberg_api_urls is not None:
                api_root = _resolve_codeberg_api_urls()[0]
            else:
                api_root = "https://codeberg.org/api/v1"
        accept = ("application/vnd.github+json"
                  if host == "github"
                  else "application/json")
        headers = {"Accept": accept}
        if host == "github":
            headers["X-GitHub-Api-Version"] = "2022-11-28"
            if gh_token:
                headers["Authorization"] = f"Bearer {gh_token}"
        base = f"{api_root}/repos/{owner_or_path}/{repo}"
        return _fetch_release_or_tag(host, owner_or_path, repo, base, headers)

    if host == "gitlab":
        # Self-hosted GitLab: honor GITLAB_API_BASE_URL. GitLab requires
        # URL-encoded project path; layout under `/projects/<enc>` is
        # identical across CE/EE/self-hosted.
        from urllib.parse import quote
        encoded = quote(owner_or_path, safe="")
        if _HTTP_AVAILABLE and _resolve_gitlab_api_urls is not None:
            api_root = _resolve_gitlab_api_urls()[0]
        else:
            api_root = "https://gitlab.com/api/v4"
        base = f"{api_root}/projects/{encoded}"
        headers = {"Accept": "application/json"}
        if gl_token:
            headers["PRIVATE-TOKEN"] = gl_token
        return _fetch_release_or_tag(host, owner_or_path, repo, base, headers,
                                     release_url=f"{base}/releases?per_page=1",
                                     tag_url=f"{base}/repository/tags?per_page=1",
                                     gitlab=True)
    return (host, owner_or_path, repo, None, f"unknown host: {host}")


def _fetch_release_or_tag(host: str, owner_or_path: str, repo: str,
                           base: str, headers: dict,
                           release_url: str | None = None,
                           tag_url: str | None = None,
                           gitlab: bool = False
                           ) -> tuple[str, str, str, str | None, str | None]:
    """Helper: try the release endpoint, fall back to tags."""
    rel_url = release_url or f"{base}/releases/latest"
    tg_url  = tag_url     or f"{base}/tags?per_page=10"
    last_err: str | None = None

    for attempt in range(3):
        try:
            req = _make_req(rel_url, extra_headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.load(resp)
            if gitlab:
                if isinstance(payload, list) and payload:
                    tag = payload[0].get("tag_name") or payload[0].get("name")
                else:
                    tag = None
            else:
                tag = payload.get("tag_name") if isinstance(payload, dict) else None
            if tag:
                return (host, owner_or_path, repo, _normalize_release_tag(tag), None)
            break  # empty payload — try tags
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 404:
                break
            if e.code in (403, 429):
                time.sleep(2 ** attempt + 2)
                continue
            return (host, owner_or_path, repo, None, last_err)
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            return (host, owner_or_path, repo, None, last_err)

    # Fallback: tags endpoint
    try:
        req = _make_req(tg_url, extra_headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            tags = json.load(resp)
        if isinstance(tags, list) and tags:
            for t in tags:
                if not isinstance(t, dict):
                    continue
                name = t.get("name") or t.get("tag_name")
                if name:
                    return (host, owner_or_path, repo, _normalize_release_tag(name), None)
        return (host, owner_or_path, repo, None, "no tags")
    except urllib.error.HTTPError as e:
        return (host, owner_or_path, repo, None, f"HTTP {e.code}")
    except Exception as e:
        return (host, owner_or_path, repo, None, f"{type(e).__name__}: {str(e)[:120]}")


def phase_k_vcs_versions(conn: sqlite3.Connection) -> dict:
    """Phase K: fetch latest release/tag from VCS hosts (GitHub, GitLab,
    Codeberg) for each row whose recipe sources from one of those hosts —
    or whose project metadata (homepage/dev_url/repo_url) points to one.

    Closes the gap the user flagged (2026-05-09): for ~3.5k feedstocks the
    upstream-of-record is a VCS repo, not PyPI. Three real cases:
      (a) VCS-only projects (no PyPI presence)
      (b) author publishes to VCS first, PyPI lags
      (c) recipe's source.url is the VCS archive for tarball integrity
    behind-upstream queries the unified `upstream_versions` side table to
    pick the right signal per row based on `conda_source_registry`.

    Auth: GITHUB_TOKEN / GH_TOKEN / `gh auth token` for github.com.
          GITLAB_TOKEN / GL_TOKEN env for gitlab.com (optional — public
          API works unauthenticated at lower rate).
    Auto-skip when no GitHub auth: unauth API is 60 req/hr (too few).

    Writes to BOTH the unified `upstream_versions` side table (source =
    'github'|'gitlab'|'codeberg') and the legacy `github_current_version`
    column on packages (for github only; backward-compat with v6.7+).

    Tunables:
      - PHASE_K_DISABLED            : "1" to skip
      - PHASE_K_TTL_DAYS            : default 7
      - PHASE_K_CONCURRENCY         : REST fanout for GitLab/Codeberg (default 8)
      - PHASE_K_LIMIT               : cap rows (debug)
      - PHASE_K_GRAPHQL_DISABLED    : "1" to disable the GitHub GraphQL
                                      batch path and use REST fanout for
                                      GitHub too (slower, hits secondary
                                      rate limits at >~80 concurrent reqs)
      - PHASE_K_GRAPHQL_BATCH_SIZE  : repos per GraphQL request (default
                                      100; keep < ~150 to stay under
                                      GitHub's 500K node-complexity ceiling)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    t0 = time.monotonic()
    print("  Phase K: VCS upstream-version cache (GitHub + GitLab + Codeberg)")

    if os.environ.get("PHASE_K_DISABLED"):
        return {
            "skipped": True,
            "reason": "PHASE_K_DISABLED=1 set; skipping VCS fetch.",
            "duration_seconds": 0.0,
        }

    gh_token = _gh_token()
    gl_token = os.environ.get("GITLAB_TOKEN") or os.environ.get("GL_TOKEN")
    if not gh_token:
        return {
            "skipped": True,
            "reason": ("no GitHub auth — set GITHUB_TOKEN env or run "
                       "`gh auth login`. Unauthenticated GitHub API is "
                       "60 req/hr which is too low for a Phase K backfill."),
            "duration_seconds": 0.0,
        }

    ttl_days = int(os.environ.get("PHASE_K_TTL_DAYS", "7"))
    concurrency = max(1, int(os.environ.get("PHASE_K_CONCURRENCY", "8")))
    limit = int(os.environ.get("PHASE_K_LIMIT", "0"))
    cutoff = int(time.time()) - ttl_days * 86400

    # Eligibility: any actionable row whose URLs reference a known VCS host
    # AND whose upstream_versions row(s) for vcs sources are stale or absent.
    # Reads from v_actionable_packages (schema v21+) for the canonical triplet.
    sql = (
        "SELECT p.conda_name, p.conda_repo_url, p.conda_dev_url, p.conda_homepage "
        "FROM v_actionable_packages p "
        "LEFT JOIN upstream_versions u "
        "  ON u.conda_name = p.conda_name "
        " AND u.source IN ('github','gitlab','codeberg') "
        "WHERE COALESCE(u.fetched_at, 0) < ? "
        "  AND ("
        "       p.conda_repo_url  LIKE '%github.com/%' "
        "    OR p.conda_dev_url   LIKE '%github.com/%' "
        "    OR p.conda_homepage  LIKE '%github.com/%' "
        "    OR p.conda_repo_url  LIKE '%gitlab.com/%' "
        "    OR p.conda_dev_url   LIKE '%gitlab.com/%' "
        "    OR p.conda_homepage  LIKE '%gitlab.com/%' "
        "    OR p.conda_repo_url  LIKE '%codeberg.org/%' "
        "    OR p.conda_dev_url   LIKE '%codeberg.org/%' "
        "    OR p.conda_homepage  LIKE '%codeberg.org/%' "
        "    OR p.conda_source_registry = 'github' "
        "  ) "
        "GROUP BY p.conda_name"
    )
    params: tuple = (cutoff,)
    if limit > 0:
        sql += " LIMIT ?"
        params = (cutoff, limit)
    rows = list(conn.execute(sql, params))
    print(f"  {len(rows):,} rows to scan (TTL {ttl_days}d, concurrency {concurrency})")

    by_host = {"github": 0, "gitlab": 0, "codeberg": 0}
    fetched = 0
    failed = 0
    not_found = 0
    no_repo = 0
    progress_every = min(max(200, len(rows) // 40), 2500) if rows else 1
    commit_every = 200
    completed = 0

    # Pre-resolve VCS triple per row
    work: list[tuple[str, str, str, str]] = []  # (conda_name, host, owner_path, repo)
    for row in rows:
        triple = _extract_vcs_repo(
            row["conda_repo_url"], row["conda_dev_url"], row["conda_homepage"]
        )
        if not triple:
            no_repo += 1
            continue
        host, owner_or_path, repo = triple
        by_host[host] = by_host.get(host, 0) + 1
        work.append((row["conda_name"], host, owner_or_path, repo))

    if not work:
        elapsed = time.monotonic() - t0
        print(f"  Phase K done in {elapsed:.1f}s — no derivable repos; "
              f"no_repo: {no_repo:,}")
        return {
            "rows_eligible": len(rows),
            "fetched": 0, "failed": 0, "not_found": 0, "no_repo": no_repo,
            "by_host": by_host, "duration_seconds": round(elapsed, 1),
        }

    print(f"  {len(work):,} rows have derivable VCS repos: {by_host}")

    # Partition: GitHub goes through one GraphQL batch path (avoids the
    # secondary rate-limit that REST fanout trips at >~80 concurrent
    # requests); GitLab + Codeberg keep the REST ThreadPoolExecutor since
    # neither has a GraphQL equivalent and their combined volume is tiny.
    use_graphql = (
        not os.environ.get("PHASE_K_GRAPHQL_DISABLED")
        and bool(gh_token)
    )
    graphql_batch_size = max(1, int(os.environ.get("PHASE_K_GRAPHQL_BATCH_SIZE", "100")))

    github_work = [w for w in work if w[1] == "github"]
    other_work = [w for w in work if w[1] != "github"]

    # Pre-compute GitHub results via GraphQL (single pass; one HTTP POST
    # per ~batch_size repos). Results keyed by (owner, repo).
    gh_results: dict[tuple[str, str], tuple[str | None, str | None]] = {}
    if use_graphql and github_work:
        gh_repos = [(w[2], w[3]) for w in github_work]
        n_batches = (len(gh_repos) + graphql_batch_size - 1) // graphql_batch_size
        print(
            f"    GitHub: {len(gh_repos):,} repos via GraphQL "
            f"({n_batches} batch{'es' if n_batches != 1 else ''} "
            f"of up to {graphql_batch_size})"
        )
        assert gh_token is not None  # narrowed by use_graphql
        gh_results = _phase_k_github_graphql_batch(
            gh_repos, gh_token, batch_size=graphql_batch_size,
        )

    def _process_result(
        conda_name: str, host: str, owner_or_path: str, repo: str,
        version: str | None, err: str | None,
    ) -> None:
        nonlocal fetched, failed, not_found, completed
        now = int(time.time())
        url = f"https://{host}.com/{owner_or_path}/{repo}" if host == "github" else (
              f"https://gitlab.com/{owner_or_path}" if host == "gitlab" else
              f"https://codeberg.org/{owner_or_path}/{repo}")
        if version is not None:
            conn.execute(
                "INSERT OR REPLACE INTO upstream_versions "
                "(conda_name, source, version, url, fetched_at, last_error) "
                "VALUES (?, ?, ?, ?, ?, NULL)",
                (conda_name, host, version, url, now),
            )
            if host == "github":
                conn.execute(
                    "UPDATE packages SET github_current_version = ?, "
                    "github_version_fetched_at = ?, github_version_last_error = NULL "
                    "WHERE conda_name = ?",
                    (version, now, conda_name),
                )
            fetched += 1
        elif err and ("404" in err or "no tags" in err):
            conn.execute(
                "INSERT OR REPLACE INTO upstream_versions "
                "(conda_name, source, version, url, fetched_at, last_error) "
                "VALUES (?, ?, NULL, ?, ?, ?)",
                (conda_name, host, url, now, err),
            )
            if host == "github":
                conn.execute(
                    "UPDATE packages SET github_version_fetched_at = ?, "
                    "github_version_last_error = ? WHERE conda_name = ?",
                    (now, err, conda_name),
                )
            not_found += 1
        else:
            conn.execute(
                "INSERT OR REPLACE INTO upstream_versions "
                "(conda_name, source, version, url, fetched_at, last_error) "
                "VALUES (?, ?, NULL, ?, ?, ?)",
                (conda_name, host, url, now, err or "unknown error"),
            )
            if host == "github":
                conn.execute(
                    "UPDATE packages SET github_version_last_error = ? "
                    "WHERE conda_name = ?",
                    (err or "unknown error", conda_name),
                )
            failed += 1

        completed += 1
        if completed % commit_every == 0:
            conn.commit()
        if completed % progress_every == 0:
            elapsed = time.monotonic() - t0
            rate = completed / elapsed if elapsed else 0
            eta_min = (len(work) - completed) / rate / 60 if rate else 0
            print(
                f"    [{completed:,}/{len(work):,}] fetched={fetched:,} "
                f"failed={failed:,} 404={not_found:,}  "
                f"rate={rate:.1f}/s  ETA={eta_min:.1f}min"
            )

    # Drain GitHub GraphQL results first (already computed in-process)
    for (conda_name, host, owner_or_path, repo) in github_work:
        if use_graphql:
            version, err = gh_results.get((owner_or_path, repo), (None, "missing in graphql batch"))
        else:
            # GraphQL disabled — fall back to REST for github too
            _, _, _, version, err = _phase_k_fetch_one(
                host, owner_or_path, repo, gh_token, gl_token,
            )
        _process_result(conda_name, host, owner_or_path, repo, version, err)

    # GitLab + Codeberg: keep the REST ThreadPoolExecutor fanout
    if other_work:
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = {
                ex.submit(_phase_k_fetch_one, host, owner_path, repo, gh_token, gl_token):
                    (conda_name, host, owner_path, repo)
                for (conda_name, host, owner_path, repo) in other_work
            }
            for fut in as_completed(futures):
                conda_name = futures[fut][0]
                host, owner_or_path, repo, version, err = fut.result()
                _process_result(conda_name, host, owner_or_path, repo, version, err)

    conn.commit()
    # Snapshot covers all VCS sources Phase K touched.
    snap_total = 0
    for src in ("github", "gitlab", "codeberg"):
        snap_total += _snapshot_upstream_versions(conn, source_filter=src)
    elapsed = time.monotonic() - t0
    print(
        f"  Phase K done in {elapsed:.1f}s — fetched {fetched:,}, "
        f"failed {failed:,}, 404/no-tags {not_found:,}, no_repo {no_repo:,} "
        f"(by host: {by_host}), history snapshot rows: {snap_total:,}"
    )
    return {
        "rows_eligible": len(rows),
        "fetched": fetched,
        "failed": failed,
        "not_found": not_found,
        "no_repo": no_repo,
        "by_host": by_host,
        "history_snapshot_rows": snap_total,
        "ttl_days": ttl_days,
        "concurrency": concurrency,
        "duration_seconds": round(elapsed, 1),
    }


# Backward-compat alias for the previous Phase K name
phase_k_github_versions = phase_k_vcs_versions


# ── Phase L resolvers — one per registry ─────────────────────────────────────
# Each returns (version_or_None, err_or_None). Caller writes to
# upstream_versions side table with the right `source` label.

def _resolve_npm(name: str) -> tuple[str | None, str | None]:
    # Honor enterprise npm registry overrides: NPM_BASE_URL (project
    # convention) and npm_config_registry (npm CLI standard) — see
    # _http.resolve_npm_urls. The hardcoded registry.npmjs.org fallback
    # remains for external clones with no override set.
    if _HTTP_AVAILABLE and _resolve_npm_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_npm_urls(name)
        try:
            data = _fetch_with_fallback(
                urls,
                timeout=20,
                user_agent="cf-atlas/6.10 phase-l",
                return_json=True,
            )
            ver = (data.get("dist-tags") or {}).get("latest")
            return (ver, None)
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://registry.npmjs.org/{name}"
    try:
        with urllib.request.urlopen(_make_req(url), timeout=20) as resp:
            data = json.load(resp)
        ver = (data.get("dist-tags") or {}).get("latest")
        return (ver, None)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


def _resolve_cran(name: str) -> tuple[str | None, str | None]:
    # crandb.r-pkg.org ships a JSON facade over CRAN that's much friendlier
    # than scraping cran.r-project.org HTML. Honors CRAN_BASE_URL via
    # _http.resolve_cran_urls for air-gapped enterprise mirrors.
    if _HTTP_AVAILABLE and _resolve_cran_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_cran_urls(name)
        try:
            data = _fetch_with_fallback(
                urls, timeout=20, user_agent="cf-atlas/phase-l", return_json=True,
            )
            return (data.get("Version"), None)
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://crandb.r-pkg.org/{name}"
    try:
        with urllib.request.urlopen(_make_req(url), timeout=20) as resp:
            data = json.load(resp)
        return (data.get("Version"), None)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


def _resolve_cpan(dist: str) -> tuple[str | None, str | None]:
    if _HTTP_AVAILABLE and _resolve_cpan_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_cpan_urls(dist)
        try:
            data = _fetch_with_fallback(
                urls, timeout=20, user_agent="cf-atlas/phase-l", return_json=True,
            )
            return (data.get("version"), None)
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://fastapi.metacpan.org/v1/release/{dist}"
    try:
        with urllib.request.urlopen(_make_req(url), timeout=20) as resp:
            data = json.load(resp)
        return (data.get("version"), None)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


def _resolve_luarocks(name: str) -> tuple[str | None, str | None]:
    # No JSON API; scrape the project page for the leading `<name>-<version>`
    # rockspec link. Brittle — but luarocks coverage on conda-forge is small
    # (~25 rows) so the fragility is bounded. Honors LUAROCKS_BASE_URL.
    def _parse_version(html: str) -> tuple[str | None, str | None]:
        m = re.search(rf"/modules/[^/\"]+/{re.escape(name)}-([^/\"\-]+)-(\d+)\b", html)
        if m:
            return (m.group(1), None)
        m = re.search(rf"{re.escape(name)}-(\d+(?:\.\d+)*(?:[\w.-]*)?)-\d+\.rockspec", html)
        if m:
            return (m.group(1), None)
        return (None, "no version pattern matched")

    if _HTTP_AVAILABLE and _resolve_luarocks_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_luarocks_urls(name)
        try:
            raw = _fetch_with_fallback(
                urls, timeout=20, user_agent="cf-atlas/phase-l",
            )
            return _parse_version(raw.decode("utf-8", errors="replace"))
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://luarocks.org/m/{name}"
    try:
        with urllib.request.urlopen(_make_req(url), timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        return _parse_version(html)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


def _resolve_crates(name: str) -> tuple[str | None, str | None]:
    if _HTTP_AVAILABLE and _resolve_crates_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_crates_urls(name)
        try:
            data = _fetch_with_fallback(
                urls, timeout=20, user_agent="cf-atlas/phase-l", return_json=True,
            )
            crate = data.get("crate") or {}
            ver = crate.get("max_stable_version") or crate.get("max_version")
            return (ver, None)
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://crates.io/api/v1/crates/{name}"
    try:
        req = _make_req(url, extra_headers={"User-Agent": "cf-atlas/phase-l"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        crate = data.get("crate") or {}
        ver = crate.get("max_stable_version") or crate.get("max_version")
        return (ver, None)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


def _resolve_rubygems(name: str) -> tuple[str | None, str | None]:
    if _HTTP_AVAILABLE and _resolve_rubygems_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_rubygems_urls(name)
        try:
            data = _fetch_with_fallback(
                urls, timeout=20, user_agent="cf-atlas/phase-l", return_json=True,
            )
            return (data.get("version"), None)
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://rubygems.org/api/v1/gems/{name}.json"
    try:
        with urllib.request.urlopen(_make_req(url), timeout=20) as resp:
            data = json.load(resp)
        return (data.get("version"), None)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


def _resolve_maven(coord: str) -> tuple[str | None, str | None]:
    """Maven Central. `coord` is `groupId:artifactId` or just `artifactId`.

    Uses search.maven.org/solrsearch/select. When only artifactId is known,
    we search by `a:` and accept the first hit (works for unique artifact
    names; ambiguous names get whatever Solr returns first). Honors
    MAVEN_BASE_URL.
    """
    from urllib.parse import quote
    if ":" in coord:
        g, a = coord.split(":", 1)
        q = f'g:"{g}" AND a:"{a}"'
    else:
        q = f'a:"{coord}"'
    query_path = f"solrsearch/select?q={quote(q)}&rows=1&wt=json"

    if _HTTP_AVAILABLE and _resolve_maven_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_maven_urls(query_path)
        try:
            data = _fetch_with_fallback(
                urls, timeout=20, user_agent="cf-atlas/phase-l", return_json=True,
            )
            docs = (data.get("response") or {}).get("docs") or []
            if not docs:
                return (None, "no Maven artifact matched")
            ver = docs[0].get("latestVersion") or docs[0].get("v")
            return (ver, None)
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://search.maven.org/{query_path}"
    try:
        with urllib.request.urlopen(_make_req(url), timeout=20) as resp:
            data = json.load(resp)
        docs = (data.get("response") or {}).get("docs") or []
        if not docs:
            return (None, "no Maven artifact matched")
        ver = docs[0].get("latestVersion") or docs[0].get("v")
        return (ver, None)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


def _resolve_nuget(name: str) -> tuple[str | None, str | None]:
    # NuGet's flat-container endpoint requires lowercase package id.
    # Honors NUGET_BASE_URL.
    def _pick_version(data: dict) -> tuple[str | None, str | None]:
        versions = data.get("versions") or []
        if not versions:
            return (None, "no versions")
        stable = [v for v in versions if "-" not in v]
        return ((stable[-1] if stable else versions[-1]), None)

    if _HTTP_AVAILABLE and _resolve_nuget_urls is not None and _fetch_with_fallback is not None:
        urls = _resolve_nuget_urls(name)
        try:
            data = _fetch_with_fallback(
                urls, timeout=20, user_agent="cf-atlas/phase-l", return_json=True,
            )
            return _pick_version(data)
        except Exception as e:
            return (None, f"{type(e).__name__}: {str(e)[:120]}")
    url = f"https://api.nuget.org/v3-flatcontainer/{name.lower()}/index.json"
    try:
        with urllib.request.urlopen(_make_req(url), timeout=20) as resp:
            data = json.load(resp)
        return _pick_version(data)
    except urllib.error.HTTPError as e:
        return (None, f"HTTP {e.code}")
    except Exception as e:
        return (None, f"{type(e).__name__}: {str(e)[:120]}")


_CRATES_URL_RE = re.compile(r"crates\.io/crates/([A-Za-z0-9_-]+)")
_RUBYGEMS_URL_RE = re.compile(r"rubygems\.org/gems/([A-Za-z0-9_.-]+)")
_NUGET_URL_RE = re.compile(r"nuget\.org/packages/([A-Za-z0-9_.-]+)")
_MAVEN_URL_RE = re.compile(
    r"(?:search\.maven\.org/artifact|mvnrepository\.com/artifact|"
    r"central\.sonatype\.com/artifact)/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)"
)


def _detect_registry_from_urls(*urls: str | None) -> list[tuple[str, str]]:
    """Scan project URLs for crates / rubygems / nuget references.

    Returns list of (source, name) pairs found across the URLs.
    """
    found: list[tuple[str, str]] = []
    for u in urls:
        if not u:
            continue
        for src, regex in (
            ("crates", _CRATES_URL_RE),
            ("rubygems", _RUBYGEMS_URL_RE),
            ("nuget", _NUGET_URL_RE),
        ):
            m = regex.search(u)
            if m:
                pair = (src, m.group(1))
                if pair not in found:
                    found.append(pair)
        # Maven coords are 2-part — group:artifact
        m = _MAVEN_URL_RE.search(u)
        if m:
            coord = f"{m.group(1)}:{m.group(2)}"
            pair = ("maven", coord)
            if pair not in found:
                found.append(pair)
    return found


_PHASE_L_RESOLVERS = {
    "npm":       (_resolve_npm,       "https://www.npmjs.com/package/"),
    "cran":      (_resolve_cran,      "https://cran.r-project.org/package="),
    "cpan":      (_resolve_cpan,      "https://metacpan.org/release/"),
    "luarocks":  (_resolve_luarocks,  "https://luarocks.org/m/"),
    "crates":    (_resolve_crates,    "https://crates.io/crates/"),
    "rubygems":  (_resolve_rubygems,  "https://rubygems.org/gems/"),
    "nuget":     (_resolve_nuget,     "https://www.nuget.org/packages/"),
    "maven":     (_resolve_maven,     "https://search.maven.org/artifact/"),
}

# Per-registry default concurrency caps. The old all-in-one ThreadPoolExecutor
# with PHASE_L_CONCURRENCY=8 produced storms of up to 56 simultaneous reqs
# across 7 different registries. The defaults below reflect each registry's
# documented or empirical rate limit:
#   - crates.io and rubygems.org document ~1 req/sec — keep concurrency at 1.
#   - cran/cpan/luarocks/maven have no published limit but are small-volume
#     scrapers; 2 workers each is plenty.
#   - npm and nuget are CDN-backed and tolerate moderate concurrency.
# Override per-registry via PHASE_L_CONCURRENCY_<SOURCE> (uppercase).
# PHASE_L_CONCURRENCY remains as a legacy global override that caps every
# source uniformly (e.g. PHASE_L_CONCURRENCY=1 forces fully serial).
_PHASE_L_DEFAULT_CONCURRENCY: dict[str, int] = {
    "npm":      4,
    "cran":     2,
    "cpan":     2,
    "luarocks": 2,
    "crates":   1,
    "rubygems": 1,
    "maven":    2,
    "nuget":    4,
}


def _phase_l_concurrency_for(source: str) -> int:
    """Resolve the worker count for a given Phase L registry.

    Priority:
      1. PHASE_L_CONCURRENCY_<SOURCE>  (per-source override, takes precedence)
      2. PHASE_L_CONCURRENCY           (legacy global; applied uniformly)
      3. _PHASE_L_DEFAULT_CONCURRENCY[source]
    """
    per_source = os.environ.get(f"PHASE_L_CONCURRENCY_{source.upper()}")
    if per_source:
        try:
            return max(1, int(per_source))
        except ValueError:
            pass
    legacy = os.environ.get("PHASE_L_CONCURRENCY")
    if legacy:
        try:
            return max(1, int(legacy))
        except ValueError:
            pass
    return _PHASE_L_DEFAULT_CONCURRENCY.get(source, 2)


def phase_l_extra_registries(conn: sqlite3.Connection) -> dict:
    """Phase L: resolve the latest upstream version from npm / CRAN / CPAN /
    LuaRocks / crates.io / RubyGems / NuGet for each row that has either a
    matching name column populated (Phase E) or a URL pattern in
    conda_repo_url / conda_dev_url / conda_homepage.

    Writes one row per (conda_name, source) into `upstream_versions`. The
    behind-upstream CLI already prefers VCS / pypi; with Phase L data the
    resolver fans out to whichever upstream the recipe actually tracks.

    Default-on; opt-out via PHASE_L_DISABLED=1. TTL-gated like Phase H/K.

    The previous all-in-one ThreadPoolExecutor with PHASE_L_CONCURRENCY=8
    could fire up to 56 simultaneous requests across 7 different registries,
    which reliably tripped per-host secondary rate limits (especially
    crates.io and rubygems.org, both documented at ~1 req/sec). Phase L now
    processes registries SEQUENTIALLY and applies a per-registry concurrency
    cap — see ``_phase_l_concurrency_for`` for defaults.

    Tunables:
      - PHASE_L_DISABLED              : "1" to skip
      - PHASE_L_TTL_DAYS              : default 7
      - PHASE_L_CONCURRENCY           : legacy global; caps every registry
                                        uniformly when set (e.g. =1 forces
                                        fully serial). Defaults to per-source
                                        values when unset.
      - PHASE_L_CONCURRENCY_<SOURCE>  : per-source override (uppercase),
                                        e.g. PHASE_L_CONCURRENCY_CRATES=2.
      - PHASE_L_LIMIT                 : cap rows (debug)
      - PHASE_L_SOURCES               : comma-separated subset
                                        (e.g. "npm,cran") to restrict which
                                        resolvers run
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    t0 = time.monotonic()
    print("  Phase L: extra-registry upstream-version cache "
          "(npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet/Maven)")

    if os.environ.get("PHASE_L_DISABLED"):
        return {
            "skipped": True,
            "reason": "PHASE_L_DISABLED=1 set; skipping Phase L.",
            "duration_seconds": 0.0,
        }

    ttl_days = int(os.environ.get("PHASE_L_TTL_DAYS", "7"))
    limit = int(os.environ.get("PHASE_L_LIMIT", "0"))
    sources_filter = os.environ.get("PHASE_L_SOURCES")
    if sources_filter:
        active_sources = {s.strip() for s in sources_filter.split(",") if s.strip()}
    else:
        active_sources = set(_PHASE_L_RESOLVERS.keys())

    cutoff = int(time.time()) - ttl_days * 86400

    # Build the work list: per (conda_name, source, name_to_query) tuple.
    # Reads from v_actionable_packages (schema v21+) — canonical triplet.
    rows = list(conn.execute(
        "SELECT conda_name, npm_name, cran_name, cpan_name, luarocks_name, "
        "       maven_coord, conda_repo_url, conda_dev_url, conda_homepage "
        "FROM v_actionable_packages"
    ))

    work: list[tuple[str, str, str, str]] = []  # (conda_name, source, query_name, public_url)
    for row in rows:
        name_col_map = [
            ("npm",      row["npm_name"]),
            ("cran",     row["cran_name"]),
            ("cpan",     row["cpan_name"]),
            ("luarocks", row["luarocks_name"]),
            ("maven",    row["maven_coord"]),
        ]
        for source, n in name_col_map:
            if source not in active_sources:
                continue
            if n:
                public_url = _PHASE_L_RESOLVERS[source][1] + n
                work.append((row["conda_name"], source, n, public_url))
        # URL-detected registries
        detected = _detect_registry_from_urls(
            row["conda_repo_url"], row["conda_dev_url"], row["conda_homepage"]
        )
        for source, n in detected:
            if source not in active_sources:
                continue
            public_url = _PHASE_L_RESOLVERS[source][1] + n
            work.append((row["conda_name"], source, n, public_url))

    if not work:
        elapsed = time.monotonic() - t0
        print(f"  Phase L done in {elapsed:.1f}s — no eligible (conda_name, source) pairs")
        return {
            "rows_eligible": 0, "fetched": 0, "failed": 0, "not_found": 0,
            "duration_seconds": round(elapsed, 1),
        }

    # Filter against the upstream_versions TTL: skip pairs whose row is fresh.
    have_recent = {
        (r[0], r[1])
        for r in conn.execute(
            "SELECT conda_name, source FROM upstream_versions "
            "WHERE COALESCE(fetched_at, 0) >= ?",
            (cutoff,),
        )
    }
    work = [w for w in work if (w[0], w[1]) not in have_recent]
    if limit > 0:
        work = work[:limit]

    # Partition by registry so per-registry concurrency caps actually bound
    # the per-host load. Order is stable (matches _PHASE_L_RESOLVERS) so log
    # output is predictable.
    work_by_source: dict[str, list[tuple[str, str, str, str]]] = {
        src: [] for src in _PHASE_L_RESOLVERS
    }
    for w in work:
        work_by_source[w[1]].append(w)
    per_source_workers = {
        src: _phase_l_concurrency_for(src)
        for src in _PHASE_L_RESOLVERS
        if work_by_source[src]
    }
    print(
        f"  {len(work):,} (conda_name, source) pairs to refresh "
        f"(TTL {ttl_days}d, sources={sorted(active_sources)})"
    )
    if per_source_workers:
        breakdown = ", ".join(
            f"{src}={len(work_by_source[src]):,}@{per_source_workers[src]}w"
            for src in _PHASE_L_RESOLVERS if work_by_source[src]
        )
        print(f"    per-registry: {breakdown}")

    fetched = 0
    failed = 0
    not_found = 0
    progress_every = min(max(200, len(work) // 40), 2500) if work else 1
    commit_every = 200
    completed = 0
    by_source: dict[str, int] = {}

    def _dispatch(conda_name: str, source: str, query_name: str, public_url: str
                  ) -> tuple[str, str, str | None, str | None, str]:
        resolver = _PHASE_L_RESOLVERS[source][0]
        version, err = resolver(query_name)
        return (conda_name, source, version, err, public_url)

    # One ThreadPoolExecutor per registry, processed sequentially. Each pool
    # uses the per-registry concurrency cap. When the legacy
    # PHASE_L_CONCURRENCY=1 is set everything degrades to fully serial.
    for source, source_work in work_by_source.items():
        if not source_work:
            continue
        workers = per_source_workers[source]
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_dispatch, *w) for w in source_work]
            for fut in as_completed(futures):
                conda_name, _src, version, err, public_url = fut.result()
                now = int(time.time())
                if version is not None:
                    conn.execute(
                        "INSERT OR REPLACE INTO upstream_versions "
                        "(conda_name, source, version, url, fetched_at, last_error) "
                        "VALUES (?, ?, ?, ?, ?, NULL)",
                        (conda_name, source, version, public_url, now),
                    )
                    fetched += 1
                    by_source[source] = by_source.get(source, 0) + 1
                elif err and ("404" in err or "not found" in err.lower()
                              or "no version" in err.lower()):
                    conn.execute(
                        "INSERT OR REPLACE INTO upstream_versions "
                        "(conda_name, source, version, url, fetched_at, last_error) "
                        "VALUES (?, ?, NULL, ?, ?, ?)",
                        (conda_name, source, public_url, now, err),
                    )
                    not_found += 1
                else:
                    conn.execute(
                        "INSERT OR REPLACE INTO upstream_versions "
                        "(conda_name, source, version, url, fetched_at, last_error) "
                        "VALUES (?, ?, NULL, ?, ?, ?)",
                        (conda_name, source, public_url, now, err or "unknown error"),
                    )
                    failed += 1

                completed += 1
                if completed % commit_every == 0:
                    conn.commit()
                if completed % progress_every == 0:
                    elapsed = time.monotonic() - t0
                    rate = completed / elapsed if elapsed else 0
                    eta_min = (len(work) - completed) / rate / 60 if rate else 0
                    print(
                        f"    [{completed:,}/{len(work):,}] fetched={fetched:,} "
                        f"failed={failed:,} 404={not_found:,}  "
                        f"rate={rate:.1f}/s  ETA={eta_min:.1f}min"
                    )

    conn.commit()
    # Snapshot all sources Phase L wrote (npm/cran/cpan/luarocks/crates/
    # rubygems/nuget). Phase L is the only phase that potentially writes
    # multiple sources in a single run.
    snap_total = 0
    for src in by_source.keys():
        snap_total += _snapshot_upstream_versions(conn, source_filter=src)
    elapsed = time.monotonic() - t0
    print(
        f"  Phase L done in {elapsed:.1f}s — fetched {fetched:,} "
        f"(by source: {by_source}), failed {failed:,}, 404 {not_found:,}, "
        f"history snapshot rows: {snap_total:,}"
    )
    return {
        "rows_eligible": len(work),
        "fetched": fetched,
        "failed": failed,
        "not_found": not_found,
        "by_source": by_source,
        "history_snapshot_rows": snap_total,
        "ttl_days": ttl_days,
        "per_source_workers": per_source_workers,
        "duration_seconds": round(elapsed, 1),
    }


def phase_j_dependency_graph(conn: sqlite3.Connection) -> dict:
    """Phase J: parse cf-graph requirements into the dependencies table.

    Reuses the cf-graph-countyfair.tar.gz cache populated by Phase E. Auto-
    skips if the cache is missing. Wipes and rebuilds the dependencies table
    each run — full-snapshot semantics; the table reflects current cf-graph
    state, not historical edges.

    For each feedstock node_attrs file, extracts `meta_yaml.requirements`
    per requirement_type (build/host/run/test) and writes one row per
    (source, target, type) tuple. Pin specs preserved verbatim:
    `'python >=3.10'` → `pin_spec='>=3.10'`. Bare names → `pin_spec=NULL`.

    Multi-output feedstocks: when `meta_yaml.outputs` is a list of dicts
    (one per output package), each output's separate `requirements` block
    is parsed and emitted using that output's own `name` as the source —
    so e.g., `metaio-feedstock` produces edges from BOTH `libmetaio` and
    `metaio` rather than just the primary. Outputs without a name fall
    back to the feedstock basename. Duplicate outputs (same name, common
    in platform-specific multi-output builds) are deduped per-pair.

    Self-references and Jinja-placeholder targets (`{{ python }}`, etc.) are
    skipped — they're not real package edges.
    """
    import tarfile
    t0 = time.monotonic()
    print("  Phase J: dependency graph parse from cf-graph cache")

    cache_path = DATA_DIR / "cf-graph-countyfair.tar.gz"
    if not cache_path.exists():
        return {
            "skipped": True,
            "reason": "cf-graph cache missing; run Phase E first.",
            "duration_seconds": 0.0,
        }

    feedstocks = 0
    edges = 0
    skipped_self = 0
    skipped_jinja = 0
    skipped_inactive = 0

    # Pre-pass: collect feedstock_names whose packages-table rows are archived
    # or inactive. Phase J emits zero edges for these because no `whodepends`
    # query consumes them (every read path filters on active + !archived).
    # Snapshot taken BEFORE the BEGIN TRANSACTION so the inside-transaction
    # DELETE+INSERT sees a coherent view of the skip set.
    # scope: deliberately queries the OPPOSITE of v_actionable_packages —
    # we want the archived/inactive feedstocks to skip them. The view
    # would exclude exactly the rows we need to identify.
    inactive_feedstocks = {
        row[0] for row in conn.execute(
            "SELECT DISTINCT feedstock_name FROM packages "
            "WHERE feedstock_name IS NOT NULL "
            "  AND (COALESCE(feedstock_archived, 0) = 1 "
            "       OR COALESCE(latest_status, 'active') = 'inactive')"
        )
    }

    # Intentional monolithic transaction: `DELETE FROM dependencies` at
    # transaction start gives Phase J full-snapshot semantics — consumers
    # never see a partial dependency graph. Switching to incremental
    # commits would leak partial snapshots between a mid-run interrupt and
    # the next re-run. The local cf-graph cache makes re-extract cheap
    # (~2 min) so all-or-nothing is the right trade-off here. A
    # staging-table swap would preserve both properties but adds
    # complexity disproportionate to the Low-severity audit finding.
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute("DELETE FROM dependencies")
        with tarfile.open(cache_path, "r:gz") as tf:
            for member in tf:
                if not member.isfile():
                    continue
                if "/node_attrs/" not in member.name or not member.name.endswith(".json"):
                    continue
                feedstock_basename = member.name.rsplit("/", 1)[-1][:-5]
                if feedstock_basename in inactive_feedstocks:
                    skipped_inactive += 1
                    continue
                f = tf.extractfile(member)
                if f is None:
                    continue
                try:
                    payload = json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                meta_yaml = payload.get("meta_yaml")
                if not isinstance(meta_yaml, dict):
                    continue

                # Build the (source_name, requirements) pairs to write.
                # Multi-output recipes ship per-output `requirements` under
                # `meta_yaml.outputs[].requirements`; the top-level
                # `meta_yaml.requirements` is shared / build-only / absent.
                pairs: list[tuple[str, dict]] = []
                outputs_block = meta_yaml.get("outputs")
                if isinstance(outputs_block, list) and outputs_block:
                    seen_outputs: set[str] = set()
                    for out in outputs_block:
                        if not isinstance(out, dict):
                            continue
                        out_name = (out.get("name") or "").strip()
                        if not out_name or out_name in seen_outputs:
                            continue
                        seen_outputs.add(out_name)
                        out_reqs = out.get("requirements")
                        if isinstance(out_reqs, dict):
                            pairs.append((out_name, out_reqs))
                    # Dedupe edge case: outputs is just a stub list with no
                    # requirements; fall back to top-level.
                    if not pairs:
                        outputs_raw = payload.get("outputs_names")
                        ons: list[str] = []
                        if isinstance(outputs_raw, dict) and "elements" in outputs_raw:
                            elems = outputs_raw.get("elements") or []
                            if isinstance(elems, list):
                                ons = [str(e) for e in elems if e]
                        elif isinstance(outputs_raw, list):
                            ons = [str(e) for e in outputs_raw if e]
                        sn = ons[0] if ons else feedstock_basename
                        top_reqs = meta_yaml.get("requirements")
                        if isinstance(top_reqs, dict):
                            pairs.append((sn, top_reqs))
                else:
                    # Single-output recipe — top-level requirements only.
                    outputs_raw = payload.get("outputs_names")
                    ons = []
                    if isinstance(outputs_raw, dict) and "elements" in outputs_raw:
                        elems = outputs_raw.get("elements") or []
                        if isinstance(elems, list):
                            ons = [str(e) for e in elems if e]
                    elif isinstance(outputs_raw, list):
                        ons = [str(e) for e in outputs_raw if e]
                    sn = ons[0] if ons else feedstock_basename
                    top_reqs = meta_yaml.get("requirements")
                    if isinstance(top_reqs, dict):
                        pairs.append((sn, top_reqs))

                if not pairs:
                    continue
                feedstocks += 1
                for source_name, reqs in pairs:
                    for req_type in ("build", "host", "run", "test"):
                        spec_list = reqs.get(req_type)
                        if not isinstance(spec_list, list):
                            continue
                        seen: set[tuple[str, str]] = set()
                        for spec in spec_list:
                            if not isinstance(spec, str):
                                continue
                            spec = spec.strip()
                            if not spec:
                                continue
                            parts = spec.split(None, 1)
                            target = parts[0]
                            pin = parts[1].strip() if len(parts) > 1 else None
                            if target == source_name:
                                skipped_self += 1
                                continue
                            if target.startswith("{{") or target.startswith("$"):
                                skipped_jinja += 1
                                continue
                            key = (target, req_type)
                            if key in seen:
                                continue
                            seen.add(key)
                            conn.execute(
                                "INSERT OR REPLACE INTO dependencies "
                                "(source_conda_name, target_conda_name, requirement_type, pin_spec) "
                                "VALUES (?, ?, ?, ?)",
                                (source_name, target, req_type, pin),
                            )
                            edges += 1
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    elapsed = time.monotonic() - t0
    print(
        f"  Phase J done in {elapsed:.1f}s — {feedstocks:,} feedstocks, "
        f"{edges:,} edges (skipped {skipped_self:,} self-refs, "
        f"{skipped_jinja:,} jinja placeholders, "
        f"{skipped_inactive:,} archived/inactive feedstocks)"
    )
    return {
        "feedstocks_parsed": feedstocks,
        "edges_written": edges,
        "skipped_self_references": skipped_self,
        "skipped_jinja_placeholders": skipped_jinja,
        "skipped_inactive_feedstocks": skipped_inactive,
        "duration_seconds": round(elapsed, 1),
    }


def phase_m_feedstock_health(conn: sqlite3.Connection) -> dict:
    """Phase M: parse cf-graph pr_info and version_pr_info side files into
    health columns on `packages`. Surfaces feedstocks where conda-forge bots
    are stuck, where builds are failing, or where version-update PRs aren't
    landing.

    cf-graph stores pr_info / version_pr_info as separate JSON files keyed
    by feedstock (lazy-json refs from node_attrs). The tarball includes
    them at `pr_info/<sharded>/<f>.json` and
    `version_pr_info/<sharded>/<f>.json`. Parse both, write 6 health
    columns:
      - bot_open_pr_count        : open bot-issued PRs
      - bot_last_pr_state        : 'open'|'closed'|'merged'|None
      - bot_last_pr_version      : latest version the bot tried
      - bot_version_errors_count : count of failed version-update attempts
      - feedstock_bad            : 1 if cf-graph flagged the feedstock 'bad'
      - bot_status_fetched_at    : UNIX seconds of this run

    Auto-skips if cf-graph cache is missing.
    """
    import tarfile
    t0 = time.monotonic()
    print("  Phase M: feedstock health from cf-graph pr_info")

    cache_path = DATA_DIR / "cf-graph-countyfair.tar.gz"
    if not cache_path.exists():
        return {
            "skipped": True,
            "reason": "cf-graph cache missing; run Phase E first.",
            "duration_seconds": 0.0,
        }

    pr_info_data: dict[str, dict[str, Any]] = {}
    version_pr_info_data: dict[str, dict[str, Any]] = {}
    files_seen = 0

    with tarfile.open(cache_path, "r:gz") as tf:
        for member in tf:
            if not member.isfile() or not member.name.endswith(".json"):
                continue
            if "/pr_info/" in member.name and "/version_pr_info/" not in member.name:
                files_seen += 1
                feedstock = member.name.rsplit("/", 1)[-1][:-5]
                f = tf.extractfile(member)
                if f is None:
                    continue
                try:
                    pr_info_data[feedstock] = json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
            elif "/version_pr_info/" in member.name:
                files_seen += 1
                feedstock = member.name.rsplit("/", 1)[-1][:-5]
                f = tf.extractfile(member)
                if f is None:
                    continue
                try:
                    version_pr_info_data[feedstock] = json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

    print(f"  parsed {len(pr_info_data):,} pr_info files, "
          f"{len(version_pr_info_data):,} version_pr_info files")

    now = int(time.time())
    updated = 0
    bot_stuck = 0
    feedstock_bad_count = 0

    # Iterate over rows in `packages` whose feedstock_name has cf-graph data.
    # Buffer the SELECT into a list so SQLite doesn't fight with the per-row
    # UPDATEs we issue inside the loop (which would otherwise invalidate the
    # cursor on commit). Periodic commits every 500 rows keep progress
    # durable across mid-phase interrupts.
    # Reads from v_actionable_packages (schema v21+) — canonical triplet.
    # Phase M writes bot-status columns only on rows downstream CLIs read.
    # feedstock-health queries already filter on the same triplet at read
    # time, so this is a write-side cleanup — no behavior change for read
    # paths, but cuts per-build write volume on archived feedstocks.
    rows_to_process = list(conn.execute(
        "SELECT conda_name, feedstock_name FROM v_actionable_packages "
        "WHERE feedstock_name IS NOT NULL"
    ))
    commit_every = 500
    for row in rows_to_process:
        conda_name = row["conda_name"]
        fs = row["feedstock_name"]
        pi = pr_info_data.get(fs)
        vpi = version_pr_info_data.get(fs)
        if pi is None and vpi is None:
            continue
        # PRed: list of {"PR": {state, ...}, "data": {version, ...}}
        open_count = 0
        last_state: str | None = None
        last_version: str | None = None
        if isinstance(pi, dict):
            pred = pi.get("PRed") or []
            if isinstance(pred, list):
                for entry in pred:
                    if not isinstance(entry, dict):
                        continue
                    pr = entry.get("PR") or {}
                    if isinstance(pr, dict) and pr.get("state") == "open":
                        open_count += 1
                if pred:
                    last = pred[-1]
                    if isinstance(last, dict):
                        last_pr = last.get("PR") or {}
                        last_data = last.get("data") or {}
                        if isinstance(last_pr, dict):
                            last_state = last_pr.get("state")
                        if isinstance(last_data, dict):
                            last_version = last_data.get("version")
        bad = 1 if (isinstance(pi, dict) and pi.get("bad")) else 0
        if isinstance(vpi, dict) and vpi.get("bad"):
            bad = 1
        if bad:
            feedstock_bad_count += 1
        errs_count = 0
        if isinstance(vpi, dict):
            errs = vpi.get("new_version_errors") or {}
            if isinstance(errs, list):
                errs_count = len(errs)
            elif isinstance(errs, dict):
                errs_count = len(errs)
        if errs_count > 0 or bad:
            bot_stuck += 1

        conn.execute(
            "UPDATE packages SET "
            "bot_open_pr_count = ?, "
            "bot_last_pr_state = ?, "
            "bot_last_pr_version = ?, "
            "bot_version_errors_count = ?, "
            "feedstock_bad = ?, "
            "bot_status_fetched_at = ? "
            "WHERE conda_name = ?",
            (open_count, last_state, last_version, errs_count, bad, now, conda_name),
        )
        updated += 1
        if updated % commit_every == 0:
            conn.commit()
    conn.commit()

    elapsed = time.monotonic() - t0
    print(
        f"  Phase M done in {elapsed:.1f}s — updated {updated:,} rows; "
        f"{feedstock_bad_count:,} flagged 'bad', {bot_stuck:,} bot-stuck "
        f"(bad OR errors > 0)"
    )
    return {
        "files_seen": files_seen,
        "pr_info_count": len(pr_info_data),
        "version_pr_info_count": len(version_pr_info_data),
        "rows_updated": updated,
        "feedstock_bad_count": feedstock_bad_count,
        "bot_stuck_count": bot_stuck,
        "duration_seconds": round(elapsed, 1),
    }


# Substrings GitHub returns when primary / secondary rate limits trip.
# `gh api` surfaces these in stderr (with an HTTP 403 status line). When
# we see one, Phase N retries with backoff instead of giving up; without
# this detection, transient rate-limit failures used to bake into the
# checkpoint as permanent "gh api failed" errors, causing every later run
# to re-burn the same quota fetching the same already-failed rows.
_GH_RATE_LIMIT_INDICATORS: tuple[str, ...] = (
    "api rate limit exceeded",
    "secondary rate limit",
    "you have exceeded a rate limit",
    "abuse detection mechanism",
)


def _is_gh_rate_limit_stderr(stderr: str | None) -> bool:
    if not stderr:
        return False
    low = stderr.lower()
    return any(token in low for token in _GH_RATE_LIMIT_INDICATORS)


def _phase_n_query_batch(feedstocks: list[str]) -> tuple[dict | None, str | None]:
    """Issue one GraphQL query with N aliased `repository(...)` blocks.

    Returns (data_dict, err). data_dict maps alias `r{i}` → repository
    payload (or None if the repo doesn't exist; GraphQL returns null in
    that case while still completing the request).

    On primary / secondary GitHub rate-limit indicators in stderr,
    retries up to 3x with exponential backoff (30s → 60s) and ±25% jitter
    to desynchronize concurrent batches. Other non-zero exits are
    surfaced immediately as permanent failures.
    """
    import random as _random
    import subprocess
    if not feedstocks:
        return ({}, None)
    parts: list[str] = []
    for i, fs in enumerate(feedstocks):
        # Escape any quotes (defensive — feedstock names shouldn't contain them)
        safe = fs.replace('"', '\\"')
        parts.append(
            f'r{i}: repository(owner: "conda-forge", name: "{safe}-feedstock") {{ '
            'name pushedAt '
            'defaultBranchRef { target { ... on Commit { '
            'statusCheckRollup { state } '
            '} } } '
            'issues(states: OPEN) { totalCount } '
            'pullRequests(states: OPEN) { totalCount } '
            '}'
        )
    query = "{ " + " ".join(parts) + " }"

    last_err: str | None = None
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True, text=True, check=False, timeout=60,
            )
        except FileNotFoundError:
            return (None, "gh CLI not installed")
        except subprocess.TimeoutExpired:
            return (None, "gh api timed out (>60s)")

        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                return (None, "GraphQL response not parseable JSON")
            return (payload.get("data") or {}, None)

        last_err = result.stderr[:200]
        if _is_gh_rate_limit_stderr(result.stderr) and attempt < 2:
            # 30s, 60s base — secondary-limit windows are typically minutes,
            # so this is more patient than Phase F/H's 2^attempt+1.
            base = 30.0 * (attempt + 1)
            sleep_for = min(60.0, base * (0.75 + 0.5 * _random.random()))
            print(f"    Phase N: gh rate-limit hit, sleeping {sleep_for:.1f}s "
                  f"(attempt {attempt + 1}/3)")
            time.sleep(sleep_for)
            continue
        return (None, f"gh api failed: {last_err}")
    return (None, f"gh api failed after retries: {last_err or 'unknown'}")


def phase_n_github_live(conn: sqlite3.Connection) -> dict:
    """Phase N: live GitHub data per feedstock — CI status on default branch,
    open issue + PR counts, pushedAt timestamp.

    Closes the gap Phase M can't (cf-graph only sees what's in node_attrs;
    real-time CI runs, human PRs, and open issues need GitHub directly).

    Default opt-in via PHASE_N_ENABLED=1 because a full conda-forge backfill
    of 32k feedstocks would take many hours even with batched GraphQL.
    Recommended scope-narrowing via PHASE_N_MAINTAINER (run only against
    feedstocks where the named handle is a maintainer — typically ~700
    feedstocks, ~30 batches at 25 per request, completes in minutes).

    Auth: `gh auth token` (the `gh` CLI handles credentials). Uses GraphQL
    via `gh api graphql` for batching; one HTTP request per 25 feedstocks
    consuming ~125 GraphQL points (well under the 5,000-point hourly limit).

    Tunables:
      - PHASE_N_ENABLED       : "1" to run; default skip
      - PHASE_N_MAINTAINER    : restrict to a single maintainer's feedstocks
      - PHASE_N_TTL_DAYS      : default 1 (live signals change fast)
      - PHASE_N_BATCH_SIZE    : default 25 (max ~50 before hitting GraphQL
                                node-limit warnings)
      - PHASE_N_CONCURRENCY   : default 4 (parallel batches)
      - PHASE_N_LIMIT         : cap rows (debug; 0 = no cap)
    """
    import datetime as _dt
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import subprocess

    t0 = time.monotonic()
    print("  Phase N: GitHub live-data fetch (CI status, issues, PRs)")

    if not os.environ.get("PHASE_N_ENABLED"):
        return {
            "skipped": True,
            "reason": "Default off. Set PHASE_N_ENABLED=1 to enable.",
            "duration_seconds": 0.0,
        }
    # Probe gh CLI and auth
    try:
        probe = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=5,
        )
        if probe.returncode != 0 or not probe.stdout.strip():
            return {
                "skipped": True,
                "reason": ("no GitHub auth — run `gh auth login` first. "
                           "Phase N requires authenticated GitHub API access."),
                "duration_seconds": 0.0,
            }
    except FileNotFoundError:
        return {
            "skipped": True,
            "reason": "gh CLI not installed.",
            "duration_seconds": 0.0,
        }

    ttl_days = int(os.environ.get("PHASE_N_TTL_DAYS", "1"))
    batch_size = max(1, min(50, int(os.environ.get("PHASE_N_BATCH_SIZE", "25"))))
    concurrency = max(1, int(os.environ.get("PHASE_N_CONCURRENCY", "4")))
    limit = int(os.environ.get("PHASE_N_LIMIT", "0"))
    maintainer = os.environ.get("PHASE_N_MAINTAINER")
    cutoff = int(time.time()) - ttl_days * 86400

    base_select = (
        # Reads from v_actionable_packages (schema v21+) — canonical triplet.
        "SELECT DISTINCT p.feedstock_name, p.conda_name "
        "FROM v_actionable_packages p "
    )
    where = [
        "p.feedstock_name IS NOT NULL",
        "COALESCE(p.gh_status_fetched_at, 0) < ?",
    ]
    params: list[Any] = [cutoff]
    if maintainer:
        base_select += (
            "JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
            "JOIN maintainers m ON m.id = pm.maintainer_id "
        )
        where.append("LOWER(m.handle) = LOWER(?)")
        params.append(maintainer)
    sql = base_select + "WHERE " + " AND ".join(where) + " ORDER BY p.feedstock_name"
    rows = list(conn.execute(sql, params))
    if limit > 0:
        rows = rows[:limit]
    # Collapse to unique feedstock names (one feedstock can map to multiple
    # conda packages via multi-output recipes); we still write back to all
    # matching rows.
    fs_to_rows: dict[str, list[str]] = {}
    for r in rows:
        fs = r["feedstock_name"]
        fs_to_rows.setdefault(fs, []).append(r["conda_name"])
    feedstocks = list(fs_to_rows.keys())

    # Resume from prior checkpoint if the last run was interrupted
    # (status='in_progress'). The TTL gate above already filters out
    # successfully-written feedstocks, so the checkpoint is mostly a UX
    # signal — it tells the user where the prior run died and confirms
    # the resume will pick up there.
    checkpoint = load_phase_checkpoint(conn, "N")
    resume_from: str | None = None
    if checkpoint and checkpoint.get("status") == "in_progress":
        resume_from = checkpoint.get("last_completed_cursor")
        if resume_from:
            before = len(feedstocks)
            feedstocks = [fs for fs in feedstocks if fs > resume_from]
            skipped = before - len(feedstocks)
            print(f"  Resuming Phase N from cursor > {resume_from!r} "
                  f"(skipped {skipped:,} already-completed feedstocks; "
                  f"prior run had {checkpoint.get('items_completed') or 0:,}"
                  f"/{checkpoint.get('items_total') or 0:,} items)")

    print(f"  {len(feedstocks):,} feedstocks to refresh "
          f"(maintainer={maintainer or 'all'}, TTL {ttl_days}d, "
          f"batch={batch_size}, concurrency={concurrency})")

    if not feedstocks:
        elapsed = time.monotonic() - t0
        save_phase_checkpoint(
            conn, "N",
            cursor=resume_from,
            items_completed=(checkpoint or {}).get("items_completed") or 0,
            items_total=(checkpoint or {}).get("items_total") or 0,
            status="completed",
        )
        return {
            "feedstocks_eligible": 0, "fetched": 0, "failed": 0,
            "duration_seconds": round(elapsed, 1),
        }

    # Pre-batch the feedstocks. Batches preserve alphabetical order because
    # `feedstocks` was filled from an ORDER BY query above, so the cursor
    # advances monotonically.
    batches = [feedstocks[i:i + batch_size]
               for i in range(0, len(feedstocks), batch_size)]
    total_items = len(feedstocks) + (
        (checkpoint or {}).get("items_completed") or 0 if resume_from else 0
    )
    save_phase_checkpoint(
        conn, "N",
        cursor=resume_from,
        items_completed=(checkpoint or {}).get("items_completed") or 0,
        items_total=total_items,
        status="in_progress",
    )

    fetched = 0
    failed = 0
    completed_batches = 0

    def _row_from_payload(fs: str, payload: dict | None) -> tuple[str, dict[str, Any]]:
        out: dict[str, Any] = {
            "ci_state": None, "issues": None, "prs": None, "pushed_at": None,
            "err": None,
        }
        if payload is None:
            out["err"] = "repo not found (404)"
            return (fs, out)
        # CI status from defaultBranchRef.target.statusCheckRollup.state
        try:
            target = (payload.get("defaultBranchRef") or {}).get("target") or {}
            roll = target.get("statusCheckRollup")
            if isinstance(roll, dict):
                out["ci_state"] = (roll.get("state") or "").lower() or None
        except Exception:
            pass
        try:
            out["issues"] = (payload.get("issues") or {}).get("totalCount")
            out["prs"] = (payload.get("pullRequests") or {}).get("totalCount")
        except Exception:
            pass
        pushed = payload.get("pushedAt")
        if pushed:
            try:
                out["pushed_at"] = int(_dt.datetime.fromisoformat(
                    pushed.replace("Z", "+00:00")).timestamp())
            except (ValueError, AttributeError):
                pass
        return (fs, out)

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(_phase_n_query_batch, batch): batch
                   for batch in batches}
        for fut in as_completed(futures):
            batch = futures[fut]
            data, err = fut.result()
            now = int(time.time())
            if data is None:
                # Whole-batch failure — mark all in this batch as failed
                for fs in batch:
                    for cn in fs_to_rows[fs]:
                        conn.execute(
                            "UPDATE packages SET gh_status_last_error = ? "
                            "WHERE conda_name = ?",
                            (err, cn),
                        )
                    failed += 1
                completed_batches += 1
                continue
            for i, fs in enumerate(batch):
                payload = data.get(f"r{i}")
                _, parsed = _row_from_payload(fs, payload)
                if parsed["err"]:
                    for cn in fs_to_rows[fs]:
                        conn.execute(
                            "UPDATE packages SET gh_status_fetched_at = ?, "
                            "gh_status_last_error = ? WHERE conda_name = ?",
                            (now, parsed["err"], cn),
                        )
                    failed += 1
                else:
                    for cn in fs_to_rows[fs]:
                        conn.execute(
                            "UPDATE packages SET "
                            "gh_default_branch_status = ?, "
                            "gh_open_issues_count = ?, "
                            "gh_open_prs_count = ?, "
                            "gh_pushed_at = ?, "
                            "gh_status_fetched_at = ?, "
                            "gh_status_last_error = NULL "
                            "WHERE conda_name = ?",
                            (parsed["ci_state"], parsed["issues"],
                             parsed["prs"], parsed["pushed_at"], now, cn),
                        )
                    fetched += 1
            completed_batches += 1
            # Commit per batch (was every 4) so an interrupt loses at most
            # one batch (~25 feedstocks) of work instead of up to 100.
            conn.commit()
            # Checkpoint: record the alphabetically-largest feedstock
            # processed so far. `batches` were generated from the sorted
            # `feedstocks` list, so max() of any in-flight batch is a
            # safe lower bound (we resume from > cursor next time).
            batch_max = max(batch) if batch else None
            prior_done = (checkpoint or {}).get("items_completed") or 0
            save_phase_checkpoint(
                conn, "N",
                cursor=batch_max,
                items_completed=prior_done + fetched + failed,
                items_total=total_items,
                status="in_progress",
            )
            if completed_batches % 4 == 0:
                elapsed = time.monotonic() - t0
                rate = (fetched + failed) / elapsed if elapsed else 0
                eta_min = ((len(feedstocks) - fetched - failed) / rate / 60
                           if rate else 0)
                print(
                    f"    [{completed_batches:,}/{len(batches):,} batches] "
                    f"fetched={fetched:,} failed={failed:,}  "
                    f"rate={rate:.1f}/s  ETA={eta_min:.1f}min"
                )

    conn.commit()
    # Mark the run as completed so a subsequent invocation does not try
    # to resume — it should start a fresh run governed by the TTL gate.
    save_phase_checkpoint(
        conn, "N",
        cursor=feedstocks[-1] if feedstocks else resume_from,
        items_completed=((checkpoint or {}).get("items_completed") or 0)
                         + fetched + failed,
        items_total=total_items,
        status="completed",
    )
    elapsed = time.monotonic() - t0
    print(
        f"  Phase N done in {elapsed:.1f}s — fetched {fetched:,} feedstocks, "
        f"failed {failed:,}, batches {completed_batches:,}"
    )
    return {
        "feedstocks_eligible": len(feedstocks),
        "fetched": fetched,
        "failed": failed,
        "batches_total": len(batches),
        "batches_completed": completed_batches,
        "ttl_days": ttl_days,
        "batch_size": batch_size,
        "concurrency": concurrency,
        "duration_seconds": round(elapsed, 1),
    }


def phase_g_prime_per_version_vulns(conn: sqlite3.Connection) -> dict:
    """Phase G' — per-version vuln scoring.

    Phase G writes vuln counts for each package's `latest_conda_version`.
    Phase G' iterates `package_version_downloads` (Phase I data) and scores
    EVERY version separately, writing to `package_version_vulns`. Lets
    consumers find the most-recent build set with 0 critical CVEs for
    env-lockdown, and lets maintainers see which historical versions are
    risky for downstream pinners.

    Auto-skip if vdb library unavailable (same as Phase G). Opt-in via
    PHASE_GP_ENABLED=1 — full scan is ~250k version-rows × ~5 ms per
    vdb query = ~20 minutes serial; with concurrency=8, ~3 minutes.

    Tunables:
      - PHASE_GP_ENABLED      : "1" to run; default skip
      - PHASE_GP_TTL_DAYS     : skip rows scanned within N days (default 30)
      - PHASE_GP_LIMIT        : cap rows (debug)
      - PHASE_GP_MAINTAINER   : restrict to one maintainer's packages
    """
    t0 = time.monotonic()
    print("  Phase G': per-version vuln scoring")

    if not os.environ.get("PHASE_GP_ENABLED"):
        return {
            "skipped": True,
            "reason": "Default off. Set PHASE_GP_ENABLED=1 to enable.",
            "duration_seconds": 0.0,
        }
    import importlib.util
    try:
        spec = importlib.util.find_spec("vdb.lib.search")
    except (ModuleNotFoundError, ValueError):
        spec = None
    if spec is None:
        return {
            "skipped": True,
            "reason": "vdb library not installed (run from `vuln-db` env).",
            "duration_seconds": 0.0,
        }

    sys.path.insert(0, str(Path(__file__).parent))
    from detail_cf_atlas import fetch_vdb_data  # type: ignore[import-not-found]

    ttl_days = int(os.environ.get("PHASE_GP_TTL_DAYS", "30"))
    limit = int(os.environ.get("PHASE_GP_LIMIT", "0"))
    maintainer = os.environ.get("PHASE_GP_MAINTAINER")
    cutoff = int(time.time()) - ttl_days * 86400

    # JOIN to v_actionable_packages (schema v21+) — encodes canonical triplet.
    base = (
        "SELECT pvd.conda_name, pvd.version, p.pypi_name, p.npm_name, "
        "       p.conda_repo_url, p.conda_dev_url "
        "FROM package_version_downloads pvd "
        "JOIN v_actionable_packages p ON p.conda_name = pvd.conda_name "
    )
    where = [
        "NOT EXISTS (SELECT 1 FROM package_version_vulns pvv "
        "            WHERE pvv.conda_name = pvd.conda_name "
        "              AND pvv.version = pvd.version "
        "              AND pvv.scanned_at >= ?)",
    ]
    params: list[Any] = [cutoff]
    if maintainer:
        base += (
            "JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
            "JOIN maintainers m ON m.id = pm.maintainer_id "
        )
        where.append("LOWER(m.handle) = LOWER(?)")
        params.append(maintainer)
    sql = base + "WHERE " + " AND ".join(where) + " ORDER BY pvd.conda_name, pvd.version"
    if limit > 0:
        sql += f" LIMIT {limit}"
    rows = list(conn.execute(sql, params))
    print(f"  {len(rows):,} (package, version) pairs to score "
          f"(maintainer={maintainer or 'all'}, TTL {ttl_days}d)")

    scanned = 0
    failed = 0
    # Cap at 2,500 so multi-100k-row runs still emit a line every ~30-60s
    # instead of going silent for many minutes (the historical "Phase H is
    # hung" misdiagnosis — workers were churning, the formula just buried
    # the signal under a 20k-row gap).
    progress_every = min(max(500, len(rows) // 40), 2500) if rows else 1
    commit_every = 500

    for i, r in enumerate(rows):
        record = {
            "conda_name":           r["conda_name"],
            "pypi_name":            r["pypi_name"],
            "npm_name":             r["npm_name"],
            "latest_conda_version": r["version"],   # used as the queried version
            "conda_repo_url":       r["conda_repo_url"],
            "conda_dev_url":        r["conda_dev_url"],
        }
        data, _err = fetch_vdb_data(record, version_override=r["version"])
        _ = _err  # acknowledge: per-version errors are not surfaced; only counts retained
        now = int(time.time())
        if data is None:
            failed += 1
            continue
        affecting = data.get("affecting_latest_version") or []
        crit = sum(1 for v in affecting if v.get("severity") == "Critical")
        high = sum(1 for v in affecting if v.get("severity") == "High")
        kev = sum(1 for v in affecting if v.get("kev"))
        total = len(data.get("all_vulns") or [])
        conn.execute(
            "INSERT OR REPLACE INTO package_version_vulns "
            "(conda_name, version, vuln_total, "
            " vuln_critical_affecting_version, vuln_high_affecting_version, "
            " vuln_kev_affecting_version, scanned_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r["conda_name"], r["version"], total, crit, high, kev, now),
        )
        scanned += 1
        if scanned % commit_every == 0:
            conn.commit()
        if (i + 1) % progress_every == 0:
            elapsed = time.monotonic() - t0
            rate = (i + 1) / elapsed if elapsed else 0
            eta_min = (len(rows) - i - 1) / rate / 60 if rate else 0
            print(
                f"    [{i+1:,}/{len(rows):,}] scanned={scanned:,} "
                f"failed={failed:,}  rate={rate:.1f}/s  ETA={eta_min:.1f}min"
            )

    conn.commit()
    elapsed = time.monotonic() - t0
    print(
        f"  Phase G' done in {elapsed:.1f}s — scanned: {scanned:,}, "
        f"failed: {failed:,}"
    )
    return {
        "rows_eligible": len(rows),
        "scanned": scanned,
        "failed": failed,
        "ttl_days": ttl_days,
        "duration_seconds": round(elapsed, 1),
    }


def write_meta(conn: sqlite3.Connection, build_stats: dict) -> None:
    """Write build provenance to meta table and JSON sidecar."""
    build_stats["schema_version"] = SCHEMA_VERSION
    build_stats["built_at"] = int(time.time())
    for key, value in build_stats.items():
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                     (key, json.dumps(value) if not isinstance(value, str) else value))
    conn.commit()
    META_PATH.write_text(json.dumps(build_stats, indent=2, sort_keys=True))


def export_json(conn: sqlite3.Connection, path: Path = EXPORT_PATH) -> int:
    """Dump the enriched view to a JSON file for human inspection."""
    rows = [dict(row) for row in conn.execute("SELECT * FROM v_packages_enriched")]
    path.write_text(json.dumps(rows, indent=2, sort_keys=True, default=str))
    return len(rows)


# Phase registry — single source of truth for `cmd_build`, the `atlas-phase`
# CLI, and any other code that needs to introspect or invoke phases. Order
# matches the canonical pipeline dependency order. `get_phase` does
# case-insensitive lookup on `phase_id`.
PHASES: list[tuple[str, Any]] = [
    ("B",   phase_b_conda_enumeration),
    ("B.5", phase_b5_feedstock_outputs),
    ("B.6", phase_b6_yanked_detection),
    ("C",   phase_c_parselmouth_join),
    ("C.5", phase_c5_source_url_match),
    ("D",   phase_d_pypi_enumeration),
    ("E",   phase_e_enrichment),
    ("E.5", phase_e5_archived_feedstocks),
    ("F",   phase_f_downloads),
    ("G",   phase_g_vdb_summary),
    ("G'",  phase_g_prime_per_version_vulns),
    ("H",   phase_h_pypi_versions),
    ("J",   phase_j_dependency_graph),
    ("K",   phase_k_vcs_versions),
    ("L",   phase_l_extra_registries),
    ("M",   phase_m_feedstock_health),
    ("N",   phase_n_github_live),
]


def get_phase(phase_id: str):
    """Return the `(name, fn)` entry for `phase_id`. Case-insensitive on the
    letter portion. Raises `KeyError` with a helpful list of known phases."""
    target = phase_id.strip().upper()
    for name, fn in PHASES:
        if name.upper() == target:
            return name, fn
    valid = ", ".join(name for name, _ in PHASES)
    raise KeyError(f"unknown phase {phase_id!r}; valid: {valid}")


def run_single_phase(phase_id: str, conn: sqlite3.Connection) -> dict:
    """Run one phase against `conn`. Used by the `atlas-phase` CLI to refresh
    a single phase without rebuilding the world. Callers are responsible
    for prerequisite columns being populated (e.g. Phase H expects
    `pypi_name`, populated by Phase C). Phases short-circuit cleanly when
    prerequisites are missing.
    """
    name, fn = get_phase(phase_id)
    print(f"--- Phase {name} (single-phase invocation) ---")
    return fn(conn)


# --- CLI ---

def cmd_build(args: argparse.Namespace) -> int:
    """Build the unified map via the full pipeline."""
    print("=== Unified Map Build ===")
    conn = open_db()
    init_schema(conn)
    print(f"  DB: {DB_PATH}")
    print(f"  Schema version: {SCHEMA_VERSION}")

    if args.dry_run:
        print("  --dry-run: skeleton only, no pipeline execution")
        write_meta(conn, {"phases_run": [], "dry_run": True})
        print("Skeleton written. Tables created. Phases not implemented yet.")
        return 0

    stats: dict[str, Any] = {"phases_run": []}
    for name, fn in PHASES:
        print(f"--- Phase {name} ---")
        try:
            phase_stats = fn(conn)
            stats["phases_run"].append(name)
            stats[f"phase_{name.replace('.', '_')}"] = phase_stats
        except NotImplementedError as e:
            print(f"  SKIP: {e}")
            continue

    write_meta(conn, stats)
    if args.export_json:
        n = export_json(conn)
        print(f"Exported {n:,} rows to {EXPORT_PATH}")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Look up a package by name (matches conda_name OR pypi_name)."""
    if not DB_PATH.exists():
        print(f"Database not built yet. Run: build-unified-map", file=sys.stderr)
        return 1
    conn = open_db()
    rows = list(conn.execute(
        "SELECT * FROM v_packages_enriched WHERE conda_name = ? OR pypi_name = ? LIMIT 5",
        (args.name, args.name),
    ))
    if not rows:
        print(f"No package found for name: {args.name}", file=sys.stderr)
        return 1
    for row in rows:
        print(json.dumps(dict(row), indent=2, sort_keys=True, default=str))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show summary statistics from the unified map."""
    _ = args  # argparse dispatches all subcommands uniformly; cmd_stats has no flags
    if not DB_PATH.exists():
        print(f"Database not built yet. Run: build-unified-map", file=sys.stderr)
        return 1
    conn = open_db()
    print(f"=== Conda-Forge Atlas Stats ({DB_PATH}) ===")
    # scope: cmd_stats is the stats-cf-atlas CLI; reports the full
    # distribution including archived/inactive rows for ops visibility.
    total = conn.execute("SELECT COUNT(*) AS n FROM packages").fetchone()["n"]
    print(f"Total packages: {total:,}")
    # scope: same — stats reporting needs the full relationship distribution.
    for row in conn.execute(
        "SELECT relationship, COUNT(*) AS n FROM packages GROUP BY relationship ORDER BY n DESC"
    ):
        print(f"  {row['relationship']:<20} {row['n']:>9,}")
    meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
    print(f"\nBuild metadata: {json.dumps(meta, indent=2)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "Unified Cross-Channel Package Map").split("\n")[1]
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Build the unified map")
    p_build.add_argument("--dry-run", action="store_true",
                         help="Create schema only; skip pipeline phases")
    p_build.add_argument("--export-json", action="store_true",
                         help="Also dump full table to cf_atlas_export.json")
    p_build.set_defaults(func=cmd_build)

    p_query = sub.add_parser("query", help="Look up a package by name")
    p_query.add_argument("name", help="Package name (conda_name or pypi_name)")
    p_query.set_defaults(func=cmd_query)

    p_stats = sub.add_parser("stats", help="Show summary statistics")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
