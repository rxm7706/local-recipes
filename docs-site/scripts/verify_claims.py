#!/usr/bin/env python3
"""The dossier's one measurer (CAP-46; Stories 43.5, 43.7, 51.1): what the tree says each ``check:`` figure is.

The dossier states concrete figures -- lines of source and tests, file counts, Python floors, stories and epics done
-- and those are the claims that rot as the code grows. Every figure in a stats band and every row of the scale table
therefore carries ``check:`` and shows what this script counts, never a typed value: the Astro dossier loader
(``src/loaders/dossier-loader.ts``) runs ``--emit -`` at build and shows the result, and the content schema
(``src/content.config.ts``) refuses a stat with no ``check:`` (Story 51.1).

    python docs-site/scripts/verify_claims.py --emit -      # the measured values, as JSON

``--emit`` writes one JSON key per check key, one entry per section (``fleet`` for the hero's), and ``rows`` for a
table block carrying ``check: src_lines``, one entry per row's ``section:`` (a station id, or ``core``). The keys are
closed and structural, and every read is a static one under ``--root`` (no git call, no pattern a rename could zero).
An unknown key, a section with no package or sprint ledger, or a checked table row with no ``section:`` exits 2
naming it, so a number the measurer cannot produce never reaches the page. Story 43.7 retired the typed-value compare
and its ``site-verify`` advisory with the second generator: with every figure measured, there is nothing left to drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
#: the dossier sections that are stations, each measured from ``src/shared/packages/pyforge-<id>`` and counted from
#: ``_bmad-output/projects/pyforge-<id>/planning-artifacts/sprint-status-ledger.yaml``
STATIONS = ("atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden")
#: the one scale-table ``section:`` that is not a station: the shared leaf package, ``pyforge-core``
CORE = "core"
#: the check keys a section's stats may carry, the hero's, and a table block's
SECTION_CHECKS = ("src_lines", "test_lines", "python_floor", "stories_epics")
FLEET_CHECKS = ("fleet_src_lines", "fleet_test_lines", "fleet_stories_epics", "stations")
TABLE_CHECK = "src_lines"
LEDGER = Path("planning-artifacts") / "sprint-status-ledger.yaml"
#: a ledger's story keys (``<E>-<S>-...``) and epic keys (``epic-<n>``); ``epic-<n>-retrospective`` is neither
STORY, EPIC = re.compile(r"\d+-\d+-.+"), re.compile(r"epic-\d+")


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


def done(ledger: Path) -> tuple[int, int]:
    """The stories and the epics a sprint ledger's ``development_status`` holds at ``done``."""
    status = (yaml.safe_load(ledger.read_text(encoding="utf-8")) or {}).get("development_status") or {}
    keys = [str(key) for key, value in status.items() if value == "done"]
    return sum(1 for k in keys if STORY.fullmatch(k)), sum(1 for k in keys if EPIC.fullmatch(k))


def emit(doc: dict, packages: Path, projects: Path) -> dict[str, dict[str, dict]]:
    """The measured value of every ``check:`` figure, shaped as the dossier shows it: ``{check key: {section id:
    {"value": ..., "files": ...}}}`` (``fleet`` for the hero's; ``rows`` keyed by a checked table row's ``section:``).
    Raises ``ValueError`` naming an unknown key, a section whose package or ledger is missing, or an unnamed row."""
    memo: dict[str, dict] = {}

    def facts(section_id: str, where: str, known: tuple[str, ...] = STATIONS) -> dict:
        pkg_dir = packages / f"pyforge-{section_id}"
        if section_id not in known or not pkg_dir.is_dir():
            raise ValueError(f"{where}: no package {pkg_dir} to measure")
        return memo.setdefault(section_id, measure(pkg_dir))

    def ledger(section_id: str, where: str) -> tuple[int, int]:
        path = projects / f"pyforge-{section_id}" / LEDGER
        if section_id not in STATIONS or not path.is_file():
            raise ValueError(f"{where}: no sprint ledger {path} to count")
        return done(path)

    def shown(kind: str, section_id: str) -> dict:
        where = f"check {kind!r} in section {section_id!r}"
        if kind == "stories_epics":
            stories, epics = ledger(section_id, where)
            return {"value": f"{stories:,} / {epics:,}"}
        m = facts(section_id, where)
        if kind != "python_floor":
            return {"value": f"{m[kind]:,}", **({"files": m["src_files"]} if kind == "src_lines" else {})}
        floor = re.search(r"\d+\.\d+", m["requires_python"])
        return {"value": f"py{floor.group(0)}" if floor else m["requires_python"]}

    out: dict[str, dict[str, dict]] = {}
    for section in doc["sections"]:
        sid = section["id"]
        for block in section.get("blocks", []):
            if block.get("type") == "stats":
                for kind in [s["check"] for s in block.get("stats", []) if s.get("check")]:
                    if kind not in SECTION_CHECKS:
                        raise ValueError(f"unknown check {kind!r} in section {sid!r}")
                    out.setdefault(kind, {})[sid] = shown(kind, sid)
            elif block.get("type") == "table" and "check" in block:
                if block["check"] != TABLE_CHECK:
                    raise ValueError(f"unknown check {block['check']!r} on a table in section {sid!r}")
                for row in block.get("rows", []):
                    if not row.get("section"):
                        raise ValueError(f"checked table in section {sid!r}: row {row['cells'][0]!r} has no section:")
                    where = f"table row section {row['section']!r} in section {sid!r}"
                    m = facts(row["section"], where, (*STATIONS, CORE))
                    out.setdefault("rows", {})[row["section"]] = {"value": f"{m['src_lines']:,}", "files": m["src_files"]}
    stations = [s["id"] for s in doc["sections"] if s["id"] in STATIONS]
    for kind in [s["check"] for s in doc.get("stats", []) if s.get("check")]:
        if kind not in FLEET_CHECKS:
            raise ValueError(f"unknown check {kind!r} in the hero stats")
        if kind == "fleet_stories_epics":
            counts = [ledger(sid, f"check {kind!r} in section {sid!r}") for sid in stations]
            value = f"{sum(c[0] for c in counts):,} / {sum(c[1] for c in counts):,}"
        else:  # every station section is measured, so a missing package is refused before it is counted
            measured = [facts(sid, f"check {kind!r} in section {sid!r}") for sid in stations]
            if kind == "stations":
                value = str(len(measured))
            else:
                value = f"~{round(sum(m[kind.removeprefix('fleet_')] for m in measured) / 1000)}K"
        out[kind] = {"fleet": {"value": value}}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", default=str(ROOT / "docs-site" / "src" / "content" / "dossier" / "dossier.yml"))
    ap.add_argument("--root", type=Path, default=ROOT, help="the tree to measure (default: this repository)")
    ap.add_argument("--emit", metavar="PATH", required=True, help="write the measured values as JSON to PATH ('-': stdout)")
    args = ap.parse_args(argv)
    doc = yaml.safe_load(Path(args.content).read_text(encoding="utf-8"))
    try:
        measured = emit(doc, args.root / "src" / "shared" / "packages", args.root / "_bmad-output" / "projects")
    except ValueError as exc:
        print(f"verify_claims: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(measured, indent=2, sort_keys=True) + "\n"
    sys.stdout.write(payload) if args.emit == "-" else Path(args.emit).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
