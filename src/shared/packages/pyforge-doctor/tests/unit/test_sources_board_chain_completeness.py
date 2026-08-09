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
    """BOTH projects must be dirty: with one dirty and one clean, a bug that
    dropped every project after the first would still pass."""
    pa_a = _pa(tmp_path, "pyforge-alpha")
    _write_spec(pa_a / "specs" / "spec-foo" / "SPEC.md", "draft")

    pa_b = _pa(tmp_path, "pyforge-beta")
    _write_spec(pa_b / "specs" / "spec-bar" / "SPEC.md", "draft")

    findings = board.gather_chain_completeness(tmp_path)

    assert {f.evidence["project"] for f in findings} == {"pyforge-alpha", "pyforge-beta"}
    assert all(f.check == "spec-not-decomposed" for f in findings)
    assert all(f.status is DoctorStatus.FAIL for f in findings)


# --- one project's malformed input must not swallow another's real finding --


def test_unreadable_spec_in_one_project_does_not_hide_a_real_finding_in_another(
    tmp_path: Path,
) -> None:
    """A non-UTF-8 byte in ONE project's SPEC.md must not disturb a
    DIFFERENT, well-formed project's real ``spec-not-decomposed`` FAIL.

    NOTE on what this does and does NOT pin: ``_frontmatter`` catches the
    ``UnicodeDecodeError`` itself and returns ``{}``, so this fixture never
    reaches the per-project ``try/except`` in ``_check_chain_completeness``
    -- it passes with that isolation deleted. (An earlier revision of this
    docstring claimed otherwise; a follow-up review disproved it.) It is kept
    as an end-to-end guard on the degradation contract; the tests that
    genuinely exercise per-project isolation are the ``_board_lines`` ones
    below, whose triggers really do escape from outside the try."""
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


# --- follow-up review regressions: masking via _board_lines ------------------
#
# These are the tests that genuinely exercise the per-project isolation. Each
# trigger below raised from INSIDE `_board_lines`, which is called at the top
# of `_check_chain_completeness` OUTSIDE the per-project try -- so the error
# reached the whole-gather `degrade_on_exception` and replaced every project's
# real FAIL with one vacuous WARN (exit 2 -> exit 0). All three reproduced
# live before the fix.


def _alpha_with_real_fail(tmp_path: Path) -> None:
    """One well-formed project owning a genuine INV-A violation."""
    _write_spec(_pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md", "draft")


def _assert_alpha_fail_survives(tmp_path: Path) -> None:
    findings = board.gather_chain_completeness(tmp_path)
    assert [f.check for f in findings] == ["spec-not-decomposed"], (
        f"the real FAIL was masked: {[(f.check, f.status.value) for f in findings]}"
    )
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].evidence["project"] == "pyforge-alpha"


def test_null_epic_entry_does_not_mask_another_projects_real_fail(tmp_path: Path) -> None:
    """A `null` in a station's `epics` list. The `isinstance(e, dict)` guard
    used to TRAIL the second `for`, where a comprehension never consults it
    before evaluating `e.get("stories")`."""
    _alpha_with_real_fail(tmp_path)
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {"beta": {"epics": [None]}})

    _assert_alpha_fail_survives(tmp_path)


def test_non_list_epics_value_does_not_mask_another_projects_real_fail(
    tmp_path: Path,
) -> None:
    """`epics` as a string: iterating it yields characters, not epic dicts."""
    _alpha_with_real_fail(tmp_path)
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {"beta": {"epics": "nope"}})

    _assert_alpha_fail_survives(tmp_path)


def test_non_mapping_projects_does_not_mask_another_projects_real_fail(
    tmp_path: Path,
) -> None:
    """`projects` as a list -- valid JSON, wrong shape, `.items()` explodes
    after `_board_lines`' own try/except has already closed."""
    data_js = tmp_path / "docs" / "dashboard" / "data.js"
    data_js.parent.mkdir(parents=True, exist_ok=True)
    data_js.write_text('window.DASHBOARD_DATA = {"projects": [1, 2, 3]};\n', encoding="utf-8")
    _alpha_with_real_fail(tmp_path)

    _assert_alpha_fail_survives(tmp_path)


# --- follow-up review regression: frontmatter scalar decoding ----------------


def test_quoted_open_status_is_still_treated_as_open(tmp_path: Path) -> None:
    """`status: 'draft'` must not silently exempt an undecomposed Spec. The
    hand-rolled parser replaced `yaml.safe_load`, which decoded the quotes."""
    _write_spec(_pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md", "'draft'")

    _assert_alpha_fail_survives(tmp_path)


def test_inline_commented_open_status_is_still_treated_as_open(tmp_path: Path) -> None:
    """`status: draft  # still open` -- YAML reads the comment off; so must we."""
    _write_spec(
        _pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md",
        "draft  # still open",
    )

    _assert_alpha_fail_survives(tmp_path)


def test_quoted_epics_role_still_selects_the_canonical_epics_doc(tmp_path: Path) -> None:
    """A quoted `epics_role: "canonical"` used to miss, dropping the doc and
    skipping INV-B/INV-D entirely."""
    pa = _pa(tmp_path, "pyforge-alpha")
    path = pa / "epics-v2.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '---\nepics_role: "canonical"\n---\n\n## Epic 1: E\n### Story 1.1: title\n',
        encoding="utf-8",
    )
    _write_ledger(pa / "sprint-status-ledger.yaml", {"9-9-orphan": "done"})

    findings = board.gather_chain_completeness(tmp_path)

    assert "ledger-key-without-story" in {f.check for f in findings}, (
        f"INV-B was skipped: {[f.check for f in findings]}"
    )


