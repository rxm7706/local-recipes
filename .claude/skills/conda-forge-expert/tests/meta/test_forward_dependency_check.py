"""Meta-test: forward-dependency-check classifies coverage honestly.

The detector exists to stop `bmad-loop` dispatching a story whose documented
dependency lives in a later epic. Two of its own defects, both found 2026-08-08,
are what these tests pin:

  * atlas's alias-first headings (`### Story A1 (2.1):`) never matched, so all 46
    of its stories were invisible and it reported UNMEASURED;
  * coverage was gated on any Deps *text* rather than a parseable *reference*, so
    mason reported measured-and-clean with 0 of 30 declarations readable.

Story 6.9: `scripts/forward_dependency_check.py` retired into
`pyforge.doctor.sources.deps` (ported verbatim in behavior, Story 6.7,
AD-13 — the module RESTATES `ACTIONABLE_STATUSES` rather than importing
`bmad_loop`, so unlike the deleted script this port needs no harness at
all). This file now imports the port directly instead of the deleted
script; the three tests that used to subprocess-run the script and parse
its printed report now call `gather_forward_dependency` and read its
`Finding` tuple instead — `coverage` is always the LAST finding the gather
appends (its own module comment: "ALWAYS emitted, never only on a clean
run"), the equivalent of the origin's `tail[-1]` summary line.

Mirrors test_spec_surface_check.py's shape for a repo-level `scripts/` detector.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
PROJECTS = REPO_ROOT / "_bmad-output" / "projects"

fdc = pytest.importorskip(
    "pyforge.doctor.sources.deps",
    reason="pyforge.doctor not present (skill used standalone)",
)


# --- heading grammar -------------------------------------------------------

@pytest.mark.parametrize("line, epic, num", [
    ("### Story 2.3: A plain heading", "2", "3"),
    ("### Story 2.3a: A lettered sub-story", "2", "3a"),
    ("### Story 12.2: A two-digit epic", "12", "2"),
    ("### Story 1.1: The former 0.1, normalized", "1", "1"),
])
def test_the_canonical_heading_resolves(line, epic, num):
    m = fdc.STORY_HEADING_RE.match(line)
    assert m, f"heading did not parse: {line!r}"
    assert m.group("pe") == epic and m.group("pn") == num


@pytest.mark.parametrize("line", [
    "### Story A1 (2.1): atlas's former alias-first shape",
    "### Story J2 (12.2): likewise",
    "### Story 0.1 (1.1): numeric alias with a disagreeing parenthetical",
])
def test_the_retired_alias_shape_is_no_longer_accepted(line):
    """INV-5: one convention. The alias branch was this detector's private
    accommodation for one station — the FOURTH such copy in the repo — and was
    deleted once atlas's data was normalized on 2026-08-08. Re-adding it would
    reintroduce the root cause, so this asserts its absence deliberately.

    Not silently clean if a station regresses: zero parsed headings means zero
    declarations, which reports UNMEASURED, never MEASURED.
    """
    assert fdc.STORY_HEADING_RE.match(line) is None


def test_a_parenthetical_in_the_title_is_not_an_id():
    m = fdc.STORY_HEADING_RE.match("### Story 8.5: Marker deletion (10.2) discussed")
    assert m and m.group("pe") == "8" and m.group("pn") == "5"


# --- dependency grammar ----------------------------------------------------

def test_story_epic_and_cross_station_forms_parse():
    got = [(m.group("station"), m.group("epic"), m.group("num"))
           for m in fdc.DEP_RE.finditer("S-5.1, S-3.*, steward:S-2.1")]
    assert got == [(None, "5", "1"), (None, "3", "*"), ("steward", "2", "1")]


@pytest.mark.parametrize("text", ["—", "–", "-", "none", "nothing (first story)",
                                  "none (runs manually, ahead of Epic 7)", "n/a"])
def test_explicit_no_dependency_is_readable(text):
    """`\\b` after an em-dash can never match at end-of-string — the bug that
    misfiled steward's two `—` declarations as prose."""
    assert fdc.NO_DEP_RE.match(text), f"should read as no-dependency: {text!r}"


@pytest.mark.parametrize("text", ["A1, A2.", "Story 1.4 (informs cost)",
                                  "Epic 3 complete", "the three open questions"])
def test_prose_declarations_are_not_readable(text):
    assert not fdc.DEP_RE.findall(text)
    assert not fdc.NO_DEP_RE.match(text)


# --- the live tree ---------------------------------------------------------

def test_detector_exits_zero_on_the_live_tree():
    from pyforge.doctor.models import DoctorStatus
    findings = fdc.gather_forward_dependency(REPO_ROOT)
    fail = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not fail, f"detector reported findings:\n" + "\n".join(
        f"[{f.check}] {f.message}" for f in fail)


