#!/usr/bin/env python3
"""
version-downloads — Per-version download breakdown for one conda-forge package.

Reads from `package_version_downloads` (Phase I). Sorts by upload date by
default; supports --by-downloads to rank by adoption instead.

CLI:
  version-downloads <name> [--limit N] [--by-downloads] [--json]

Pixi:
  pixi run -e local-recipes version-downloads -- llms-py
  pixi run -e local-recipes version-downloads -- numpy --limit 50
  pixi run -e local-recipes version-downloads -- cachetools --by-downloads
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"


def query(name: str, limit: int, by_downloads: bool) -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    order = "total_downloads DESC" if by_downloads else "upload_unix DESC"
    sql = (
        "SELECT version, file_count, total_downloads, upload_unix, fetched_at "
        "FROM package_version_downloads WHERE conda_name = ? "
        f"ORDER BY {order} LIMIT ?"
    )
    return [dict(r) for r in conn.execute(sql, (name, limit))]


def render_table(rows: list[dict[str, Any]], name: str, by_downloads: bool) -> str:
    if not rows:
        return (f"No per-version data for {name}. Run `pixi run -e local-recipes "
                f"build-cf-atlas` (with TTL-expired Phase F) to populate.\n")
    out: list[str] = []
    sort_label = "by downloads" if by_downloads else "newest first"
    out.append(f"  Per-version downloads — {name}  ({len(rows)} version(s), {sort_label})")
    out.append("  " + "─" * 80)
    out.append(f"  {'VERSION':<14} {'UPLOADED':<11} {'AGE':>6}  {'FILES':>6}  {'DOWNLOADS':>11}")
    out.append("  " + "─" * 80)
    now = int(dt.datetime.now().timestamp())
    for r in rows:
        ts = r.get("upload_unix")
        upload_iso = dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "?"
        age = (now - ts) // 86400 if ts else 0
        out.append(
            f"  {r['version']:<14} {upload_iso:<11} {age:>4}d  {r['file_count']:>6}  "
            f"{r['total_downloads']:>11,}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Per-version download breakdown.")
    parser.add_argument("name", help="conda_name")
    parser.add_argument("--limit", type=int, default=30, help="max versions (default 30)")
    parser.add_argument("--by-downloads", action="store_true", dest="by_downloads",
                        help="Rank by total_downloads DESC instead of upload_unix DESC")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of table")
    args = parser.parse_args()

    rows = query(args.name, args.limit, args.by_downloads)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.name, args.by_downloads))
    return 0


if __name__ == "__main__":
    sys.exit(main())
