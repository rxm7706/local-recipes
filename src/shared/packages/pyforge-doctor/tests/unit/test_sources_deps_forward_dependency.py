"""``gather_forward_dependency`` — Story 6.7's port of forward_dependency_check.

Pins the behaviours the origin script's own two live defects (both found
2026-08-08) established, plus the ones the port itself introduces:

  * coverage is keyed on a parseable REFERENCE, not on Deps *text* — the old
    gate reported mason measured-and-clean with 0 of 30 declarations readable;
  * a forward reference only counts while UNSATISFIED — before that fix a story
    could never leave `blocked` once its later-epic dep actually landed;
  * NO-DISPATCH is decided before parse-cleanliness and is REPORTED, not merely
    counted (the port's own fix — see the module's no-dispatch comment);
  * the coverage line is always emitted, including on a red run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources.deps import (
    ACTIONABLE_STATUSES,
    gather_forward_dependency,
)


def _station(root: Path, slug: str, epics: str, ledger: str | None) -> Path:
    pa = root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    pa.mkdir(parents=True, exist_ok=True)
    (pa / "epics.md").write_text(epics, encoding="utf-8")
    if ledger is not None:
        (pa / "sprint-status-ledger.yaml").write_text(ledger, encoding="utf-8")
    return pa


def _by_check(findings, check):
    return [f for f in findings if f.check == check]


# --- the defect it exists to catch -----------------------------------------


def test_forward_dep_on_actionable_story_is_a_fail(tmp_path: Path) -> None:
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.3: Something\n**Type:** feature • **Deps:** S-3.2\n",
        "development-status:\n  2-3-something: backlog\n  3-2-later: backlog\n",
    )
    findings = gather_forward_dependency(tmp_path)
    fails = _by_check(findings, "forward-dep")
    assert len(fails) == 1
    assert fails[0].status is DoctorStatus.FAIL
    assert fails[0].source is Source.FORWARD_DEPENDENCY
    assert fails[0].evidence["story"] == "2-3"
    assert fails[0].evidence["forward_epics"] == ["3"]


def test_forward_dep_already_satisfied_is_not_reported(tmp_path: Path) -> None:
    """The 2026-08-08 fix: ordering alone is not the test. Once the later-epic
    dependency is done, the dependent story is free — otherwise the ledger had
    to keep asserting `blocked` about work that was ready, or this check went
    red forever."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.3: Something\n**Deps:** S-3.2\n",
        "development-status:\n  2-3-something: backlog\n  3-2-later: done\n",
    )
    assert not _by_check(gather_forward_dependency(tmp_path), "forward-dep")


def test_forward_dep_on_non_actionable_story_is_not_reported(tmp_path: Path) -> None:
    """`blocked` IS the prescribed fix, so a story already carrying it is the
    success case, not a finding."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.3: Something\n**Deps:** S-3.2\n",
        "development-status:\n  2-3-something: blocked\n  3-2-later: backlog\n",
    )
    assert not _by_check(gather_forward_dependency(tmp_path), "forward-dep")


def test_story_missing_from_ledger_still_reported(tmp_path: Path) -> None:
    """Absent is treated as actionable — conservative by construction."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.3: Something\n**Deps:** S-3.2\n",
        "development-status:\n  3-2-later: backlog\n",
    )
    fails = _by_check(gather_forward_dependency(tmp_path), "forward-dep")
    assert len(fails) == 1
    assert fails[0].evidence["ledger_status"] == "MISSING FROM LEDGER"


def test_backward_dependency_is_not_forward(tmp_path: Path) -> None:
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 3.1: Later\n**Deps:** S-2.1\n",
        "development-status:\n  3-1-later: backlog\n  2-1-earlier: backlog\n",
    )
    assert not _by_check(gather_forward_dependency(tmp_path), "forward-dep")


def test_cross_station_reference_is_not_judged(tmp_path: Path) -> None:
    """A qualified cross-station ref is a real dependency the picker also cannot
    see, but that is a different defect and an explicit SPEC non-goal."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.3: Something\n**Deps:** steward:S-9.1\n",
        "development-status:\n  2-3-something: backlog\n",
    )
    assert not _by_check(gather_forward_dependency(tmp_path), "forward-dep")


# --- whole-epic grammar ----------------------------------------------------


def test_whole_epic_ref_unsatisfied_when_any_story_open(tmp_path: Path) -> None:
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.1: A\n**Deps:** S-3.*\n",
        "development-status:\n  2-1-a: backlog\n  3-1-x: done\n  3-2-y: backlog\n",
    )
    assert len(_by_check(gather_forward_dependency(tmp_path), "forward-dep")) == 1


def test_whole_epic_ref_satisfied_when_all_done(tmp_path: Path) -> None:
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.1: A\n**Deps:** S-3.*\n",
        "development-status:\n  2-1-a: backlog\n  3-1-x: done\n  3-2-y: done\n",
    )
    assert not _by_check(gather_forward_dependency(tmp_path), "forward-dep")


def test_whole_epic_ref_with_no_stories_is_never_satisfied(tmp_path: Path) -> None:
    """An epic absent from the ledger must not read as a satisfied dependency —
    that would make an unreadable ledger look clean."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.1: A\n**Deps:** S-3.*\n",
        "development-status:\n  2-1-a: backlog\n",
    )
    assert len(_by_check(gather_forward_dependency(tmp_path), "forward-dep")) == 1


