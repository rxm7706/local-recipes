"""Unit tests for ``pyforge.doctor.sources.board.gather_chain_completeness``
(Story 6.5) -- covers every row of the spec's I/O & Edge-Case Matrix that
belongs to ``chain_completeness`` (INV-A/B/C/D) against REAL tmp fixture
trees (planning-artifacts directories, a ledger, a data.js), mirroring
``test_sources_ledger.py``'s own real-fixture discipline.

Each of the four invariants below was independently verified, during
development, to actually FIRE its own dedicated test: temporarily commenting
out that invariant's ``findings.append(...)`` branch in
``sources/board.py::_check_chain_completeness`` and re-running the single
test made it fail (the invariant it exercises stopped being enforced). That
verification is not re-encoded here -- see the story spec's own Tasks &
Acceptance for the requirement.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import board

# --- fixture helpers ---------------------------------------------------------


def _write_spec(path: Path, status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nstatus: {status}\nowner-dream: docs/dreams/x.md\n---\n\nbody\n",
                     encoding="utf-8")


def _write_epics_md(path: Path, story_ids: list[str], *, canonical: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    if canonical:
        lines.append("epics_role: canonical")
    lines.append("---")
    lines.append("")
    lines.append("## Epic 1: Test Epic")
    lines.extend(f"### Story {sid}: title" for sid in story_ids)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ledger(path: Path, rows: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {k}: {v}" for k, v in rows.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_data_js(path: Path, projects: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"projects": projects})
    path.write_text(f"window.DASHBOARD_DATA = {payload};\n", encoding="utf-8")


def _pa(target: Path, project: str) -> Path:
    return target / "_bmad-output" / "projects" / project / "planning-artifacts"


# --- INV-A: every open Spec is decomposed ------------------------------------


def test_open_undecomposed_spec_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHAIN_COMPLETENESS
    assert finding.check == "spec-not-decomposed"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-A"
    assert finding.evidence["project"] == "pyforge-testproj"
    assert finding.evidence["subject"] == "spec-foo"
    assert "no FR or epic references" in finding.message


def test_spec_decomposed_in_prd_prose_reports_no_finding(tmp_path: Path) -> None:
    """The mirror-image control: the same open Spec, but its slug DOES appear
    in the project's PRD prose -- INV-A must not fire."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")
    prd = pa / "prds" / "prd-x" / "prd.md"
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text("This PRD decomposes spec-foo into FR-1.\n", encoding="utf-8")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_deferred_spec_reports_no_finding(tmp_path: Path) -> None:
    """A slug registered in DEFERRED_SPECS is a recorded decision, not a
    silent gap -- INV-A must not fire for it even though it is undecomposed."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-agentic-sdlc-autonomy" / "SPEC.md", "draft")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_shipped_spec_is_not_open_and_reports_no_finding(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "shipped")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- INV-B: epics.md set == ledger set ---------------------------------------


def test_ledger_key_without_epics_story_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {
        "1-1-foo": "done",
        "9-9-orphan": "done",
    })

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "ledger-key-without-story"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-B"
    assert "9-9" in finding.evidence["status"]


def test_epics_story_without_ledger_key_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-foo": "done"})

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "story-without-ledger-key"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-B"
    assert "1-2" in finding.evidence["status"]


def test_unparseable_ledger_key_reports_fail(tmp_path: Path) -> None:
    """A ledger key with no recognisable id shape is REPORTED, not silently
    dropped from the comparison (the original script's own rationale)."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {
        "1-1-foo": "done",
        "not_a_recognisable_key": "done",
    })

    findings = board.gather_chain_completeness(tmp_path)

    kinds = {f.check for f in findings}
    assert "unparseable-ledger-key" in kinds
    unparsed = next(f for f in findings if f.check == "unparseable-ledger-key")
    assert unparsed.status is DoctorStatus.FAIL
    assert unparsed.evidence["inv"] == "INV-B"


def test_epics_and_ledger_in_full_agreement_reports_no_finding(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {
        "1-1-foo": "done",
        "1-2-bar": "in-progress",
    })

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- INV-D: canonical epics declares zero stories ----------------------------


def test_canonical_epics_with_zero_stories_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", [])  # zero `### Story` headings
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-foo": "done"})

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "canonical-epics-declares-no-stories"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-D"
    assert "0 `### Story` headings vs 1 ledger key(s)" == finding.evidence["status"]


