#!/usr/bin/env python3
"""
platform-breakdown — Per-platform conda-forge download breakdown (Phase F+ Wave 2).

Reads cf_atlas.db (offline) and surfaces per-platform 90d/lifetime download
counts from the `package_platform_downloads` side table populated by the
Wave 2 (v8.18.0) parquet sweep extension. Maintainer-triage signal for
"should I drop osx-x86_64 from feedstock X?" and "is anyone using my
linux-aarch64 build?" questions.

Modes:
  - Single package:           platform-breakdown <pkg>
  - Top-N by platform:        platform-breakdown --top 50 --platform osx-arm64
  - Feedstock roundup:        platform-breakdown --feedstock-roundup --maintainer X

All three modes accept --format markdown|json|csv (default markdown).
Read-only — no urllib / requests imports; cf_atlas.db is the sole input.

Pixi:
  pixi run -e local-recipes platform-breakdown numpy
  pixi run -e local-recipes platform-breakdown --top 50 --platform linux-aarch64
  pixi run -e local-recipes platform-breakdown --feedstock-roundup --maintainer rxm7706
  pixi run -e local-recipes platform-breakdown numpy --format json
"""
from __future__ import annotations

import argparse
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
    """Skill-scoped data directory: .claude/data/conda-forge-expert/"""
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
    """All per-platform rows for one package, sorted by 90d downloads DESC."""
    rows = list(conn.execute(
        """
        SELECT p.conda_name, p.feedstock_name, ppd.pkg_platform,
               ppd.downloads_90d, ppd.downloads_total, ppd.fetched_at
        FROM packages p
        JOIN package_platform_downloads ppd USING (conda_name)
        WHERE p.conda_name = ?
        ORDER BY ppd.downloads_90d DESC
        """,
        (package,),
    ))
    return [dict(r) for r in rows]


def query_top_by_platform(
    conn: sqlite3.Connection,
    platform: str,
    top: int,
) -> list[dict[str, Any]]:
    """Top-N packages by absolute 90d downloads on the given platform."""
    rows = list(conn.execute(
        """
        SELECT p.conda_name, p.feedstock_name, ppd.pkg_platform,
               ppd.downloads_90d, ppd.downloads_total, ppd.fetched_at
        FROM packages p
        JOIN package_platform_downloads ppd USING (conda_name)
        WHERE ppd.pkg_platform = ?
          AND p.conda_name IS NOT NULL
          AND COALESCE(p.latest_status, 'active') = 'active'
          AND COALESCE(p.feedstock_archived, 0) = 0
        ORDER BY ppd.downloads_90d DESC
        LIMIT ?
        """,
        (platform, top),
    ))
    return [dict(r) for r in rows]


def query_feedstock_roundup(
    conn: sqlite3.Connection,
    maintainer: str,
) -> list[dict[str, Any]]:
    """All per-platform rows for the maintainer's feedstocks.

    Grouped by `feedstock_name` (one feedstock = one rerender target —
    the maintainer's mental model per OQ-2 in the spec).
    """
    rows = list(conn.execute(
        """
        SELECT p.conda_name, p.feedstock_name, ppd.pkg_platform,
               ppd.downloads_90d, ppd.downloads_total, ppd.fetched_at
        FROM packages p
        JOIN package_platform_downloads ppd USING (conda_name)
        JOIN package_maintainers pm ON pm.conda_name = p.conda_name
        JOIN maintainers m ON m.id = pm.maintainer_id
        WHERE LOWER(m.handle) = LOWER(?)
          AND COALESCE(p.latest_status, 'active') = 'active'
          AND COALESCE(p.feedstock_archived, 0) = 0
        ORDER BY p.feedstock_name, ppd.downloads_90d DESC
        """,
        (maintainer,),
    ))
    return [dict(r) for r in rows]


def _share_pct(value: int, total: int) -> float:
    return round((value / total) * 100.0, 1) if total else 0.0


