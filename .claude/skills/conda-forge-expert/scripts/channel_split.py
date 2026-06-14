#!/usr/bin/env python3
"""
channel-split — Per-channel download breakdown (Phase F+ Wave 3).

Reads cf_atlas.db (offline) and surfaces per-channel 90d/lifetime download
counts from the `package_channel_downloads` side table populated by the
Wave 3 (v8.19.0) parquet sweep extension. The raw channel string is what
the parquet ships (no normalization): `conda-forge`, `defaults`, `bioconda`,
`pytorch`, `nvidia`, etc. Migration-opportunity signal — surfaces packages
with significant `defaults`-channel share that the conda-forge feedstock
could capture by rerendering / publishing for the channel.

Modes:
  - Single package:            channel-split <pkg>
  - Top-N by defaults share:   channel-split --defaults-share-min 10.0 --top 50
  - Migration checklist:       channel-split --migration-checklist --maintainer X

All modes accept --format markdown|json|csv (default markdown).
--migration-checklist emits markdown checkbox lines suitable for paste
into a GitHub issue. Read-only.

Pixi:
  pixi run -e local-recipes channel-split matplotlib
  pixi run -e local-recipes channel-split --defaults-share-min 10.0 --top 50
  pixi run -e local-recipes channel-split --migration-checklist --maintainer rxm7706
  pixi run -e local-recipes channel-split matplotlib --format json
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _positive_int(s: str) -> int:
    """EC-6b: argparse validator that rejects --top <= 0."""
    n = int(s)
    if n <= 0:
        raise argparse.ArgumentTypeError(f"--top must be positive, got {n}")
    return n


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"


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
        SELECT p.conda_name, p.feedstock_name, pcd.data_source,
               pcd.downloads_90d, pcd.downloads_total, pcd.fetched_at
        FROM packages p
        JOIN package_channel_downloads pcd USING (conda_name)
        WHERE p.conda_name = ?
        ORDER BY pcd.downloads_90d DESC
        """,
        (package,),
    ))
    return [dict(r) for r in rows]


def _aggregate_share(
    rows: list[dict[str, Any]],
    *,
    channel: str = "defaults",
) -> dict[str, dict[str, Any]]:
    """Per-package totals across channels + share on `channel`.

    `relationship` is carried through so the migration-checklist renderer
    can branch the message (EC-9b): packages with no conda-forge feedstock
    (`pypi_only`) get an "open feedstock" call to action, while packages
    already on conda-forge get a "rerender + outreach" call to action.
    """
    by_pkg: dict[str, dict[str, Any]] = {}
    for r in rows:
        pkg = r["conda_name"]
        entry = by_pkg.setdefault(pkg, {
            "conda_name": pkg,
            "feedstock_name": r.get("feedstock_name"),
            "relationship": r.get("relationship"),
            "total_90d": 0,
            f"{channel}_90d": 0,
            f"{channel}_share_pct": 0.0,
        })
        d90 = r.get("downloads_90d") or 0
        entry["total_90d"] += d90
        if r.get("data_source") == channel:
            # H6: defensive accumulation. PK = (conda_name, data_source)
            # prevents duplicates at the SQL level, but `+=` keeps the
            # aggregation correct even if the query ever returns multiple
            # rows for the same (pkg, channel) pair.
            ch_key = f"{channel}_90d"
            entry[ch_key] = entry.get(ch_key, 0) + d90
    for pkg, entry in by_pkg.items():
        total = entry["total_90d"]
        share_key = f"{channel}_share_pct"
        ch_key = f"{channel}_90d"
        entry[share_key] = (
            round((entry[ch_key] / total) * 100.0, 1) if total else 0.0
        )
    return by_pkg


