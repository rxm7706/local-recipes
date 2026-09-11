#!/usr/bin/env python3
"""Mutation-only: ingest spec-frontmatter ``deferred:`` into tracked ledgers.

Hand-driven ``bmad-build-auto`` runs record deferrals in spec frontmatter (BMAD
6.11 era). bmad-loop's ``Engine._harvest_spec_deferrals`` bridges loop runs into
Tier-3 since 0.9.1; this script closes the hand-driven gap by promoting
findings into each project's tracked ``deferred-work-ledger.md`` without a
human relay (marshal Story 25.6 / CAP-6).

Story 21.8 / CAP-9: a deferral citing no resolvable repo path is **refused**
(not appended). Refusals go to stderr and count toward exit code 1 when nothing
ingestible remains for a project; partial batches still ingest resolvable rows.

Imports the pure helpers from ``pyforge.doctor.sources.chain`` — the same
algorithms the ``deferred-work`` detector uses — rather than duplicating
parsing or fingerprint logic.

Usage (plain ``python``, no pixi task — mirrors ``deferred_work_promote.py``):
        python scripts/deferred_work_intake.py --fix [--project SLUG ...]
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

for _pkg in ("pyforge-doctor", "pyforge-core"):
    _src = REPO_ROOT / "src" / "shared" / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from pyforge.doctor.sources.chain import (  # noqa: E402
    LegacyEntry,
    Tier3Shape,
    TRACKED_REL,
    discover_spec_frontmatter_deferrals,
    finding_has_resolvable_location,
    format_frontmatter_intake_entry,
    format_intake_location_refusal,
    frontmatter_deferral_in_tracked,
    mint_id_for_entry,
)

TIER3_REL = Path("implementation-artifacts") / "deferred-work.md"


@dataclass
class _Outcome:
    slug: str
    status: str  # "ingested" | "no-op" | "aborted" | "refused"
    message: str
    refused: int = 0


def _project_slug_map() -> dict[str, str]:
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return {}
    slug_map: dict[str, str] = {}
    for p in sorted(projects_dir.iterdir()):
        if not p.is_dir():
            continue
        short = p.name.removeprefix("pyforge-")
        if short in slug_map:
            raise ValueError(
                f"project directories {slug_map[short]!r} and {p.name!r} "
                f"both map to the same --project short slug {short!r}"
            )
        slug_map[short] = p.name
    return slug_map


def _discover_projects(slug_map: dict[str, str]) -> list[str]:
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    return [
        short
        for short, dirname in sorted(slug_map.items())
        if (projects_dir / dirname / Path("planning-artifacts") / "specs").is_dir()
    ]


def _legacy_entry_for_finding(spec_rel: str, summary: str) -> LegacyEntry:
    return LegacyEntry(
        shape=Tier3Shape.LEGACY_FLAT,
        id=None,
        start_line=0,
        end_line=0,
        fields={"source_spec": f"`{spec_rel}`", "summary": summary},
    )


def _ingest_project(slug: str, project_dir: Path) -> _Outcome:
    tracked_path = project_dir / TRACKED_REL
    tier3_path = project_dir / TIER3_REL

    findings = discover_spec_frontmatter_deferrals(project_dir)
    if not findings:
        return _Outcome(slug, "no-op", f"{slug}: no spec-frontmatter deferrals found")

    tracked_existed = tracked_path.is_file()
    tracked_text = tracked_path.read_text(encoding="utf-8") if tracked_existed else ""
    to_ingest = [f for f in findings if not frontmatter_deferral_in_tracked(f, tracked_text)]
    if not to_ingest:
        return _Outcome(
            slug,
            "no-op",
            f"{slug}: all {len(findings)} spec-frontmatter deferral(s) already in tracked ledger",
        )

    already_minted: set[str] = set()
    blocks: list[str] = []
    minted_ids: list[str] = []
    refused: list[str] = []
    for finding in to_ingest:
        if not finding_has_resolvable_location(finding):
            refused.append(format_intake_location_refusal(finding))
            continue
        try:
            new_id = mint_id_for_entry(
                _legacy_entry_for_finding(finding.spec_rel, finding.summary),
                slug,
                tier3_path if tier3_path.is_file() else tracked_path,
                tracked_path if tracked_path.is_file() else tier3_path,
                already_minted,
            )
        except ValueError as exc:
            for refusal in refused:
                print(refusal, file=sys.stderr)
            return _Outcome(
                slug,
                "aborted",
                f"{slug}: ABORTED, no write — could not mint id for {finding.spec_rel!r}: {exc}",
                refused=len(refused),
            )
        already_minted.add(new_id)
        minted_ids.append(new_id)
        blocks.append(format_frontmatter_intake_entry(new_id, finding))

    for refusal in refused:
        print(refusal, file=sys.stderr)

    if refused and not blocks:
        return _Outcome(
            slug,
            "refused",
            f"{slug}: refused {len(refused)} spec-frontmatter deferral(s) — no resolvable `location:`",
            refused=len(refused),
        )

    new_blocks_text = "\n".join(blocks)
    if tracked_text:
        prefix = tracked_text if tracked_text.endswith("\n") else tracked_text + "\n"
        if not prefix.endswith("\n\n"):
            prefix += "\n"
        new_text = prefix + new_blocks_text
    else:
        new_text = new_blocks_text

    tracked_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(tracked_path.parent), prefix=tracked_path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp_name, tracked_path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise

    ids_str = ", ".join(minted_ids)
    refused_note = (
        f"; refused {len(refused)} with no resolvable `location:`"
        if refused
        else ""
    )
    return _Outcome(
        slug,
        "ingested",
        f"{slug}: ingested {len(minted_ids)} spec-frontmatter deferral(s) — "
        f"{ids_str}{refused_note}",
        refused=len(refused),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--fix",
        action="store_true",
        help="append missing spec-frontmatter deferrals into tracked ledgers",
    )
    ap.add_argument(
        "--project",
        action="append",
        metavar="SLUG",
        default=None,
        help="limit --fix to this project short name (repeatable)",
    )
    args = ap.parse_args()

    if args.project and not args.fix:
        ap.error("--project only makes sense with --fix")

    if not args.fix:
        print(
            "this script ingests spec-frontmatter `deferred:` lists into each "
            "project's tracked deferred-work-ledger.md — the hand-driven "
            "build-auto gap bmad-loop's harvest does not cover. Nothing is "
            "written without --fix. Pass --fix [--project SLUG ...].",
            file=sys.stderr,
        )
        return 2

    try:
        slug_map = _project_slug_map()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.project:
        unknown = sorted(set(args.project) - set(slug_map))
        if unknown:
            print(
                f"unknown project(s): {', '.join(unknown)}\n"
                f"known: {', '.join(sorted(slug_map))}",
                file=sys.stderr,
            )
            return 2
        targets = sorted(set(args.project))
    else:
        targets = _discover_projects(slug_map)

    if not targets:
        print("no project with planning-artifacts/specs/ found — nothing to do")
        return 0

    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    exit_code = 0
    refused_total = 0
    for slug in targets:
        try:
            outcome = _ingest_project(slug, projects_dir / slug_map[slug])
        except Exception as exc:  # noqa: BLE001
            print(f"{slug}: ABORTED, no write — unexpected {exc.__class__.__name__}: {exc}")
            exit_code = 1
            continue
        print(outcome.message)
        refused_total += outcome.refused
        if outcome.status in {"aborted", "refused"}:
            exit_code = 1
    if refused_total:
        print(
            f"\n{refused_total} spec-frontmatter deferral(s) refused — each "
            f"cited no resolvable `location:`. Add a repo file path before "
            f"intake can promote the entry into the tracked ledger."
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
