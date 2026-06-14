#!/usr/bin/env python3
"""
pyver-breakdown — Per-Python-version conda-forge download breakdown.

Reads cf_atlas.db (offline) and surfaces per-Python 90d/lifetime download
counts from the `package_python_downloads` side table populated by the
Wave 2 (v8.18.0) parquet sweep extension. Headline value: --policy-check
joins the empirical Python floor against the recipe's *declared* `python_min`
(populated by Phase E into `packages.python_min` at schema v28) to flag
bump-safe candidates — feedstocks where the maintainer can safely raise
the floor without losing material adoption.

Modes:
  - Single package:    pyver-breakdown <pkg>
  - Policy check:      pyver-breakdown --policy-check <pkg>
  - Maintainer batch:  pyver-breakdown --policy-check --maintainer X
                       (optionally --threshold-pct 5.0)

Output sort order in --policy-check (per spec Q1=A): bump-safe → aligned →
aggressive. Maintainers see the actionable signal first; aggressive rows
are background info.

All modes accept --format markdown|json|csv (default markdown). Read-only.

Pixi:
  pixi run -e local-recipes pyver-breakdown numpy
  pixi run -e local-recipes pyver-breakdown --policy-check numpy
  pixi run -e local-recipes pyver-breakdown --policy-check --maintainer rxm7706
  pixi run -e local-recipes pyver-breakdown --policy-check --threshold-pct 5.0 --maintainer rxm7706
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import io
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
# Spec FR-4: skip per-package rows whose Phase F sweep is older than this.
PHASE_F_TTL_DAYS = 7


def _open_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(
            f"cf_atlas.db not found at {DB_PATH}. Run: bootstrap-data --profile admin",
            file=sys.stderr,
        )
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_single_package(conn: sqlite3.Connection, package: str) -> list[dict[str, Any]]:
    rows = list(conn.execute(
        """
        SELECT p.conda_name, p.feedstock_name, p.python_min,
               ppd.pkg_python, ppd.downloads_90d, ppd.downloads_total,
               ppd.fetched_at
        FROM packages p
        JOIN package_python_downloads ppd USING (conda_name)
        WHERE p.conda_name = ?
        ORDER BY ppd.downloads_90d DESC
        """,
        (package,),
    ))
    return [dict(r) for r in rows]


def _empirical_floor(per_pkg_rows: list[dict[str, Any]], threshold_pct: float) -> str | None:
    """Smallest pkg_python with >= threshold_pct of the package's 90d total.

    "Smallest" means lowest 3.X minor (we ignore 2.7 in floor calculation —
    a feedstock whose 90d data shows 2% on py2.7 should not have its
    python_min reported as 2.7; py2 is EOL and the recommendation column
    flags this scenario as `unknown` if it were possible). The empirical
    floor surfaces the lowest Python that still has material adoption.
    """
    total_90d = sum(r.get("downloads_90d") or 0 for r in per_pkg_rows)
    if total_90d <= 0:
        return None
    threshold = (threshold_pct / 100.0) * total_90d
    survivors: list[str] = []
    for r in per_pkg_rows:
        py = r.get("pkg_python") or ""
        if not py.startswith("3."):
            continue
        if (r.get("downloads_90d") or 0) >= threshold:
            survivors.append(py)
    if not survivors:
        return None
    # Sort by minor version numeric (e.g. '3.10' < '3.9' lexically but
    # 3.10 is numerically larger).
    def _key(s: str) -> tuple[int, int]:
        parts = s.split(".")
        try:
            return (int(parts[0]), int(parts[1]))
        except (IndexError, ValueError):
            return (99, 99)
    return min(survivors, key=_key)


def policy_check_status(declared: str | None, empirical: str | None) -> str:
    """Classify a (declared, empirical) pair per spec § Story 4."""
    if declared is None or empirical is None:
        return "unknown"
    def _key(s: str) -> tuple[int, int]:
        parts = s.split(".")
        try:
            return (int(parts[0]), int(parts[1]))
        except (IndexError, ValueError):
            return (99, 99)
    d = _key(declared)
    e = _key(empirical)
    if e > d:
        return "bump-safe"
    if e < d:
        return "aggressive"
    return "aligned"


def _delta_90d(per_pkg_rows: list[dict[str, Any]], py: str) -> int:
    """90d downloads on a specific Python version (0 if absent)."""
    for r in per_pkg_rows:
        if r.get("pkg_python") == py:
            return r.get("downloads_90d") or 0
    return 0


def run_policy_check(
    conn: sqlite3.Connection,
    *,
    package: str | None,
    maintainer: str | None,
    threshold_pct: float,
) -> tuple[list[dict[str, Any]], int]:
    """Returns (rows, n_unknown_declared)."""
    # Pull declared-min + all per-Python rows in one query per package set.
    params: list[Any] = []
    where = [
        "p.conda_name IS NOT NULL",
        "COALESCE(p.latest_status, 'active') = 'active'",
        "COALESCE(p.feedstock_archived, 0) = 0",
    ]
    join_clause = ""
    if maintainer:
        join_clause = (
            "JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
            "JOIN maintainers m ON m.id = pm.maintainer_id "
        )
        where.append("LOWER(m.handle) = LOWER(?)")
        params.append(maintainer)
    if package:
        where.append("p.conda_name = ?")
        params.append(package)
    sql = (
        "SELECT p.conda_name, p.feedstock_name, p.python_min, "
        "       ppd.pkg_python, ppd.downloads_90d, ppd.downloads_total, "
        "       ppd.fetched_at "
        "FROM packages p "
        "JOIN package_python_downloads ppd USING (conda_name) "
        f"{join_clause}"
        f"WHERE {' AND '.join(where)}"
    )
    rows = list(conn.execute(sql, params))
    by_pkg: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_pkg.setdefault(r["conda_name"], []).append(dict(r))

    now = int(dt.datetime.now().timestamp())
    stale_cutoff = now - PHASE_F_TTL_DAYS * 86400

    out: list[dict[str, Any]] = []
    n_unknown_declared = 0
    n_stale = 0
    for pkg, per_pkg_rows in by_pkg.items():
        first = per_pkg_rows[0]
        declared = first.get("python_min")
        empirical = _empirical_floor(per_pkg_rows, threshold_pct)
        # Stale check (FR-4): if every row's fetched_at is older than the
        # TTL, the package's per-Python data is stale.
        fetched_ats = [r.get("fetched_at") or 0 for r in per_pkg_rows]
        max_fetched = max(fetched_ats) if fetched_ats else 0
        is_stale = (max_fetched > 0) and (max_fetched < stale_cutoff)
        if is_stale:
            n_stale += 1
            status = "stale"
        else:
            status = policy_check_status(declared, empirical)
            # H5: count every "unknown" status (declared is None, OR
            # empirical is None) — the exit-gate fires when ALL rows
            # are unknown regardless of *why*.
            if status == "unknown":
                n_unknown_declared += 1
        delta_share = None
        if declared and status in {"bump-safe", "aligned", "aggressive"}:
            delta_share = _delta_90d(per_pkg_rows, declared)
        out.append({
            "conda_name": pkg,
            "feedstock_name": first.get("feedstock_name"),
            "declared_python_min": declared,
            "empirical_python_floor": empirical,
            "threshold_pct": threshold_pct,
            "status": status,
            "delta_90d_on_declared": delta_share,
            "fetched_at": max_fetched,
        })

    # Sort: bump-safe → aligned → aggressive → unknown → stale, then by
    # delta_90d_on_declared DESC for actionable triage ordering. Final
    # tiebreaker on conda_name keeps ordering deterministic when both
    # status and delta tie (H4: prevents nondeterministic test runs).
    order = {
        "bump-safe": 0, "aligned": 1, "aggressive": 2,
        "unknown": 3, "stale": 4,
    }
    out.sort(key=lambda r: (order.get(r["status"], 9),
                            -(r.get("delta_90d_on_declared") or 0),
                            r["conda_name"]))

    # FR-4 stderr: report n_unknown_declared + stale.
    if n_unknown_declared:
        print(
            f"warning: {n_unknown_declared} packages have no declared python_min "
            "cached; run `bootstrap-data --profile admin` to refresh Phase E",
            file=sys.stderr,
        )
    if n_stale:
        print(
            f"warning: {n_stale} packages have stale per-Python data "
            f"(>{PHASE_F_TTL_DAYS} days); run `bootstrap-data --profile admin` "
            "to refresh Phase F",
            file=sys.stderr,
        )

    return out, n_unknown_declared


def render_markdown_single(rows: list[dict[str, Any]], package: str,
                           threshold_pct: float) -> str:
    if not rows:
        return f"No per-Python download data for `{package}`.\n"
    total_90d = sum(r.get("downloads_90d") or 0 for r in rows)
    out = [
        f"{package} — per-Python downloads (90d)",
        "",
        "| Python | 90d downloads | Share |",
        "|---|---:|---:|",
    ]
    for r in sorted(rows, key=lambda x: -(x.get("downloads_90d") or 0)):
        py = r.get("pkg_python") or "?"
        d90 = r.get("downloads_90d") or 0
        share = (d90 / total_90d) * 100 if total_90d else 0
        out.append(f"| {py} | {d90:,} | {share:.1f}% |")
    floor = _empirical_floor(rows, threshold_pct)
    out.append("")
    out.append(
        f"Empirical python_min floor (>={threshold_pct:.1f}% share): "
        f"{floor if floor else '—'}"
    )
    return "\n".join(out) + "\n"


def render_markdown_policy(rows: list[dict[str, Any]], threshold_pct: float,
                          maintainer: str | None, package: str | None) -> str:
    if not rows:
        scope = ""
        if maintainer:
            scope = f" maintained by `{maintainer}`"
        elif package:
            scope = f" for `{package}`"
        return f"No packages with cached per-Python data{scope}.\n"
    title = "Python-min policy check"
    if maintainer:
        title += f" — maintainer `{maintainer}`"
    elif package:
        title += f" — `{package}`"
    out = [
        title,
        "",
        f"Threshold for empirical floor: >={threshold_pct:.1f}% of 90d downloads.",
        "",
        "| Feedstock | Declared | Empirical | Status | Δ 90d (on declared) |",
        "|---|---|---|---|---:|",
    ]
    for r in rows:
        delta = r.get("delta_90d_on_declared")
        delta_s = f"{delta:,}" if delta is not None else "—"
        out.append(
            f"| {r.get('feedstock_name') or r.get('conda_name', '?')} | "
            f"{r.get('declared_python_min') or '—'} | "
            f"{r.get('empirical_python_floor') or '—'} | "
            f"{r.get('status', '?')} | "
            f"{delta_s} |"
        )
    return "\n".join(out) + "\n"


def _emit_csv_single(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    field_order = [
        "conda_name", "feedstock_name", "pkg_python",
        "downloads_90d", "downloads_total", "fetched_at",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(field_order)
    for r in rows:
        writer.writerow([r.get(c, "") for c in field_order])
    return buf.getvalue()


def _emit_csv_policy(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    field_order = [
        "conda_name", "feedstock_name", "declared_python_min",
        "empirical_python_floor", "status", "delta_90d_on_declared",
        "threshold_pct", "fetched_at",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(field_order)
    for r in rows:
        writer.writerow([r.get(c, "") for c in field_order])
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Per-Python conda-forge download breakdown + python_min policy "
            "check. Reads cf_atlas.db offline."
        )
    )
    parser.add_argument("package", nargs="?", default=None,
                        help="Single-package mode: show per-Python breakdown.")
    parser.add_argument("--policy-check", action="store_true",
                        help="Compare declared `python_min` against the "
                             "empirical floor from 90d downloads.")
    parser.add_argument("--maintainer", default=None,
                        help="Restrict --policy-check to this handle.")
    parser.add_argument("--threshold-pct", type=float, default=2.0,
                        help="Noise floor for the empirical floor (default 2.0).")
    parser.add_argument("--format", default="markdown",
                        choices=["markdown", "json", "csv"],
                        help="Output format (default markdown).")
    args = parser.parse_args()

    # DW-W3-4 (v8.21.0): contextlib.closing wraps the DB so the connection
    # is released even when the in-process MCP-server wrapper reuses the
    # script (subprocess mode is fine; in-process mode leaked).
    with contextlib.closing(_open_db()) as conn:
        if args.policy_check:
            rows, n_unknown_declared = run_policy_check(
                conn,
                package=args.package,
                maintainer=args.maintainer,
                threshold_pct=args.threshold_pct,
            )
            if args.format == "json":
                print(json.dumps(rows, indent=2, default=str))
            elif args.format == "csv":
                sys.stdout.write(_emit_csv_policy(rows))
            else:
                sys.stdout.write(render_markdown_policy(
                    rows, args.threshold_pct, args.maintainer, args.package,
                ))
            # Spec I/O matrix line 47: non-zero exit if ALL packages are unknown.
            if rows and n_unknown_declared == len(rows):
                return 1
            return 0

        # Single-package non-policy mode.
        if not args.package:
            print("error: provide PACKAGE, or use --policy-check.", file=sys.stderr)
            return 2
        rows = query_single_package(conn, args.package)
        if args.format == "json":
            print(json.dumps(rows, indent=2, default=str))
        elif args.format == "csv":
            sys.stdout.write(_emit_csv_single(rows))
        else:
            sys.stdout.write(render_markdown_single(
                rows, args.package, args.threshold_pct,
            ))
        return 0


if __name__ == "__main__":
    sys.exit(main())
