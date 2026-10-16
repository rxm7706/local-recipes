#!/usr/bin/env python3
"""The dossier's one measurer (CAP-46; Stories 43.5, 43.7): what the source tree says each ``check:`` stat is.

The dossier states concrete figures -- lines of source, file counts, Python floors -- and those are the claims that
rot as the code grows. Every stat that carries ``check:`` therefore shows what this script counts, never a typed
value: the Astro dossier loader (``src/loaders/dossier-loader.ts``) runs ``--emit -`` at build and shows the result.

    python docs-site/scripts/verify_claims.py --emit -      # the measured values, as JSON

``--emit`` writes one JSON key per check key, one entry per section (``fleet`` for the hero's total); an unknown
check key or a station package it cannot find exits 2 naming it, so a number the measurer cannot produce never
reaches the page. Story 43.7 retired the typed-value compare and its ``site-verify`` advisory with the second
generator: with every checked number measured, there is nothing left to drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
#: the dossier sections that are stations, each measured from ``src/shared/packages/pyforge-<id>``
STATIONS = ("atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden")
#: the check keys a section's stats may carry, and the one the hero's total may carry
SECTION_CHECKS = ("src_lines", "test_lines", "python_floor")
FLEET_CHECK = "fleet_src_lines"


def measure(pkg_dir: Path) -> dict:
    """Count what the dossier claims to count, the way it counts it: ``*.py`` lines under ``src/`` and ``tests/``."""

    def files(root: Path) -> list[Path]:
        return list(root.rglob("*.py")) if root.exists() else []

    def lines(root: Path) -> int:
        return sum(len(p.read_bytes().splitlines()) for p in files(root))

    pyproject = pkg_dir / "pyproject.toml"
    floor = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8")) if pyproject.exists() else None
    return {
        "src_lines": lines(pkg_dir / "src"),
        "src_files": len(files(pkg_dir / "src")),
        "test_lines": lines(pkg_dir / "tests"),
        "requires_python": floor.group(1) if floor else "",
    }


def emit(doc: dict, packages: Path) -> dict[str, dict[str, dict]]:
    """The measured value of every ``check:`` stat, shaped as the dossier shows it: ``{check key: {section id:
    {"value": ..., "files": ...}}}`` (``fleet`` for the hero's total). Raises ``ValueError`` naming an unknown key or a
    section whose package is missing."""
    memo: dict[str, dict] = {}

    def facts(section_id: str, kind: str) -> dict:
        pkg_dir = packages / f"pyforge-{section_id}"
        if section_id not in STATIONS or not pkg_dir.is_dir():
            raise ValueError(f"check {kind!r} in section {section_id!r}: no package {pkg_dir} to measure")
        return memo.setdefault(section_id, measure(pkg_dir))

    out: dict[str, dict[str, dict]] = {}
    for section in doc["sections"]:
        blocks = [b for b in section.get("blocks", []) if b.get("type") == "stats"]
        for kind in [s["check"] for b in blocks for s in b.get("stats", []) if s.get("check")]:
            if kind not in SECTION_CHECKS:
                raise ValueError(f"unknown check {kind!r} in section {section['id']!r}")
            m = facts(section["id"], kind)
            floor = re.search(r"\d+\.\d+", m["requires_python"])
            shown = {"src_lines": f"{m['src_lines']:,}", "test_lines": f"{m['test_lines']:,}",
                     "python_floor": f"py{floor.group(0)}" if floor else m["requires_python"]}[kind]
            files = {"files": m["src_files"]} if kind == "src_lines" else {}
            out.setdefault(kind, {})[section["id"]] = {"value": shown, **files}
    for kind in [s["check"] for s in doc.get("stats", []) if s.get("check")]:
        if kind != FLEET_CHECK:
            raise ValueError(f"unknown check {kind!r} in the hero stats")
        total = sum(facts(s["id"], kind)["src_lines"] for s in doc["sections"] if s["id"] in STATIONS)
        out[kind] = {"fleet": {"value": f"~{round(total / 1000)}K"}}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", default=str(ROOT / "docs-site" / "src" / "content" / "dossier" / "dossier.yml"))
    ap.add_argument("--root", type=Path, default=ROOT, help="the tree to measure (default: this repository)")
    ap.add_argument("--emit", metavar="PATH", required=True, help="write the measured values as JSON to PATH ('-': stdout)")
    args = ap.parse_args(argv)
    doc = yaml.safe_load(Path(args.content).read_text(encoding="utf-8"))
    try:
        payload = json.dumps(emit(doc, args.root / "src" / "shared" / "packages"), indent=2, sort_keys=True) + "\n"
    except ValueError as exc:
        print(f"verify_claims: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(payload) if args.emit == "-" else Path(args.emit).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
