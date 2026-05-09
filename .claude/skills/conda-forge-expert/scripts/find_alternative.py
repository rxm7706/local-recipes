#!/usr/bin/env python3
"""
find-alternative — Suggest healthier conda-forge packages for one that's
archived / abandoned / behind upstream.

Strategy (no ML, no embeddings):
  1. Pull the source package's `conda_summary`, `conda_keywords`, and any
     dependent set from Phase J. Tokenize summary into a bag of terms.
  2. For every candidate (active, not-archived, non-self), compute a
     similarity score:
       - keyword Jaccard overlap          (weight 3)
       - summary term Jaccard overlap     (weight 2)
       - shared dependents (Phase J)      (weight 4)
       - shared maintainers               (weight 1)
  3. Filter to candidates with a non-trivial score, recent uploads, and
     non-zero lifetime downloads. Rank by combined score × recency factor.

CLI:
  find-alternative <name> [--limit N] [--json]

Pixi:
  pixi run -e local-recipes find-alternative -- vllm-nccl-cu12
  pixi run -e local-recipes find-alternative -- dbt
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"


_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with",
    "is", "are", "be", "this", "that", "from", "as", "by", "at", "it",
    "package", "library", "module", "tool", "tools", "python", "py",
    "client", "lib", "support", "via", "based", "uses", "use", "using",
    "implementation", "wrapper", "interface", "api",
}
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text)
            if len(t) > 2 and t.lower() not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def find_alternatives(name: str, limit: int = 10) -> list[dict[str, Any]]:
    if not DB_PATH.exists():
        print(f"cf_atlas.db not found at {DB_PATH}.", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. Pull source package fields
    src = conn.execute(
        "SELECT conda_name, conda_summary, conda_keywords, "
        "       latest_conda_upload, feedstock_archived "
        "FROM packages WHERE conda_name = ? LIMIT 1",
        (name,),
    ).fetchone()
    if src is None:
        return []
    src_terms = _tokenize(src["conda_summary"])
    src_keywords: set[str] = set()
    if src["conda_keywords"]:
        try:
            kw = json.loads(src["conda_keywords"])
            if isinstance(kw, list):
                src_keywords = {str(k).lower() for k in kw if k}
        except (json.JSONDecodeError, TypeError):
            pass
    src_dependents = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT source_conda_name FROM dependencies "
            "WHERE target_conda_name = ?",
            (name,),
        )
    }
    src_maintainers = {
        r[0] for r in conn.execute(
            "SELECT m.handle FROM package_maintainers pm "
            "JOIN maintainers m ON m.id = pm.maintainer_id "
            "WHERE pm.conda_name = ?",
            (name,),
        )
    }

    # 2. Candidates: active non-archived non-self with summary or keywords
    sql = (
        "SELECT p.conda_name, p.conda_summary, p.conda_keywords, "
        "       p.latest_conda_version, p.latest_conda_upload, "
        "       p.total_downloads, p.feedstock_archived "
        "FROM packages p "
        "WHERE p.conda_name IS NOT NULL "
        "  AND p.conda_name != ? "
        "  AND p.latest_status = 'active' "
        "  AND COALESCE(p.feedstock_archived, 0) = 0 "
        "  AND (p.conda_summary IS NOT NULL OR p.conda_keywords IS NOT NULL)"
    )
    candidates: list[dict[str, Any]] = []
    now_ts = int(dt.datetime.now().timestamp())
    for r in conn.execute(sql, (name,)):
        cand_terms = _tokenize(r["conda_summary"])
        cand_kw: set[str] = set()
        if r["conda_keywords"]:
            try:
                kw = json.loads(r["conda_keywords"])
                if isinstance(kw, list):
                    cand_kw = {str(k).lower() for k in kw if k}
            except (json.JSONDecodeError, TypeError):
                pass
        kw_score = _jaccard(src_keywords, cand_kw)
        term_score = _jaccard(src_terms, cand_terms)
        if kw_score == 0 and term_score == 0:
            continue
        # Shared-dependent and shared-maintainer joins
        dep_score = 0.0
        if src_dependents:
            cand_dependents = {
                r2[0] for r2 in conn.execute(
                    "SELECT DISTINCT source_conda_name FROM dependencies "
                    "WHERE target_conda_name = ?",
                    (r["conda_name"],),
                )
            }
            dep_score = _jaccard(src_dependents, cand_dependents)
        maint_score = 0.0
        if src_maintainers:
            cand_maintainers = {
                r3[0] for r3 in conn.execute(
                    "SELECT m.handle FROM package_maintainers pm "
                    "JOIN maintainers m ON m.id = pm.maintainer_id "
                    "WHERE pm.conda_name = ?",
                    (r["conda_name"],),
                )
            }
            maint_score = _jaccard(src_maintainers, cand_maintainers)
        # Combine: keyword=3, summary=2, dependents=4, maintainer=1
        score = (3 * kw_score + 2 * term_score + 4 * dep_score + 1 * maint_score)
        if score < 0.10:
            continue
        # Recency factor: 1.0 if uploaded within 30d, decaying linearly to 0
        # over 5 years.
        recency = 1.0
        if r["latest_conda_upload"]:
            age_days = (now_ts - r["latest_conda_upload"]) / 86400
            recency = max(0.0, 1.0 - age_days / (5 * 365))
        composite = score * (0.5 + 0.5 * recency) * (
            1.0 if (r["total_downloads"] or 0) > 0 else 0.5
        )
        candidates.append({
            "conda_name": r["conda_name"],
            "summary": r["conda_summary"],
            "version": r["latest_conda_version"],
            "uploaded_iso": (dt.datetime.fromtimestamp(r["latest_conda_upload"])
                             .strftime("%Y-%m-%d") if r["latest_conda_upload"] else None),
            "age_days": ((now_ts - r["latest_conda_upload"]) // 86400
                         if r["latest_conda_upload"] else None),
            "downloads": r["total_downloads"] or 0,
            "kw_score": round(kw_score, 3),
            "term_score": round(term_score, 3),
            "dep_score": round(dep_score, 3),
            "maint_score": round(maint_score, 3),
            "composite_score": round(composite, 3),
        })
    candidates.sort(key=lambda c: -c["composite_score"])
    return candidates[:limit]


def render_table(rows: list[dict[str, Any]], name: str) -> str:
    if not rows:
        return f"No alternatives found for {name}.\n"
    out: list[str] = []
    out.append(f"  Alternatives to {name}  ({len(rows)} candidate(s))")
    out.append("  " + "─" * 130)
    out.append(
        f"  {'PACKAGE':<37} {'VERSION':<14} {'UPLOADED':<11} {'AGE':>6} "
        f"{'DOWNLOADS':>11} {'SCORE':>6}  SUMMARY"
    )
    out.append("  " + "─" * 130)
    for r in rows:
        ver = (r.get("version") or "?")[:13]
        age = r.get("age_days") or 0
        sm = (r.get("summary") or "")[:45]
        out.append(
            f"  {r['conda_name']:<37} {ver:<14} "
            f"{(r['uploaded_iso'] or '?'):<11} {age:>4}d "
            f"{r['downloads']:>11,} {r['composite_score']:>6.2f}  {sm}"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Suggest maintained alternatives to a (likely archived) package."
    )
    parser.add_argument("name", help="conda_name to find alternatives for")
    parser.add_argument("--limit", type=int, default=10,
                        help="Maximum candidates (default 10)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of table")
    args = parser.parse_args()

    rows = find_alternatives(args.name, args.limit)
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        sys.stdout.write(render_table(rows, args.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
