"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``'s
Story 3.5 additions (``stop``/``resume``, AD-9/AD-20) -- the idle ladder's
``stop-and-retry`` primitive. Monkeypatches ``subprocess.run``/``Popen``
directly, mirroring ``test_harness_bmadloop_spin.py``'s own convention for
``spin``/``attach``/``run_foreground`` -- a real launch would try to drive a
full ``bmad-loop`` process this suite does not provision.
"""

from __future__ import annotations

import subprocess

import pyforge.marshal.adapters.harness_bmadloop as module
import pytest
from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness, HarnessError


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


class _FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid


# --- stop: synchronous, captures output -----------------------------------------


def test_stop_builds_the_expected_argv_and_returns_true_on_success(harness, tmp_path, monkeypatch):
    calls: list[tuple[list[str], dict]] = []

    def _fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="run x stopped\n")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.stop(tmp_path, "acme-20260803T054512123Z-ab12cd") is True
    [(argv, kwargs)] = calls
    assert argv == ["bmad-loop", "stop", "acme-20260803T054512123Z-ab12cd"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["stdin"] == subprocess.DEVNULL


def test_stop_returns_false_for_a_nonzero_exit(harness, tmp_path, monkeypatch):
    """A non-zero exit (already finished, or any other non-launch failure)
    is the ordinary "did not stop" shape -- never raised."""

    def _fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=1, stdout="already finished\n")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.stop(tmp_path, "acme-run") is False


def test_stop_raises_harness_error_when_the_process_could_not_be_launched(
    harness, tmp_path, monkeypatch
):
    def _fake_run(argv, **kwargs):
        raise FileNotFoundError("no such file: bmad-loop")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    with pytest.raises(HarnessError, match="cannot launch bmad-loop stop"):
        harness.stop(tmp_path, "acme-run")


def test_stop_raises_harness_error_on_timeout(harness, tmp_path, monkeypatch):
    def _fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=module._STOP_TIMEOUT_S)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    with pytest.raises(HarnessError, match="timed out"):
        harness.stop(tmp_path, "acme-run")


def test_stop_raises_harness_error_for_an_embedded_null_byte(harness, tmp_path, monkeypatch):
    def _fake_run(argv, **kwargs):
        raise ValueError("embedded null byte")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    with pytest.raises(HarnessError, match="cannot launch bmad-loop stop"):
        harness.stop(tmp_path, "acme-run")


def test_stop_passes_the_bounded_timeout(harness, tmp_path, monkeypatch):
    seen: dict[str, object] = {}

    def _fake_run(argv, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    harness.stop(tmp_path, "acme-run")
    assert seen["timeout"] == module._STOP_TIMEOUT_S


# --- resume: detached, mirrors spin's own recipe --------------------------------


def test_resume_builds_the_expected_argv_and_returns_the_new_pid(harness, tmp_path, monkeypatch):
    calls: list[tuple[list[str], dict]] = []

    def _fake_popen(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return _FakeProcess(pid=424242)

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    log_path = tmp_path / "harness.log"

    result = harness.resume(tmp_path, "acme-20260803T054512123Z-ab12cd", log_path=log_path)

    assert result == 424242
    [(argv, kwargs)] = calls
    assert argv == ["bmad-loop", "resume", "acme-20260803T054512123Z-ab12cd"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["stdout"].name == str(log_path)
    assert kwargs["stderr"] is kwargs["stdout"]


def test_resume_appends_to_the_log_and_never_truncates_it(harness, tmp_path, monkeypatch):
    """Review finding: ``resume`` opened its ``log_path`` with mode ``"wb"``,
    copied from ``spin``'s own detach recipe. But the file ``spin`` opens is
    brand new, while the one ``resume`` is handed is the WEDGED run's
    existing ``harness.log`` -- everything the original engine attempt wrote
    for however long it ran. Truncating it destroyed the only record of what
    the run was doing when it stopped producing output, at exactly the
    moment ``stop-and-retry`` fires and that record is most valuable."""
    monkeypatch.setattr(module.subprocess, "Popen", lambda argv, **kw: _FakeProcess(pid=1))
    log_path = tmp_path / "harness.log"
    log_path.write_text("the wedged run's own output\n", encoding="utf-8")

    harness.resume(tmp_path, "acme-run", log_path=log_path)

    contents = log_path.read_text(encoding="utf-8")
    assert contents.startswith("the wedged run's own output\n")
    # Follow-up review finding: the append preserves the wedged attempt's
    # output, but with no delimiter the resumed engine's output is
    # byte-concatenated onto it and the operator cannot tell where the record
    # they came for ends. The marker is written BEFORE the child is spawned,
    # so it always separates the two streams.
    assert "--- marshal stop-and-retry: resuming acme-run ---" in contents


def test_resume_forces_pythonunbuffered_on_the_child_env(harness, tmp_path, monkeypatch):
    captured_env: dict = {}

    def _fake_popen(argv, **kwargs):
        captured_env.update(kwargs["env"])
        return _FakeProcess(pid=1)

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    monkeypatch.setenv("SOME_UNRELATED_VAR", "kept")
    harness.resume(tmp_path, "acme-run", log_path=tmp_path / "harness.log")
    assert captured_env["PYTHONUNBUFFERED"] == "1"
    assert captured_env["SOME_UNRELATED_VAR"] == "kept"


def test_resume_never_waits_on_the_child(harness, tmp_path, monkeypatch):
    """Mirrors ``spin``'s own detached-launch contract: a resumed engine run
    is synchronous and unbounded IN THE CHILD (confirmed live against the
    installed 0.9.0 ``_resume_paused_run``), so this method must never call
    ``.wait()``/``.communicate()`` on the ``Popen`` handle."""

    class _TrackedProcess:
        def __init__(self, pid: int) -> None:
            self.pid = pid
            self.waited = False

        def wait(self, *args, **kwargs):
            self.waited = True

    tracked = _TrackedProcess(pid=99)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: tracked)
    harness.resume(tmp_path, "acme-run", log_path=tmp_path / "harness.log")
    assert tracked.waited is False


def test_resume_raises_harness_error_when_the_log_cannot_be_opened(harness, tmp_path):
    log_path = tmp_path / "nonexistent-dir" / "harness.log"
    with pytest.raises(HarnessError, match="cannot open resume log"):
        harness.resume(tmp_path, "acme-run", log_path=log_path)


def test_resume_raises_harness_error_when_popen_raises_oserror(harness, tmp_path, monkeypatch):
    def _fake_popen(argv, **kwargs):
        raise FileNotFoundError("no such file: bmad-loop")

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    with pytest.raises(HarnessError, match="cannot launch bmad-loop resume"):
        harness.resume(tmp_path, "acme-run", log_path=tmp_path / "harness.log")


def test_resume_raises_harness_error_for_an_embedded_null_byte_in_argv(
    harness, tmp_path, monkeypatch
):
    def _fake_popen(argv, **kwargs):
        raise ValueError("embedded null byte")

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    with pytest.raises(HarnessError, match="cannot launch bmad-loop resume"):
        harness.resume(tmp_path, "acme-run", log_path=tmp_path / "harness.log")
