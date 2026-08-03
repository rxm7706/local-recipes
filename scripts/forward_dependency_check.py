#!/usr/bin/env python3
"""Detector: a story's own documented dependency lives in a later epic, and
bmad-loop cannot see it.

THE DEFECT THIS CATCHES
------------------------
`bmad-loop`'s picker (`next_actionable` in `bmad_loop.sprintstatus`, called
from `engine.py`'s `_pick_next`) is a strict file-order scan within the
current epic. It has no `depends_on` concept at all -- confirmed against the
installed library source. It only ever checks whether a story's status in
`sprint-status.yaml` is in `ACTIONABLE_STATUSES` (imported below, never
restated, so this check stays tied to the real engine behavior).

A station's `epics.md`-family document can document a real per-story
dependency via a `**Deps:** S-X.Y` field under a `### Story E.N: Title`
heading. When that dependency names a story from a LATER epic than the one
declaring it, the engine cannot tell -- it will dispatch the dependent story
the moment its own epic's earlier stories clear, and burn a real dev attempt
(plus review cycles) on work that structurally cannot complete yet.

Found live 2026-08-03 in pyforge-marshal: `2-3` (deps `S-3.2`), `2-7` (deps
`S-4.1`), and `8-5` (deps `S-10.2`, in the absorbed genesis-installer epics
7-12) -- all three already documented their forward dependency in prose, it
just never reached the file the engine reads. See
docs/dreams/bmad-loop-forward-dependency-blindness.md.

THE FIX (not this detector's job -- this only catches a MISSING fix)
----------------------------------------------------------------------
Set the forward-dependent story's status to a non-standard value, `blocked`,
in the loop-home's live Tier-3 feed and promote it to the tracked twin via
`python3 scripts/promote_sprint_status.py`. Safe because
`bmad_loop.sprintstatus.load()` does not validate `status` against its own
declared `STORY_STATUSES` enum -- any string is accepted, and
`ACTIONABLE_STATUSES` naturally excludes anything that isn't
`backlog`/`ready-for-dev`. Same mechanism the pre-existing `optional`
retrospective status already relies on. Flip back to `backlog` once the real
dependency lands.

FORMAT COVERAGE -- and why an unparseable station is reported, not silently passed
------------------------------------------------------------------------------------
Not every station's `epics.md` uses the structured `### Story E.N:` +
`**Deps:**` format. Confirmed: `pyforge-warden`'s uses an older narrative
style (epic-level prose + a `**Stories (N):**` one-liner per epic) with ZERO
`**Deps:**` fields anywhere -- a mechanical extraction cannot run there. This
repo's fidelity-enforcement doctrine is "never claim green you did not
measure" (the dashboard's status strip has behaved this way since it was
built), so a station with no parseable Deps fields is reported as
UNMEASURED, distinct from a station that was checked and found clean.

EXIT
    0  every station with a parseable epics doc has no unmarked forward dependency
    1  at least one forward-dependent story is still actionable (backlog/ready-for-dev)
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "_bmad-output" / "projects"

# `### Story 2.3: Title *(optional trailing note)*` — heading only. Deliberately
# narrow to the plain `Story <epic>.<num>:` shape (marshal, mason's satellite):
# atlas uses a different alias-first heading (`### Story A1 (2.1): Title`) that
# this pattern will not match, and atlas is reported UNMEASURED rather than
# risking a wrong epic/num from a looser regex — atlas is already 100% shipped
# and was confirmed clean by direct read, so the coverage gap here is
# low-risk; a future station adding this heading shape should extend this
# pattern deliberately, not by loosening it blindly.
STORY_HEADING_RE = re.compile(r"^### Story (\d+)\.(\d+[a-z]?): ?(.*?)(?:\s*\*\(.*?\)\*)?\s*$", re.M)
# `**Deps:**` (marshal, mason's satellite) or `**Depends on:**` (atlas's field
# name, though atlas's headings never reach this point — see above), searched
# within the story's own block, not anchored to a line start: the field
# routinely shares a line with `**Type:**`/`**Effort:**` (`**Type:** feature
# • **Effort:** M • **Deps:** S-1.1, S-1.3`), so a line-boundary-anchored scan
# would never find it.
DEPS_FIELD_RE = re.compile(r"\*\*(?:Deps|Depends on):\*\* ?(.*?)(?:\s*•|\n|$)")
DEP_RE = re.compile(r"S-(\d+)\.(\d+[a-z]?)")
LEDGER_STORY_RE = re.compile(r"^  (\d+)-(\d+)([a-z]?)-\S+: (\S+)$", re.M)

# Same enum the engine actually reads — derived, not restated, so this check
# stays tied to real bmad-loop behavior if it ever changes upstream.
try:
    from bmad_loop.sprintstatus import ACTIONABLE_STATUSES
except ImportError:
    print("UNKNOWN: bmad_loop is not importable in this environment "
          "(run under `pixi run -e local-recipes`) — cannot judge actionability.")
    sys.exit(2)


def find_epics_files(project_dir: Path) -> list[Path]:
    pa = project_dir / "planning-artifacts"
    if not pa.is_dir():
        return []
    return sorted(
        p for p in pa.glob("epics*.md")
        if p.name != "epics-with-stories.md"  # derived summary, no Deps field
    )


def story_deps(epics_file: Path) -> list[tuple[int, str, str, str]]:
    """[(epic, num, title, deps_text)] for every structured story found.

    A story's Deps field must appear within its own block (up to the next
    `### Story` heading), searched anywhere in that text — not anchored to a
    line start, since it routinely shares a line with Type/Effort.
    """
    text = epics_file.read_text(encoding="utf-8")
    headings = list(STORY_HEADING_RE.finditer(text))
    out: list[tuple[int, str, str, str]] = []
    for i, m in enumerate(headings):
        block_end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        block = text[m.end():block_end]
        dm = DEPS_FIELD_RE.search(block)
        deps = dm.group(1).strip() if dm else ""
        out.append((int(m.group(1)), m.group(2), m.group(3).strip(), deps))
    return out


def ledger_statuses(ledger_path: Path) -> dict[str, str]:
    if not ledger_path.is_file():
        return {}
    return {
        f"{ep}-{num}{suf}": status
        for ep, num, suf, status in LEDGER_STORY_RE.findall(ledger_path.read_text())
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verbose", action="store_true", help="show every measured station")
    args = ap.parse_args()

    findings: list[tuple[str, str, str, str, str]] = []  # slug, key, title, deps, status
    unmeasured: list[str] = []
    measured = 0

    for project_dir in sorted(PROJECTS.glob("pyforge-*")):
        slug = project_dir.name
        epics_files = find_epics_files(project_dir)
        if not epics_files:
            continue
        ledger = ledger_statuses(project_dir / "planning-artifacts" / "sprint-status-ledger.yaml")

        station_stories: list[tuple[int, str, str, str]] = []
        for ef in epics_files:
            station_stories.extend(story_deps(ef))

        # "measured" requires at least one ACTUAL Deps field found, not just a
        # heading — several stations (doctor, scribe, steward, warden, mason's
        # main epics.md) carry marshal-shaped `### Story E.N:` headings with
        # NO Deps field anywhere. Counting those as measured would silently
        # report "0 findings" instead of the honest "can't tell" — the exact
        # false-green this detector exists to avoid elsewhere.
        if not any(deps for _, _, _, deps in station_stories):
            unmeasured.append(slug)
            continue
        measured += 1

        for epic, num, title, deps in station_stories:
            dep_ids = DEP_RE.findall(deps)
            forward = sorted({de for de, dn in dep_ids if int(de) > epic})
            if not forward:
                continue
            key = f"{epic}-{num}"
            status = ledger.get(key)
            if status in ACTIONABLE_STATUSES or status is None:
                findings.append((slug, key, title, deps, status or "MISSING FROM LEDGER"))
            elif args.verbose:
                print(f"  ok  {slug}/{key} (forward dep on epic {forward}, "
                      f"status={status!r}, already non-actionable)")

    print(f"forward-dependency -- {measured} station(s) measured "
          f"({len(unmeasured)} unmeasurable: format has no structured **Deps:** field)\n")

    if unmeasured:
        for slug in unmeasured:
            print(f"  ? [unmeasured] {slug}: epics doc has no structured **Deps:** field "
                  "— coverage unknown, not asserted clean.")
        print()

    if findings:
        for slug, key, title, deps, status in findings:
            print(f"  ✗ [forward-dep] {slug}/{key} ({title[:50]!r}): deps={deps!r} "
                  f"names a later epic, but ledger status is {status!r} (actionable). "
                  "Set to `blocked` in the loop-home's live Tier-3 feed, then "
                  "`python3 scripts/promote_sprint_status.py`.")
        print(f"\n{len(findings)} forward-dependent story(s) are still actionable — "
              "a plain `bmad-loop run` would dispatch them prematurely.")
        return 1

    print("OK: every forward-dependent story found is already non-actionable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
