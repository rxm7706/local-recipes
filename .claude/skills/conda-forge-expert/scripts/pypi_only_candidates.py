#!/usr/bin/env python3
"""
pypi-only-candidates — List PyPI projects that have no conda-forge equivalent.

Reads the `pypi_universe` side table (populated by Phase D's TTL-gated
universe upsert, schema v20+) and joins LEFT-OUTER to `packages.pypi_name`
to find PyPI projects with no matching conda-forge row.

Use cases (admin persona):
  • Channel-growth triage — which PyPI projects might be worth packaging?
  • Coordination with conda-forge admins on naming conflicts.
  • Spot newly-popular PyPI projects (high last_serial) that the channel
    hasn't picked up yet.

CLI:
  pypi-only-candidates [--limit N] [--min-serial M] [--json]

Pixi:
  pixi run -e local-recipes pypi-only-candidates -- --limit 50
  pixi run -e local-recipes pypi-only-candidates -- --min-serial 100000000 --json

If `pypi_universe` is empty, prints an actionable hint to run Phase D
first and exits with rc=0 (informational, not an error).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"


def fetch_candidates(
    conn: sqlite3.Connection,
    limit: int,
    min_serial: int,
) -> list[dict[str, Any]]:
    """Return PyPI projects with no conda-forge equivalent.

    Ordered by `last_serial DESC` — newer / more-active projects first.
    Caller is responsible for the connection's lifetime.
    """
    rows = list(conn.execute(
        """
        SELECT pu.pypi_name, pu.last_serial, pu.fetched_at
        FROM pypi_universe pu
        LEFT JOIN packages p ON p.pypi_name = pu.pypi_name
        WHERE p.conda_name IS NULL
          AND pu.last_serial >= ?
        ORDER BY pu.last_serial DESC
        LIMIT ?
        """,
        (min_serial, limit),
    ))
    return [
        {
            "pypi_name": r[0],
            "last_serial": r[1],
            "fetched_at": r[2],
        }
        for r in rows
    ]


def _universe_is_populated(conn: sqlite3.Connection) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM pypi_universe LIMIT 1"
    ).fetchone())


def render_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "  No matching PyPI-only projects.\n"
    out = []
    out.append(f"  {'PYPI NAME':<40} {'SERIAL':>14}  FETCHED_AT")
    out.append("  " + "─" * 80)
    for r in rows:
        out.append(
            f"  {r['pypi_name']:<40} {r['last_serial'] or 0:>14,}  "
            f"{r['fetched_at'] or 0}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List PyPI projects that don't have a conda-forge equivalent."
    )
    parser.add_argument("--limit", type=int, default=100,
                        help="Maximum rows to return (default 100)")
    parser.add_argument("--min-serial", type=int, default=0,
                        help="Filter to projects with last_serial >= N "
                             "(rough activity proxy; default 0)")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON list instead of a text table")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n"
        )
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Surface empty-universe state with an actionable hint rather than an
    # empty result. Universe is populated by Phase D's universe-upsert
    # branch (TTL-gated, default 7d). Operators who only ran the lean
    # daily Phase D see this until the first weekly universe refresh.
    if not _universe_is_populated(conn):
        sys.stdout.write(
            "  pypi_universe is empty. Run "
            "`pixi run -e local-recipes atlas-phase D` to populate it "
            "(the universe upsert branch is TTL-gated; the first run on a "
            "fresh atlas always upserts).\n"
        )
        return 0

    rows = fetch_candidates(conn, args.limit, args.min_serial)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
