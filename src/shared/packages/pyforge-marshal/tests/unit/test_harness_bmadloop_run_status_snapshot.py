"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``'s
Story 3.7 additions (``run_status_snapshot``/``resolution_reference``,
AD-9/AD-34/AD-45) -- the escalation/deferral read seam.

Exercised against REAL ``state.json`` fixtures written to ``tmp_path``, read
back through the REAL installed ``bmad_loop`` 0.9.0, mirroring
``test_harness_bmadloop_usage_snapshot.py``'s own convention exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness
from pyforge.marshal.core.policy import REDACTED_SENTINEL
from pyforge.marshal.ports.harness import DeferredStory, RunStatusSnapshot


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


def _write_state(
    project: Path,
    run_id: str,
    *,
    tasks: dict[str, object],
    paused_stage: str | None = None,
    paused_story_key: str | None = None,
    paused_reason: str | None = None,
) -> Path:
    run_dir = project / ".bmad-loop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    state = {
        "run_id": run_id,
        "project": str(project),
        "started_at": "2026-08-03T00:00:00Z",
        "paused_stage": paused_stage,
        "paused_story_key": paused_story_key,
        "paused_reason": paused_reason,
        "tasks": tasks,
    }
    state_path = run_dir / "state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def _task(
    story_key: str,
    phase: str,
    *,
    defer_reason: str | None = None,
    attempt: int = 0,
    branch: str = "",
    worktree_path: str = "",
    spec_file: str | None = None,
) -> dict[str, object]:
    return {
        "story_key": story_key,
        "epic": 3,
        "phase": phase,
        "defer_reason": defer_reason,
        "attempt": attempt,
        "branch": branch,
        "worktree_path": worktree_path,
        "spec_file": spec_file,
    }


# --- ordinary finish: no pause, no deferred stories ------------------------------


def test_no_pause_and_no_deferred_stories_reports_a_clean_snapshot(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={"3.5": _task("3.5", "done"), "3.6": _task("3.6", "dev-running")},
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.paused_stage is None
    assert snapshot.paused_story_key is None
    assert snapshot.paused_reason is None
    assert snapshot.escalated_spec_file is None
    assert snapshot.escalated_task_phase is None
    assert snapshot.deferred == ()


def test_paused_at_a_different_stage_still_reports_no_deferred_by_default(harness, tmp_path):
    """``paused_stage`` values other than ``"escalation"`` are reported
    verbatim -- this port's own job is reading the field, never
    classifying it (that is ``core.supervise.evaluate_escalation``'s own
    job, a separate pure decision over the values this method returns)."""
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={"3.5": _task("3.5", "dev-running")},
        paused_stage="spec-approval",
        paused_story_key=None,
        paused_reason=None,
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.paused_stage == "spec-approval"
    assert snapshot.deferred == ()


# --- escalation pause fields -------------------------------------------------------


def test_escalation_pause_reports_the_paused_storys_own_spec_file_and_phase(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3-7-escalation-deferral-and-resume": _task(
                "3-7-escalation-deferral-and-resume",
                "escalated",
                spec_file="spec-3-7.md",
            )
        },
        paused_stage="escalation",
        paused_story_key="3-7-escalation-deferral-and-resume",
        paused_reason="the frozen spec contradicts itself",
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.paused_stage == "escalation"
    assert snapshot.paused_story_key == "3-7-escalation-deferral-and-resume"
    assert snapshot.paused_reason == "the frozen spec contradicts itself"
    assert snapshot.escalated_spec_file == "spec-3-7.md"
    assert snapshot.escalated_task_phase == "escalated"


def test_escalation_pause_after_a_human_rearm_reports_the_new_phase(harness, tmp_path):
    """bmad-loop's own ``rearm_escalation`` flips the task's phase back to
    ``pending`` WITHOUT clearing the pause -- exactly the window
    ``EscalationStatus.RESOLVED`` classifies. This port reports the raw
    phase either way; the classification lives elsewhere."""
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3-7-escalation-deferral-and-resume": _task(
                "3-7-escalation-deferral-and-resume", "pending", spec_file="spec-3-7.md"
            )
        },
        paused_stage="escalation",
        paused_story_key="3-7-escalation-deferral-and-resume",
        paused_reason="the frozen spec contradicts itself",
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.escalated_task_phase == "pending"


def test_paused_story_key_naming_no_known_task_reports_no_task_fields(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={"3.5": _task("3.5", "done")},
        paused_stage="escalation",
        paused_story_key="no-such-task",
        paused_reason="orphaned pause",
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.paused_story_key == "no-such-task"
    assert snapshot.escalated_spec_file is None
    assert snapshot.escalated_task_phase is None


# --- deferred stories ---------------------------------------------------------------


def test_a_single_deferred_story_is_collected(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3.6": _task(
                "3.6",
                "deferred",
                defer_reason="verify exhausted its retry budget",
                attempt=2,
                branch="loop/3.6",
                worktree_path="/home/acme-loop/.worktrees/3.6",
                spec_file="spec-3-6.md",
            )
        },
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert len(snapshot.deferred) == 1
    deferred = snapshot.deferred[0]
    assert isinstance(deferred, DeferredStory)
    assert deferred.story_key == "3.6"
    assert deferred.reason == "verify exhausted its retry budget"
    assert deferred.attempt == 2
    assert deferred.branch == "loop/3.6"
    assert deferred.worktree_path == "/home/acme-loop/.worktrees/3.6"
    assert deferred.spec_file == "spec-3-6.md"


