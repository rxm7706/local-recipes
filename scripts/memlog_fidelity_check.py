#!/usr/bin/env python3
"""Memlog fidelity harness — inventory and scratch-derive comparison for Epic 44.13.

Re-derivation itself is LLM-driven (`bmad-spec`, `bmad-architecture`). This script
covers the deterministic half: discover every in-scope artifact, verify structural
prerequisites, diff scratch re-derives against live rendered files, and print the
headless invocation recipe (`render_skill.py` + `BMAD_ACTIVE_PROJECT`).

Usage:
  python scripts/memlog_fidelity_check.py              # inventory (default)
  python scripts/memlog_fidelity_check.py --json
  python scripts/memlog_fidelity_check.py --compare SCRATCH_ROOT
  python scripts/memlog_fidelity_check.py --invoke-hints

Exit codes: 0 = structural pass (compare may still report drift); 1 = findings.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

DETECTOR = {"scope": "repo"}

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "_bmad-output" / "projects"
STATIONS = (
    "pyforge-atlas",
    "pyforge-doctor",
    "pyforge-herald",
    "pyforge-marshal",
    "pyforge-mason",
    "pyforge-scribe",
    "pyforge-steward",
    "pyforge-warden",
)
SPEC_GLOB = "planning-artifacts/specs/spec-*/SPEC.md"
SPINE_GLOB = "planning-artifacts/architecture/*/ARCHITECTURE-SPINE.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class ArtifactRow:
    kind: str  # "spec" | "spine"
    station: str
    rel_dir: str
    live_path: str
    memlog_path: str | None
    memlog_present: bool
    live_sha256: str | None = None
    scratch_path: str | None = None
    scratch_sha256: str | None = None
    byte_equivalent: bool | None = None
    diff_lines: int | None = None
    notes: list[str] = field(default_factory=list)


def _discover_specs() -> list[ArtifactRow]:
    rows: list[ArtifactRow] = []
    for station in STATIONS:
        base = PROJECTS / station
        if not base.is_dir():
            continue
        for spec_md in sorted(base.glob(SPEC_GLOB)):
            memlog = spec_md.parent / ".memlog.md"
            rows.append(
                ArtifactRow(
                    kind="spec",
                    station=station,
                    rel_dir=spec_md.parent.relative_to(ROOT).as_posix(),
                    live_path=spec_md.relative_to(ROOT).as_posix(),
                    memlog_path=(
                        memlog.relative_to(ROOT).as_posix() if memlog.exists() else None
                    ),
                    memlog_present=memlog.is_file(),
                    live_sha256=_sha256(spec_md) if spec_md.is_file() else None,
                )
            )
    return rows


def _discover_spines() -> list[ArtifactRow]:
    rows: list[ArtifactRow] = []
    for station in STATIONS:
        base = PROJECTS / station
        if not base.is_dir():
            continue
        for spine in sorted(base.glob(SPINE_GLOB)):
            memlog = spine.parent / ".memlog.md"
            rows.append(
                ArtifactRow(
                    kind="spine",
                    station=station,
                    rel_dir=spine.parent.relative_to(ROOT).as_posix(),
                    live_path=spine.relative_to(ROOT).as_posix(),
                    memlog_path=(
                        memlog.relative_to(ROOT).as_posix() if memlog.exists() else None
                    ),
                    memlog_present=memlog.is_file(),
                    live_sha256=_sha256(spine) if spine.is_file() else None,
                )
            )
    return rows


def _scratch_path(scratch_root: Path, live_rel: str) -> Path | None:
    """Map live artifact path to scratch re-derive layout."""
    live = ROOT / live_rel
    if not live.is_file():
        return None
    # Preferred: mirror repo-relative path under scratch root.
    candidate = scratch_root / live_rel
    if candidate.is_file():
        return candidate
    # Fallback: same basename in a folder named like the spec/arch dir.
    parent_name = live.parent.name
    for alt in (
        scratch_root / parent_name / live.name,
        scratch_root / live.name,
    ):
        if alt.is_file():
            return alt
    return None


def _compare_rows(rows: list[ArtifactRow], scratch_root: Path) -> None:
    for row in rows:
        scratch = _scratch_path(scratch_root, row.live_path)
        if scratch is None:
            row.notes.append("scratch re-derive missing")
            row.byte_equivalent = False
            continue
        row.scratch_path = scratch.relative_to(ROOT).as_posix()
        row.scratch_sha256 = _sha256(scratch)
        row.byte_equivalent = row.live_sha256 == row.scratch_sha256
        if not row.byte_equivalent:
            live_text = (ROOT / row.live_path).read_text(encoding="utf-8").splitlines(
                keepends=True
            )
            scratch_text = scratch.read_text(encoding="utf-8").splitlines(keepends=True)
            row.diff_lines = sum(
                1
                for _ in difflib.unified_diff(
                    live_text, scratch_text, fromfile="live", tofile="scratch", n=0
                )
            )


def _structural_findings(rows: list[ArtifactRow]) -> list[str]:
    findings: list[str] = []
    for row in rows:
        if not row.memlog_present:
            findings.append(
                f"missing-memlog: {row.kind} {row.station}/{Path(row.rel_dir).name} "
                f"(live={row.live_path})"
            )
    return findings


def _invoke_hints() -> str:
    return "\n".join(
        [
            "# Headless re-derive (per artifact; never scripts/bmad-switch)",
            "",
            "export BMAD_ACTIVE_PROJECT=<station>",
            "export PYTHONPATH=\"$PWD/_bmad/scripts:$PYTHONPATH\"",
            "",
            "# Render skill instructions (read-only snapshot):",
            "uv run _bmad/scripts/render_skill.py \\",
            "  --project-root \"$PWD\" \\",
            "  --skill .claude/skills/bmad-spec",
            "",
            "uv run _bmad/scripts/render_skill.py \\",
            "  --project-root \"$PWD\" \\",
            "  --skill .claude/skills/bmad-architecture",
            "",
            "# Memlog writes (append-only):",
            "uv run _bmad/scripts/memlog.py append \\",
            "  --workspace _bmad-output/projects/<station>/planning-artifacts/specs/spec-<slug> \\",
            "  --type change --text \"<one-line gist>\"",
            "",
            "# Re-derive to scratch (LLM session — marshal HarnessSkillInvoker pattern):",
            "#   cursor agent --trust --workspace \"$PWD\" \\",
            "#     \"Run bmad-spec headlessly; BMAD_ACTIVE_PROJECT=<station>; \\",
            "#      write SPEC.md under $SCRATCH/<rel-path>; never hand-edit live SPEC.md\"",
            "",
            "# Compare scratch vs live:",
            "python scripts/memlog_fidelity_check.py --compare \"$SCRATCH\"",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    ap.add_argument(
        "--compare",
        metavar="SCRATCH_ROOT",
        type=Path,
        help="diff scratch re-derives against live rendered files",
    )
    ap.add_argument(
        "--invoke-hints",
        action="store_true",
        help="print headless bmad-spec / bmad-architecture invocation recipe",
    )
    ap.add_argument(
        "--station",
        action="append",
        metavar="SLUG",
        help="limit inventory/compare to one station (repeatable)",
    )
    args = ap.parse_args(argv)

    if args.invoke_hints:
        print(_invoke_hints())
        return 0

    stations = set(args.station) if args.station else set(STATIONS)
    rows = [r for r in _discover_specs() + _discover_spines() if r.station in stations]

    if args.compare:
        scratch = args.compare.resolve()
        if not scratch.is_dir():
            print(f"ERROR: scratch root not a directory: {scratch}", file=sys.stderr)
            return 1
        _compare_rows(rows, scratch)

    findings = _structural_findings(rows)
    drift = [
        r
        for r in rows
        if r.byte_equivalent is False
        or (args.compare is None and not r.memlog_present)
    ]

    summary = {
        "stations": sorted(stations),
        "spec_count": sum(1 for r in rows if r.kind == "spec"),
        "spine_count": sum(1 for r in rows if r.kind == "spine"),
        "missing_memlog": sum(1 for r in rows if not r.memlog_present),
        "compare_mode": args.compare is not None,
        "byte_equivalent": sum(1 for r in rows if r.byte_equivalent is True),
        "byte_drift": sum(1 for r in rows if r.byte_equivalent is False),
        "scratch_missing": sum(
            1 for r in rows if r.byte_equivalent is False and "scratch re-derive missing" in r.notes
        ),
        "findings": findings,
        "artifacts": [asdict(r) for r in rows],
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"memlog-fidelity: {summary['spec_count']} specs, "
            f"{summary['spine_count']} spines across {len(stations)} station(s)"
        )
        print(f"  missing memlog: {summary['missing_memlog']}")
        if args.compare:
            print(
                f"  byte-equivalent: {summary['byte_equivalent']}, "
                f"drift: {summary['byte_drift']}, "
                f"scratch missing: {summary['scratch_missing']}"
            )
        for msg in findings:
            print(f"  FINDING: {msg}")
        if args.compare:
            for row in rows:
                if row.byte_equivalent is False:
                    print(
                        f"  DRIFT: {row.live_path} "
                        f"(diff_lines={row.diff_lines}, scratch={row.scratch_path})"
                    )

    if findings or (args.compare and summary["byte_drift"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
