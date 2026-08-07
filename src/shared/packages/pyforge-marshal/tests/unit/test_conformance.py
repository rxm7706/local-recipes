"""Unit tests for ``core.conformance`` (Story 6.3, FR-42, AD-31/AD-36) --
pure ``TreeLiveState``/``TreeConformance``/``evaluate_conformance`` matrix,
no filesystem, no I/O."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pyforge.marshal.core.conformance import (
    ALL_STATUSES,
    ENTRY_FILE_FAMILY,
    ENTRY_FILE_TOOLS,
    STAGE_CHANGE,
    STAGE_COMMIT,
    STAGE_READ,
    STAGE_VERIFY,
    STATUS_ADDED,
    STATUS_AVAILABLE,
    STATUS_LINK_TARGET_CONFIRMED,
    STATUS_MATRIX_FAIL,
    STATUS_MATRIX_NOT_ATTEMPTED,
    STATUS_MATRIX_PASS,
    STATUS_MATRIX_UNAVAILABLE,
    STATUS_MODIFIED,
    STATUS_REMOVED,
    STATUS_SMOKE_FAIL,
    STATUS_SMOKE_PASS,
    STATUS_SMOKE_UNAVAILABLE,
    STATUS_UNAVAILABLE,
    ConformanceReport,
    EntryFileState,
    SmokeFacts,
    TreeLiveState,
    _check_symlink_identity,
    build_matrix_row,
    build_probe_record,
    build_smoke_record,
    evaluate_conformance,
    evaluate_entry_file_family,
    evaluate_smoke,
    render_matrix_markdown,
)
from pyforge.marshal.ports.harness import AdapterProbe

_TREE = ".agents/skills"
_ADAPTERS = ("codex",)
_EXPECTED = "../.claude/skills"


def _state(
    *,
    desired: bool = False,
    previously_projected: bool = False,
    live_target: str | None = None,
    live_exists: bool = False,
) -> TreeLiveState:
    return TreeLiveState(
        tree=_TREE,
        adapters=_ADAPTERS,
        desired=desired,
        previously_projected=previously_projected,
        live_target=live_target,
        live_exists=live_exists,
        expected_target=_EXPECTED,
    )


def test_confirmed_when_desired_and_target_matches():
    state = _state(desired=True, live_target=_EXPECTED, live_exists=True)
    result = _check_symlink_identity(state)
    assert result.status == STATUS_LINK_TARGET_CONFIRMED
    assert result.tree == _TREE
    assert result.adapters == _ADAPTERS


def test_added_when_desired_never_projected_and_absent():
    state = _state(desired=True, previously_projected=False, live_target=None, live_exists=False)
    result = _check_symlink_identity(state)
    assert result.status == STATUS_ADDED


def test_removed_when_tracked_but_now_absent():
    state = _state(desired=True, previously_projected=True, live_target=None, live_exists=False)
    result = _check_symlink_identity(state)
    assert result.status == STATUS_REMOVED


def test_removed_when_no_longer_desired_but_still_live_and_correct():
    state = _state(desired=False, previously_projected=True, live_target=_EXPECTED, live_exists=True)
    result = _check_symlink_identity(state)
    assert result.status == STATUS_REMOVED


def test_modified_when_retargeted():
    state = _state(desired=True, live_target="../elsewhere", live_exists=True)
    result = _check_symlink_identity(state)
    assert result.status == STATUS_MODIFIED
    assert "elsewhere" in result.detail


def test_modified_when_real_content_occupies_the_path():
    state = _state(desired=True, previously_projected=True, live_target=None, live_exists=True)
    result = _check_symlink_identity(state)
    assert result.status == STATUS_MODIFIED
    assert "real file or directory" in result.detail


def test_neither_desired_nor_tracked_raises_value_error():
    state = _state(desired=False, previously_projected=False, live_target=None, live_exists=False)
    with pytest.raises(ValueError, match="neither desired nor previously projected"):
        _check_symlink_identity(state)


def test_evaluate_conformance_with_symlink_mechanism_dispatches_per_tree():
    states = [
        _state(desired=True, live_target=_EXPECTED, live_exists=True),
    ]
    report = evaluate_conformance(states, mechanism="symlink")
    assert isinstance(report, ConformanceReport)
    assert report.mechanism == "symlink"
    assert len(report.checks) == 1
    assert report.checks[0].status == STATUS_LINK_TARGET_CONFIRMED
    assert report.unevaluated_trees == ()


def test_evaluate_conformance_with_none_mechanism_never_checks_anything():
    states = [_state(desired=True, live_target=_EXPECTED, live_exists=True)]
    report = evaluate_conformance(states, mechanism=None, unevaluated_trees=("some/other/tree",))
    assert report.checks == ()
    assert set(report.unevaluated_trees) == {_TREE, "some/other/tree"}


def test_evaluate_conformance_with_unregistered_mechanism_never_checks_anything():
    states = [_state(desired=True, live_target=_EXPECTED, live_exists=True)]
    report = evaluate_conformance(states, mechanism="junction")
    assert report.checks == ()
    assert report.unevaluated_trees == (_TREE,)


def test_evaluate_conformance_empty_input_is_empty_report():
    report = evaluate_conformance([], mechanism="symlink")
    assert report.checks == ()
    assert report.unevaluated_trees == ()


# --- build_probe_record (Story 6.4, FR-43, AD-31) ---------------------------


def _probe(
    *,
    binary_present: bool = True,
    binary_version: str | None = "1.0.0",
    probe_output: str | None = '{"schema_version": 2}',
    probe_note: str | None = None,
) -> AdapterProbe:
    return AdapterProbe(
        adapter="claude",
        binary="claude",
        binary_present=binary_present,
        binary_version=binary_version,
        capabilities={"hookless": False},
        probe_output=probe_output,
        probe_note=probe_note,
    )


def test_build_probe_record_available_when_binary_present():
    record = build_probe_record(_probe(binary_present=True))
    assert record["status"] == STATUS_AVAILABLE
    assert record["adapter"] == "claude"
    assert record["binary"] == "claude"
    assert record["binary_present"] is True
    assert record["binary_version"] == "1.0.0"
    assert record["capabilities"] == {"hookless": False}
    assert record["probe_output"] == '{"schema_version": 2}'
    assert record["probe_note"] is None


def test_build_probe_record_unavailable_when_binary_absent():
    record = build_probe_record(
        _probe(binary_present=False, binary_version=None, probe_output=None, probe_note="binary not found on PATH")
    )
    assert record["status"] == STATUS_UNAVAILABLE
    assert record["binary_version"] is None
    assert record["probe_output"] is None
    assert record["probe_note"] == "binary not found on PATH"


def test_build_probe_record_fields_are_independently_none():
    record = build_probe_record(_probe(binary_version=None, probe_output=None, probe_note="probe timed out"))
    assert record["status"] == STATUS_AVAILABLE
    assert record["binary_version"] is None
    assert record["probe_output"] is None
    assert record["probe_note"] == "probe timed out"


def test_probe_statuses_never_appear_in_the_tree_drift_vocabulary():
    """A DIFFERENT fact from tree-drift status -- the two vocabularies never
    share a member (Story 6.3's own closed set stays unchanged)."""
    assert STATUS_AVAILABLE not in ALL_STATUSES
    assert STATUS_UNAVAILABLE not in ALL_STATUSES


# --- Story 6.5: `evaluate_smoke`/`build_smoke_record` ------------------------


def _facts(
    *,
    binary_present: bool = True,
    launched: bool = True,
    timed_out: bool = False,
    returncode: int | None = 0,
    file_changed: bool = False,
    commit_made: bool = False,
) -> SmokeFacts:
    return SmokeFacts(
        binary_present=binary_present,
        launched=launched,
        timed_out=timed_out,
        returncode=returncode,
        file_changed=file_changed,
        commit_made=commit_made,
    )


def test_evaluate_smoke_unavailable_when_binary_absent():
    report = evaluate_smoke(_facts(binary_present=False, launched=False, returncode=None))
    assert report.status == STATUS_SMOKE_UNAVAILABLE
    assert report.failing_stage is None


def test_evaluate_smoke_pass_when_commit_made():
    report = evaluate_smoke(_facts(file_changed=True, commit_made=True))
    assert report.status == STATUS_SMOKE_PASS
    assert report.failing_stage is None


def test_evaluate_smoke_fail_verify_when_file_changed_but_no_commit():
    report = evaluate_smoke(_facts(file_changed=True, commit_made=False))
    assert report.status == STATUS_SMOKE_FAIL
    assert report.failing_stage == STAGE_VERIFY


def test_evaluate_smoke_fail_change_when_launched_but_no_file_change():
    report = evaluate_smoke(_facts(launched=True, file_changed=False, commit_made=False))
    assert report.status == STATUS_SMOKE_FAIL
    assert report.failing_stage == STAGE_CHANGE


def test_evaluate_smoke_fail_read_when_never_launched_despite_present_binary():
    report = evaluate_smoke(
        _facts(binary_present=True, launched=False, returncode=None, file_changed=False, commit_made=False)
    )
    assert report.status == STATUS_SMOKE_FAIL
    assert report.failing_stage == STAGE_READ


def test_evaluate_smoke_timed_out_folds_into_detail_never_status():
    report = evaluate_smoke(_facts(launched=True, timed_out=True, returncode=None))
    assert report.status == STATUS_SMOKE_FAIL
    assert report.failing_stage == STAGE_CHANGE
    assert "timed out" in report.detail


def test_evaluate_smoke_nonzero_returncode_with_commit_is_not_a_pass():
    """Review finding: a commit landing alone used to be treated as PASS
    regardless of `returncode` -- a non-zero exit alongside a landed commit
    must not be reported as a clean pass."""
    report = evaluate_smoke(_facts(file_changed=True, commit_made=True, returncode=1))
    assert report.status == STATUS_SMOKE_FAIL
    assert report.failing_stage == STAGE_COMMIT
    assert "exited 1" in report.detail


def test_evaluate_smoke_commit_without_file_change_is_not_a_pass():
    """Review finding: a commit that never touched the smoke's own target
    file is not corroborating evidence of a completed run -- it used to be
    reported as PASS purely on `commit_made`."""
    report = evaluate_smoke(_facts(file_changed=False, commit_made=True, returncode=0))
    assert report.status == STATUS_SMOKE_FAIL
    assert report.failing_stage == STAGE_COMMIT


def test_build_smoke_record_shape():
    report = evaluate_smoke(_facts(file_changed=True, commit_made=True))
    record = build_smoke_record("claude", report, binary="claude", binary_present=True)
    assert record == {
        "adapter": "claude",
        "binary": "claude",
        "binary_present": True,
        "status": STATUS_SMOKE_PASS,
        "failing_stage": None,
        "detail": report.detail,
        "harness_version": None,
        "recorded_at": None,
    }


def test_build_smoke_record_threads_harness_version_and_recorded_at():
    """Story 6.6 (FR-45): additive, backward-compatible keyword parameters
    -- an omitted call (the test above) keeps `None`, a supplied one is
    threaded through unchanged."""
    report = evaluate_smoke(_facts(file_changed=True, commit_made=True))
    record = build_smoke_record(
        "claude",
        report,
        binary="claude",
        binary_present=True,
        harness_version="0.9.0",
        recorded_at="2026-08-07T00:00:00+00:00",
    )
    assert record["harness_version"] == "0.9.0"
    assert record["recorded_at"] == "2026-08-07T00:00:00+00:00"


def test_smoke_statuses_never_appear_in_the_tree_drift_or_probe_vocabularies():
    """A THIRD, independent fact from both tree-drift status and adapter-
    probe status -- none of the three vocabularies share a member, even
    though 'unavailable' happens to coincide as a STRING between this
    module's own STATUS_SMOKE_UNAVAILABLE and Story 6.4's STATUS_UNAVAILABLE
    (AD-31: never conflated as a CONSTANT/classification)."""
    smoke_statuses = {STATUS_SMOKE_PASS, STATUS_SMOKE_FAIL, STATUS_SMOKE_UNAVAILABLE}
    assert smoke_statuses.isdisjoint(ALL_STATUSES)
    assert STATUS_SMOKE_PASS != STATUS_AVAILABLE
    assert STATUS_SMOKE_FAIL != STATUS_AVAILABLE
    # STATUS_SMOKE_UNAVAILABLE and STATUS_UNAVAILABLE ARE the same string by
    # coincidence (both "unavailable") -- asserted explicitly so a future
    # refactor cannot silently rely on that coincidence for correctness.
    assert STATUS_SMOKE_UNAVAILABLE == STATUS_UNAVAILABLE
    assert STAGE_COMMIT not in (STAGE_READ, STAGE_CHANGE, STAGE_VERIFY)


# --- Story 6.6: the conformance matrix ---------------------------------

_NOW = datetime(2026, 8, 7, tzinfo=timezone.utc)


def test_matrix_row_not_attempted_when_no_smoke_record():
    row = build_matrix_row("claude", smoke_record=None, probe_record=None, now=_NOW, stale_after_days=30)
    assert row.status == STATUS_MATRIX_NOT_ATTEMPTED
    assert row.adapter_version is None
    assert row.harness_version is None
    assert row.date is None
    assert row.failing_stage is None
    assert row.stale is False


@pytest.mark.parametrize(
    ("smoke_status", "expected"),
    [
        (STATUS_SMOKE_PASS, STATUS_MATRIX_PASS),
        (STATUS_SMOKE_FAIL, STATUS_MATRIX_FAIL),
        (STATUS_SMOKE_UNAVAILABLE, STATUS_MATRIX_UNAVAILABLE),
    ],
)
def test_matrix_row_maps_each_real_smoke_status(smoke_status, expected):
    smoke_record = {
        "status": smoke_status,
        "failing_stage": "verify" if smoke_status == STATUS_SMOKE_FAIL else None,
        "harness_version": "0.9.0",
        "recorded_at": "2026-08-06T00:00:00+00:00",
    }
    probe_record = {"binary_version": "1.2.3"}
    row = build_matrix_row(
        "claude", smoke_record=smoke_record, probe_record=probe_record, now=_NOW, stale_after_days=30
    )
    assert row.status == expected
    assert row.adapter_version == "1.2.3"
    assert row.harness_version == "0.9.0"
    assert row.date == "2026-08-06T00:00:00+00:00"
    if smoke_status == STATUS_SMOKE_FAIL:
        assert row.failing_stage == "verify"
    else:
        assert row.failing_stage is None


def test_matrix_row_unrecognized_smoke_status_degrades_to_not_attempted():
    """Defensive: a hand-edited/corrupt adapter-smoke.json entry must never
    fabricate a pass."""
    row = build_matrix_row(
        "claude",
        smoke_record={"status": "bogus"},
        probe_record=None,
        now=_NOW,
        stale_after_days=30,
    )
    assert row.status == STATUS_MATRIX_NOT_ATTEMPTED


def test_matrix_row_no_smoke_record_still_reports_a_known_probed_version():
    """Review finding: an earlier draft hardcoded adapter_version=None
    whenever smoke_record was None, discarding a real, already-known probe
    fact -- an adapter that has been probed but never smoked should still
    report its known version, even while status stays not-attempted."""
    row = build_matrix_row(
        "claude",
        smoke_record=None,
        probe_record={"binary_version": "9.9.9"},
        now=_NOW,
        stale_after_days=30,
    )
    assert row.status == STATUS_MATRIX_NOT_ATTEMPTED
    assert row.adapter_version == "9.9.9"


def test_matrix_row_unrecognized_status_never_reports_stale_or_date():
    """Review finding: a hand-edited/corrupt smoke record with BOTH an
    unrecognized status AND a stale-looking recorded_at used to still
    compute stale=True from the malformed record's own recorded_at,
    producing a self-contradictory not-attempted row that also claims to
    be stale and dated -- "no claim exists to age" must hold for every
    not-attempted row, not just the no-smoke-record-at-all case."""
    row = build_matrix_row(
        "claude",
        smoke_record={"status": "corrupted", "recorded_at": "2020-01-01T00:00:00+00:00"},
        probe_record=None,
        now=_NOW,
        stale_after_days=30,
    )
    assert row.status == STATUS_MATRIX_NOT_ATTEMPTED
    assert row.stale is False
    assert row.date is None
    assert row.harness_version is None


def test_matrix_row_stale_when_older_than_threshold():
    smoke_record = {"status": STATUS_SMOKE_PASS, "recorded_at": "2026-06-01T00:00:00+00:00"}
    row = build_matrix_row("claude", smoke_record=smoke_record, probe_record=None, now=_NOW, stale_after_days=30)
    assert row.stale is True


def test_matrix_row_not_stale_within_threshold():
    smoke_record = {"status": STATUS_SMOKE_PASS, "recorded_at": "2026-08-06T00:00:00+00:00"}
    row = build_matrix_row("claude", smoke_record=smoke_record, probe_record=None, now=_NOW, stale_after_days=30)
    assert row.stale is False


def test_matrix_row_naive_recorded_at_is_treated_as_utc():
    smoke_record = {"status": STATUS_SMOKE_PASS, "recorded_at": "2026-08-06T00:00:00"}
    row = build_matrix_row("claude", smoke_record=smoke_record, probe_record=None, now=_NOW, stale_after_days=30)
    assert row.stale is False
    assert row.date == "2026-08-06T00:00:00"


def test_matrix_row_malformed_recorded_at_never_raises_and_is_not_stale():
    smoke_record = {"status": STATUS_SMOKE_PASS, "recorded_at": "not-a-timestamp"}
    row = build_matrix_row("claude", smoke_record=smoke_record, probe_record=None, now=_NOW, stale_after_days=30)
    assert row.stale is False
    assert row.date == "not-a-timestamp"


def test_matrix_row_missing_recorded_at_never_raises():
    smoke_record = {"status": STATUS_SMOKE_PASS}
    row = build_matrix_row("claude", smoke_record=smoke_record, probe_record=None, now=_NOW, stale_after_days=30)
    assert row.stale is False
    assert row.date is None


def test_render_matrix_markdown_empty_rows():
    text = render_matrix_markdown([], hostname="host1", generated_at="2026-08-07T00:00:00+00:00")
    assert "host1" in text
    assert "2026-08-07T00:00:00+00:00" in text
    assert "| Adapter | Status |" in text


def test_render_matrix_markdown_sorts_rows_by_adapter_and_renders_every_column():
    rows = [
        build_matrix_row("zeta", smoke_record=None, probe_record=None, now=_NOW, stale_after_days=30),
        build_matrix_row(
            "alpha",
            smoke_record={
                "status": STATUS_SMOKE_PASS,
                "failing_stage": None,
                "harness_version": "0.9.0",
                "recorded_at": "2026-08-06T00:00:00+00:00",
            },
            probe_record={"binary_version": "1.0.0"},
            now=_NOW,
            stale_after_days=30,
        ),
    ]
    text = render_matrix_markdown(rows, hostname="host1", generated_at="2026-08-07T00:00:00+00:00")
    alpha_index = text.index("alpha")
    zeta_index = text.index("zeta")
    assert alpha_index < zeta_index
    assert "1.0.0" in text
    assert "0.9.0" in text
    assert STATUS_MATRIX_PASS in text
    assert STATUS_MATRIX_NOT_ATTEMPTED in text


def test_matrix_statuses_never_appear_in_any_other_vocabulary():
    """A FOURTH, independent fact -- never merged into ALL_STATUSES,
    STATUS_AVAILABLE/UNAVAILABLE, or the smoke-status pair, even though
    three of the four literals coincide (AD-31: never conflated as a
    CONSTANT/classification)."""
    matrix_statuses = {
        STATUS_MATRIX_NOT_ATTEMPTED,
        STATUS_MATRIX_UNAVAILABLE,
        STATUS_MATRIX_FAIL,
        STATUS_MATRIX_PASS,
    }
    assert matrix_statuses.isdisjoint(ALL_STATUSES)
    assert STATUS_MATRIX_NOT_ATTEMPTED not in (STATUS_AVAILABLE, STATUS_UNAVAILABLE)
    # Coincidental string equality, asserted explicitly (mirrors the
    # smoke-vocabulary test's own precedent above).
    assert STATUS_MATRIX_UNAVAILABLE == STATUS_SMOKE_UNAVAILABLE
    assert STATUS_MATRIX_FAIL == STATUS_SMOKE_FAIL
    assert STATUS_MATRIX_PASS == STATUS_SMOKE_PASS


# --- Story 6.7: entry-file family drift check, detect-only -------------

_HUB = ENTRY_FILE_FAMILY[0]


def _consistent_states() -> dict[str, EntryFileState]:
    states: dict[str, EntryFileState] = {}
    for path in ENTRY_FILE_FAMILY:
        if path == _HUB:
            states[path] = EntryFileState(path=path, exists=True, mentions_hub=None)
        else:
            states[path] = EntryFileState(path=path, exists=True, mentions_hub=True)
    return states


def test_entry_file_family_all_consistent_reports_no_divergence():
    assert evaluate_entry_file_family(_consistent_states()) == ()


def test_entry_file_family_missing_hub_names_every_tool_that_reads_it():
    states = _consistent_states()
    states[_HUB] = EntryFileState(path=_HUB, exists=False, mentions_hub=None)
    divergences = evaluate_entry_file_family(states)
    assert len(divergences) == 1
    divergence = divergences[0]
    assert divergence.path == _HUB
    expected_tools = tuple(sorted(t.tool for t in ENTRY_FILE_TOOLS if _HUB in t.reads))
    assert divergence.affected_tools == expected_tools
    assert "claude" in divergence.affected_tools  # claude reads both CLAUDE.md and AGENTS.md


def test_entry_file_family_missing_satellite_single_reader_not_cross_contaminating():
    cursor_path = ".cursor/rules/specs.mdc"
    states = _consistent_states()
    states[cursor_path] = EntryFileState(path=cursor_path, exists=False, mentions_hub=None)
    divergences = evaluate_entry_file_family(states)
    assert len(divergences) == 1
    divergence = divergences[0]
    assert divergence.path == cursor_path
    assert divergence.affected_tools == ("cursor",)
    assert divergence.cross_contaminating is False


def test_entry_file_family_satellite_no_longer_mentions_hub_is_a_divergence():
    states = _consistent_states()
    states["CLAUDE.md"] = EntryFileState(path="CLAUDE.md", exists=True, mentions_hub=False)
    divergences = evaluate_entry_file_family(states)
    assert len(divergences) == 1
    assert divergences[0].path == "CLAUDE.md"
    assert "no longer references" in divergences[0].detail


def test_entry_file_family_multi_reader_tool_divergence_is_cross_contaminating():
    """CLAUDE.md's own tool (claude) reads TWO family members -- a
    divergence on either one is cross-contaminating for it."""
    states = _consistent_states()
    states["CLAUDE.md"] = EntryFileState(path="CLAUDE.md", exists=True, mentions_hub=False)
    divergences = evaluate_entry_file_family(states)
    assert divergences[0].cross_contaminating is True
    assert "claude" in divergences[0].affected_tools


def test_entry_file_family_missing_state_entry_treated_as_absent():
    """A caller that omits a family member from `states` entirely (never
    crashes)."""
    states = _consistent_states()
    del states[".github/copilot-instructions.md"]
    divergences = evaluate_entry_file_family(states)
    assert len(divergences) == 1
    assert divergences[0].path == ".github/copilot-instructions.md"


def test_entry_file_tools_reads_are_all_declared_family_members():
    """The declared table's own internal consistency -- every tool's
    `reads` entry is a real, declared family member."""
    for tool in ENTRY_FILE_TOOLS:
        for path in tool.reads:
            assert path in ENTRY_FILE_FAMILY
