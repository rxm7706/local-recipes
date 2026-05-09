#!/usr/bin/env python3
"""
release-cadence — Release cadence analysis from Phase I per-version data.

For each package (or one specified by --package), counts releases in
rolling 30/90/365-day windows and classifies the trend:
  - 'accelerating' : recent window has >= 1.5x older window
  - 'stable'       : within 0.7x–1.5x ratio
  - 'decelerating' : recent < 0.7x older
  - 'one-version'  : only one release total
  - 'silent'       : no releases in last 365 days

CLI:
  release-cadence [--package NAME | --maintainer HANDLE] [--limit N] [--json]

Pixi:
  pixi run -e local-recipes release-cadence -- --package wagtail
  pixi run -e local-recipes release-cadence -- --maintainer rxm7706 --limit 30
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


def _classify(r30: int, r90: int, r365: int) -> str:
    if r365 == 0:
        return "silent"
    # Use 30d-vs-prior-30d-thru-90d as accel signal
    older_60 = max(0, r90 - r30)
    if r30 == 0 and older_60 == 0:
        # Look at older history
        if r365 == 1:
            return "one-version"
        return "decelerating"
    if older_60 == 0:
        return "accelerating"
    ratio = r30 / older_60
    if ratio >= 1.5:
        return "accelerating"
    if ratio <= 0.7:
        return "decelerating"
    return "stable"


def query(*, package: str | None, maintainer: str | None, limit: int) -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    now = int(dt.datetime.now().timestamp())
    cut30 = now - 30 * 86400
    cut90 = now - 90 * 86400
    cut365 = now - 365 * 86400

    base = """
        SELECT
            pvd.conda_name,
            COUNT(*) AS total_versions,
            SUM(CASE WHEN pvd.upload_unix >= ? THEN 1 ELSE 0 END) AS releases_30d,
            SUM(CASE WHEN pvd.upload_unix >= ? THEN 1 ELSE 0 END) AS releases_90d,
            SUM(CASE WHEN pvd.upload_unix >= ? THEN 1 ELSE 0 END) AS releases_365d,
            MAX(pvd.upload_unix) AS last_upload,
            MIN(pvd.upload_unix) AS first_upload,
            (SELECT version FROM package_version_downloads WHERE conda_name = pvd.conda_name ORDER BY upload_unix DESC LIMIT 1) AS latest_v
        FROM package_version_downloads pvd
    """
    where = []
    params: list[Any] = [cut30, cut90, cut365]
    if package:
        where.append("pvd.conda_name = ?")
        params.append(package)
    if maintainer:
        base += (
            " JOIN package_maintainers pm ON pm.conda_name = pvd.conda_name "
            " JOIN maintainers m ON m.id = pm.maintainer_id "
        )
        where.append("LOWER(m.handle) = LOWER(?)")
        params.append(maintainer)
    if where:
        base += "WHERE " + " AND ".join(where) + " "
    base += "GROUP BY pvd.conda_name ORDER BY releases_30d DESC, last_upload DESC LIMIT ?"
    params.append(limit)

    rows = []
    for r in conn.execute(base, params):
        d = dict(r)
        d["trend"] = _classify(d["releases_30d"], d["releases_90d"], d["releases_365d"])
        rows.append(d)
    return rows


def render_table(rows: list[dict[str, Any]], maintainer: str | None) -> str:
    if not rows:
        return ("No per-version data found. Run a Phase F refresh "
                "(`build-cf-atlas` after TTL expires) to populate.\n")
    out: list[str] = []
    title = "Release cadence"
    if maintainer:
        title += f" — {maintainer}"
    out.append(f"  {title}  ({len(rows)} package(s))")
    out.append("  " + "─" * 110)
    out.append(
        f"  {'PACKAGE':<37} {'TOTAL':>6} {'30d':>4} {'90d':>4} {'365d':>5} "
        f"{'LATEST':<14} {'TREND':<14}"
    )
    out.append("  " + "─" * 110)
    for r in rows:
        latest = (r.get("latest_v") or "?")[:13]
        out.append(
            f"  {r['conda_name']:<37} {r['total_versions']:>6} "
            f"{r['releases_30d']:>4} {r['releases_90d']:>4} {r['releases_365d']:>5} "
            f"{latest:<14} {r['trend']:<14}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Release cadence trend analysis.")
    parser.add_argument("--package", default=None, help="Restrict to one package")
    parser.add_argument("--maintainer", default=None, help="Restrict to packages where HANDLE is a maintainer")
    parser.add_argument("--limit", type=int, default=30, help="max packages (default 30)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of table")
    args = parser.parse_args()

    rows = query(package=args.package, maintainer=args.maintainer, limit=args.limit)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.maintainer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