# --- coverage classes ------------------------------------------------------


def test_prose_declaration_reports_partial_not_measured(tmp_path: Path) -> None:
    """The mason false-green: Deps TEXT is not a readable REFERENCE."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.1: A\n**Deps:** after the installer lands\n",
        "development-status:\n  2-1-a: backlog\n",
    )
    findings = gather_forward_dependency(tmp_path)
    partial = _by_check(findings, "partial")
    assert len(partial) == 1
    assert partial[0].status is DoctorStatus.WARN
    assert partial[0].evidence["readable"] == 0
    assert partial[0].evidence["total"] == 1
    assert _by_check(findings, "coverage")[0].evidence["measured"] == 0


@pytest.mark.parametrize("none_form", ["—", "-", "none", "nothing", "n/a", "N/A"])
def test_explicit_no_dependency_is_readable(none_form: str, tmp_path: Path) -> None:
    """`—` resolves to the empty set rather than being unparseable. The lookahead
    is `(?![\\w-])` and not `\\b`, which silently misfiled steward's two `—`
    declarations as prose on the first attempt."""
    _station(
        tmp_path,
        "pyforge-x",
        f"### Story 2.1: A\n**Deps:** {none_form}\n",
        "development-status:\n  2-1-a: backlog\n",
    )
    findings = gather_forward_dependency(tmp_path)
    assert not _by_check(findings, "partial")
    assert _by_check(findings, "coverage")[0].evidence["measured"] == 1


def test_no_dispatch_is_reported_not_merely_counted(tmp_path: Path) -> None:
    """The port's own fix: a station that CANNOT suffer this defect must stay
    distinguishable from one that was never looked at."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.1: A\nno deps field here\n",
        "development-status:\n  2-1-a: done\n  2-2-b: done\n",
    )
    findings = gather_forward_dependency(tmp_path)
    nd = _by_check(findings, "no-dispatch")
    assert len(nd) == 1
    assert nd[0].status is DoctorStatus.OK
    assert nd[0].evidence["ledger_stories"] == 2
    assert not _by_check(findings, "unmeasured")


def test_no_dispatch_wins_over_partial(tmp_path: Path) -> None:
    """NO-DISPATCH dominates: nothing actionable means the defect is impossible,
    whatever grammar the Deps fields use."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.1: A\n**Deps:** prose only\n",
        "development-status:\n  2-1-a: done\n",
    )
    findings = gather_forward_dependency(tmp_path)
    assert _by_check(findings, "no-dispatch")
    assert not _by_check(findings, "partial")


def test_headings_without_deps_field_report_unmeasured(tmp_path: Path) -> None:
    """Structured headings with NO Deps field anywhere is 'can't tell', never
    'clean' — live for herald/scribe/warden."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.1: A\nsome prose\n",
        "development-status:\n  2-1-a: backlog\n",
    )
    findings = gather_forward_dependency(tmp_path)
    un = _by_check(findings, "unmeasured")
    assert len(un) == 1
    assert un[0].status is DoctorStatus.WARN


def test_unparseable_heading_is_not_silently_clean(tmp_path: Path) -> None:
    """A station regressing to a non-canonical heading reports UNMEASURED —
    zero parsed stories means zero declarations, never MEASURED."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story A1 (2.1): Alias-first\n**Deps:** S-3.2\n",
        "development-status:\n  2-1-a: backlog\n",
    )
    findings = gather_forward_dependency(tmp_path)
    assert _by_check(findings, "unmeasured")
    assert not _by_check(findings, "forward-dep")
    assert _by_check(findings, "coverage")[0].evidence["measured"] == 0


# --- envelope / degradation ------------------------------------------------


def test_coverage_finding_is_emitted_even_on_a_red_run(tmp_path: Path) -> None:
    """'How much did you measure?' matters most precisely when something failed."""
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.3: Something\n**Deps:** S-3.2\n",
        "development-status:\n  2-3-something: backlog\n  3-2-later: backlog\n",
    )
    findings = gather_forward_dependency(tmp_path)
    assert _by_check(findings, "forward-dep")
    cov = _by_check(findings, "coverage")
    assert len(cov) == 1 and cov[0].status is DoctorStatus.OK


def test_missing_projects_dir_warns_rather_than_raising(tmp_path: Path) -> None:
    findings = gather_forward_dependency(tmp_path)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].check == "coverage"


def test_every_finding_carries_the_source_tag(tmp_path: Path) -> None:
    _station(
        tmp_path,
        "pyforge-x",
        "### Story 2.3: Something\n**Deps:** S-3.2\n",
        "development-status:\n  2-3-something: backlog\n",
    )
    assert all(f.source is Source.FORWARD_DEPENDENCY for f in gather_forward_dependency(tmp_path))


# --- the restated constant -------------------------------------------------


def test_actionable_statuses_is_the_expected_literal() -> None:
    """Guards the value locally. Equality with the INSTALLED harness is asserted
    by the meta-suite's test_actionable_statuses_conformance.py (AD-13) — that
    one needs bmad_loop, which Doctor's lean env deliberately does not carry."""
    assert ACTIONABLE_STATUSES == frozenset({"backlog", "ready-for-dev"})
