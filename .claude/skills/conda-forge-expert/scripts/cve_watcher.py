#!/usr/bin/env python3
"""
cve-watcher — Diff vuln_history snapshots to surface "what's new this week."

Compares the latest Phase G snapshot against another (default: 7 days back)
and reports packages whose Critical/High/KEV-affecting-current counts changed.

CLI:
  cve-watcher [--maintainer HANDLE] [--since-days N] [--severity C|H|K]
              [--only-increases] [--limit N] [--json]

Pixi:
  pixi run -e local-recipes cve-watcher
  pixi run -e local-recipes cve-watcher --maintainer rxm7706 --since-days 7
  pixi run -e local-recipes cve-watcher --only-increases --severity C
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


def query(*, maintainer: str | None, since_days: int, severity: str,
          only_increases: bool, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    snapshots = [r[0] for r in cur.execute(
        "SELECT DISTINCT snapshot_at FROM vuln_history ORDER BY snapshot_at DESC"
    )]
    if not snapshots:
        return [], {"error": "no Phase G snapshots yet — run build-cf-atlas first"}
    if len(snapshots) < 2:
        return [], {
            "latest_snapshot_at": snapshots[0],
            "older_snapshot_at": snapshots[0],
            "snapshots_available": 1,
            "note": "only one snapshot available; nothing to diff",
        }
    latest_ts = snapshots[0]
    target_ts_floor = latest_ts - since_days * 86400
    # Pick the most recent snapshot strictly older than the floor. If
    # since_days is 0/negative, fall through to the immediate-prior snapshot.
    older_candidates = [s for s in snapshots if s < target_ts_floor]
    if older_candidates:
        older_ts = older_candidates[0]
    else:
        # No snapshot old enough; use the second-most-recent as the fallback.
        older_ts = snapshots[1]

    sev_col = {
        "C": "vuln_critical_affecting_current",
        "H": "vuln_high_affecting_current",
        "K": "vuln_kev_affecting_current",
        "T": "vuln_total",
    }[severity]

    base_sql = f"""
        SELECT
            l.conda_name,
            COALESCE(l.{sev_col}, 0) AS now_v,
            COALESCE(o.{sev_col}, 0) AS then_v,
            (COALESCE(l.{sev_col}, 0) - COALESCE(o.{sev_col}, 0)) AS delta,
            p.latest_conda_version, p.total_downloads
        FROM vuln_history l
        LEFT JOIN vuln_history o
          ON o.conda_name = l.conda_name AND o.snapshot_at = ?
        LEFT JOIN packages p ON p.conda_name = l.conda_name
        WHERE l.snapshot_at = ?
    """
    params: list[Any] = [older_ts, latest_ts]

    if only_increases:
        base_sql += " AND (COALESCE(l." + sev_col + ", 0) - COALESCE(o." + sev_col + ", 0)) > 0"
    else:
        base_sql += " AND COALESCE(l." + sev_col + ", 0) != COALESCE(o." + sev_col + ", 0)"

    if maintainer:
        base_sql = base_sql.replace(
            "FROM vuln_history l",
            "FROM vuln_history l "
            "JOIN package_maintainers pm ON pm.conda_name = l.conda_name "
            "JOIN maintainers m ON m.id = pm.maintainer_id"
        )
        base_sql += " AND LOWER(m.handle) = LOWER(?)"
        params.append(maintainer)

    base_sql += " ORDER BY ABS(delta) DESC, l.conda_name LIMIT ?"
    params.append(limit)

    rows = [dict(r) for r in cur.execute(base_sql, params)]
    meta = {
        "latest_snapshot_at": latest_ts,
        "older_snapshot_at": older_ts,
        "since_days": since_days,
        "severity": severity,
        "snapshots_available": len(snapshots),
    }
    return rows, meta


def render_table(rows: list[dict[str, Any]], meta: dict[str, Any],
                 maintainer: str | None) -> str:
    if "error" in meta:
        return f"Error: {meta['error']}\n"
    if "note" in meta:
        return f"({meta['note']})\n"
    if not rows:
        return f"No changes since {dt.datetime.fromtimestamp(meta['older_snapshot_at']).strftime('%Y-%m-%d')}.\n"

    out: list[str] = []
    sev_label = {"C": "Critical", "H": "High", "K": "KEV", "T": "Total"}[meta["severity"]]
    title = f"CVE delta — {sev_label}-affecting-current"
    if maintainer:
        title += f" — {maintainer}"
    title += f" ({len(rows)} change(s))"
    out.append(f"  {title}")
    older = dt.datetime.fromtimestamp(meta["older_snapshot_at"]).strftime("%Y-%m-%d %H:%M")
    newer = dt.datetime.fromtimestamp(meta["latest_snapshot_at"]).strftime("%Y-%m-%d %H:%M")
    out.append(f"  comparing {older}  →  {newer}  ({meta['snapshots_available']} snapshots in DB)")
    out.append("  " + "─" * 100)
    out.append(f"  {'PACKAGE':<35} {'VERSION':<14} {'THEN':>5}  {'NOW':>5}  {'DELTA':>6}  {'DOWNLOADS':>11}")
    out.append("  " + "─" * 100)
    for r in rows:
        ver = (r.get("latest_conda_version") or "?")[:13]
        delta = r.get("delta", 0)
        sign = f"+{delta}" if delta > 0 else f"{delta}"
        dl = r.get("total_downloads")
        dl_s = f"{dl:,}" if dl is not None else "—"
        out.append(
            f"  {r['conda_name']:<35} {ver:<14} {r['then_v']:>5}  {r['now_v']:>5}  {sign:>6}  {dl_s:>11}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diff vuln_history snapshots — what changed since last week?"
    )
    parser.add_argument("--maintainer", default=None,
                        help="Restrict to packages where HANDLE is a maintainer")
    parser.add_argument("--since-days", type=int, default=7, dest="since_days",
                        help="Compare current snapshot to one >=N days back (default 7)")
    parser.add_argument("--severity", choices=["C", "H", "K", "T"], default="C",
                        help="C=Critical, H=High, K=KEV, T=Total (default C)")
    parser.add_argument("--only-increases", action="store_true", dest="only_increases",
                        help="Only show packages where the count went up")
    parser.add_argument("--limit", type=int, default=25,
                        help="Maximum rows (default 25)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of a formatted table")
    args = parser.parse_args()

    rows, meta = query(
        maintainer=args.maintainer, since_days=args.since_days,
        severity=args.severity, only_increases=args.only_increases,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps({"meta": meta, "rows": rows}, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, meta, args.maintainer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
