#!/usr/bin/env python3
"""cwe-seed-gap — propose cwe_categories_seed.json entries by finding MITRE
CWEs that currently default to 'Other' but whose name a keyword heuristic
can confidently classify (a mapping-gap sibling for the CWE seed).

The seed (data/cwe_categories_seed.json) maps 67 CWE-IDs to cf_atlas
categories; every CWE not in it lands in the 'Other' bucket of the
`cwe_categories` atlas table. This CLI closes the DISCOVERY gap only —
it scans catalog rows mapped to 'Other', matches each `cwe_name` against a
curated keyword heuristic for the 7 real categories, and emits ready-to-paste
seed lines with two confidence tiers:

  strong  a category-defining phrase (`sql injection`, `use after free`,
          `path traversal`) — high confidence
  weak    a generic word (`injection`, `memory`, `authorization`) — verify

Accept/reject stays with git review — this tool NEVER writes the seed.
Fully offline: reads the `cwe_categories` table only (populated by
`fetch-cwe-catalog`). Exit code 0 always (report tool).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from conda_forge_atlas import open_db  # noqa: E402
from cwe_catalog_fetcher import _load_seed_mapping  # noqa: E402


# ── keyword heuristic (auditable; advisory — the human picks the category) ──
#
# Derived from the seed's own category descriptions. `strong` = a phrase that
# names the weakness class; `weak` = a generic word that merely hints at it.
# Categories are checked in PRECEDENCE order so overlapping names resolve
# sensibly (e.g. "OS Command Injection" → RCE via "command injection",
# not Injection via the bare "injection" weak word).

PRECEDENCE = ["Memory-Safety", "Traversal", "RCE", "Injection",
              "Auth-Bypass", "Info-Disclosure", "DoS"]

STRONG: dict[str, list[str]] = {
    "Memory-Safety": [
        "buffer overflow", "buffer underflow", "out-of-bounds",
        "out of bounds", "use after free", "double free", "null pointer",
        "integer overflow", "integer underflow", "heap-based", "stack-based",
        "memory corruption", "type confusion", "wild pointer",
        "improper restriction of operations within the bounds",
        "uninitialized",
    ],
    "Traversal": [
        "path traversal", "directory traversal", "link following",
        "absolute path traversal", "relative path traversal",
    ],
    "RCE": [
        "code execution", "command injection", "os command",
        "arbitrary code", "code injection", "argument injection",
        "expression language injection",
    ],
    "Injection": [
        "cross-site scripting", "sql injection", "xml external entity",
        "ldap injection", "xpath injection", "crlf", "template injection",
        "format string", "deserialization of untrusted data",
    ],
    "Auth-Bypass": [
        "authentication bypass", "authorization bypass",
        "improper authentication", "missing authentication",
        "improper access control", "improper authorization",
        "incorrect authorization", "privilege management",
        "incorrect permission", "improper privilege",
    ],
    "Info-Disclosure": [
        "information exposure", "sensitive information",
        "information disclosure", "exposure of", "cleartext storage",
        "cleartext transmission", "insertion of sensitive information",
    ],
    "DoS": [
        "denial of service", "resource exhaustion",
        "uncontrolled resource consumption", "infinite loop",
        "reachable assertion", "excessive iteration",
        "allocation of resources",
    ],
}

WEAK: dict[str, list[str]] = {
    "Memory-Safety": ["dereference", "memory"],
    "Traversal": ["traversal"],
    "RCE": [],
    "Injection": ["injection", "serialization"],
    "Auth-Bypass": ["authentication", "authorization", "privilege",
                    "permission"],
    "Info-Disclosure": ["exposure", "leak"],
    "DoS": ["denial of service"],
}


def classify_cwe(name: str) -> tuple[str, str, str] | None:
    """(category, tier, matched_keyword) or None. Strong beats weak globally;
    within a tier the PRECEDENCE order breaks ties."""
    lname = (name or "").lower()
    for cat in PRECEDENCE:
        for kw in STRONG[cat]:
            if kw in lname:
                return cat, "strong", kw
    for cat in PRECEDENCE:
        for kw in WEAK[cat]:
            if kw in lname:
                return cat, "weak", kw
    return None


def _other_cwes(conn) -> list[tuple[str, str]]:
    """(cwe_id, cwe_name) for catalog rows currently bucketed 'Other'."""
    rows = conn.execute(
        "SELECT cwe_id, cwe_name FROM cwe_categories "
        "WHERE cf_atlas_category = 'Other' ORDER BY cwe_id").fetchall()
    return [(r[0], r[1] or "") for r in rows]


def _other_impact(conn) -> int:
    """Packages whose vuln_cwe_categories_json carries a non-zero 'Other'
    bucket — the universe cost of the un-seeded weaknesses."""
    n = 0
    for (blob,) in conn.execute(
            "SELECT vuln_cwe_categories_json FROM packages "
            "WHERE vuln_cwe_categories_json IS NOT NULL"):
        try:
            data = json.loads(blob)
            if isinstance(data, dict) and int(data.get("Other", 0)) > 0:
                n += 1
        except (ValueError, TypeError):
            continue
    return n


def classify(candidates: list[tuple[str, str]],
             seed: dict[str, str]) -> list[dict[str, Any]]:
    """One proposal per un-seeded, keyword-classifiable 'Other' CWE. Seed
    coverage is a belt-and-braces exclusion — a seeded CWE would not be
    'Other' in the catalog, but a direct caller may pass a raw seed."""
    proposals: list[dict[str, Any]] = []
    for cwe_id, cwe_name in candidates:
        if cwe_id in seed:
            continue
        hit = classify_cwe(cwe_name)
        if hit is None:
            continue
        proposals.append({
            "cwe_id": cwe_id,
            "cwe_name": cwe_name,
            "category": hit[0],
            "confidence": hit[1],
            "matched": hit[2],
        })
    return proposals


def render_seed_lines(proposals: list[dict[str, Any]]) -> str:
    """Ready-to-paste JSON seed lines, grouped strong-first. The operator
    verifies the category against the CWE's MITRE page before committing."""
    lines: list[str] = []
    for tier in ("strong", "weak"):
        rows = [p for p in proposals if p["confidence"] == tier]
        if not rows:
            continue
        lines.append(f"  // proposed ({tier}) — verify each against its MITRE "
                     "CWE page before adding")
        for p in rows:
            lines.append(f'  "{p["cwe_id"]}": "{p["category"]}",'
                         f'   // {p["cwe_name"]}  [{p["matched"]}]')
    return "\n".join(lines) + ("\n" if lines else "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Propose cwe_categories_seed.json entries by keyword-"
                    "classifying MITRE CWEs currently bucketed 'Other'. "
                    "READ-ONLY: never writes the seed.")
    from cwe_catalog_fetcher import _SEED_PATH
    ap.add_argument("--db", type=Path, default=None,
                    help="Path to atlas DB (default: the skill data dir)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Cap proposals per tier (0 = no cap)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write the seed-line snippets to FILE instead of stdout")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Machine-readable summary on stdout")
    args = ap.parse_args(argv)

    if args.db is None:
        from conda_forge_atlas import DB_PATH
        args.db = DB_PATH

    seed = _load_seed_mapping(_SEED_PATH)
    conn = open_db(path=args.db)
    try:
        proposals = classify(_other_cwes(conn), seed)
        impact = _other_impact(conn)
    finally:
        conn.close()

    if args.limit > 0:
        capped: list[dict[str, Any]] = []
        for tier in ("strong", "weak"):
            capped.extend(
                [p for p in proposals if p["confidence"] == tier][:args.limit])
        proposals = capped

    summary = {
        "seed_entries": len(seed),
        "other_cwes_classifiable": len(proposals),
        "packages_with_other_bucket": impact,
        "counts": {
            "strong": sum(1 for p in proposals if p["confidence"] == "strong"),
            "weak": sum(1 for p in proposals if p["confidence"] == "weak"),
        },
        "proposals": proposals,
    }
    snippets = render_seed_lines(proposals)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(snippets, encoding="utf-8")
    if args.as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"cwe-seed-gap: {len(proposals)} classifiable 'Other' CWE(s) "
              f"({summary['counts']['strong']} strong / "
              f"{summary['counts']['weak']} weak) — {len(seed)} seeded; "
              f"'Other' bucket affects {impact} package(s)")
        if snippets and args.out is None:
            print(snippets, end="")
        elif args.out is not None:
            print(f"snippets written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
