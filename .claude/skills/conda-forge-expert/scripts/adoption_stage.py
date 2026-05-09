#!/usr/bin/env python3
"""
adoption-stage — Classify package(s) into a lifecycle stage based on
release cadence (Phase I) + age (Phase B) + downloads (Phase F).

Stages:
  - bleeding-edge : ≥3 releases in last 30 days; high churn
  - stable        : 1-2 releases in last 30 days; active maintenance
  - mature        : last release 30-365 days ago; low cadence; sustained downloads
  - declining     : last release 365-730 days ago; unmaintained but not abandoned
  - silent        : no release in last 730 days; effectively abandoned
  - unknown       : insufficient data (no per-version history yet)

CLI:
  adoption-stage [--package NAME | --maintainer HANDLE] [--limit N] [--json]

Pixi:
  pixi run -e local-recipes adoption-stage -- --package wagtail
  pixi run -e local-recipes adoption-stage -- --maintainer rxm7706
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


def _classify(latest_upload_age_days: int | None,
              releases_30d: int,
              total_versions: int) -> str:
    if latest_upload_age_days is None and total_versions == 0:
        return "unknown"
    age = latest_upload_age_days or 99999
    if age > 730:
        return "silent"
    if age > 365:
        return "declining"
    if releases_30d >= 3:
        return "bleeding-edge"
    if releases_30d >= 1:
        return "stable"
    if age <= 365:
        # Active enough not to be declining, but no recent release
        return "mature"
    return "unknown"


def query(*, package: str | None, maintainer: str | None, limit: int
          ) -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    now = int(dt.datetime.now().timestamp())
    cut30 = now - 30 * 86400

    base = """
        SELECT
            p.conda_name, p.latest_conda_version, p.latest_conda_upload,
            p.total_downloads, p.latest_version_downloads,
            (SELECT COUNT(*) FROM package_version_downloads pvd
             WHERE pvd.conda_name = p.conda_name) AS total_versions,
            (SELECT COUNT(*) FROM package_version_downloads pvd
             WHERE pvd.conda_name = p.conda_name AND pvd.upload_unix >= ?
            ) AS releases_30d,
            (SELECT MIN(pvd.upload_unix) FROM package_version_downloads pvd
             WHERE pvd.conda_name = p.conda_name) AS first_upload_unix
        FROM packages p
    """
    where = ["p.conda_name IS NOT NULL"]
    params: list[Any] = [cut30]
    if package:
        where.append("p.conda_name = ?")
        params.append(package)
    if maintainer:
        base += (
            " JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
            " JOIN maintainers m ON m.id = pm.maintainer_id "
        )
        where.append("LOWER(m.handle) = LOWER(?)")
        params.append(maintainer)
    if where:
        base += "WHERE " + " AND ".join(where) + " "
    base += "ORDER BY p.total_downloads DESC LIMIT ?"
    params.append(limit)

    rows: list[dict[str, Any]] = []
    for r in conn.execute(base, params):
        d = dict(r)
        age_days = ((now - r["latest_conda_upload"]) // 86400
                    if r["latest_conda_upload"] else None)
        d["age_days"] = age_days
        d["stage"] = _classify(age_days, r["releases_30d"] or 0,
                                r["total_versions"] or 0)
        if r["first_upload_unix"]:
            d["lifetime_days"] = (now - r["first_upload_unix"]) // 86400
        else:
            d["lifetime_days"] = None
        rows.append(d)
    return rows


def render_table(rows: list[dict[str, Any]], maintainer: str | None) -> str:
    if not rows:
        return "No matching packages.\n"
    out: list[str] = []
    title = "Adoption stage"
    if maintainer:
        title += f" — {maintainer}"
    out.append(f"  {title}  ({len(rows)} package(s))")
    out.append("  " + "─" * 120)
    out.append(
        f"  {'PACKAGE':<37} {'VERSION':<14} {'AGE':>6} {'30d':>4} "
        f"{'TOTAL_V':>7} {'DOWNLOADS':>11} {'STAGE':<14}"
    )
    out.append("  " + "─" * 120)
    for r in rows:
        ver = (r.get("latest_conda_version") or "?")[:13]
        age = r.get("age_days") or 0
        rel30 = r.get("releases_30d") or 0
        tv = r.get("total_versions") or 0
        dl = r.get("total_downloads") or 0
        out.append(
            f"  {r['conda_name']:<37} {ver:<14} {age:>4}d {rel30:>4} "
            f"{tv:>7} {dl:>11,} {r['stage']:<14}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Adoption-stage classifier.")
    parser.add_argument("--package", default=None, help="One package")
    parser.add_argument("--maintainer", default=None, help="Restrict to maintainer")
    parser.add_argument("--limit", type=int, default=30,
                        help="Max packages (default 30)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of table")
    args = parser.parse_args()

    rows = query(package=args.package, maintainer=args.maintainer,
                 limit=args.limit)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.maintainer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
