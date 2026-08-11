#!/usr/bin/env python3
"""Mutation-only: stamp the deferred-work anonymous-entry grandfather baseline.

Epic 7 ("deferred-work visibility") is teaching Doctor's deferred-work
detector (``pyforge.doctor.sources.chain::gather_deferred_work``) to see
anonymous ``- source_spec:`` bullets on the gitignored Tier-3 file, not just
the tracked ledger (Story 7.3). Turning that check on cold would red every
pre-existing anonymous entry across the fleet at once -- measured live at
authoring time: marshal 207, doctor 72, steward 71, atlas 54, warden 41,
herald 33, mason 22, scribe 6. This script stamps each project's CURRENT
count of anonymous Tier-3 entries into a committed baseline at a dated
cut-off, so Story 7.3's eventual comparison can treat "existed at the
cut-off" as grandfathered and red only on a genuinely NEW anonymous entry.

This script does not yet wire into anything -- no detector reads the file
it stamps. That is Story 7.3's job. This story produces the data file only
(mirrors ``scripts/spec_surface_check.py``'s own split between the read-only
Doctor-source verdict and this kind of mutation-only residual, Story 6.9).

Duplicates (never imports) ``pyforge.doctor.sources.chain``'s
``_ENTRY_RE``/``_ANON_RE``/``_anonymous()`` -- every ``scripts/*.py`` file
must run standalone with plain ``python``, no package install required,
exactly the reason ``spec_surface_check.py`` already duplicates its own
algorithm instead of importing ``pyforge.doctor``.

Usage (plain `python`, no pixi task -- mirrors `spec_surface_check.py`'s own
precedent):
        python scripts/deferred_work_baseline.py --write-baseline [--project SLUG ...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TIER3_REL = Path("implementation-artifacts") / "deferred-work.md"
BASELINE = REPO_ROOT / "scripts" / ".deferred-work-baseline.json"

# Verbatim shape from chain.py:_ENTRY_RE / _ANON_RE / _anonymous -- see this
# script's own module docstring for why this is a duplicate, not an import.
_ENTRY_RE = re.compile(r"^#{2,4}\s+(DW-[A-Za-z0-9][A-Za-z0-9-]*)", re.M)
_ANON_RE = re.compile(r"^-\s+source_spec:", re.M)


def _anonymous(path: Path) -> list[int]:
    """Line numbers of entries with no ``## DW-<id>`` heading of their own --
    duplicated verbatim (in shape) from ``chain.py::_anonymous`` so the
    stamped count matches exactly what that function would report."""
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[int] = []
    field_taken = False
    in_entry = False
    for n, ln in enumerate(lines, 1):
        if _ENTRY_RE.match(ln):
            field_taken, in_entry = False, True
        elif re.match(r"^#{1,6}\s", ln):
            field_taken, in_entry = False, False
        elif _ANON_RE.match(ln):
            if in_entry and not field_taken:
                field_taken = True
            else:
                out.append(n)
    return out


def _live_state() -> dict[str, int]:
    """Every discovered project's CURRENT anonymous-Tier-3-entry count -- the
    ground truth ``--write-baseline`` merges into the committed file. A
    project is "discovered" only when its Tier-3 file
    (``implementation-artifacts/deferred-work.md``) actually exists; a
    project directory with no Tier-3 file yet contributes no entry."""
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    out: dict[str, int] = {}
    if not projects_dir.is_dir():
        return out
    for proj in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        t3_path = proj / TIER3_REL
        if not t3_path.is_file():
            continue
        out[proj.name] = len(_anonymous(t3_path))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp the anonymous-Tier-3-entry grandfather baseline")
    ap.add_argument("--project", action="append", metavar="SLUG", default=None,
                    help=("limit --write-baseline to this project (repeatable). "
                          "WITHOUT it the stamp covers EVERY discovered project, "
                          "which accepts every other project's growth as "
                          "\"always was this way.\""))
    args = ap.parse_args()

    if args.project and not args.write_baseline:
        ap.error("--project only makes sense with --write-baseline")

    if not args.write_baseline:
        print(
            "this script stamps scripts/.deferred-work-baseline.json, the count "
            "of pre-existing anonymous Tier-3 `- source_spec:` entries per "
            "project at a dated cut-off, so a future detector change (Story "
            "7.3) can grandfather them instead of redding on day one. No "
            "detector reads this file yet. Pass --write-baseline "
            "[--project SLUG ...] to stamp it.",
            file=sys.stderr,
        )
        return 2

    current = _live_state()
    existing = (json.loads(BASELINE.read_text(encoding="utf-8"))
                if BASELINE.exists() else {})

    # SCOPED stamping, mirroring spec_surface_check.py's own S-13.1
    # rationale: an all-or-nothing stamp would silently accept every OTHER
    # project's growth as "always was this way."
    if args.project:
        unknown = sorted(set(args.project) - set(current))
        if unknown:
            print(f"unknown project(s): {', '.join(unknown)}\n"
                  f"known: {', '.join(sorted(current))}", file=sys.stderr)
            return 2
        # MERGE, never rewrite: building from `current` alone would silently
        # drop every project this invocation did not name.
        merged = dict(existing)
        for name in args.project:
            merged[name] = current[name]
        scope = f"{len(set(args.project))} project(s): {', '.join(sorted(set(args.project)))}"
    else:
        # MERGE here too, never a full rebuild: `_live_state()` only sees
        # projects whose gitignored Tier-3 scratch happens to be present
        # (readable) on THIS machine/checkout right now -- a partial clone,
        # a worktree that hasn't backlinked every project, or one unreadable
        # directory all silently shrink `current` below the full fleet.
        # Reproduced live during review: a bare run from a checkout with
        # only 1 of 8 projects' Tier-3 scratch present collapsed an 8-entry
        # committed baseline down to 1, discarding grandfather protection
        # for the other 7. A previously-stamped project this run cannot
        # currently see is left untouched, never dropped; only a project
        # this run CAN see gets its count refreshed.
        merged = {**existing, **current}
        scope = (f"{len(current)} project(s) discovered locally "
                 f"({len(merged)} total after merge)")
    BASELINE.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"baseline stamped: {BASELINE.relative_to(REPO_ROOT)} — {scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
