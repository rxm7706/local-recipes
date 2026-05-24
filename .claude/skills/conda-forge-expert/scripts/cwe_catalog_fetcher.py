#!/usr/bin/env python3
"""MITRE CWE catalog fetcher (v8.6.0 Wave B).

Pulls MITRE's Common Weakness Enumeration (CWE) Research Concepts CSV and
upserts it into the `cwe_categories` table of cf_atlas.db. Phase G / G'
overlay this table on vdb's per-CVE output (via `_load_cwe_categories`) to
populate per-package `vuln_cwe_top` and `vuln_cwe_categories_json` —
operators can triage by severity *type* (RCE vs DoS vs Info-Disclosure)
instead of by raw Critical/High count.

URL: https://cwe.mitre.org/data/csv/1000.csv.zip (Research Concepts view).

Note: the v8.6.0 parent spec references `2000.csv.zip` (Architectural
Concepts) — that's wrong; 1000 is the Research Concepts view we want
(944 weaknesses as of 2026-05-23). Verified against MITRE downloads page.

CSV format (verified 2026-05-23):
  - First row is the header: `CWE-ID,Name,Weakness Abstraction,Status,Description,...`
  - `CWE-ID` is a bare integer (e.g., `79`, `22`) — this fetcher prepends
    `CWE-` at store time to match vdb's `cweId: "CWE-79"` convention.
  - 944 data rows.

Seed-mapping JSON committed at
`.claude/skills/conda-forge-expert/data/cwe_categories_seed.json` maps the
top-N well-known CWEs to 7 cf_atlas categories (RCE / DoS / Info-Disclosure
/ Auth-Bypass / Memory-Safety / Traversal / Injection). Any CWE not in
the seed gets `cf_atlas_category = 'Other'` at upsert time.

Usage:
    pixi run -e local-recipes fetch-cwe-catalog                # standard refresh
    pixi run -e local-recipes fetch-cwe-catalog --dry-run      # fetch + parse only
    pixi run -e local-recipes fetch-cwe-catalog --json         # machine-readable
    pixi run -e local-recipes fetch-cwe-catalog --db PATH      # write to alt DB
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _http  # noqa: E402
import conda_forge_atlas as atlas  # noqa: E402

CWE_URL = "https://cwe.mitre.org/data/csv/1000.csv.zip"
_SEED_PATH = _SCRIPTS_DIR.parent / "data" / "cwe_categories_seed.json"


def _load_seed_mapping(path: Path = _SEED_PATH) -> dict[str, str]:
    """Load the committed CWE-ID → cf_atlas_category seed mapping.

    Drops the `_doc` metadata key (present for human readability, not data).
    Returns {} if file missing — callers degrade to 'Other' for every CWE.
    """
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def fetch_cwe_zip(*, timeout: int = 60) -> bytes:
    """Pull the CWE Research Concepts zip. Returns raw zip bytes."""
    return _http.fetch_with_fallback(
        [CWE_URL],
        timeout=timeout,
        user_agent="conda-forge-expert-cwe/1.0",
    )


def parse_cwe_csv(zip_bytes: bytes) -> list[dict[str, str]]:
    """Extract the inner CSV from the zip + parse into row dicts.

    MITRE ships the CSV inside the zip without a fixed inner-filename
    convention; we use the first .csv file in the archive.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_name = next(
            (n for n in zf.namelist() if n.lower().endswith(".csv")),
            None,
        )
        if csv_name is None:
            raise RuntimeError(
                "CWE zip contains no .csv file (got: "
                f"{zf.namelist()!r})"
            )
        with zf.open(csv_name) as fh:
            # utf-8-sig strips a BOM if MITRE ever ships one (they have
            # historically) — without it, the first DictReader key would be
            # "﻿CWE-ID" and every row.get("CWE-ID") would silently miss.
            text = fh.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def upsert_cwe_rows(
    conn: sqlite3.Connection,
    rows: list[dict[str, str]],
    seed: dict[str, str],
    *,
    fetched_at: int | None = None,
) -> dict[str, int | str | None]:
    """Upsert MITRE CWE rows into `cwe_categories`.

    Builds `cwe_id = "CWE-" + row["CWE-ID"]` to match vdb's CVE-record
    `cweId` format. Applies seed mapping; unmapped CWEs get 'Other'.
    Idempotent — re-running produces zero net diff.
    """
    if fetched_at is None:
        fetched_at = int(time.time())

    rows_before = conn.execute("SELECT COUNT(*) FROM cwe_categories").fetchone()[0]
    rows_seeded = 0
    rows_other = 0
    rows_skipped = 0

    sql = (
        "INSERT OR REPLACE INTO cwe_categories "
        "(cwe_id, cwe_name, cf_atlas_category, cwe_abstraction, source_fetched_at) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    conn.execute("BEGIN")
    try:
        for row in rows:
            raw_id = (row.get("CWE-ID") or "").strip()
            if not raw_id:
                rows_skipped += 1
                continue
            # Defensive: MITRE ships bare integers today, but guard against a
            # future format shift to pre-prefixed IDs ("CWE-79"). Strip any
            # case-insensitive existing prefix before re-adding canonical.
            if raw_id[:4].upper() == "CWE-":
                raw_id = raw_id[4:]
            cwe_id = f"CWE-{raw_id}"
            cwe_name = (row.get("Name") or "").strip() or None
            cwe_abstraction = (row.get("Weakness Abstraction") or "").strip() or None
            if cwe_id in seed:
                category = seed[cwe_id]
                rows_seeded += 1
            else:
                category = "Other"
                rows_other += 1
            conn.execute(
                sql,
                (cwe_id, cwe_name, category, cwe_abstraction, fetched_at),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    rows_after = conn.execute("SELECT COUNT(*) FROM cwe_categories").fetchone()[0]
    return {
        "rows_in_feed": len(rows),
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_new": rows_after - rows_before,
        "rows_seeded": rows_seeded,
        "rows_other": rows_other,
        "rows_skipped": rows_skipped,
    }


def refresh_cwe(
    db_path: Path | None = None,
    *,
    dry_run: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """End-to-end refresh: fetch the zip, parse, upsert into the atlas DB."""
    t0 = time.monotonic()
    zip_bytes = fetch_cwe_zip(timeout=timeout)
    rows = parse_cwe_csv(zip_bytes)
    seed = _load_seed_mapping()

    result: dict[str, Any] = {
        "url": CWE_URL,
        "rows_in_feed": len(rows),
        "seed_entries": len(seed),
        "dry_run": dry_run,
    }

    if dry_run:
        result["duration_seconds"] = round(time.monotonic() - t0, 2)
        return result

    path = db_path or atlas.DB_PATH
    conn = atlas.open_db(path=path)
    try:
        atlas.init_schema(conn)
        stats = upsert_cwe_rows(conn, rows, seed)
    finally:
        conn.close()

    result.update(stats)
    result["db_path"] = str(path)
    result["duration_seconds"] = round(time.monotonic() - t0, 2)
    return result


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fetch-cwe-catalog",
        description="Refresh the MITRE CWE Research Concepts table in cf_atlas.db. "
                    "~640 KB zip pull from cwe.mitre.org; runs in seconds.",
    )
    p.add_argument("--db", type=Path, default=None,
                   help=f"Path to atlas DB (default: {atlas.DB_PATH})")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch + parse the feed, but skip the DB write.")
    p.add_argument("--timeout", type=int, default=60,
                   help="HTTP timeout in seconds (default: 60).")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="Emit the result as JSON (default: human-readable).")
    return p


def _print_human(result: dict[str, Any]) -> None:
    print(f"CWE catalog refresh — {result['url']}")
    print(f"  rows_in_feed    : {result['rows_in_feed']:,}")
    print(f"  seed_entries    : {result.get('seed_entries', 0):,}")
    if result.get("dry_run"):
        print("  (dry-run: no DB write)")
    else:
        before = result.get("rows_before", 0)
        after = result.get("rows_after", 0)
        new = result.get("rows_new", 0)
        seeded = result.get("rows_seeded", 0)
        other = result.get("rows_other", 0)
        skipped = result.get("rows_skipped", 0)
        print(f"  rows_before     : {before:,}")
        print(f"  rows_after      : {after:,}")
        print(f"  net new         : {new:+,}")
        print(f"  rows_seeded     : {seeded:,}  (mapped to a cf_atlas category)")
        print(f"  rows_other      : {other:,}  (defaulted to 'Other')")
        print(f"  rows_skipped    : {skipped:,}")
        print(f"  db_path         : {result.get('db_path')}")
    print(f"  duration        : {result.get('duration_seconds')}s")


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    try:
        result = refresh_cwe(
            db_path=args.db,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    except Exception as e:
        if args.as_json:
            print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        else:
            print(f"CWE fetch FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