def test_scalar_decoding_does_not_over_strip_an_ordinary_value() -> None:
    """Only surrounding quotes and a real ` #` inline comment come off."""
    assert board._scalar("  draft  ") == "draft"
    assert board._scalar("'draft'") == "draft"
    assert board._scalar('"draft"') == "draft"
    assert board._scalar("draft # note") == "draft"
    assert board._scalar("issue#12") == "issue#12"  # no space -> not a comment
    assert board._scalar("it's") == "it's"  # unbalanced quote left alone
    assert board._scalar("") == ""


# --- adversarial-review regressions (2026-08-09, third pass) -----------------
#
# Every test below reproduces a defect a review pass found in `_board_lines`
# and `_scalar`, each confirmed by reverting the fix and watching the test
# fail. `_board_lines` runs OUTSIDE `_check_chain_completeness`'s own
# per-project try, so anything it raises escapes to the whole-gather
# `degrade_on_exception` and replaces EVERY project's real findings with one
# WARN -- turning exit 2 into exit 0. That is the shared consequence.


def _one_real_fail(target: Path) -> None:
    """A well-formed project carrying a genuine `spec-not-decomposed` FAIL --
    the finding each masking test below asserts does NOT disappear."""
    pa = _pa(target, "pyforge-good")
    _write_spec(pa / "specs" / "spec-orphan" / "SPEC.md", "draft")
    _write_epics_md(pa / "epics.md", ["1.1"])


def test_truthy_non_iterable_stories_does_not_hide_another_projects_finding(
    tmp_path: Path,
) -> None:
    """`{"stories": 7}` -- truthy, so `or ()` does not catch it, and not a
    list, so it raised `TypeError: 'int' object is not iterable` out of
    `_board_lines`. Reproduced live: the well-formed project's real FAIL
    vanished behind one `chain-completeness` WARN."""
    _one_real_fail(tmp_path)
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"marshal": {"epics": [{"stories": 7}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert "spec-not-decomposed" in {f.check for f in findings}, (
        f"a malformed board line masked a real finding: {[f.check for f in findings]}"
    )
    assert any(f.status is DoctorStatus.FAIL for f in findings)


def test_stories_as_a_mapping_does_not_hide_another_projects_finding(
    tmp_path: Path,
) -> None:
    """The same class one shape over: a mapping iterates to its KEYS, so this
    reached `len(s) > 1 and s[1]` with a string and raised there instead."""
    _one_real_fail(tmp_path)
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"marshal": {"epics": [{"stories": {"1.1": "done"}}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert "spec-not-decomposed" in {f.check for f in findings}, (
        f"a malformed board line masked a real finding: {[f.check for f in findings]}"
    )


def test_one_malformed_station_does_not_drop_a_well_formed_stations_board_line(
    tmp_path: Path,
) -> None:
    """Per-STATION isolation, not merely per-project: a broken `marshal` line
    must not cost `good` its INV-C comparison."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {
            "marshal": {"epics": 7},  # malformed
            "good": {"epics": [{"stories": [["1.1", "done"]]}]},  # 1 story vs 2 rows
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    inv_c = [f for f in findings if f.check == "board-diverges-from-ledger"]
    assert len(inv_c) == 1, f"INV-C was skipped for the healthy station: {findings}"
    assert inv_c[0].evidence["status"] == "board 1/1 vs ledger 1/2"


def test_empty_epics_list_is_skipped_exactly_as_the_original_skips_it(
    tmp_path: Path,
) -> None:
    """The original guards with `if not epics: continue`, so a well-formed
    `"epics": []` is a station it deliberately does not compare. Recording
    (0, 0) for it instead fired a false `board-diverges-from-ledger` -- a
    divergence on input the original handled cleanly, not one where it
    crashed."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {"good": {"epics": []}})

    findings = board.gather_chain_completeness(tmp_path)

    assert "board-diverges-from-ledger" not in {f.check for f in findings}, (
        f"an empty board line produced a false INV-C FAIL: {findings}"
    )


def test_an_empty_story_slot_still_counts_toward_the_boards_total(
    tmp_path: Path,
) -> None:
    """INV-C is a COUNT comparison, and the original counts an empty `[]`
    slot into the total (`len(s) > 1` already guards the done-count).
    Filtering it out shrank the denominator until a 3-slot board read as
    matching a 2-row ledger -- a false NEGATIVE."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"good": {"epics": [{"stories": [["1.1", "done"], ["1.2", "todo"], []]}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    inv_c = [f for f in findings if f.check == "board-diverges-from-ledger"]
    assert len(inv_c) == 1, f"INV-C missed a real 3-vs-2 divergence: {findings}"
    assert inv_c[0].evidence["status"] == "board 1/3 vs ledger 1/2"


def test_scalar_keeps_a_hash_that_lives_inside_quotes() -> None:
    """YAML treats `#` inside quotes as data. Stripping the comment BEFORE the
    quotes truncated `"a # b"` to `"a` -- a mis-decode of exactly the kind
    `_scalar` exists to prevent, with a stray quote left on the front."""
    assert board._scalar('"a # b"') == "a # b"
    assert board._scalar("'draft # x'") == "draft # x"
    assert board._scalar("'draft' # trailing note") == "draft"
    assert board._scalar('"draft"  # trailing note') == "draft"
