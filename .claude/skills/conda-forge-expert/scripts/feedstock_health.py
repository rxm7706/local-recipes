#!/usr/bin/env python3
"""
feedstock-health — Surface feedstocks where the conda-forge bots are stuck,
builds are flagged bad, or version-update PRs aren't landing.

Reads Phase M data (bot_open_pr_count, bot_last_pr_state, bot_last_pr_version,
bot_version_errors_count, feedstock_bad, bot_status_fetched_at).

CLI:
  feedstock-health [--maintainer HANDLE] [--limit N]
                   [--filter stuck|bad|open-pr|all] [--json]

  --filter stuck      : bot_version_errors_count > 0 (default)
  --filter bad        : feedstock_bad = 1
  --filter open-pr    : bot_open_pr_count > 0 (PR awaiting maintainer review)
  --filter all        : any health concern (union of the three)

Pixi:
  pixi run -e local-recipes feedstock-health
  pixi run -e local-recipes feedstock-health --maintainer rxm7706
  pixi run -e local-recipes feedstock-health --filter open-pr --limit 30
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


def query(*, maintainer: str | None, filter_kind: str, limit: int) -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    where = [
        "p.conda_name IS NOT NULL",
        "COALESCE(p.feedstock_archived, 0) = 0",
        "p.latest_status = 'active'",
    ]
    params: list[Any] = []

    if filter_kind == "stuck":
        where.append("COALESCE(p.bot_version_errors_count, 0) > 0")
    elif filter_kind == "bad":
        where.append("COALESCE(p.feedstock_bad, 0) = 1")
    elif filter_kind == "open-pr":
        where.append("COALESCE(p.bot_open_pr_count, 0) > 0")
    elif filter_kind == "ci-red":
        # Phase N signal: live default-branch CI is failing or in error
        where.append("p.gh_default_branch_status IN ('failure', 'error')")
    elif filter_kind == "open-issues":
        # Phase N: any open issues
        where.append("COALESCE(p.gh_open_issues_count, 0) > 0")
    elif filter_kind == "open-prs-human":
        # Phase N: any open PRs (human + bot — distinguishing requires
        # an additional Phase N query for author types). Combined with
        # `--filter open-pr` (bot-only via Phase M) gives a triangulation.
        where.append("COALESCE(p.gh_open_prs_count, 0) > 0")
    elif filter_kind == "all":
        where.append(
            "(COALESCE(p.bot_version_errors_count, 0) > 0 "
            " OR COALESCE(p.feedstock_bad, 0) = 1 "
            " OR COALESCE(p.bot_open_pr_count, 0) > 0 "
            " OR p.gh_default_branch_status IN ('failure', 'error') "
            " OR COALESCE(p.gh_open_issues_count, 0) > 0 "
            " OR COALESCE(p.gh_open_prs_count, 0) > 0)"
        )

    cols = (
        "p.conda_name, p.feedstock_name, p.latest_conda_version, "
        "p.bot_open_pr_count, p.bot_last_pr_state, p.bot_last_pr_version, "
        "p.bot_version_errors_count, p.feedstock_bad, p.bot_status_fetched_at, "
        "p.total_downloads, "
        "p.vuln_critical_affecting_current, p.vuln_high_affecting_current, "
        "p.gh_default_branch_status, p.gh_open_issues_count, "
        "p.gh_open_prs_count, p.gh_pushed_at, p.gh_status_fetched_at"
    )

    if maintainer:
        sql = (
            f"SELECT {cols} FROM packages p "
            "JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
            "JOIN maintainers m ON m.id = pm.maintainer_id "
            f"WHERE {' AND '.join(where)} "
            "  AND LOWER(m.handle) = LOWER(?) "
            "ORDER BY COALESCE(p.bot_version_errors_count, 0) DESC, "
            "         COALESCE(p.bot_open_pr_count, 0) DESC, "
            "         p.total_downloads DESC LIMIT ?"
        )
        params.append(maintainer)
    else:
        sql = (
            f"SELECT {cols} FROM packages p "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY COALESCE(p.bot_version_errors_count, 0) DESC, "
            "         COALESCE(p.bot_open_pr_count, 0) DESC, "
            "         p.total_downloads DESC LIMIT ?"
        )
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def render_table(rows: list[dict[str, Any]], maintainer: str | None,
                 filter_kind: str) -> str:
    if not rows:
        scope = f" maintained by {maintainer}" if maintainer else ""
        return f"No feedstocks match filter '{filter_kind}'{scope}.\n"

    out: list[str] = []
    title = f"Feedstock health [{filter_kind}]"
    if maintainer:
        title += f" — {maintainer}"
    out.append(f"  {title}  ({len(rows)} feedstock(s))")
    out.append("  " + "─" * 152)
    out.append(
        f"  {'PACKAGE':<37} {'CONDA':<13} {'BOT TRIED':<13} {'ERRS':>5} "
        f"{'BOT-PR':>6} {'CI':<8} {'ISSUES':>6} {'GH-PR':>5} {'C/H':>5} {'DOWNLOADS':>11}"
    )
    out.append("  " + "─" * 152)
    for r in rows:
        ver = (r.get("latest_conda_version") or "?")[:12]
        bot_ver = (r.get("bot_last_pr_version") or "—")[:12]
        errs = r.get("bot_version_errors_count") or 0
        open_n = r.get("bot_open_pr_count") or 0
        ci_state = r.get("gh_default_branch_status") or "—"
        gh_issues = r.get("gh_open_issues_count")
        gh_prs = r.get("gh_open_prs_count")
        gh_issues_s = f"{gh_issues}" if gh_issues is not None else "—"
        gh_prs_s = f"{gh_prs}" if gh_prs is not None else "—"
        c = r.get("vuln_critical_affecting_current") or 0
        h = r.get("vuln_high_affecting_current") or 0
        risk = f"{c}/{h}" if (c or h) else "—"
        dl = r.get("total_downloads")
        dl_s = f"{dl:,}" if dl is not None else "—"
        out.append(
            f"  {r['conda_name']:<37} {ver:<13} {bot_ver:<13} {errs:>5} "
            f"{open_n:>6} {ci_state[:8]:<8} {gh_issues_s:>6} {gh_prs_s:>5} "
            f"{risk:>5} {dl_s:>11}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Surface feedstocks with bot/build/PR issues from cf_atlas Phase M."
    )
    parser.add_argument("--maintainer", default=None,
                        help="Restrict to packages where HANDLE is a maintainer")
    parser.add_argument("--limit", type=int, default=25,
                        help="Maximum rows (default 25)")
    parser.add_argument("--filter", default="stuck", dest="filter_kind",
                        choices=["stuck", "bad", "open-pr", "ci-red",
                                 "open-issues", "open-prs-human", "all"],
                        help="Filter to a specific kind of issue (default 'stuck'). "
                             "ci-red / open-issues / open-prs-human require Phase N data.")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of a formatted table")
    args = parser.parse_args()

    rows = query(maintainer=args.maintainer, filter_kind=args.filter_kind,
                 limit=args.limit)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.maintainer, args.filter_kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())
