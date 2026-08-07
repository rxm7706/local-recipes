"""Unit tests for ``core.conformance`` (Story 6.3, FR-42, AD-31/AD-36) --
pure ``TreeLiveState``/``TreeConformance``/``evaluate_conformance`` matrix,
no filesystem, no I/O."""

from __future__ import annotations

import pytest

from pyforge.marshal.core.conformance import (
    ALL_STATUSES,
    STATUS_ADDED,
    STATUS_AVAILABLE,
    STATUS_LINK_TARGET_CONFIRMED,
    STATUS_MODIFIED,
    STATUS_REMOVED,
    STATUS_UNAVAILABLE,
    ConformanceReport,
    TreeLiveState,
    _check_symlink_identity,
    build_probe_record,
    evaluate_conformance,
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
