#!/usr/bin/env python3
"""Per-maintainer feedstock portfolio + triage view.

Composes signals from atlas Phases B (status), G (CVE), H (PyPI lag),
M (cf-graph bot state), and N (GitHub CI / open PRs / open issues) into a
single ranked "today's punch list" for one maintainer.

Default mode
    Portfolio overview (mirrors the `my_feedstocks` MCP tool shape).
    Sorted by total downloads.

--triage
    Compute an urgency score from CVE counts, CI-red, stuck-bot state,
    upstream lag, and open-PR / open-issue counts. Emit the top --limit
    rows as a punch list grouped by severity band.

Maintainer resolution
    --maintainer NAME (explicit)
    or $GITHUB_USERNAME / $USER (auto-detected if not provided)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[4]
_ATLAS_DB = _REPO_ROOT / ".claude" / "data" / "conda-forge-expert" / "cf_atlas.db"
_ATLAS_STALE_DAYS = 7

_SELECT_COLS = [
    "conda_name", "feedstock_name", "latest_conda_version",
    "latest_conda_upload", "total_downloads", "latest_status",
    "feedstock_archived", "recipe_format",
    "vuln_critical_affecting_current", "vuln_high_affecting_current",
    "vuln_kev_affecting_current",
    "bot_open_pr_count", "bot_last_pr_state", "bot_last_pr_version",
    "bot_version_errors_count", "feedstock_bad",
    "pypi_current_version", "github_current_version",
    "gh_default_branch_status", "gh_open_prs_count", "gh_open_issues_count",
    "gh_pushed_at",
]


def resolve_maintainer(args: argparse.Namespace) -> str:
    if args.maintainer:
        return args.maintainer
    env = os.environ.get("GITHUB_USERNAME") or os.environ.get("USER")
    if env:
        return env
    raise SystemExit(
        "No maintainer specified. Pass --maintainer NAME or set $GITHUB_USERNAME."
    )


def load_atlas_meta() -> dict[str, Any]:
    meta: dict[str, Any] = {"available": False, "db_path": str(_ATLAS_DB)}
    if not _ATLAS_DB.exists():
        return meta
    con = sqlite3.connect(f"file:{_ATLAS_DB}?mode=ro", uri=True)
    row = con.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
    built_at = int(row[0]) if row else 0
    meta.update(
        available=True,
        built_at=built_at,
        age_days=(time.time() - built_at) / 86400 if built_at else None,
    )
    con.close()
    return meta


def query_feedstocks(maintainer: str) -> list[dict[str, Any]]:
    if not _ATLAS_DB.exists():
        raise SystemExit(f"atlas DB not found at {_ATLAS_DB}")
    con = sqlite3.connect(f"file:{_ATLAS_DB}?mode=ro", uri=True)
    select = ", ".join(_SELECT_COLS)
    q = (
        f"SELECT {select} FROM packages WHERE conda_name IN ("
        " SELECT pm.conda_name FROM package_maintainers pm"
        " JOIN maintainers m ON m.id = pm.maintainer_id"
        " WHERE LOWER(m.handle) = LOWER(?)"
        ") ORDER BY total_downloads DESC"
    )
    rows = [dict(zip(_SELECT_COLS, r)) for r in con.execute(q, (maintainer,))]
    con.close()
    return rows


def _version_lt(a: str | None, b: str | None) -> bool:
    if not a or not b or a == b:
        return False
    try:
        from packaging.version import Version
        return Version(a) < Version(b)
    except Exception:  # noqa: BLE001
        return a < b


def triage_score(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Return (score, reasons). Higher = more urgent."""
    score = 0
    reasons: list[str] = []

    kev = row.get("vuln_kev_affecting_current") or 0
    crit = row.get("vuln_critical_affecting_current") or 0
    high = row.get("vuln_high_affecting_current") or 0
    if kev:
        score += 1000 * kev
        reasons.append(f"{kev} KEV")
    if crit:
        score += 100 * crit
        reasons.append(f"{crit} Critical")
    if high:
        score += 20 * high
        reasons.append(f"{high} High")

    if row.get("gh_default_branch_status") == "failure":
        score += 50
        reasons.append("CI red")

    if (row.get("bot_version_errors_count") or 0) > 0:
        score += 30
        reasons.append(f"stuck-bot ({row['bot_version_errors_count']} attempts)")

    if row.get("feedstock_bad"):
        score += 20
        reasons.append("cf-graph: bad")

    if _version_lt(row.get("latest_conda_version"), row.get("pypi_current_version")):
        score += 10
        reasons.append(f"behind pypi ({row['latest_conda_version']} → {row['pypi_current_version']})")

    bot_pr = row.get("bot_open_pr_count") or 0
    if bot_pr > 0:
        score += 5 * bot_pr
        reasons.append(f"{bot_pr} bot PR{'s' if bot_pr != 1 else ''}")

    human_pr = row.get("gh_open_prs_count") or 0
    # bot PRs are included in gh_open_prs_count; estimate human as max(total - bot, 0)
    human_only = max(human_pr - bot_pr, 0)
    if human_only > 0:
        score += human_only
        reasons.append(f"{human_only} human PR{'s' if human_only != 1 else ''}")

    issues = row.get("gh_open_issues_count") or 0
    if issues > 0:
        score += min(issues, 10)  # capped at 10
        reasons.append(f"{issues} issue{'s' if issues != 1 else ''}")

    if row.get("feedstock_archived"):
        score -= 1000  # archived = don't bother
        reasons.append("ARCHIVED")

    return score, reasons


