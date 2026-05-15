#!/usr/bin/env python3
"""pypi-intelligence — surface PyPI candidates with rich enrichment filters.

Reads the `pypi_intelligence` side table (schema v22+) joined via the
`v_pypi_candidates` view. Default sort is `conda_forge_readiness DESC`,
which surfaces high-readiness pypi-only candidates first — the "what
should I package next?" admin-persona query.

Usage:
  pypi-intelligence --not-in-conda-forge --score-min 70 --limit 25
  pypi-intelligence --activity hot --license-ok --noarch-python-candidate
  pypi-intelligence --in-bioconda --not-in-conda-forge --limit 50
  pypi-intelligence --min-downloads 10000 --sort-by downloads --json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


DATA_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "conda-forge-expert"
)
DB_PATH = DATA_DIR / "cf_atlas.db"


SORT_BY_COLUMNS = {
    "score":     "conda_forge_readiness DESC NULLS LAST, last_serial DESC",
    "downloads": "downloads_30d DESC NULLS LAST",
    "serial":    "last_serial DESC",
    "name":      "pypi_name ASC",
}


def build_query(args: argparse.Namespace) -> tuple[str, tuple]:
    where: list[str] = []
    params: list = []

    if args.not_in_conda_forge:
        where.append("conda_name IS NULL")
    if args.activity:
        where.append("activity_band = ?")
        params.append(args.activity)
    if args.license_ok:
        # License is in the OSI-approved subset (matches Phase S's set)
        from conda_forge_atlas import _OSI_APPROVED_SPDX  # type: ignore[import-untyped]
        ph = ",".join(["?"] * len(_OSI_APPROVED_SPDX))
        where.append(f"license_spdx IN ({ph})")
        params.extend(sorted(_OSI_APPROVED_SPDX))
    if args.noarch_python_candidate:
        where.append("packaging_shape = 'pure-python'")
        where.append("(requires_python IS NULL OR requires_python LIKE '%>=3.1%' OR requires_python LIKE '%>=3.2%')")
    if args.min_downloads is not None:
        where.append("downloads_30d >= ?")
        params.append(args.min_downloads)
    if args.score_min is not None:
        where.append("conda_forge_readiness >= ?")
        params.append(args.score_min)
    for ch in ("bioconda", "pytorch", "nvidia", "robostack",
               "homebrew", "nixpkgs", "spack", "debian", "fedora"):
        flag = getattr(args, f"in_{ch}", False)
        if flag:
            where.append(f"in_{ch} = 1")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = SORT_BY_COLUMNS[args.sort_by]
    sql = (
        "SELECT pypi_name, last_serial, conda_name, "
        "  activity_band, serial_delta_7d, serial_delta_30d, "
        "  downloads_30d, downloads_90d, "
        "  in_bioconda, in_pytorch, in_nvidia, in_robostack, "
        "  latest_version, latest_upload_at, latest_yanked, "
        "  requires_python, license_spdx, summary, repo_url, "
        "  has_wheel, has_sdist, packaging_shape, "
        "  conda_forge_readiness, recommended_template, "
        "  staged_recipes_pr_url, staged_recipes_pr_state, notes "
        f"FROM v_pypi_candidates {where_sql} "
        f"ORDER BY {order_sql} LIMIT ?"
    )
    params.append(args.limit)
    return sql, tuple(params)


def render_table(rows: list[dict]) -> str:
    if not rows:
        return "No candidates match the given filters.\n"
    out: list[str] = []
    out.append("")
    header = (
        f"  {'PYPI NAME':<30} {'SCORE':>5} {'BAND':<8} {'DL/30d':>9} "
        f"{'SHAPE':<14} {'LICENSE':<14} {'REPO':<3}"
    )
    out.append(header)
    out.append("  " + "─" * (len(header) - 2))
    for r in rows:
        name = (r.get("pypi_name") or "")[:30]
        score = r.get("conda_forge_readiness")
        score_s = f"{score:>5}" if score is not None else "    —"
        band = (r.get("activity_band") or "—")[:8]
        dl = r.get("downloads_30d")
        dl_s = f"{dl:>9,}" if dl is not None else "        —"
        shape = (r.get("packaging_shape") or "—")[:14]
        license_ = (r.get("license_spdx") or "—")[:14]
        repo = "✓" if r.get("repo_url") else "—"
        out.append(f"  {name:<30} {score_s} {band:<8} {dl_s} {shape:<14} {license_:<14} {repo:<3}")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Surface PyPI candidates with enrichment filters from "
                    "pypi_intelligence (schema v22+).")
    parser.add_argument("--not-in-conda-forge", action="store_true",
                        help="Only pypi-only rows (conda_name IS NULL)")
    parser.add_argument("--activity",
                        choices=["hot", "warm", "cold", "dormant"],
                        help="Filter by activity_band")
    parser.add_argument("--license-ok", action="store_true",
                        help="Only OSI-approved SPDX licenses")
    parser.add_argument("--noarch-python-candidate", action="store_true",
                        help="packaging_shape='pure-python' AND requires_python compatible with >=3.10")
    parser.add_argument("--min-downloads", type=int, default=None,
                        help="Minimum downloads_30d threshold")
    parser.add_argument("--score-min", type=int, default=None,
                        help="Minimum conda_forge_readiness (0-100)")
    for ch in ("bioconda", "pytorch", "nvidia", "robostack",
               "homebrew", "nixpkgs", "spack", "debian", "fedora"):
        parser.add_argument(
            f"--in-{ch}", action="store_true", dest=f"in_{ch}",
            help=f"Only rows with in_{ch}=1")
    parser.add_argument("--limit", type=int, default=25,
                        help="Maximum rows (default 25)")
    parser.add_argument("--sort-by", choices=list(SORT_BY_COLUMNS),
                        default="score",
                        help="Sort key (default: score = conda_forge_readiness)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of a formatted table")
    parser.add_argument("--db", default=str(DB_PATH),
                        help="Override path to cf_atlas.db")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"  DB not found at {args.db}; run `bootstrap-data --profile maintainer` first",
              file=sys.stderr)
        return 2

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        sql, params = build_query(args)
        rows = [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()

    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
