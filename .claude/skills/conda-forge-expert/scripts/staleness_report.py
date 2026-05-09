#!/usr/bin/env python3
"""
staleness-report — Surface conda-forge feedstocks that haven't shipped lately.

Reads cf_atlas.db (offline) and lists active feedstocks ordered by oldest
`latest_conda_upload`. The default view picks up the kind of "should I look
at this?" question that maintainers ask quarterly: which of my feedstocks
have gone the longest without a release.

CLI:
  staleness-report [--maintainer HANDLE] [--days N] [--limit N] [--json]
                   [--all-status]

  --maintainer    Restrict to packages where HANDLE appears in the
                  recipe-maintainers list (joined via package_maintainers).
  --days          Only include feedstocks whose latest_conda_upload is
                  older than N days (default 0 = no floor; just sort).
  --limit         Cap the number of rows printed (default 25).
  --all-status    Include archived feedstocks. Default excludes them since
                  archived = explicitly retired, not stale.
  --json          Emit machine-readable JSON instead of the formatted table.

Pixi:
  pixi run -e local-recipes staleness-report
  pixi run -e local-recipes staleness-report --maintainer rxm7706 --limit 15
  pixi run -e local-recipes staleness-report --days 730 --json
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
    """Skill-scoped data directory: .claude/data/conda-forge-expert/"""
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"


def query(
    *,
    maintainer: str | None,
    min_age_days: int,
    limit: int,
    include_archived: bool,
    by_risk: bool = False,
    has_vulns: bool = False,
    bot_stuck: bool = False,
) -> list[dict[str, Any]]:
    """Run the staleness query and return result rows as dicts.

    By default sorts by oldest `latest_conda_upload`. With `by_risk=True`,
    sorts primarily by `vuln_critical_affecting_current DESC`, then `vuln_high
    _affecting_current DESC`, then by stalest upload — surfaces feedstocks
    that combine "old" with "actively risky." `has_vulns=True` filters to
    feedstocks where Critical or High CVEs affect the current version.
    """
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}. Run: build-cf-atlas",
              file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cutoff_ts: int | None = None
    if min_age_days > 0:
        cutoff_ts = int(dt.datetime.now().timestamp()) - min_age_days * 86400

    where = [
        "p.conda_name IS NOT NULL",
        "p.latest_status = 'active'",
        "p.latest_conda_upload IS NOT NULL",
    ]
    params: list[Any] = []

    if not include_archived:
        where.append("COALESCE(p.feedstock_archived, 0) = 0")
    if cutoff_ts is not None:
        where.append("p.latest_conda_upload < ?")
        params.append(cutoff_ts)
    if has_vulns:
        where.append(
            "(COALESCE(p.vuln_critical_affecting_current, 0) > 0 "
            " OR COALESCE(p.vuln_high_affecting_current, 0) > 0)"
        )
    if bot_stuck:
        where.append("COALESCE(p.bot_version_errors_count, 0) > 0")

    order_clause = (
        "COALESCE(p.vuln_critical_affecting_current, 0) DESC, "
        "COALESCE(p.vuln_high_affecting_current, 0) DESC, "
        "COALESCE(p.vuln_kev_affecting_current, 0) DESC, "
        "p.latest_conda_upload ASC"
        if by_risk
        else "p.latest_conda_upload ASC"
    )

    select_cols = (
        "p.conda_name, p.feedstock_name, p.latest_conda_version, "
        "p.latest_conda_upload, p.total_downloads, "
        "p.recipe_format, p.feedstock_archived, "
        "p.vuln_total, p.vuln_critical_affecting_current, "
        "p.vuln_high_affecting_current, p.vuln_kev_affecting_current, "
        "p.vdb_scanned_at"
    )

    if maintainer:
        sql = (
            f"SELECT {select_cols} "
            "FROM packages p "
            "JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
            "JOIN maintainers m ON m.id = pm.maintainer_id "
            f"WHERE {' AND '.join(where)} "
            "  AND LOWER(m.handle) = LOWER(?) "
            f"ORDER BY {order_clause} "
            "LIMIT ?"
        )
        params.append(maintainer)
        params.append(limit)
    else:
        sql = (
            f"SELECT {select_cols} "
            "FROM packages p "
            f"WHERE {' AND '.join(where)} "
            f"ORDER BY {order_clause} "
            "LIMIT ?"
        )
        params.append(limit)

    rows = [dict(r) for r in cur.execute(sql, params)]
    now = int(dt.datetime.now().timestamp())
    for r in rows:
        ts = r["latest_conda_upload"]
        r["age_days"] = (now - ts) // 86400 if ts else None
        r["uploaded_iso"] = (
            dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else None
        )
    return rows


def render_table(rows: list[dict[str, Any]], maintainer: str | None,
                 by_risk: bool = False) -> str:
    """Render a fixed-width terminal table; designed for ~140-col terminals."""
    if not rows:
        scope = f" maintained by {maintainer}" if maintainer else ""
        return f"No matching feedstocks found{scope}.\n"

    out: list[str] = []
    title = "Staleness report"
    if maintainer:
        title += f" — {maintainer}"
    if by_risk:
        title += "  [ordered by risk]"
    out.append(f"  {title}  ({len(rows)} row(s))")
    out.append("  " + "─" * 132)
    out.append(
        f"  {'PACKAGE':<37} {'VERSION':<14} {'UPLOADED':<11} "
        f"{'AGE':>6}  {'DOWNLOADS':>11}  {'C/H/KEV':>9}  {'TOTAL':>6}  "
        f"{'FORMAT':<11} ARCH"
    )
    out.append("  " + "─" * 132)
    for r in rows:
        ver = (r.get("latest_conda_version") or "?")[:13]
        dl = r.get("total_downloads")
        dl_s = f"{dl:,}" if dl is not None else "—"
        fmt = r.get("recipe_format") or "—"
        arch = "y" if r.get("feedstock_archived") == 1 else ""
        c = r.get("vuln_critical_affecting_current") or 0
        h = r.get("vuln_high_affecting_current") or 0
        k = r.get("vuln_kev_affecting_current") or 0
        risk = (
            "—" if r.get("vdb_scanned_at") is None else f"{c}/{h}/{k}"
        )
        total = r.get("vuln_total")
        total_s = f"{total}" if total is not None else "—"
        out.append(
            f"  {r['conda_name']:<37} {ver:<14} {r['uploaded_iso'] or '?':<11} "
            f"{r.get('age_days') or 0:>4}d  {dl_s:>11}  {risk:>9}  {total_s:>6}  "
            f"{fmt:<11} {arch}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List conda-forge feedstocks ordered by stalest "
                    "(oldest latest_conda_upload). Reads cf_atlas.db offline."
    )
    parser.add_argument("--maintainer", default=None,
                        help="Filter to feedstocks where this handle is a maintainer")
    parser.add_argument("--days", type=int, default=0, dest="min_age_days",
                        help="Only show feedstocks older than N days (default 0)")
    parser.add_argument("--limit", type=int, default=25,
                        help="Maximum rows to return (default 25)")
    parser.add_argument("--all-status", action="store_true", dest="include_archived",
                        help="Include archived feedstocks (default: skip)")
    parser.add_argument("--by-risk", action="store_true", dest="by_risk",
                        help="Sort by Critical/High/KEV affecting current version, "
                             "tiebroken by stalest upload (requires Phase G data)")
    parser.add_argument("--has-vulns", action="store_true", dest="has_vulns",
                        help="Filter to feedstocks with non-zero Critical or High "
                             "CVEs affecting current version (requires Phase G data)")
    parser.add_argument("--bot-stuck", action="store_true", dest="bot_stuck",
                        help="Filter to feedstocks where the conda-forge bot has "
                             "failed to land a version-update PR at least once "
                             "(requires Phase M data)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of a formatted table")
    args = parser.parse_args()

    rows = query(
        maintainer=args.maintainer,
        min_age_days=args.min_age_days,
        limit=args.limit,
        include_archived=args.include_archived,
        by_risk=args.by_risk,
        has_vulns=args.has_vulns,
        bot_stuck=args.bot_stuck,
    )
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.maintainer, by_risk=args.by_risk))
    return 0


if __name__ == "__main__":
    sys.exit(main())