def severity_band(score: int) -> str:
    if score >= 1000:
        return "CRIT"
    if score >= 50:
        return "WARN"
    if score >= 10:
        return "REV"
    return "ok"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="my-feedstocks",
        description="Per-maintainer feedstock portfolio + triage view.",
    )
    p.add_argument("--maintainer", help="GitHub handle (default: $GITHUB_USERNAME or $USER)")
    p.add_argument("--triage", action="store_true", help="Rank by urgency score; emit top-N punch list")
    p.add_argument("--limit", type=int, default=25, help="Max rows in --triage output (default 25)")
    p.add_argument("--include-archived", action="store_true", help="Include archived feedstocks (default: hidden)")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return p.parse_args(argv)


def render_portfolio(rows: list[dict[str, Any]], maintainer: str) -> None:
    print(f"Feedstock portfolio for maintainer '{maintainer}' ({len(rows)} feedstocks):\n")
    print(f"{'PACKAGE':<32} {'VERSION':<14} {'DOWNLOADS':>12} STATUS")
    for r in rows:
        flags = []
        if r.get("feedstock_archived"):
            flags.append("ARCHIVED")
        if r.get("feedstock_bad"):
            flags.append("BAD")
        kev = r.get("vuln_kev_affecting_current") or 0
        crit = r.get("vuln_critical_affecting_current") or 0
        if kev:
            flags.append(f"KEV={kev}")
        if crit:
            flags.append(f"CRIT={crit}")
        flag_s = " " + ",".join(flags) if flags else ""
        print(
            f"  {r['conda_name']:<30} {(r.get('latest_conda_version') or '-'):<14} "
            f"{(r.get('total_downloads') or 0):>12,} {r.get('latest_status') or '-'}{flag_s}"
        )


def render_triage(scored: list[tuple[int, list[str], dict[str, Any]]], maintainer: str, atlas_meta: dict[str, Any], limit: int) -> None:
    print(f"Triage for maintainer '{maintainer}' (top {min(limit, len(scored))} of {len(scored)} feedstocks):\n")
    if not atlas_meta.get("available"):
        print(f"⚠  atlas DB not available at {atlas_meta['db_path']}.\n")
    elif (atlas_meta.get("age_days") or 0) > _ATLAS_STALE_DAYS:
        print(f"⚠  atlas DB is {atlas_meta['age_days']:.1f} days old (threshold: {_ATLAS_STALE_DAYS} d).\n")

    by_band: dict[str, list[tuple[int, list[str], dict[str, Any]]]] = {}
    for score, reasons, row in scored[:limit]:
        by_band.setdefault(severity_band(score), []).append((score, reasons, row))

    summary_parts = []
    for band in ("CRIT", "WARN", "REV", "ok"):
        if band in by_band:
            summary_parts.append(f"{len(by_band[band])} {band}")
    print(f"Summary: " + ", ".join(summary_parts) + "\n")

    for band, label in (
        ("CRIT", "Critical — drop everything (KEV / multi-Critical)"),
        ("WARN", "Needs attention — CI red, stuck bot, behind upstream, bad feedstock"),
        ("REV",  "Review queue — open PRs / issues / minor lag"),
        ("ok",   "Looks fine"),
    ):
        items = by_band.get(band)
        if not items:
            continue
        print(f"── [{band}] {label} ({len(items)}) ──")
        for score, reasons, row in items:
            extras = "; ".join(reasons) if reasons else "—"
            print(f"   {row['conda_name']:<30} (score={score:>5})  {extras}")
        print()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    maintainer = resolve_maintainer(args)
    atlas_meta = load_atlas_meta()
    rows = query_feedstocks(maintainer)
    if not args.include_archived:
        rows = [r for r in rows if not r.get("feedstock_archived")]

    if not args.triage:
        if args.json:
            print(json.dumps({
                "maintainer": maintainer, "atlas": atlas_meta,
                "count": len(rows), "rows": rows,
            }, indent=2))
            return 0
        render_portfolio(rows, maintainer)
        return 0

    scored = []
    for r in rows:
        s, reasons = triage_score(r)
        scored.append((s, reasons, r))
    scored.sort(key=lambda x: -x[0])

    if args.json:
        print(json.dumps({
            "maintainer": maintainer, "atlas": atlas_meta,
            "scored": [
                {"score": s, "band": severity_band(s), "reasons": rs, "row": row}
                for s, rs, row in scored[: args.limit]
            ],
        }, indent=2))
        return 0

    render_triage(scored, maintainer, atlas_meta, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
