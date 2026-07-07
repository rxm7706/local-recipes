#!/usr/bin/env python3
"""license-map-gap — propose _LICENSE_TO_SPDX entries by finding raw PyPI
license strings that currently normalize to nothing (a mapping-gap sibling
for the in-code free-text→SPDX map).

`conda_forge_atlas._LICENSE_TO_SPDX` maps ~36 lowercased free-text PyPI
license forms to canonical SPDX IDs; `_normalize_license_to_spdx()` returns
None for anything it doesn't cover, silently degrading the Phase R/S license
readiness score. This CLI closes the DISCOVERY gap only — it scans
`pypi_intelligence` for `license_raw` values that stored `license_spdx = NULL`
(the map missed), ranks them by how many packages carry each, and emits:

  likely  a single vendored-SPDX-id candidate is a whole-token match in the
          form → a ready-to-paste `"<form>": "<SPDX-id>",` line
  report  zero or several candidates → the form + candidate set, for a human
          to pick the SPDX target

NO fuzzy matching — a wrong license mapping is a correctness bug, so the
target is only ever a conservative hint the human confirms. Accept/reject
stays with git review; this tool NEVER writes conda_forge_atlas.py. Fully
offline: reads `pypi_intelligence` only. Exit code 0 always (report tool).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from conda_forge_atlas import open_db, _LICENSE_TO_SPDX  # noqa: E402
from _sbom import _spdx_id_enum  # noqa: E402

# SPDX expression (not a single-ID map entry) — same idea as spdx_schema_gap.
_EXPRESSION_RE = re.compile(r"[()]|(?:^|\s)(?:AND|OR|WITH)(?:\s|$)")
# A non-word char (whitespace / punctuation) or string edge — for whole-token
# candidate matching so "isc" doesn't match inside "basiclicense".
_MAX_LEN = 60          # longer than this = a pasted full license text, not a form
_JUNK_SUBSTRINGS = ("see ", "http://", "https://", "copyright", "\n")


def _is_junk(form: str) -> bool:
    low = form.lower().strip()
    if not low or low == "unknown" or len(form) > _MAX_LEN:
        return True
    if any(j in low for j in _JUNK_SUBSTRINGS):
        return True
    if _EXPRESSION_RE.search(form):     # compound expression → not one entry
        return True
    return False


def _unmapped_licenses(conn) -> dict[str, int]:
    """{license_raw: package_count} for rows the map missed (license_spdx
    NULL) with a non-empty raw form. Reads the version-truth view
    `v_pypi_intelligence_valid` (schema v29 ORPHAN_RULE) so the gap reflects
    non-orphaned intelligence rows only."""
    counts: dict[str, int] = {}
    for raw, n in conn.execute(
            "SELECT license_raw, COUNT(*) FROM v_pypi_intelligence_valid "
            "WHERE license_spdx IS NULL AND license_raw IS NOT NULL "
            "AND TRIM(license_raw) != '' GROUP BY license_raw"):
        counts[str(raw)] = int(n)
    return counts


def _candidates(form: str, enum_by_lower: dict[str, str]) -> list[str]:
    """Vendored SPDX ids whose lowercased id is a whole-token match inside the
    lowercased form. Conservative hint only — never an auto-commit."""
    low = form.lower()
    hits: list[str] = []
    for lid, canon in enum_by_lower.items():
        if len(lid) < 3:                     # skip 2-char ids (too noisy)
            continue
        if re.search(r"(?:^|[^0-9a-z])" + re.escape(lid) + r"(?:$|[^0-9a-z])", low):
            hits.append(canon)
    return sorted(set(hits))


def classify(unmapped: dict[str, int], enum: set[str],
             seed: dict[str, str]) -> list[dict[str, Any]]:
    """One proposal per un-mapped, non-junk, not-already-seeded form.
    `likely` = exactly one candidate; else `report`."""
    enum_by_lower = {e.lower(): e for e in enum}
    proposals: list[dict[str, Any]] = []
    for form, count in unmapped.items():
        if form.lower() in seed or _is_junk(form):
            continue
        cands = _candidates(form, enum_by_lower)
        proposals.append({
            "license_raw": form,
            "packages": count,
            "candidates": cands,
            "confidence": "likely" if len(cands) == 1 else "report",
            "suggested_spdx": cands[0] if len(cands) == 1 else None,
        })
    proposals.sort(key=lambda p: (-p["packages"], p["license_raw"].lower()))
    return proposals


def render_map_lines(proposals: list[dict[str, Any]]) -> str:
    """Ready-to-paste `_LICENSE_TO_SPDX` lines for the `likely` tier (single
    candidate). The operator verifies each target before committing."""
    rows = [p for p in proposals if p["confidence"] == "likely"]
    if not rows:
        return ""
    lines = ["  # add to _LICENSE_TO_SPDX (single-candidate; VERIFY each target):"]
    for p in rows:
        lines.append(f'  "{p["license_raw"].lower()}": "{p["suggested_spdx"]}",'
                     f'   # {p["packages"]} package(s)')
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Propose _LICENSE_TO_SPDX entries by ranking raw PyPI "
                    "license strings that normalize to nothing. READ-ONLY: "
                    "never writes conda_forge_atlas.py.")
    from conda_forge_atlas import DB_PATH
    ap.add_argument("--db", type=Path, default=DB_PATH,
                    help=f"Path to atlas DB (default: {DB_PATH})")
    ap.add_argument("--limit", type=int, default=0,
                    help="Cap proposals per tier (0 = no cap)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Write the map-line snippets to FILE instead of stdout")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Machine-readable summary on stdout")
    args = ap.parse_args(argv)

    enum = set(_spdx_id_enum())
    conn = open_db(path=args.db)
    try:
        proposals = classify(_unmapped_licenses(conn), enum, _LICENSE_TO_SPDX)
    finally:
        conn.close()

    if args.limit > 0:
        capped: list[dict[str, Any]] = []
        for tier in ("likely", "report"):
            capped.extend(
                [p for p in proposals if p["confidence"] == tier][:args.limit])
        proposals = capped

    summary = {
        "map_entries": len(_LICENSE_TO_SPDX),
        "unmapped_forms": len(proposals),
        "counts": {
            "likely": sum(1 for p in proposals if p["confidence"] == "likely"),
            "report": sum(1 for p in proposals if p["confidence"] == "report"),
        },
        "proposals": proposals,
    }
    snippets = render_map_lines(proposals)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(snippets, encoding="utf-8")
    if args.as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"license-map-gap: {len(proposals)} unmapped license form(s) "
              f"({summary['counts']['likely']} likely / "
              f"{summary['counts']['report']} report) — "
              f"{len(_LICENSE_TO_SPDX)} currently mapped")
        if snippets and args.out is None:
            print(snippets, end="")
        elif args.out is not None:
            print(f"snippets written to {args.out}")
        report = [p for p in proposals if p["confidence"] == "report"]
        if report:
            top = "; ".join(
                f"{p['license_raw']} ({p['packages']}"
                f"{' → ' + '/'.join(p['candidates']) if p['candidates'] else ''})"
                for p in report[:8])
            print(f"  report (pick a target): {top}"
                  f"{' …' if len(report) > 8 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