def query_defaults_heavy(
    conn: sqlite3.Connection,
    *,
    defaults_share_min: float,
    top: int,
    maintainer: str | None = None,
) -> list[dict[str, Any]]:
    """Packages with defaults share >= floor, ranked by absolute defaults 90d."""
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
    rows = list(conn.execute(
        f"""
        SELECT p.conda_name, p.feedstock_name, p.relationship,
               pcd.data_source,
               pcd.downloads_90d, pcd.downloads_total, pcd.fetched_at
        FROM packages p
        JOIN package_channel_downloads pcd USING (conda_name)
        {join_clause}
        WHERE {' AND '.join(where)}
        """,
        params,
    ))
    by_pkg = _aggregate_share([dict(r) for r in rows], channel="defaults")
    surviving = [
        v for v in by_pkg.values()
        if v["defaults_share_pct"] >= defaults_share_min and v["defaults_90d"] > 0
    ]
    surviving.sort(key=lambda v: -v["defaults_90d"])
    return surviving[:top]


def render_markdown_single(rows: list[dict[str, Any]], package: str) -> str:
    if not rows:
        return f"No per-channel download data for `{package}`.\n"
    total_90d = sum(r.get("downloads_90d") or 0 for r in rows)
    out = [
        f"{package} — per-channel downloads (90d)",
        "",
        "| Channel | 90d downloads | Lifetime | Share |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        ch = r.get("data_source") or "?"
        d90 = r.get("downloads_90d") or 0
        dlt = r.get("downloads_total") or 0
        share = (d90 / total_90d * 100) if total_90d else 0
        out.append(f"| {ch} | {d90:,} | {dlt:,} | {share:.1f}% |")
    # Migration-opportunity footer when defaults share > 10%.
    defaults_d90 = sum(
        (r.get("downloads_90d") or 0) for r in rows
        if r.get("data_source") == "defaults"
    )
    defaults_share = (defaults_d90 / total_90d * 100) if total_90d else 0
    out.append("")
    # EC-5b: use >= to stay consistent with query_defaults_heavy's
    # `defaults_share_pct >= floor` SQL filter (default floor 10.0%).
    # A package at exactly 10.0% should trigger the migration message,
    # not the "no signal" footer.
    if defaults_share >= 10.0:
        out.append(
            f"Migration opportunity: {defaults_share:.1f}% on defaults — "
            "consider rerendering for cross-channel adoption."
        )
    else:
        out.append(
            f"Defaults share: {defaults_share:.1f}% (below 10% — no migration "
            "signal)."
        )
    return "\n".join(out) + "\n"


def render_markdown_top(
    rows: list[dict[str, Any]],
    *,
    defaults_share_min: float,
) -> str:
    if not rows:
        return (
            f"No packages with defaults share >= {defaults_share_min:.1f}% found.\n"
        )
    out = [
        (f"Top {len(rows)} migration targets — defaults share "
         f">= {defaults_share_min:.1f}%"),
        "",
        "| Feedstock | Defaults 90d | Total 90d | Defaults Share |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        out.append(
            f"| {r.get('feedstock_name') or r.get('conda_name', '?')} | "
            f"{r['defaults_90d']:,} | {r['total_90d']:,} | "
            f"{r['defaults_share_pct']:.1f}% |"
        )
    return "\n".join(out) + "\n"


def render_migration_checklist(rows: list[dict[str, Any]]) -> str:
    """Markdown checkbox lines (per spec Q3=B). Paste-into-GitHub-issue ready.

    EC-9b: the message is context-aware. A `relationship='pypi_only'` row
    means there is NO conda-forge feedstock yet — the call-to-action is to
    open one. Every other relationship (`both_same_name`, `both_renamed`,
    `conda_only`) already has a conda-forge feedstock — the call-to-action
    is to drive defaults users to the existing feedstock via rerender +
    outreach.
    """
    if not rows:
        return "# Migration checklist — no defaults-heavy packages found.\n"
    out = ["# Migration checklist", ""]
    for r in rows:
        name = r.get("feedstock_name") or r.get("conda_name", "?")
        share = r["defaults_share_pct"]
        d90 = r["defaults_90d"]
        relationship = r.get("relationship")
        if relationship == "pypi_only":
            out.append(
                f"- [ ] Open conda-forge feedstock for `{name}`; "
                f"defaults has {share:.1f}% share ({d90:,} 90d downloads)"
            )
        else:
            out.append(
                f"- [ ] Bump rerender + outreach to drive defaults users "
                f"to conda-forge for `{name}`; defaults has {share:.1f}% "
                f"share ({d90:,} 90d downloads)"
            )
    return "\n".join(out) + "\n"


def _emit_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    # Stable column order across single-pkg and top-N modes (different schemas).
    if rows and "data_source" in rows[0]:
        field_order = [
            "conda_name", "feedstock_name", "data_source",
            "downloads_90d", "downloads_total", "fetched_at",
        ]
    else:
        field_order = [
            "conda_name", "feedstock_name",
            "defaults_90d", "total_90d", "defaults_share_pct",
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
            "Per-channel conda-forge download breakdown + defaults-share "
            "migration targets. Reads cf_atlas.db offline."
        )
    )
    parser.add_argument("package", nargs="?", default=None,
                        help="Single-package mode: show per-channel breakdown.")
    parser.add_argument("--defaults-share-min", type=float, default=None,
                        metavar="PCT",
                        help="Filter to packages with defaults share >= PCT. "
                             "Triggers top-N mode.")
    parser.add_argument("--top", type=_positive_int, default=50,
                        help="Top-N for --defaults-share-min mode (default 50).")
    parser.add_argument("--migration-checklist", action="store_true",
                        help="Emit markdown checkbox lines (paste into "
                             "GitHub issue). Requires --maintainer.")
    parser.add_argument("--maintainer", default=None,
                        help="Restrict ranking modes to this handle.")
    parser.add_argument("--format", default="markdown",
                        choices=["markdown", "json", "csv"],
                        help="Output format (default markdown).")
    args = parser.parse_args()

    # DW-W3-4 (v8.21.0): contextlib.closing wraps the DB so the connection
    # is released even when the in-process MCP-server wrapper reuses the
    # script (subprocess mode is fine; in-process mode leaked).
    with contextlib.closing(_open_db()) as conn:
        if args.migration_checklist:
            if not args.maintainer:
                print("error: --migration-checklist requires --maintainer",
                      file=sys.stderr)
                return 2
            # Default threshold for the checklist when none given.
            floor = args.defaults_share_min if args.defaults_share_min is not None else 10.0
            rows = query_defaults_heavy(
                conn,
                defaults_share_min=floor,
                top=args.top,
                maintainer=args.maintainer,
            )
            if args.format == "json":
                print(json.dumps(rows, indent=2, default=str))
            elif args.format == "csv":
                sys.stdout.write(_emit_csv(rows))
            else:
                sys.stdout.write(render_migration_checklist(rows))
            return 0

        if args.defaults_share_min is not None:
            rows = query_defaults_heavy(
                conn,
                defaults_share_min=args.defaults_share_min,
                top=args.top,
                maintainer=args.maintainer,
            )
            if args.format == "json":
                print(json.dumps(rows, indent=2, default=str))
            elif args.format == "csv":
                sys.stdout.write(_emit_csv(rows))
            else:
                sys.stdout.write(render_markdown_top(
                    rows, defaults_share_min=args.defaults_share_min,
                ))
            return 0

        if not args.package:
            print("error: provide PACKAGE, --defaults-share-min, or "
                  "--migration-checklist + --maintainer",
                  file=sys.stderr)
            return 2

        rows = query_single_package(conn, args.package)
        if args.format == "json":
            print(json.dumps(rows, indent=2, default=str))
        elif args.format == "csv":
            sys.stdout.write(_emit_csv(rows))
        else:
            sys.stdout.write(render_markdown_single(rows, args.package))
        return 0


if __name__ == "__main__":
    sys.exit(main())
