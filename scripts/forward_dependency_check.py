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

# `### Story 2.3: Title *(optional trailing note)*` — the ONE canonical shape
# (EXEMPLAR-STANDARD INV-5), used by all 8 stations.
#
# This deliberately carries NO station-specific accommodation, and that is the
# point. On 2026-08-08 an alias-first branch was added here to see atlas's
# `### Story A1 (2.1):` headings — making this the FOURTH codebase carrying a
# private guess at one station's shape, alongside `docs/dashboard/generate.py`,
# `dashboard_drift_check.py` and `chain_completeness_check.py`. The branch was
# removed the same day once atlas's data was normalized instead: 38 headings,
# 32 ledger keys, 32 story-spec filenames and 32 board ids renamed in lockstep,
# so there is exactly one convention left to parse. INV-5's rule is that a
# detector reads the (now empty) legacy register rather than re-deriving an
# accommodation — a detector that pattern-matches a station-specific shape
# inline is non-conformant even when it works.
#
# A station that regresses to an unparseable heading is NOT silently clean: zero
# parsed stories means zero declarations, which reports UNMEASURED (or
# NO-DISPATCH when its ledger proves nothing is actionable) — never MEASURED.
STORY_HEADING_RE = re.compile(
    r"^### Story (?P<pe>\d+)\.(?P<pn>\d+[a-z]?): ?"
    r"(?P<title>.*?)(?:\s*\*\(.*?\)\*)?\s*$",
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
#
# An OPTIONAL `<station>:` prefix marks a cross-station reference. It must be
# honoured rather than ignored: forward-ness is an ordering claim about ONE
# station's epics, so reading another station's `S-2.1` as this station's epic 2
# is simply a wrong answer. That misread is live today — atlas 12.2 declares
# `Steward S-2.1` (space, no colon), which still parses as atlas's own epic 2;
# it is harmless only because 2 < 12 and atlas's epic 2 is shipped. Rewriting it
# as `steward:S-2.1` is part of the grammar migration, not of this regex.
DEP_RE = re.compile(
    r"(?:(?P<station>[a-z][a-z0-9-]*):)?S-(?P<epic>\d+)\.(?P<num>\d+[a-z]?|\*)", re.I)
LEDGER_STORY_RE = re.compile(r"^  (\d+)-(\d+)([a-z]?)-\S+: (\S+)$", re.M)
# An explicit "no dependency" declaration, which is READABLE — it resolves to the
# empty set rather than being unparseable. Covers marshal/doctor/steward's `—` and
# atlas/mason's prose-qualified forms (`none (runs manually, …)`, `nothing (first
# story of the effort)`). The lookahead is `(?![\w-])` and NOT `\b`: `\b` after a
# non-word character like `—` can never match at end-of-string, which silently
# misfiled steward's two `—` declarations as prose on the first attempt.
NO_DEP_RE = re.compile(r"^\s*(?:—|–|-|none|nothing|n/?a)(?![\w-])", re.I)

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
        out.append((int(m.group("pe")), m.group("pn"),
                    (m.group("title") or "").strip(), deps))
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
    partial: list[tuple[str, int, int, list[str]]] = []  # slug, readable, total, examples
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
        # NO-DISPATCH is checked FIRST because it dominates every other class: a
        # station with nothing actionable cannot suffer this defect at all,
        # whatever grammar its Deps fields use. It is a measured claim about the
        # LEDGER — never a claim that the Deps fields parsed clean. A ledger we
        # could not read stays UNMEASURED: no data is not the same as no risk.
        if ledger and not any(st in ACTIONABLE_STATUSES for st in ledger.values()):
            no_dispatch.append((slug, len(ledger)))
            continue

        declared = [d for _, _, _, d in station_stories if d]
        if not declared:
            unmeasured.append(slug)
            continue

        # Coverage is keyed on READABLE references, not on the presence of Deps
        # TEXT. The old gate (`any(deps)`) reported mason measured-and-clean with
        # 0 of 30 declarations parseable — a false green in the detector's own
        # bookkeeping, for months. A declaration is readable when DEP_RE resolves
        # it, or when it explicitly declares no dependency.
        prose = [d for d in declared if not DEP_RE.findall(d) and not NO_DEP_RE.match(d)]
        if prose:
            readable = len(declared) - len(prose)
            partial.append((slug, readable, len(declared), prose[:2]))
        else:
            measured += 1

        for epic, num, title, deps in station_stories:
            # Only SAME-station references can be forward: "a later epic" is an
            # ordering claim within one station's epics doc. A cross-station ref
            # is a real dependency the per-station picker also cannot see, but
            # that is a different defect and an explicit SPEC non-goal (no
            # general dependency graph) — it must not be judged by this test.
            same_station = [(m.group("epic"), m.group("num"))
                            for m in DEP_RE.finditer(deps) if not m.group("station")]
            forward = sorted({de for de, dn in same_station if int(de) > epic})
            if not forward:
                continue
            key = f"{epic}-{num}"
            status = ledger.get(key)
            if status in ACTIONABLE_STATUSES or status is None:
                findings.append((slug, key, title, deps, status or "MISSING FROM LEDGER"))
            elif args.verbose:
                print(f"  ok  {slug}/{key} (forward dep on epic {forward}, "
                      f"status={status!r}, already non-actionable)")

    coverage = (f"{measured} measured, {len(partial)} partial, "
                f"{len(no_dispatch)} no-dispatch, {len(unmeasured)} unmeasured")
    print(f"forward-dependency -- {coverage}\n")

    if partial:
        for slug, readable, total, examples in partial:
            print(f"  ◐ [partial] {slug}: only {readable} of {total} dependency "
                  f"declaration(s) are machine-readable — the rest state a real "
                  f"dependency in a grammar DEP_RE cannot parse, so they are NOT "
                  f"checked for forward-epic references.")
            for ex in examples:
                print(f"        e.g. {ex[:88]!r}")
            print("        → rewrite as `S-<epic>.<num>` / `S-<epic>.*` / "
                  "`<station>:S-<epic>.<num>`; prose may follow as trailing context.")
        print()

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
