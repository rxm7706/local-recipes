#!/usr/bin/env python3
"""FIRST.org EPSS (Exploit Prediction Scoring System) fetcher (v8.6.0 Wave A).

Pulls the daily EPSS scores CSV and upserts it into the `epss_scores` table
of cf_atlas.db. Phase G / G' overlay this table on vdb's per-CVE output
(via `_load_epss_scores`) to compute per-package `vuln_max_epss_score`
and `vuln_max_epss_percentile` — operationally more meaningful than raw
Critical/High counts since EPSS quantifies exploitation probability.

Background: cf_atlas ranks vulnerability surface by Critical/High/KEV
count. A medium-severity CVE with EPSS 0.94 (worst 6% by exploitation
probability) is operationally more dangerous than a critical-severity
CVE with EPSS 0.02. FIRST publishes EPSS daily as a small (~3 MB
gzipped) CSV; pulling it directly into a side table mirrors the v8.5.3
DW13 Path C pattern.

URL: https://epss.empiricalsecurity.com/epss_scores-current.csv.gz
(Cyentia rebranded to Empirical Security; the older `epss.cyentia.com`
host redirects but the canonical hostname is `empiricalsecurity.com`.)

CSV format (verified 2026-05-23 against https://www.first.org/epss/data_stats):
  - Header comment line(s) starting with `#` carry `model_version` and
    `score_date`. The first non-`#` line is the CSV header.
  - Columns: `cve`, `epss`, `percentile`
  - Both `epss` and `percentile` are 0.0-1.0 decimals at the source.
  - ~334,567 CVEs as of May 2026.

This module normalizes `percentile` 0.0-1.0 → 0.0-100.0 at store time to
match CISA's published convention (cheaper than normalizing at every read).

Usage:
    pixi run -e local-recipes fetch-epss                # standard refresh
    pixi run -e local-recipes fetch-epss --dry-run      # fetch + parse only
    pixi run -e local-recipes fetch-epss --json         # machine-readable
    pixi run -e local-recipes fetch-epss --db PATH      # write to alt DB
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
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

EPSS_URL = "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"


def _normalize_percentile(raw: float) -> float:
    """FIRST publishes percentile as 0.0-1.0; we store 0.0-100.0."""
    return raw * 100.0


def _parse_snapshot_date(csv_text: str) -> str | None:
    """Extract `score_date` from the leading `#` header line(s).

    FIRST's CSV starts with one or two comment lines like:
        #model_version:v2025.03.14,score_date:2026-05-22T00:00:00+0000
    Returns the score_date as ISO string, or None when absent.
    """
    for line in csv_text.splitlines():
        if not line.startswith("#"):
            return None
        if "score_date:" in line:
            tail = line.split("score_date:", 1)[1]
            # value is up to the next comma OR end of line
            return tail.split(",", 1)[0].strip()
    return None


def fetch_epss_csv(*, timeout: int = 60) -> str:
    """Pull the EPSS CSV. Returns decoded text (gzip-decompressed).

    Raises RuntimeError on network failure (from `_http.fetch_with_fallback`).
    """
    raw = _http.fetch_with_fallback(
        [EPSS_URL],
        timeout=timeout,
        user_agent="conda-forge-expert-epss/1.0",
    )
    # fetch_with_fallback returns bytes by default; gunzip + utf-8 decode
    return gzip.decompress(raw).decode("utf-8")


def upsert_epss_rows(
    conn: sqlite3.Connection,
    csv_text: str,
    *,
    fetched_at: int | None = None,
) -> dict[str, int | str | None]:
    """Upsert every row in `csv_text` into the `epss_scores` table.

    Idempotent — re-running with an unchanged feed produces zero net diff
    (INSERT OR REPLACE on cve_id PK). Malformed rows (missing cve_id,
    unparseable score/percentile) are skipped + counted. Returns stats:
      - rows_in_feed  : int   — rows parsed from CSV (excluding header/comments)
      - rows_before   : int   — epss_scores rows before upsert
      - rows_after    : int   — epss_scores rows after upsert
      - rows_new      : int   — net delta (after − before)
      - rows_skipped  : int   — malformed rows skipped
      - snapshot_date : str | None — FIRST's score_date from header comment
    """
    if fetched_at is None:
        fetched_at = int(time.time())

    snapshot_date = _parse_snapshot_date(csv_text)
    rows_before = conn.execute("SELECT COUNT(*) FROM epss_scores").fetchone()[0]

    # Strip leading # comment lines before csv.DictReader sees the header
    data_lines = [line for line in csv_text.splitlines() if not line.startswith("#")]
    reader = csv.DictReader(io.StringIO("\n".join(data_lines)))

    sql = (
        "INSERT OR REPLACE INTO epss_scores "
        "(cve_id, epss_score, epss_percentile, snapshot_date, source_fetched_at) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    rows_in_feed = 0
    rows_skipped = 0
    conn.execute("BEGIN")
    try:
        for row in reader:
            rows_in_feed += 1
            cve_id = (row.get("cve") or "").strip()
            if not cve_id:
                rows_skipped += 1
                continue
            try:
                epss_score = float(row["epss"])
                epss_percentile = _normalize_percentile(float(row["percentile"]))
            except (KeyError, ValueError, TypeError):
                rows_skipped += 1
                continue
            conn.execute(
                sql,
                (cve_id, epss_score, epss_percentile, snapshot_date, fetched_at),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    rows_after = conn.execute("SELECT COUNT(*) FROM epss_scores").fetchone()[0]
    return {
        "rows_in_feed": rows_in_feed,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_new": rows_after - rows_before,
        "rows_skipped": rows_skipped,
        "snapshot_date": snapshot_date,
    }


def refresh_epss(
    db_path: Path | None = None,
    *,
    dry_run: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """End-to-end refresh: fetch the CSV, upsert into the atlas DB.

    With `dry_run=True`, fetches + parses + counts but skips DB write.
    """
    t0 = time.monotonic()
    csv_text = fetch_epss_csv(timeout=timeout)
    snapshot_date = _parse_snapshot_date(csv_text)
    rows_in_feed = sum(
        1 for line in csv_text.splitlines()
        if line and not line.startswith("#") and not line.startswith("cve,")
    )

    result: dict[str, Any] = {
        "url": EPSS_URL,
        "rows_in_feed": rows_in_feed,
        "snapshot_date": snapshot_date,
        "dry_run": dry_run,
    }

    if dry_run:
        result["duration_seconds"] = round(time.monotonic() - t0, 2)
        return result

    path = db_path or atlas.DB_PATH
    conn = atlas.open_db(path=path)
    try:
        atlas.init_schema(conn)
        stats = upsert_epss_rows(conn, csv_text)
    finally:
        conn.close()

    result.update(stats)
    result["db_path"] = str(path)
    result["duration_seconds"] = round(time.monotonic() - t0, 2)
    return result


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fetch-epss",
        description="Refresh the FIRST.org EPSS scores table in cf_atlas.db. "
                    "~3 MB gzipped CSV pull from epss.empiricalsecurity.com; "
                    "runs in ~30 s.",
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
    print(f"EPSS refresh — {result['url']}")
    print(f"  snapshot_date   : {result.get('snapshot_date')}")
    print(f"  rows_in_feed    : {result['rows_in_feed']:,}")
    if result.get("dry_run"):
        print("  (dry-run: no DB write)")
    else:
        before = result.get("rows_before", 0)
        after = result.get("rows_after", 0)
        new = result.get("rows_new", 0)
        skipped = result.get("rows_skipped", 0)
        print(f"  rows_before     : {before:,}")
        print(f"  rows_after      : {after:,}")
        print(f"  net new         : {new:+,}")
        print(f"  rows_skipped    : {skipped:,}")
        print(f"  db_path         : {result.get('db_path')}")
    print(f"  duration        : {result.get('duration_seconds')}s")


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    try:
        result = refresh_epss(
            db_path=args.db,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    except Exception as e:
        if args.as_json:
            print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        else:
            print(f"EPSS fetch FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
