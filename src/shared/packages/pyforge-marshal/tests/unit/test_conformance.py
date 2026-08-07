"""Unit tests for ``core.conformance`` (Story 6.3, FR-42, AD-31/AD-36) --
pure ``TreeLiveState``/``TreeConformance``/``evaluate_conformance`` matrix,
no filesystem, no I/O."""

from __future__ import annotations

import pytest

from pyforge.marshal.core.conformance import (
    STATUS_ADDED,
    STATUS_LINK_TARGET_CONFIRMED,
    STATUS_MODIFIED,
    STATUS_REMOVED,
    ConformanceReport,
    TreeLiveState,
    _check_symlink_identity,
    evaluate_conformance,
)

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
