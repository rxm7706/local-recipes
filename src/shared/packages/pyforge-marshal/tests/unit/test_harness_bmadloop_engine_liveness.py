"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``'s
Story 24.1 addition (``engine_liveness``, FR-195 CAP-1) -- the on-demand engine
liveness primitive spec-3-7's deferred double-drive entry names as missing.
Monkeypatches ``PosixProcess.run`` directly, mirroring ``test_harness_bmadloop_
stop_resume.py``'s convention for bounded subprocess seams.
"""

from __future__ import annotations

import json

import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


def _status_ok(run_id: str) -> ProcessResult:
    return ProcessResult(returncode=0, stdout=json.dumps({"run_id": run_id}), stderr="")


def _list_doc(*entries: dict[str, str]) -> ProcessResult:
    return ProcessResult(
        returncode=0,
        stdout=json.dumps({"schema_version": 1, "runs": list(entries)}),
        stderr="",
    )


def test_engine_liveness_maps_running_to_alive(harness, tmp_path, monkeypatch):
    run_id = "acme-20260823T120000Z-ab12cd"
    calls: list[list[str]] = []

    def _fake_run(self, argv, *, cwd, timeout_s):
        calls.append(list(argv))
        if argv[:3] == ["bmad-loop", "status", run_id]:
            return _status_ok(run_id)
        if argv == ["bmad-loop", "list", "--json"]:
            return _list_doc({"run_id": run_id, "status": "running"})
        raise AssertionError(f"unexpected argv: {argv!r}")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert harness.engine_liveness(tmp_path, run_id) == "alive"
    assert calls[0] == ["bmad-loop", "status", run_id, "--json"]
    assert calls[1] == ["bmad-loop", "list", "--json"]


def test_engine_liveness_maps_stopped_to_dead(harness, tmp_path, monkeypatch):
    run_id = "acme-stopped"

    def _fake_run(self, argv, *, cwd, timeout_s):
        if argv[:3] == ["bmad-loop", "status", run_id]:
            return _status_ok(run_id)
        if argv == ["bmad-loop", "list", "--json"]:
            return _list_doc({"run_id": run_id, "status": "stopped"})
        raise AssertionError(argv)

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert harness.engine_liveness(tmp_path, run_id) == "dead"


def test_engine_liveness_returns_unknown_when_status_subprocess_fails(harness, tmp_path, monkeypatch):
    def _fake_run(self, argv, *, cwd, timeout_s):
        return ProcessResult(returncode=1, stdout="", stderr="no such run: absent")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert harness.engine_liveness(tmp_path, "absent-run") == "unknown"


def test_engine_liveness_returns_unknown_when_status_cannot_launch(harness, tmp_path, monkeypatch):
    def _fake_run(self, argv, *, cwd, timeout_s):
        raise ProcessError("cannot launch") from FileNotFoundError("bmad-loop")

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert harness.engine_liveness(tmp_path, "any-run") == "unknown"


def test_engine_liveness_returns_unknown_when_run_missing_from_list(harness, tmp_path, monkeypatch):
    run_id = "acme-missing-from-list"

    def _fake_run(self, argv, *, cwd, timeout_s):
        if argv[:3] == ["bmad-loop", "status", run_id]:
            return _status_ok(run_id)
        if argv == ["bmad-loop", "list", "--json"]:
            return _list_doc({"run_id": "other-run", "status": "running"})
        raise AssertionError(argv)

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert harness.engine_liveness(tmp_path, run_id) == "unknown"


def test_engine_liveness_preserves_unknown_list_status(harness, tmp_path, monkeypatch):
    run_id = "acme-unverifiable"

    def _fake_run(self, argv, *, cwd, timeout_s):
        if argv[:3] == ["bmad-loop", "status", run_id]:
            return _status_ok(run_id)
        if argv == ["bmad-loop", "list", "--json"]:
            return _list_doc({"run_id": run_id, "status": "unknown"})
        raise AssertionError(argv)

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert harness.engine_liveness(tmp_path, run_id) == "unknown"


def test_engine_liveness_never_coerces_unrecognized_list_status_to_alive_or_dead(harness, tmp_path, monkeypatch):
    run_id = "acme-future-status"

    def _fake_run(self, argv, *, cwd, timeout_s):
        if argv[:3] == ["bmad-loop", "status", run_id]:
            return _status_ok(run_id)
        if argv == ["bmad-loop", "list", "--json"]:
            return _list_doc({"run_id": run_id, "status": "future-upstream-token"})
        raise AssertionError(argv)

    monkeypatch.setattr(PosixProcess, "run", _fake_run)
    assert harness.engine_liveness(tmp_path, run_id) == "unknown"
