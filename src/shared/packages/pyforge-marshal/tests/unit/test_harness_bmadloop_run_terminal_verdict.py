"""Unit tests for ``BmadLoopHarness.run_terminal_verdict`` (Story 5.11, FR-196)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


def _write_state(project: Path, run_id: str, *, finished: bool) -> None:
    run_dir = project / ".bmad-loop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    state = {
        "run_id": run_id,
        "project": str(project),
        "started_at": "2026-08-20T14:05:36Z",
        "paused_stage": None,
        "paused_story_key": None,
        "paused_reason": None,
        "finished": finished,
        "tasks": {},
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")


def test_finished_state_reports_terminal(harness, tmp_path):
    run_id = "20260820-140536-988f"
    _write_state(tmp_path, run_id, finished=True)
    assert harness.run_terminal_verdict(tmp_path, run_id) == "terminal"


def test_unfinished_state_reports_non_terminal(harness, tmp_path):
    run_id = "20260820-140536-988f"
    _write_state(tmp_path, run_id, finished=False)
    assert harness.run_terminal_verdict(tmp_path, run_id) == "non_terminal"


def test_missing_state_reports_unknown(harness, tmp_path):
    assert harness.run_terminal_verdict(tmp_path, "absent-run") == "unknown"
