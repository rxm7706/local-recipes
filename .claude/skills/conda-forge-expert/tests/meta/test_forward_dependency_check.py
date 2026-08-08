"""Meta-test: forward-dependency-check classifies coverage honestly.

The detector exists to stop `bmad-loop` dispatching a story whose documented
dependency lives in a later epic. Two of its own defects, both found 2026-08-08,
are what these tests pin:

  * atlas's alias-first headings (`### Story A1 (2.1):`) never matched, so all 46
    of its stories were invisible and it reported UNMEASURED;
  * coverage was gated on any Deps *text* rather than a parseable *reference*, so
    mason reported measured-and-clean with 0 of 30 declarations readable.

Mirrors test_spec_surface_check.py's shape for a repo-level `scripts/` detector.
"""
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
CHECKER = REPO_ROOT / "scripts" / "forward_dependency_check.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
fdc = pytest.importorskip(
    "forward_dependency_check",
    reason="requires bmad_loop (pixi run -e local-recipes)",
)


# --- heading grammar -------------------------------------------------------

@pytest.mark.parametrize("line, epic, num", [
    ("### Story 2.3: Marshal-shaped plain heading", "2", "3"),
    ("### Story 2.3a: A lettered sub-story", "2", "3a"),
    ("### Story A1 (2.1): atlas alias-first", "2", "1"),
    ("### Story J2 (12.2): two-digit epic via parenthetical", "12", "2"),
    ("### Story 0.1 (1.1): numeric alias — parenthetical must win", "1", "1"),
])
def test_both_heading_shapes_resolve(line, epic, num):
    m = fdc.STORY_HEADING_RE.match(line)
    assert m, f"heading did not parse: {line!r}"
    assert (m.group("pe") or m.group("ae")) == epic
    assert (m.group("pn") or m.group("an")) == num


def test_plain_branch_wins_over_alias_branch():
    """A plain heading whose TITLE holds a `(n.n)` must not be read as an alias."""
    m = fdc.STORY_HEADING_RE.match("### Story 8.5: Marker deletion (10.2) discussed")
    assert m and m.group("pe") == "8" and m.group("pn") == "5"
    assert m.group("ae") is None


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
    r = subprocess.run([sys.executable, str(CHECKER)],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    assert r.returncode == 0, f"detector reported findings:\n{r.stdout}\n{r.stderr}"


def test_no_station_reads_unmeasured():
    """atlas was the last one, and it was a parsing defect rather than missing data."""
    r = subprocess.run([sys.executable, str(CHECKER)],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    assert "[unmeasured]" not in r.stdout, r.stdout


def test_last_line_carries_the_coverage_breakdown():
    """scripts/detectors.py lifts tail[-1][:200] as this detector's registry
    summary, so the final line must never read as fully measured."""
    r = subprocess.run([sys.executable, str(CHECKER)],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    last = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-1]
    for word in ("measured", "partial", "no-dispatch", "unmeasured"):
        assert word in last, f"{word!r} missing from summary line: {last!r}"


def test_atlas_parses_and_is_not_silently_clean():
    """0 -> 46 stories. Atlas must appear, and must NOT claim full coverage:
    only 7 of its 43 declarations are machine-readable."""
    d = fdc.PROJECTS / "pyforge-atlas"
    stories = [t for ef in fdc.find_epics_files(d) for t in fdc.story_deps(ef)]
    assert len(stories) >= 40, f"atlas parsed only {len(stories)} stories"
    declared = [x[3] for x in stories if x[3]]
    prose = [x for x in declared
             if not fdc.DEP_RE.findall(x) and not fdc.NO_DEP_RE.match(x)]
    assert prose, "atlas's prose declarations vanished — did coverage regress to any-text?"


def test_marshals_three_known_forward_deps_are_still_found():
    """The original defect. 2-3 -> epic 3, 2-7 -> epic 4, 8-5 -> epic 10."""
    d = fdc.PROJECTS / "pyforge-marshal"
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
