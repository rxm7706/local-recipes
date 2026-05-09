#!/usr/bin/env python3
"""
whodepends — Dependency graph queries against cf_atlas (Phase J data).

Two directions:
  * forward (default): show packages that <name> depends on
  * --reverse: show packages that depend on <name>

CLI:
  whodepends <name> [--reverse] [--type build|host|run|test] [--limit N] [--json]

Pixi:
  pixi run -e local-recipes whodepends -- numpy --reverse --limit 20
  pixi run -e local-recipes whodepends -- llms-py
  pixi run -e local-recipes whodepends -- opentelemetry-api --reverse --type run
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


def query(name: str, reverse: bool, req_type: str | None, limit: int) -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}. Run: build-cf-atlas",
              file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    where = []
    params: list[Any] = []
    col_filter = "target_conda_name" if reverse else "source_conda_name"
    col_return = "source_conda_name" if reverse else "target_conda_name"
    where.append(f"{col_filter} = ?")
    params.append(name)
    if req_type:
        where.append("requirement_type = ?")
        params.append(req_type)

    sql = (
        f"SELECT d.{col_return} AS other, d.requirement_type, d.pin_spec, "
        "       p.latest_conda_version, p.total_downloads, "
        "       p.vuln_critical_affecting_current, p.vuln_high_affecting_current, "
        "       p.feedstock_archived "
        "FROM dependencies d "
        f"LEFT JOIN packages p ON p.conda_name = d.{col_return} "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY d.requirement_type, d.target_conda_name "
        "LIMIT ?"
    )
    params.append(limit)
    rows = [dict(r) for r in conn.execute(sql, params)]
    return rows


def render_table(rows: list[dict[str, Any]], name: str, reverse: bool) -> str:
    if not rows:
        direction = "depends on" if not reverse else "is depended on by"
        return f"No edges found: {name} {direction} nothing.\n"
    direction = "depends on" if not reverse else "← depended on by"
    out: list[str] = []
    out.append(f"  {name} {direction}  ({len(rows)} edge(s))")
    out.append("  " + "─" * 110)
    out.append(
        f"  {'PACKAGE':<35} {'TYPE':<6} {'PIN':<22} "
        f"{'VERSION':<14} {'DOWNLOADS':>11}  {'C/H':>6}  ARCH"
    )
    out.append("  " + "─" * 110)
    for r in rows:
        ver = (r.get("latest_conda_version") or "—")[:13]
        dl = r.get("total_downloads")
        dl_s = f"{dl:,}" if dl is not None else "—"
        c = r.get("vuln_critical_affecting_current") or 0
        h = r.get("vuln_high_affecting_current") or 0
        risk = f"{c}/{h}" if (c or h) else "—"
        arch = "y" if r.get("feedstock_archived") == 1 else ""
        pin = (r.get("pin_spec") or "")[:21]
        out.append(
            f"  {r['other']:<35} {r['requirement_type']:<6} {pin:<22} "
            f"{ver:<14} {dl_s:>11}  {risk:>6}  {arch}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query the cf_atlas dependency graph (Phase J data)."
    )
    parser.add_argument("name", help="Package name (conda_name)")
    parser.add_argument("--reverse", action="store_true",
                        help="Reverse lookup: show packages that depend on <name>")
    parser.add_argument("--type", dest="req_type", default=None,
                        choices=["build", "host", "run", "test"],
                        help="Filter to a single requirement_type")
    parser.add_argument("--limit", type=int, default=50,
                        help="Maximum rows (default 50)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of a formatted table")
    args = parser.parse_args()

    rows = query(args.name, args.reverse, args.req_type, args.limit)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.name, args.reverse))
    return 0


if __name__ == "__main__":
    sys.exit(main())
