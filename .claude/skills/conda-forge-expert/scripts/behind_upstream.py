#!/usr/bin/env python3
"""
behind-upstream — Find feedstocks where conda-forge lags PyPI.

Compares `latest_conda_version` (Phase B) against `pypi_current_version`
(Phase H). Uses packaging.version for proper PEP 440 comparison; falls
back to string-equality for non-PEP-440 strings.

CLI:
  behind-upstream [--maintainer HANDLE] [--limit N] [--json]

Pixi:
  pixi run -e local-recipes behind-upstream
  pixi run -e local-recipes behind-upstream --maintainer rxm7706 --limit 20
  pixi run -e local-recipes behind-upstream --json
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


try:
    from packaging.version import parse as _parse_version
except ImportError:  # pragma: no cover
    _parse_version = None  # type: ignore[assignment]


def _classify_lag(conda_v: str | None, pypi_v: str | None) -> tuple[str, int]:
    """Classify how far behind a feedstock is.

    Returns (label, sort_priority) where priority is higher for "more behind."
      - 'major'    : major version bump (e.g., 2.x → 3.x)
      - 'minor'    : minor version bump (e.g., 3.0.x → 3.1.x)
      - 'patch'    : patch only (e.g., 3.0.42 → 3.0.45)
      - 'unknown'  : non-PEP-440 versions
      - 'current'  : matches
    """
    if not conda_v or not pypi_v:
        return ("unknown", 0)
    if conda_v == pypi_v:
        return ("current", 0)
    if _parse_version is None:
        return ("unknown", 1)
    try:
        c = _parse_version(conda_v)
        p = _parse_version(pypi_v)
    except Exception:
        return ("unknown", 1)
    if not (hasattr(c, "release") and hasattr(p, "release")):
        return ("unknown", 1)
    c_rel = c.release  # type: ignore[union-attr]
    p_rel = p.release  # type: ignore[union-attr]
    if p <= c:
        return ("current", 0)
    if len(c_rel) == 0 or len(p_rel) == 0:
        return ("unknown", 1)
    if p_rel[0] != c_rel[0]:
        return ("major", 4)
    if len(c_rel) >= 2 and len(p_rel) >= 2 and p_rel[1] != c_rel[1]:
        return ("minor", 3)
    return ("patch", 2)


def query(*, maintainer: str | None, limit: int) -> list[dict[str, Any]]:
    """Find feedstocks behind their upstream source.

    Joins `packages` to `upstream_versions` (Phase H/K side table) and
    picks the right upstream-source per row using `conda_source_registry`
    as the primary signal:
      - source='pypi'   → match upstream_versions.source='pypi'
      - source='github' → match upstream_versions.source='github'
      - source='other'  → fall back to whichever upstream we have data for,
                          preferring github (newer signal) over pypi.

    A row is "behind upstream" iff:
      latest_conda_version is set, upstream version is set, they differ,
      and PEP 440 comparison classifies upstream as strictly newer.
    """
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Pull all candidate (package, upstream-source) pairs in one query, then
    # filter+rank in Python where PEP 440 comparison lives.
    base_select = (
        "SELECT p.conda_name, p.pypi_name, p.latest_conda_version, "
        "       p.latest_conda_upload, p.total_downloads, "
        "       p.vuln_critical_affecting_current, p.vuln_high_affecting_current, "
        "       p.conda_source_registry, "
        "       u.source AS upstream_source, u.version AS upstream_version, "
        "       u.url AS upstream_url "
        "FROM packages p "
        "JOIN upstream_versions u ON u.conda_name = p.conda_name "
    )
    where = [
        "p.conda_name IS NOT NULL",
        "p.latest_conda_version IS NOT NULL",
        "u.version IS NOT NULL",
        "p.latest_status = 'active'",
        "COALESCE(p.feedstock_archived, 0) = 0",
    ]
    params: list[Any] = []
    if maintainer:
        base_select += (
            "JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
            "JOIN maintainers m ON m.id = pm.maintainer_id "
        )
        where.append("LOWER(m.handle) = LOWER(?)")
        params.append(maintainer)
    sql = base_select + "WHERE " + " AND ".join(where)

    # Group rows by conda_name and pick the relevant upstream per row.
    by_name: dict[str, list[dict[str, Any]]] = {}
    for r in conn.execute(sql, params):
        d = dict(r)
        by_name.setdefault(d["conda_name"], []).append(d)

    rows = []
    for conda_name, candidates in by_name.items():
        # Pick the relevant upstream source per the recipe's source registry.
        registry = (candidates[0].get("conda_source_registry") or "").lower()
        preferred_order: list[str]
        if registry == "pypi":
            preferred_order = ["pypi", "github", "gitlab", "codeberg"]
        elif registry == "github":
            preferred_order = ["github", "gitlab", "codeberg", "pypi"]
        else:
            # 'other' / NULL — prefer VCS (typically newer signal) then PyPI
            preferred_order = ["github", "gitlab", "codeberg", "pypi"]
        chosen = None
        for src in preferred_order:
            for c in candidates:
                if c["upstream_source"] == src and c["upstream_version"]:
                    chosen = c
                    break
            if chosen is not None:
                break
        if chosen is None:
            continue
        label, priority = _classify_lag(
            chosen["latest_conda_version"], chosen["upstream_version"]
        )
        if label == "current":
            continue
        chosen["lag_label"] = label
        chosen["_priority"] = priority
        rows.append(chosen)

    rows.sort(key=lambda r: (-r["_priority"], -(r.get("total_downloads") or 0)))
    return rows[:limit]


def render_table(rows: list[dict[str, Any]], maintainer: str | None) -> str:
    if not rows:
        return f"All up-to-date.\n"

    out: list[str] = []
    title = "Behind upstream"
    if maintainer:
        title += f" — {maintainer}"
    out.append(f"  {title}  ({len(rows)} feedstock(s))")
    out.append("  " + "─" * 120)
    out.append(
        f"  {'PACKAGE':<35} {'CONDA':<14} {'UPSTREAM':<14} {'SOURCE':<8} "
        f"{'LAG':<7} {'DOWNLOADS':>11}  {'C/H':>6}"
    )
    out.append("  " + "─" * 120)
    for r in rows:
        c = r.get("vuln_critical_affecting_current") or 0
        h = r.get("vuln_high_affecting_current") or 0
        risk = f"{c}/{h}" if (c or h) else "—"
        dl = r.get("total_downloads")
        dl_s = f"{dl:,}" if dl is not None else "—"
        out.append(
            f"  {r['conda_name']:<35} {(r['latest_conda_version'] or '?')[:13]:<14} "
            f"{(r['upstream_version'] or '?')[:13]:<14} "
            f"{(r['upstream_source'] or '?'):<8} "
            f"{r['lag_label']:<7} {dl_s:>11}  {risk:>6}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find conda-forge feedstocks behind their PyPI counterpart."
    )
    parser.add_argument("--maintainer", default=None,
                        help="Restrict to packages where HANDLE is a maintainer")
    parser.add_argument("--limit", type=int, default=50,
                        help="Maximum rows (default 50)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of a formatted table")
    args = parser.parse_args()

    rows = query(maintainer=args.maintainer, limit=args.limit)
    # Drop the internal sort key from JSON / dict output
    for r in rows:
        r.pop("_priority", None)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.maintainer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
