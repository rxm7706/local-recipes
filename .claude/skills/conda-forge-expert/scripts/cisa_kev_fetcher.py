#!/usr/bin/env python3
"""CISA Known Exploited Vulnerabilities catalog fetcher (DW13 / Path C).

Pulls the CISA KEV JSON feed and upserts it into the `cisa_kev` table of
cf_atlas.db. Phase G / G' overlay this table on vdb's per-CVE `kev` field
so `vuln_kev_affecting_current` reflects the live CISA catalogue.

Background: appthreat-vulnerability-db's aqua.py hardcodes the `kevc`
(CISA KEV) directory into DEFAULT_IGNORE_SOURCE_PATTERNS. Even a
successful `vdb --cache-os` run downloads ~33 GB of distro CVE data and
still leaves the KEV signal empty. CISA itself publishes the catalogue as
a small (~2 MB) JSON; pulling it directly is far simpler than monkey-
patching vdb's ignore list.

URL: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
Schema is stable since 2021; documented at
https://www.cisa.gov/known-exploited-vulnerabilities .

Usage:
    pixi run -e local-recipes fetch-cisa-kev                # standard refresh
    pixi run -e local-recipes fetch-cisa-kev --dry-run      # fetch + parse only, no DB write
    pixi run -e local-recipes fetch-cisa-kev --json         # machine-readable result
    pixi run -e local-recipes fetch-cisa-kev --db PATH      # write to a different atlas DB
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _http  # noqa: E402
import conda_forge_atlas as atlas  # noqa: E402

CISA_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
)

# CISA's `knownRansomwareCampaignUse` is a free-text string; observed values
# are "Known" and "Unknown" (case-insensitive). Map to a tri-state INTEGER:
# 1 = Known, 0 = Unknown, NULL = anything else (future-proofing in case
# CISA adds a value we don't recognize — surface as NULL so SQL queries
# can `IS NOT NULL` rather than misclassify).
def _map_ransomware_use(raw: str | None) -> int | None:
    if raw is None:
        return None
    s = raw.strip().lower()
    if s == "known":
        return 1
    if s == "unknown":
        return 0
    return None


def fetch_cisa_kev_json(*, timeout: int = 60) -> dict[str, Any]:
    """Pull the CISA KEV JSON feed. Returns the parsed top-level object.

    Raises RuntimeError on network failure (delegated from
    `_http.fetch_with_fallback`). The CISA feed is a single canonical URL
    — no JFrog / enterprise proxy resolution applies — but we still route
    through `_http.fetch_with_fallback` for retry-with-backoff behavior.
    """
    return _http.fetch_with_fallback(
        [CISA_KEV_URL],
        return_json=True,
        timeout=timeout,
        user_agent="conda-forge-expert-cisa-kev/1.0",
    )


def upsert_kev_rows(
    conn: sqlite3.Connection,
    catalog: dict[str, Any],
    *,
    fetched_at: int | None = None,
) -> dict[str, int | str | None]:
    """Upsert every vulnerability in `catalog` into the `cisa_kev` table.

    Idempotent — re-running with an unchanged feed produces zero net diff
    (INSERT OR REPLACE on the cve_id PK). Returns a stats dict:
      - rows_in_feed : int   — vulnerabilities reported by CISA
      - rows_before  : int   — cisa_kev rows before upsert
      - rows_after   : int   — cisa_kev rows after upsert
      - rows_new     : int   — net delta (after − before)
      - catalog_version : str | None — CISA's catalogVersion at this fetch
      - date_released   : str | None — CISA's dateReleased at this fetch
    """
    if fetched_at is None:
        fetched_at = int(time.time())

    rows_before = conn.execute("SELECT COUNT(*) FROM cisa_kev").fetchone()[0]
    vulns = catalog.get("vulnerabilities") or []
    catalog_version = catalog.get("catalogVersion")
    date_released = catalog.get("dateReleased")

    sql = (
        "INSERT OR REPLACE INTO cisa_kev "
        "(cve_id, vendor, product, vulnerability_name, date_added, "
        " short_description, required_action, due_date, "
        " known_ransomware_use, notes, cwes, "
        " cisa_catalog_version, source_fetched_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn.execute("BEGIN")
    try:
        for v in vulns:
            cve_id = v.get("cveID")
            if not cve_id:
                # Defensive: a row without a cveID would violate the PK. CISA
                # has never shipped one, but skip rather than crash if they do.
                continue
            cwes_raw = v.get("cwes")
            cwes_json = json.dumps(cwes_raw) if cwes_raw else None
            conn.execute(
                sql,
                (
                    cve_id,
                    v.get("vendorProject"),
                    v.get("product"),
                    v.get("vulnerabilityName"),
                    v.get("dateAdded"),
                    v.get("shortDescription"),
                    v.get("requiredAction"),
                    v.get("dueDate"),
                    _map_ransomware_use(v.get("knownRansomwareCampaignUse")),
                    v.get("notes"),
                    cwes_json,
                    catalog_version,
                    fetched_at,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    rows_after = conn.execute("SELECT COUNT(*) FROM cisa_kev").fetchone()[0]
    return {
        "rows_in_feed": len(vulns),
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_new": rows_after - rows_before,
        "catalog_version": catalog_version,
        "date_released": date_released,
    }


def refresh_cisa_kev(
    db_path: Path | None = None,
    *,
    dry_run: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """End-to-end refresh: fetch the feed, upsert into the atlas DB.

    With `dry_run=True`, fetches and counts entries but skips the DB
    write — useful for connectivity / schema-shape sanity checks.
    """
    t0 = time.monotonic()
    catalog = fetch_cisa_kev_json(timeout=timeout)
    vulns = catalog.get("vulnerabilities") or []

    result: dict[str, Any] = {
        "url": CISA_KEV_URL,
        "rows_in_feed": len(vulns),
        "catalog_version": catalog.get("catalogVersion"),
        "date_released": catalog.get("dateReleased"),
        "dry_run": dry_run,
    }

    if dry_run:
        result["duration_seconds"] = round(time.monotonic() - t0, 2)
        return result

    path = db_path or atlas.DB_PATH
    conn = atlas.open_db(path=path)
    try:
        atlas.init_schema(conn)
        stats = upsert_kev_rows(conn, catalog)
    finally:
        conn.close()

    result.update(stats)
    result["db_path"] = str(path)
    result["duration_seconds"] = round(time.monotonic() - t0, 2)
    return result


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fetch-cisa-kev",
        description="Refresh the CISA Known Exploited Vulnerabilities table "
                    "in cf_atlas.db. ~2 MB pull from cisa.gov; runs in seconds.",
    )
    p.add_argument(
        "--db",
        type=Path,
        default=None,
        help=f"Path to atlas DB (default: {atlas.DB_PATH})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch + parse the feed, but skip the DB write.",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds (default: 60).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the result as JSON (default: human-readable).",
    )
    return p


def _print_human(result: dict[str, Any]) -> None:
    print(f"CISA KEV refresh — {result['url']}")
    print(f"  catalog_version : {result.get('catalog_version')}")
    print(f"  date_released   : {result.get('date_released')}")
    print(f"  rows_in_feed    : {result['rows_in_feed']:,}")
    if result.get("dry_run"):
        print("  (dry-run: no DB write)")
    else:
        before = result.get("rows_before", 0)
        after = result.get("rows_after", 0)
        new = result.get("rows_new", 0)
        print(f"  rows_before     : {before:,}")
        print(f"  rows_after      : {after:,}")
        print(f"  net new         : {new:+,}")
        print(f"  db_path         : {result.get('db_path')}")
    print(f"  duration        : {result.get('duration_seconds')}s")


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    try:
        result = refresh_cisa_kev(
            db_path=args.db,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    except Exception as e:
        if args.as_json:
            print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        else:
            print(f"fetch-cisa-kev FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
