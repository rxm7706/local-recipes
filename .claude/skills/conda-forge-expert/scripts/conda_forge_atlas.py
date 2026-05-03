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
        fetch_with_fallback as _fetch_with_fallback,
    )
    inject_ssl_truststore()
    _HTTP_AVAILABLE = True
except ImportError:
    _http_make_request = None  # type: ignore[assignment]
    _resolve_conda_forge_urls = None  # type: ignore[assignment]
    _resolve_pypi_simple_urls = None  # type: ignore[assignment]
    _resolve_github_urls = None  # type: ignore[assignment]
    _fetch_with_fallback = None  # type: ignore[assignment]
    _HTTP_AVAILABLE = False


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

SCHEMA_VERSION = 1


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
    pypi_last_serial       INTEGER,
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

CREATE INDEX IF NOT EXISTS idx_relationship ON packages(relationship);
CREATE INDEX IF NOT EXISTS idx_match_source ON packages(match_source);
CREATE INDEX IF NOT EXISTS idx_pypi_name    ON packages(pypi_name);
CREATE INDEX IF NOT EXISTS idx_conda_name   ON packages(conda_name);
CREATE INDEX IF NOT EXISTS idx_feedstock    ON packages(feedstock_name);
CREATE INDEX IF NOT EXISTS idx_license      ON packages(conda_license);
CREATE INDEX IF NOT EXISTS idx_status       ON packages(latest_status);
CREATE INDEX IF NOT EXISTS idx_archived     ON packages(feedstock_archived);
CREATE INDEX IF NOT EXISTS idx_handle       ON maintainers(handle);

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


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables, indexes, and views if not present."""
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
            for filename, rec in source_dict.items():
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

    print(f"  Inserting into SQLite (single transaction)...")
    conn.execute("BEGIN TRANSACTION")
    try:
        for rec in aggregated.values():
            conn.execute(
                """
                INSERT INTO packages (
                    conda_name, conda_subdirs, conda_noarch,
                    latest_conda_version, latest_conda_upload,
                    conda_license, conda_license_family,
                    relationship, match_source, match_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'conda_only', 'none', 'n/a')
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
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

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

    existing = {row[0] for row in conn.execute("SELECT conda_name FROM packages WHERE conda_name IS NOT NULL")}
    print(f"  Existing conda_name rows: {len(existing):,}")

    conn.execute("BEGIN TRANSACTION")
    try:
        updated = 0
        inserted_inactive = 0
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
                    INSERT INTO packages (
                        conda_name, feedstock_name,
                        relationship, match_source, match_confidence, latest_status
                    ) VALUES (?, ?, 'conda_only', 'none', 'n/a', 'inactive')
                    """,
                    (pkg_name, feedstock_name),
                )
                inserted_inactive += 1
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

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
    conn.execute("BEGIN TRANSACTION")
    try:
        # Active: has a current version from Phase B
        active = conn.execute(
            "UPDATE packages SET latest_status = 'active' "
            "WHERE latest_conda_version IS NOT NULL AND latest_status IS NULL"
        ).rowcount
        # Inactive: registered but no current version (already set in Phase B.5)
        inactive = conn.execute(
            "SELECT COUNT(*) FROM packages WHERE latest_status = 'inactive'"
        ).fetchone()[0]
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    elapsed = time.monotonic() - t0
    print(f"  Phase B.6 done in {elapsed:.1f}s — active: {active:,}, inactive: {inactive:,}")
    return {
        "active_count": active,
        "inactive_count": inactive,
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

    conn.execute("BEGIN TRANSACTION")
    try:
        updated = 0
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
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

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
    print("  Phase C.5 folded into Phase E (needs cf-graph data); skipping standalone")
    return {"folded_into": "E"}


def phase_d_pypi_enumeration(conn: sqlite3.Connection) -> dict:
    """Phase D: enumerate PyPI universe via Simple API v1.

    Fetches all ~800k PyPI package names + freshness serials. For each:
      - if pypi_name already set in a conda row (matched in Phase C) → set pypi_last_serial
      - elif a conda row exists with same conda_name (case-insensitive) → mark
        match_source='name_coincidence', match_confidence='likely', set pypi_name
      - else INSERT a new pypi_only row
    """
    t0 = time.monotonic()
    print("  Fetching PyPI Simple v1 JSON (~40MB)...")
    if _HTTP_AVAILABLE and _resolve_pypi_simple_urls is not None and _fetch_with_fallback is not None:
        # Each PyPI Simple base URL needs a trailing slash for the index endpoint.
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
    projects = simple.get("projects", [])
    print(f"  Got {len(projects):,} PyPI projects")

    # Build a quick lookup of existing conda rows
    existing_conda = {row[0].lower(): row[0] for row in
                      conn.execute("SELECT conda_name FROM packages WHERE conda_name IS NOT NULL")
                      if row[0]}
    existing_pypi = {row[0] for row in
                     conn.execute("SELECT pypi_name FROM packages WHERE pypi_name IS NOT NULL")
                     if row[0]}

    conn.execute("BEGIN TRANSACTION")
    try:
        updated_serial = 0
        upgraded_to_coincidence = 0
        inserted_pypi_only = 0
        for proj in projects:
            pypi_name = proj.get("name", "").lower()
            serial = proj.get("_last-serial")
            if not pypi_name:
                continue
            if pypi_name in existing_pypi:
                # Already matched via parselmouth — just record serial
                conn.execute(
                    "UPDATE packages SET pypi_last_serial = ? WHERE pypi_name = ?",
                    (serial, pypi_name),
                )
                updated_serial += 1
            elif pypi_name in existing_conda:
                # Same-name conda package not yet matched — mark name_coincidence
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
            else:
                # PyPI-only row
                conn.execute(
                    """
                    INSERT INTO packages (
                        pypi_name, pypi_last_serial,
                        relationship, match_source, match_confidence
                    ) VALUES (?, ?, 'pypi_only', 'none', 'n/a')
                    """,
                    (pypi_name, serial),
                )
                inserted_pypi_only += 1
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    elapsed = time.monotonic() - t0
    print(f"  Phase D done in {elapsed:.1f}s")
    print(f"    parselmouth-matched serial updates: {updated_serial:,}")
    print(f"    upgraded to name_coincidence:        {upgraded_to_coincidence:,}")
    print(f"    inserted pypi_only:                  {inserted_pypi_only:,}")
    return {
        "pypi_projects": len(projects),
        "serial_updates": updated_serial,
        "name_coincidence_upgrades": upgraded_to_coincidence,
        "pypi_only_inserts": inserted_pypi_only,
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
]
# Specific extractors for cross-channel name within source.url
_NPM_NAME_RE = r"registry\.npmjs\.org/(@[^/]+/[^/]+|[^/]+)/-/"
_PYPI_NAME_RE = r"(?:pypi\.io|pypi\.org)/packages/source/[^/]/([^/]+)/"


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
    # don't re-download the 139MB archive
    import tarfile
    import io
    cache_path = DATA_DIR / "cf-graph-countyfair.tar.gz"
    cache_age = (time.time() - cache_path.stat().st_mtime) / 86400 if cache_path.exists() else 999
    if cache_path.exists() and cache_age < 1:
        print(f"  Using cached cf-graph archive ({cache_path.stat().st_size:,} bytes, {cache_age:.2f}d old)")
        tar_bytes = cache_path.read_bytes()
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
        cache_path.write_bytes(tar_bytes)
        print(f"  Cached to {cache_path}")
    print(f"  Got {len(tar_bytes):,} bytes; extracting node_attrs/...")

    # Build feedstock_name → conda_name map for reverse-lookup
    feedstock_to_conda: dict[str, list[str]] = {}
    for row in conn.execute(
        "SELECT conda_name, feedstock_name FROM packages WHERE feedstock_name IS NOT NULL"
    ):
        feedstock_to_conda.setdefault(row[1], []).append(row[0])

    enriched = 0
    pypi_url_matched = 0
    conn.execute("BEGIN TRANSACTION")
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
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
                # recipe_format detection: rendered_recipe schema_version
                rendered = payload.get("rendered_recipes") or []
                recipe_format = "unknown"
                if rendered and isinstance(rendered, list):
                    first_rendered = rendered[0] if rendered else {}
                    if isinstance(first_rendered, dict) and "schema_version" in first_rendered:
                        recipe_format = "recipe.yaml"
                    else:
                        recipe_format = "meta.yaml"
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
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

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
    feedstock_archived=1 on rows whose feedstock_name appears in the archived
    list, 0 on the rest.
    """
    import subprocess
    t0 = time.monotonic()
    print("  Phase E.5: querying conda-forge org for archived feedstock repos...")

    # Paginated GraphQL — conda-forge has thousands of feedstocks; we filter to archived only
    archived: set[str] = set()
    cursor = None
    page = 0
    while True:
        page += 1
        cursor_arg = f', after: "{cursor}"' if cursor else ""
        query = (
            "{ organization(login: \"conda-forge\") { "
            f"  repositories(first: 100, isArchived: true{cursor_arg}) {{ "
            "    nodes { name } "
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
            print(f"  GraphQL failed on page {page}: {e.stderr[:200]}")
            break
        repos = data["data"]["organization"]["repositories"]
        for node in repos["nodes"]:
            archived.add(node["name"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    print(f"  Found {len(archived):,} archived repos in conda-forge org (across {page} pages)")

    # Filter to *-feedstock repos and apply
    archived_feedstocks = {name for name in archived if name.endswith("-feedstock")}
    print(f"  {len(archived_feedstocks):,} are *-feedstock repos")

    conn.execute("BEGIN TRANSACTION")
    try:
        # Default everyone to 0 (not archived)
        conn.execute("UPDATE packages SET feedstock_archived = 0 WHERE feedstock_name IS NOT NULL")
        # Strip "-feedstock" suffix from GitHub repo names — feedstock-outputs
        # stores them WITHOUT the suffix (e.g., "numpy" not "numpy-feedstock"),
        # but GraphQL returns the full repo name.
        marked = 0
        for fs_repo_name in archived_feedstocks:
            fs_short = fs_repo_name[:-len("-feedstock")]  # strip suffix
            cursor = conn.execute(
                "UPDATE packages SET feedstock_archived = 1 WHERE feedstock_name = ?", (fs_short,)
            )
            marked += cursor.rowcount
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    elapsed = time.monotonic() - t0
    print(f"  Phase E.5 done in {elapsed:.1f}s — marked {marked:,} rows as archived")
    return {
        "archived_repos_total": len(archived),
        "archived_feedstocks": len(archived_feedstocks),
        "marked_rows": marked,
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

    # Phases will be implemented incrementally (B, B.5, B.6, C, C.5, D, E, E.5)
    phases = [
        ("B",   phase_b_conda_enumeration),
        ("B.5", phase_b5_feedstock_outputs),
        ("B.6", phase_b6_yanked_detection),
        ("C",   phase_c_parselmouth_join),
        ("C.5", phase_c5_source_url_match),
        ("D",   phase_d_pypi_enumeration),
        ("E",   phase_e_enrichment),
        ("E.5", phase_e5_archived_feedstocks),
    ]
    stats: dict[str, Any] = {"phases_run": []}
    for name, fn in phases:
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
    if not DB_PATH.exists():
        print(f"Database not built yet. Run: build-unified-map", file=sys.stderr)
        return 1
    conn = open_db()
    print(f"=== Conda-Forge Atlas Stats ({DB_PATH}) ===")
    total = conn.execute("SELECT COUNT(*) AS n FROM packages").fetchone()["n"]
    print(f"Total packages: {total:,}")
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