def test_no_station_reads_unmeasured():
    """atlas was the last one, and it was a parsing defect rather than missing data."""
    findings = fdc.gather_forward_dependency(REPO_ROOT)
    unmeasured = [f for f in findings if f.check == "unmeasured"]
    assert not unmeasured, unmeasured


def test_last_line_carries_the_coverage_breakdown():
    """`coverage` is always the LAST finding `gather_forward_dependency`
    appends -- the equivalent of scripts/detectors.py's own `tail[-1][:200]`
    registry summary over the origin script's printed report."""
    findings = fdc.gather_forward_dependency(REPO_ROOT)
    last = findings[-1]
    assert last.check == "coverage"
    for word in ("measured", "partial", "no-dispatch", "unmeasured"):
        assert word in last.message, f"{word!r} missing from coverage message: {last.message!r}"


def test_atlas_parses_and_is_not_silently_clean():
    """0 -> 46 stories. Atlas must appear, and must NOT claim full coverage:
    only 7 of its 43 declarations are machine-readable."""
    d = PROJECTS / "pyforge-atlas"
    stories = [t for ef in fdc.find_epics_files(d) for t in fdc.story_deps(ef)]
    assert len(stories) >= 40, f"atlas parsed only {len(stories)} stories"
    declared = [x[3] for x in stories if x[3]]
    prose = [x for x in declared
             if not fdc.DEP_RE.findall(x) and not fdc.NO_DEP_RE.match(x)]
    assert prose, "atlas's prose declarations vanished — did coverage regress to any-text?"


def test_marshals_three_known_forward_deps_are_still_found():
    """The original defect. 2-3 -> epic 3, 2-7 -> epic 4, 8-5 -> epic 10."""
    d = PROJECTS / "pyforge-marshal"
    found = {}
    for ef in fdc.find_epics_files(d):
        for epic, num, _title, deps in fdc.story_deps(ef):
            same = [(m.group("epic"), m.group("num"))
                    for m in fdc.DEP_RE.finditer(deps) if not m.group("station")]
            fwd = sorted({e for e, _ in same if int(e) > epic})
            if fwd:
                found[f"{epic}-{num}"] = fwd
    assert found.get("2-3") == ["3"], found
    assert found.get("2-7") == ["4"], found
    assert found.get("8-5") == ["10"], found


def test_cross_station_ref_is_not_judged_as_forward():
    """`steward:S-9.1` from epic 2 is a later NUMBER but another station's epic —
    forward-ness is an ordering claim within one station."""
    same = [(m.group("epic"), m.group("num"))
            for m in fdc.DEP_RE.finditer("steward:S-9.1") if not m.group("station")]
    assert same == [], "cross-station ref leaked into the same-station set"


# --- a forward dep only blocks while it is UNSATISFIED ---------------------

def test_a_finished_forward_dep_no_longer_blocks():
    """Ordering alone used to be the whole test, so a story could never leave
    `blocked` once its later-epic dep actually landed — the ledger had to keep
    asserting "blocked" about ready work, or this detector went red. Found live
    2026-08-08 when doctor's S-6.1 completed and unblocked S-5.2."""
    assert fdc._dep_satisfied({"6-1": "done"}, "6", "1") is True
    assert fdc._dep_satisfied({"6-1": "backlog"}, "6", "1") is False


def test_a_dep_absent_from_the_ledger_is_not_satisfied():
    """Conservative by construction: unknown is not done, so an unreadable or
    incomplete ledger can never launder a real forward dependency."""
    assert fdc._dep_satisfied({}, "6", "1") is False
    assert fdc._dep_satisfied({"6-2": "done"}, "6", "1") is False


@pytest.mark.parametrize("ledger, expected", [
    ({"6-1": "done", "6-2": "done"}, True),
    ({"6-1": "done", "6-2": "backlog"}, False),
    ({}, False),  # no stories for that epic at all — never vacuously satisfied
])
def test_whole_epic_ref_is_satisfied_only_when_every_story_is_done(ledger, expected):
    """`S-6.*` is the grammar's whole-epic form; one unfinished story keeps it
    blocking, and an epic with no ledger stories is NOT a satisfied dependency
    (that shape would make an unreadable ledger look green)."""
    assert fdc._dep_satisfied(ledger, "6", "*") is expected


def test_epic_rollup_keys_do_not_count_as_stories():
    """The ledger carries `epic-6: in-progress` rollups alongside real stories;
    counting one as a story would make `S-6.*` unsatisfiable forever."""
    assert fdc._dep_satisfied({"6-1": "done", "epic-6": "in-progress"}, "6", "*") is True