def test_multiple_deferred_stories_are_all_collected(harness, tmp_path):
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3.5": _task("3.5", "deferred", defer_reason="a plugin veto"),
            "3.6": _task("3.6", "deferred", defer_reason="verify exhausted"),
            "3.7": _task("3.7", "dev-running"),
        },
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert {story.story_key for story in snapshot.deferred} == {"3.5", "3.6"}


def test_a_deferred_task_with_no_reason_reports_none(harness, tmp_path):
    _write_state(tmp_path, "acme-run-1", tasks={"3.6": _task("3.6", "deferred")})

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.deferred[0].reason is None


def test_escalation_and_deferral_can_coexist_in_one_snapshot(harness, tmp_path):
    """Escalation is a RUN-level fact; deferral is per-story -- a single
    run can carry an unresolved escalation on one story while another was
    independently deferred earlier in the same run."""
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={
            "3.6": _task("3.6", "deferred", defer_reason="verify exhausted"),
            "3.7": _task("3.7", "escalated", spec_file="spec-3-7.md"),
        },
        paused_stage="escalation",
        paused_story_key="3.7",
        paused_reason="ambiguous spec",
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.paused_story_key == "3.7"
    assert snapshot.escalated_task_phase == "escalated"
    assert len(snapshot.deferred) == 1
    assert snapshot.deferred[0].story_key == "3.6"


# --- redaction at capture (AD-34) ---------------------------------------------------


def test_paused_reason_is_redacted_at_capture(harness, tmp_path):
    secret = "sk-" + "a" * 45
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={"3.7": _task("3.7", "escalated")},
        paused_stage="escalation",
        paused_story_key="3.7",
        paused_reason=f"leaked during session: {secret}",
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert secret not in snapshot.paused_reason
    assert REDACTED_SENTINEL in snapshot.paused_reason


def test_defer_reason_is_redacted_at_capture(harness, tmp_path):
    secret = "ghp_" + "b" * 40
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={"3.6": _task("3.6", "deferred", defer_reason=f"token in output: {secret}")},
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert secret not in snapshot.deferred[0].reason
    assert REDACTED_SENTINEL in snapshot.deferred[0].reason


def test_an_ordinary_reason_survives_redaction_unchanged(harness, tmp_path):
    """Negative control: redaction must not mangle ordinary text that
    carries no known token shape."""
    _write_state(
        tmp_path,
        "acme-run-1",
        tasks={"3.7": _task("3.7", "escalated")},
        paused_stage="escalation",
        paused_story_key="3.7",
        paused_reason="the frozen spec contradicts AD-38",
    )

    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")

    assert snapshot is not None
    assert snapshot.paused_reason == "the frozen spec contradicts AD-38"


# --- never raises: every plausible read/parse failure degrades to None -------------


def test_returns_none_for_a_missing_run(harness, tmp_path):
    assert harness.run_status_snapshot(tmp_path, "no-such-run") is None


def test_returns_none_for_malformed_json(harness, tmp_path):
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{not valid json at all", encoding="utf-8")

    assert harness.run_status_snapshot(tmp_path, "acme-run-1") is None


def test_returns_none_for_an_unknown_phase(harness, tmp_path):
    """``Phase(d["phase"])`` raises ``ValueError`` for a phase string
    outside the closed enum -- the SAME widened guard ``usage_snapshot``
    documents at length, reused verbatim (never re-derived narrower)."""
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    state = {
        "run_id": "acme-run-1",
        "project": str(tmp_path),
        "started_at": "2026-08-03T00:00:00Z",
        "tasks": {"3.6": {"story_key": "3.6", "epic": 3, "phase": "not-a-real-phase"}},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")

    assert harness.run_status_snapshot(tmp_path, "acme-run-1") is None


def test_returns_none_for_a_deeply_nested_document(harness, tmp_path):
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("[" * 200_000 + "]" * 200_000, encoding="utf-8")

    assert harness.run_status_snapshot(tmp_path, "acme-run-1") is None


def test_result_is_a_frozen_dataclass(harness, tmp_path):
    _write_state(tmp_path, "acme-run-1", tasks={"3.6": _task("3.6", "dev-running")})
    snapshot = harness.run_status_snapshot(tmp_path, "acme-run-1")
    assert isinstance(snapshot, RunStatusSnapshot)
    with pytest.raises(AttributeError):
        snapshot.paused_stage = "mutated"  # type: ignore[misc]


# --- resolution_reference (AD-3/AD-45) ----------------------------------------------


def test_resolution_reference_returns_the_posix_path_when_the_marker_exists(harness, tmp_path):
    run_dir = tmp_path / ".bmad-loop" / "runs" / "acme-run-1"
    marker_dir = run_dir / "resolve" / "3-7-escalation-deferral-and-resume"
    marker_dir.mkdir(parents=True)
    (marker_dir / "resolution.json").write_text("{}", encoding="utf-8")

    result = harness.resolution_reference(
        tmp_path, "acme-run-1", "3-7-escalation-deferral-and-resume"
    )

    assert result == (marker_dir / "resolution.json").as_posix()


def test_resolution_reference_returns_none_when_the_marker_is_absent(harness, tmp_path):
    """A ``--no-interactive`` resolve is never guaranteed to leave a
    marker -- documented as a limitation, not a defect."""
    result = harness.resolution_reference(
        tmp_path, "acme-run-1", "3-7-escalation-deferral-and-resume"
    )

    assert result is None


def test_resolution_reference_never_raises_for_a_path_traversal_shaped_key(harness, tmp_path):
    # A story key containing characters that would otherwise need
    # sanitizing -- `safe_segment` (bmad-loop's own) handles it; no marker
    # exists at the sanitized path, so this degrades to None like any
    # other absent marker, never raising.
    result = harness.resolution_reference(tmp_path, "acme-run-1", "weird/../key")
    assert result is None
