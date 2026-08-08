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

COVERAGE -- four classes, keyed on MACHINE-READABLE references
---------------------------------------------------------------
This repo's fidelity-enforcement doctrine is "never claim green you did not
measure" (the dashboard's status strip has behaved this way since it was
built). Until 2026-08-08 this detector violated that doctrine in its own
bookkeeping: a station counted as MEASURED if any `**Deps:**` field held ANY
text, but the only grammar `DEP_RE` can actually read is `S-<epic>.<num>`.
A station whose dependencies are written in prose therefore parsed as
"measured, zero findings" while nothing had in fact been checked.

That was not hypothetical. Measured 2026-08-08: `pyforge-mason` carried 30
dependency declarations of which **zero** were machine-readable (`'Story 1.4
(informs cost of the "add two more recipes" branch)'`, `'none (runs manually,
ahead of Epic 7's automation)'`) and had been reported clean since this
detector shipped. `pyforge-atlas` is the same shape: 43 declarations, 5
readable, 38 prose (`'A1, A2.'`, `'B1 (Core pipeline datasets).'`, `'Epic 3
complete'`). The shipped SPEC's CAP-1 asserts both stations were "structured
enough to carry a mechanical Deps field" -- for mason that is simply false.

So coverage is classified on readable references, and a declaration the
detector cannot parse is counted against coverage rather than ignored:

  NO-DISPATCH  the tracked ledger positively shows zero stories in
               `ACTIONABLE_STATUSES`. The engine cannot dispatch a story that
               does not exist, so no forward dependency can fire regardless of
               Deps grammar. A *measured* fact read from the ledger, NOT a
               claim that this station's Deps fields are clean. Checked first
               because it dominates: nothing dispatchable means no risk.
  MEASURED     every declaration either resolved to `S-<epic>.<num>` or
               explicitly declared no dependency ("—", "none (…)"). The only
               genuine parse-clean claim.
  PARTIAL      at least one declaration states a real dependency in a grammar
               `DEP_RE` cannot read. Readable refs ARE still checked -- partial
               coverage beats none -- but the ratio is reported, so the station
               can never read as fully verified.
  UNMEASURED   no declaration at all, and work remains -- or the ledger is
               missing/unparseable, so actionability itself is unknown. No data
               is not the same as no risk.

NO-DISPATCH requires POSITIVE ledger evidence (>=1 story key parsed, none
actionable). A station whose ledger cannot be read falls to UNMEASURED, never
to NO-DISPATCH -- otherwise a missing file would read as reassurance.

Historical note: this docstring previously stated that `pyforge-warden`'s
epics doc used "an older narrative style (epic-level prose + a
`**Stories (N):**` one-liner per epic)". No longer true -- warden's doc now
carries 31 structured `### Story E.N:` headings; what it lacks is `**Deps:**`
fields, which is a different thing. Corrected 2026-08-08.

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