def _annotate_shares(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate each row with share_pct against its package's 90d total."""
    by_pkg_total: dict[str, int] = {}
    for r in rows:
        by_pkg_total[r["conda_name"]] = by_pkg_total.get(r["conda_name"], 0) + (
            r.get("downloads_90d") or 0
        )
    for r in rows:
        total = by_pkg_total.get(r["conda_name"], 0)
        r["share_pct"] = _share_pct(r.get("downloads_90d") or 0, total)
    return rows


def render_markdown_single(rows: list[dict[str, Any]], package: str) -> str:
    if not rows:
        return (
            f"No per-platform download data for `{package}`. "
            "If the package exists, it may not have been swept by Phase F yet — "
            "run `bootstrap-data --profile admin` to refresh.\n"
        )
    total_90d = sum(r.get("downloads_90d") or 0 for r in rows)
    total_life = sum(r.get("downloads_total") or 0 for r in rows)
    out = [
        f"{package} — per-platform downloads (90d)",
        "",
        "| Platform | 90d downloads | Lifetime | Share |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        plat = r.get("pkg_platform") or "?"
        d90 = r.get("downloads_90d") or 0
        dlt = r.get("downloads_total") or 0
        share = _share_pct(d90, total_90d)
        out.append(f"| {plat} | {d90:,} | {dlt:,} | {share:.1f}% |")
    out.append(f"| **Total** | **{total_90d:,}** | **{total_life:,}** | **100.0%** |")
    return "\n".join(out) + "\n"


def render_markdown_top(rows: list[dict[str, Any]], platform: str) -> str:
    if not rows:
        return f"No packages with `{platform}` downloads found.\n"
    out = [
        f"Top {len(rows)} packages by 90d downloads on `{platform}`",
        "",
        "| Package | Feedstock | 90d downloads | Lifetime |",
        "|---|---|---:|---:|",
    ]
    for r in rows:
        out.append(
            f"| {r.get('conda_name', '?')} | {r.get('feedstock_name') or '—'} | "
            f"{(r.get('downloads_90d') or 0):,} | "
            f"{(r.get('downloads_total') or 0):,} |"
        )
    return "\n".join(out) + "\n"


def render_markdown_roundup(rows: list[dict[str, Any]], maintainer: str) -> str:
    if not rows:
        return f"No per-platform data for maintainer `{maintainer}`.\n"
    out = [
        f"Per-platform download roundup — maintainer `{maintainer}`",
        "",
        "| Feedstock | Package | Platform | 90d downloads | Share |",
        "|---|---|---|---:|---:|",
    ]
    for r in rows:
        out.append(
            f"| {r.get('feedstock_name') or '—'} | {r.get('conda_name', '?')} | "
            f"{r.get('pkg_platform') or '?'} | "
            f"{(r.get('downloads_90d') or 0):,} | "
            f"{r.get('share_pct', 0.0):.1f}% |"
        )
    return "\n".join(out) + "\n"


def _emit_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    field_order = [
        "conda_name", "feedstock_name", "pkg_platform",
        "downloads_90d", "downloads_total", "share_pct", "fetched_at",
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
            "Per-platform conda-forge download breakdown (Phase F+ Wave 2). "
            "Reads cf_atlas.db offline."
        )
    )
    parser.add_argument("package", nargs="?", default=None,
                        help="Single-package mode: show all platforms for PACKAGE.")
    parser.add_argument("--top", type=_positive_int, default=None, metavar="N",
                        help="Top-N mode: rank packages by absolute 90d downloads "
                             "on --platform (requires --platform).")
    parser.add_argument("--platform", default=None, metavar="P",
                        help="Platform filter for --top mode (e.g., osx-arm64).")
    parser.add_argument("--feedstock-roundup", action="store_true",
                        help="Group by feedstock_name across all packages a "
                             "maintainer owns (requires --maintainer).")
    parser.add_argument("--maintainer", default=None,
                        help="Restrict --feedstock-roundup to this handle.")
    parser.add_argument("--format", default="markdown",
                        choices=["markdown", "json", "csv"],
                        help="Output format (default markdown).")
    args = parser.parse_args()

    conn = _open_db()
    rows: list[dict[str, Any]]
    mode: str

    if args.feedstock_roundup:
        if not args.maintainer:
            print("error: --feedstock-roundup requires --maintainer",
                  file=sys.stderr)
            return 2
        rows = query_feedstock_roundup(conn, args.maintainer)
        rows = _annotate_shares(rows)
        mode = "roundup"
    elif args.top is not None:
        if not args.platform:
            print("error: --top requires --platform", file=sys.stderr)
            return 2
        rows = query_top_by_platform(conn, args.platform, args.top)
        # Single-platform queries: share_pct is N/A (intra-package share is
        # always 100% on the filtered platform); set to None to make
        # downstream renderers skip it cleanly.
        for r in rows:
            r["share_pct"] = None
        mode = "top"
    elif args.package:
        rows = query_single_package(conn, args.package)
        rows = _annotate_shares(rows)
        mode = "single"
    else:
        print("error: provide PACKAGE, --top + --platform, or "
              "--feedstock-roundup + --maintainer",
              file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(rows, indent=2, default=str))
    elif args.format == "csv":
        sys.stdout.write(_emit_csv(rows))
    else:
        if mode == "single":
            sys.stdout.write(render_markdown_single(rows, args.package or "?"))
        elif mode == "top":
            sys.stdout.write(render_markdown_top(rows, args.platform or "?"))
        else:
            sys.stdout.write(render_markdown_roundup(rows, args.maintainer or "?"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
