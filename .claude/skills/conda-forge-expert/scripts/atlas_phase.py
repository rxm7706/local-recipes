#!/usr/bin/env python3
"""
atlas-phase — invoke a single cf_atlas phase against the existing DB.

Useful when you've already built the atlas once and want to refresh just
one phase (e.g. nightly Phase H to pull new PyPI versions, or rerun Phase
F after switching `PHASE_F_SOURCE`). Avoids the ~30-45 min cost of a full
`build-cf-atlas` run.

Usage:
  atlas-phase <PHASE_ID> [--reset-ttl]

  PHASE_ID    one of B, B.5, B.6, C, C.5, D, E, E.5, F, G, G', H, J, K, L, M, N
  --reset-ttl forcibly NULL the phase's `*_fetched_at` timestamps before
              running, so the phase re-processes every eligible row.
              (Applies only to TTL-gated phases: F, G, G', H, K, L.)
  --list      list known phases and exit.

Examples:
  pixi run -e local-recipes atlas-phase H
  pixi run -e local-recipes atlas-phase H --reset-ttl
  PHASE_H_SOURCE=cf-graph pixi run -e local-recipes atlas-phase H
  pixi run -e local-recipes atlas-phase F
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import conda_forge_atlas as cfa  # type: ignore[import-not-found]


# Phases that gate on per-row `*_fetched_at` timestamps. Used by
# --reset-ttl to NULL the relevant columns. Maps `phase_id` (upper) to a
# list of `(column, scope_predicate)` tuples. The predicate scopes the
# UPDATE to rows the phase would actually process — without it, a bare
# `UPDATE packages SET col = NULL` touches every row (including ones
# where the column is already NULL because the phase wouldn't pick them
# up anyway). Keep predicates in sync with each phase's eligibility SQL.
_TTL_GATED: dict[str, list[tuple[str, str]]] = {
    "F":  [("downloads_fetched_at",       "conda_name IS NOT NULL")],
    "G":  [("vdb_scanned_at",             "conda_name IS NOT NULL")],
    "G'": [],  # Phase G' resets via `package_version_vulns` row absence
    "H":  [("pypi_version_fetched_at",    "pypi_name IS NOT NULL")],
    "K":  [("github_version_fetched_at",  "conda_name IS NOT NULL")],
    "L":  [],  # Phase L tracks `*_fetched_at` per registry; reset is per-source
}


def _reset_ttl(conn, phase_id: str) -> int:
    """NULL the phase's `*_fetched_at` column(s), scoped to rows the phase
    would actually pick up. Returns rows touched.
    """
    specs = _TTL_GATED.get(phase_id.upper(), [])
    if not specs:
        print(f"  --reset-ttl: phase {phase_id!r} has no simple TTL column; no-op.")
        return 0
    touched = 0
    for col, scope in specs:
        cur = conn.execute(
            f"UPDATE packages SET {col} = NULL WHERE {scope}"
        )
        touched += cur.rowcount or 0
    conn.commit()
    return touched


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a single cf_atlas phase against the existing DB."
    )
    parser.add_argument("phase_id", nargs="?",
                        help="Phase to run (e.g. B, F, H, G')")
    parser.add_argument("--reset-ttl", action="store_true",
                        help="NULL the phase's *_fetched_at column(s) first")
    parser.add_argument("--list", action="store_true",
                        help="List known phases and exit")
    args = parser.parse_args()

    if args.list or not args.phase_id:
        print("Known phases:")
        for name, fn in cfa.PHASES:
            print(f"  {name:5s}  {fn.__name__}")
        return 0 if args.list else 2

    try:
        name, _ = cfa.get_phase(args.phase_id)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    conn = cfa.open_db()
    cfa.init_schema(conn)
    print(f"  DB: {cfa.DB_PATH}")
    print(f"  Schema version: {cfa.SCHEMA_VERSION}")

    if args.reset_ttl:
        touched = _reset_ttl(conn, name)
        if touched:
            print(f"  --reset-ttl: cleared timestamps on {touched:,} row(s)")

    result = cfa.run_single_phase(name, conn)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