# --- INV-C: board line == ledger ---------------------------------------------


def test_board_diverging_from_ledger_reports_fail(tmp_path: Path) -> None:
    """Herald's own 2026-08-08 incident, shrunk to a fixture: the board
    renders a smaller/different story set than the durable ledger record."""
    pa = _pa(tmp_path, "pyforge-herald")
    _write_ledger(pa / "sprint-status-ledger.yaml", {
        "1-1-a": "done", "1-2-b": "done", "1-3-c": "in-progress",
    })
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "herald": {"epics": [{"stories": [["1.1", "done", "a"], ["1.2", "pending", "b"]]}]},
    })

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "board-diverges-from-ledger"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-C"
    assert finding.evidence["subject"] == "herald"
    assert "board 1/2 vs ledger 2/3" == finding.evidence["status"]


def test_board_matching_ledger_reports_no_finding(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-herald")
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "in-progress"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "herald": {"epics": [{"stories": [["1.1", "done", "a"], ["1.2", "pending", "b"]]}]},
    })

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- data.js unreadable: INV-C silently skipped; INV-A/B/D unaffected -------


def test_unreadable_data_js_skips_inv_c_without_affecting_others(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")  # INV-A fires
    data_js = tmp_path / "docs" / "dashboard" / "data.js"
    data_js.parent.mkdir(parents=True, exist_ok=True)
    data_js.write_text("not the expected prefix at all\n", encoding="utf-8")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].check == "spec-not-decomposed"
    assert findings[0].status is DoctorStatus.FAIL
    assert not any(f.check == "board-diverges-from-ledger" for f in findings)


def test_missing_data_js_never_raises(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-foo": "done"})
    # deliberately no docs/dashboard/data.js at all, and no epics.md either

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- No projects / never raises ----------------------------------------------


def test_no_projects_directory_reports_ok_with_zero_projects(tmp_path: Path) -> None:
    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHAIN_COMPLETENESS
    assert finding.check == "chain-completeness"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"projects": 0}


def test_multiple_projects_are_all_reported_independently(tmp_path: Path) -> None:
    pa_a = _pa(tmp_path, "pyforge-alpha")
    _write_spec(pa_a / "specs" / "spec-foo" / "SPEC.md", "draft")

    pa_b = _pa(tmp_path, "pyforge-beta")
    _write_epics_md(pa_b / "epics.md", ["2.1"])
    _write_ledger(pa_b / "sprint-status-ledger.yaml", {"2-1-x": "done"})  # clean

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].evidence["project"] == "pyforge-alpha"


# --- one project's malformed input must not swallow another's real finding --


def test_unreadable_spec_in_one_project_does_not_hide_a_real_finding_in_another(
    tmp_path: Path,
) -> None:
    """Adversarial-review regression: a non-UTF-8 byte in ONE project's
    SPEC.md used to escape as an uncaught UnicodeDecodeError, get caught by
    the whole-function ``degrade_on_exception`` wrap, and convert a
    DIFFERENT, well-formed project's real ``spec-not-decomposed`` FAIL into a
    single vacuous WARN -- silently turning a real compliance violation into
    exit-0. Reproduced live before the fix; this pins the fix."""
    pa_alpha = _pa(tmp_path, "pyforge-alpha")
    _write_spec(pa_alpha / "specs" / "spec-foo" / "SPEC.md", "draft")  # real FAIL

    pa_beta = _pa(tmp_path, "pyforge-beta")
    bad_spec = pa_beta / "specs" / "spec-bar" / "SPEC.md"
    bad_spec.parent.mkdir(parents=True, exist_ok=True)
    bad_spec.write_bytes(b"---\nstatus: draft\n---\n\n\xe9 bad byte\n")  # malformed

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "spec-not-decomposed"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["project"] == "pyforge-alpha"


def test_non_dict_data_js_project_entry_does_not_crash_or_hide_other_findings(
    tmp_path: Path,
) -> None:
    """A malformed ``data.js`` entry (e.g. ``null``) for one station must not
    take down INV-C for a different, well-formed station."""
    pa_herald = _pa(tmp_path, "pyforge-herald")
    _write_ledger(pa_herald / "sprint-status-ledger.yaml", {"1-1-a": "done"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "alpha": None,
        "herald": {"epics": [{"stories": [["1.1", "pending", "a"]]}]},
    })

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "board-diverges-from-ledger"
    assert finding.evidence["subject"] == "herald"