# Story headings, as TWO deliberately-enumerated shapes rather than one loose
# pattern. Alternation order matters: the plain branch is tried first, so a
# plain heading whose *title* happens to contain a `(<n>.<n>)` parenthetical can
# never be re-read as an alias.
#
#   plain        `### Story 2.3: Title *(optional trailing note)*`
#                marshal, mason's satellite, doctor, steward
#   alias-first  `### Story A1 (2.1): Scaffold the Kedro + pixi project`
#                `### Story J2 (12.2): Publish the real DAG continuously (FR-62)`
#                `### Story 0.1 (1.1): Generate legacy contextual skill`
#                atlas only. The PARENTHETICAL is canonical, not the alias.
#
# Why the parenthetical wins, and why that is safe despite atlas being
# internally inconsistent about it: atlas keys `0.1` from its *alias* (`0-1-…`)
# but `J1 (12.1)` from its *parenthetical* (`12-1-…`). A story whose derived key
# therefore misses the ledger is not a new hazard — a finding is only ever
# emitted for a story that HAS a `**Deps:**` field, and all five of atlas's sit
# in Epics 12–13, whose ledger keys are parenthetical-derived (verified against
# `sprint-status-ledger.yaml`, 2026-08-08). Everything else is skipped exactly
# as before.
#
# Superseded justification (kept so the reasoning is auditable): this pattern
# used to match only the plain shape, accepting atlas as UNMEASURED because
# "atlas is already 100% shipped and was confirmed clean by direct read." That
# premise expired — atlas has 8 actionable stories in Epics 12–13, which is
# precisely where its Deps fields live. The shipped SPEC's CAP-1 also already
# claims atlas was swept clean, so CAP-3's detector had to be able to verify
# that continuously instead of asserting it once by hand.
STORY_HEADING_RE = re.compile(
    r"^### Story (?:"
    r"(?P<pe>\d+)\.(?P<pn>\d+[a-z]?)"           # plain: 2.3
    r"|\S+ \((?P<ae>\d+)\.(?P<an>\d+[a-z]?)\)"  # alias-first: A1 (2.1)
    r"): ?(?P<title>.*?)(?:\s*\*\(.*?\)\*)?\s*$",
    re.M,
)
# `**Deps:**` (marshal, mason's satellite) or `**Depends on:**` (atlas's field
# name, though atlas's headings never reach this point — see above), searched
# within the story's own block, not anchored to a line start: the field
# routinely shares a line with `**Type:**`/`**Effort:**` (`**Type:** feature
# • **Effort:** M • **Deps:** S-1.1, S-1.3`), so a line-boundary-anchored scan
# would never find it.
DEPS_FIELD_RE = re.compile(r"\*\*(?:Deps|Depends on):\*\* ?(.*?)(?:\s*•|\n|$)")
# KNOWN LIMITATION -- `S-<epic>.<num>` has no station qualifier, so a
# cross-station dependency is silently read as one of the DECLARING station's own
# epics. Live example: atlas 12.2's `**Deps:** Steward S-2.1` parses as atlas's
# own epic 2. Harmless today only because 2 < 12 (so it is not "forward") and
# atlas's epic 2 is shipped anyway. Tracked as DW-FWDDEP-2026-08-08-1; fixing it
# means giving the field a station-qualified grammar, which is a contract change
# to every station's epics doc, not a regex tweak.
# `S-<epic>.<num>` for a story, `S-<epic>.*` for a whole-epic dependency.
# The epic-level form exists because real declarations legitimately depend on an
# entire epic ("Epic 3 complete", "Epics 4-6") and there was previously no
# machine-readable way to say so -- which pushed those declarations into prose,
# where this detector could not see them at all. Forward-ness is judged on the
# epic component either way, so `.*` needs no special handling downstream.
DEP_RE = re.compile(r"S-(\d+)\.(\d+[a-z]?|\*)")
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
        # Exactly one of the two heading branches matched (see STORY_HEADING_RE).
        epic = m.group("pe") or m.group("ae")
        num = m.group("pn") or m.group("an")
        out.append((int(epic), num, (m.group("title") or "").strip(), deps))
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
    no_dispatch: list[tuple[str, int]] = []  # slug, ledger story count
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
        # heading — several stations carry structured `### Story E.N:` headings
        # with NO Deps field anywhere (live: herald 47, scribe 9, warden 31).
        # Counting those as measured would silently report "0 findings" instead
        # of the honest "can't tell" — the exact false-green this detector
        # exists to avoid elsewhere.
        if not any(deps for _, _, _, deps in station_stories):
            # Split the two causes (see § COVERAGE). A station with nothing left
            # to dispatch cannot suffer this defect, and saying so is a measured
            # claim about the LEDGER — never a claim that its Deps fields parsed
            # clean. A ledger we could not read stays UNMEASURED.
            if ledger and not any(st in ACTIONABLE_STATUSES for st in ledger.values()):
                no_dispatch.append((slug, len(ledger)))
            else:
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

    coverage = (f"{measured} measured, {len(no_dispatch)} no-dispatch, "
                f"{len(unmeasured)} unmeasured")
    print(f"forward-dependency -- {coverage}\n")

    if no_dispatch:
        for slug, total in no_dispatch:
            print(f"  ○ [no-dispatch] {slug}: no structured **Deps:** field, but the "
                  f"tracked ledger shows 0 of {total} stories actionable — nothing can "
                  "be dispatched early. NOT a parse-clean claim.")
        print()

    if unmeasured:
        for slug in unmeasured:
            print(f"  ? [unmeasured] {slug}: epics doc has no structured **Deps:** field "
                  "and work remains (or its ledger is unreadable) — coverage unknown, "
                  "not asserted clean.")
        print()

    if findings:
        for slug, key, title, deps, status in findings:
            print(f"  ✗ [forward-dep] {slug}/{key} ({title[:50]!r}): deps={deps!r} "
                  f"names a later epic, but ledger status is {status!r} (actionable). "
                  "Set to `blocked` in the loop-home's live Tier-3 feed, then "
                  "`python3 scripts/promote_sprint_status.py`.")
        # Last non-empty line is lifted verbatim as this detector's registry
        # summary (scripts/detectors.py reads tail[-1][:200]) — it carries the
        # coverage breakdown so the fleet view can never read as fully measured.
        print(f"\n{len(findings)} forward-dependent story(s) are still actionable — "
              "a plain `bmad-loop run` would dispatch them prematurely. "
              f"[coverage: {coverage}]")
        return 1

    print(f"OK: no actionable forward-dependent story [{coverage}] — "
          "'no-dispatch' and 'unmeasured' assert nothing about Deps parse-cleanliness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
