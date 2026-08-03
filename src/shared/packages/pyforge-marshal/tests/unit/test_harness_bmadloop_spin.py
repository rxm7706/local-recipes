"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``'s
Story 3.3 additions (``story_feed_keys``/``spin``/``attach``/
``run_foreground``, AD-3/AD-22/AD-25/AD-38) -- ``ports.HarnessPort``'s
launch-side methods.

``story_feed_keys`` is exercised against the REAL installed ``bmad_loop``
0.9.0 (mirrors ``test_harness_bmadloop_preflight.py``'s own
``story_feed_error`` coverage -- no fakes for the package itself).
``spin``/``attach``/``run_foreground`` monkeypatch ``subprocess.Popen``/
``subprocess.run`` directly (the SAME technique
``test_harness_bmadloop_preflight.py``'s own ``harness_version`` failure-mode
tests use for ``subprocess.run``) rather than actually launching a real
``bmad-loop run``/``attach`` process -- a real launch would try to drive a
full engine loop against a project this test suite does not provision, and
these three methods' own contracts (argv shape, launch-failure mapping, the
detached/foreground/attach split) do not depend on the child's real
behavior. ``cli/spin.py``'s own tests (``test_spin.py``) cover the CLI-layer
orchestration against a FAKE ``HarnessPort``."""

from __future__ import annotations

import subprocess
import sys

import pyforge.marshal.adapters.harness_bmadloop as module
import pytest
from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness, HarnessError


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


@pytest.fixture(autouse=True)
def _fast_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file drives ``spin``'s own bounded log-poll --
    pinned to a tiny interval/timeout so a test exercising the "never
    confirmed" degrade path (the real, documented behavior) does not cost
    this suite several real seconds."""
    monkeypatch.setattr(module, "_SPIN_LOG_POLL_INTERVAL_S", 0.01)
    monkeypatch.setattr(module, "_SPIN_LOG_POLL_TIMEOUT_S", 0.2)


def _seed_bmad_config(project, *, valid_config: bool = True) -> None:
    """Mirrors ``test_harness_bmadloop_preflight.py``'s own identical
    helper -- kept as a separate copy (not imported cross-file) per this
    package's flat, standalone-test-file convention."""
    bmad_dir = project / "_bmad" / "bmm"
    bmad_dir.mkdir(parents=True)
    if valid_config:
        (bmad_dir / "config.yaml").write_text(
            "implementation_artifacts: '{project-root}/_bmad-output/implementation-artifacts'\n"
            "planning_artifacts: '{project-root}/_bmad-output/planning-artifacts'\n",
            encoding="utf-8",
        )


# --- story_feed_keys (AD-38's M, against the REAL bmad_loop) -----------------


def test_story_feed_keys_unions_stories_then_unknown_keys_in_file_order(harness, tmp_path):
    _seed_bmad_config(tmp_path)
    feed_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
    feed_dir.mkdir(parents=True)
    (feed_dir / "sprint-status.yaml").write_text(
        "development_status:\n"
        "  epic-1: in-progress\n"
        "  1-1-first-story: done\n"
        "  1-2-second-story: backlog\n"
        "  some-unrecognized-key: something\n",
        encoding="utf-8",
    )
    # epic-1 is administrative (excluded); the two real stories precede the
    # one unrecognized key, matching sprintstatus.load's own file order for
    # each of its two separately-accumulated lists.
    assert harness.story_feed_keys(tmp_path) == (
        "1-1-first-story",
        "1-2-second-story",
        "some-unrecognized-key",
    )


def test_story_feed_keys_returns_empty_tuple_for_an_empty_feed(harness, tmp_path):
    _seed_bmad_config(tmp_path)
    feed_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
    feed_dir.mkdir(parents=True)
    (feed_dir / "sprint-status.yaml").write_text("development_status: {}\n", encoding="utf-8")
    assert harness.story_feed_keys(tmp_path) == ()


def test_story_feed_keys_raises_harness_error_when_bmad_config_missing(harness, tmp_path):
    with pytest.raises(HarnessError):
        harness.story_feed_keys(tmp_path)


def test_story_feed_keys_raises_harness_error_when_sprint_status_file_missing(harness, tmp_path):
    _seed_bmad_config(tmp_path)
    with pytest.raises(HarnessError):
        harness.story_feed_keys(tmp_path)


def test_story_feed_keys_raises_harness_error_when_sprint_status_is_invalid_yaml(
    harness, tmp_path
):
    _seed_bmad_config(tmp_path)
    feed_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
    feed_dir.mkdir(parents=True)
    (feed_dir / "sprint-status.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
    with pytest.raises(HarnessError):
        harness.story_feed_keys(tmp_path)


# --- spin: argv shape + detached-launch mechanics -----------------------------


class _FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_spin_builds_the_expected_argv_with_all_selectors(harness, tmp_path, monkeypatch):
    calls: list[tuple[list[str], dict]] = []

    def _fake_popen(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return _FakeProcess(pid=4242)

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    log_path = tmp_path / "harness.log"

    result = harness.spin(tmp_path, epic=3, story="3-1", max_count=5, log_path=log_path)

    assert result.pid == 4242
    assert result.harness_run_id is None  # nothing written to the log
    [(argv, kwargs)] = calls
    assert argv == [
        "bmad-loop",
        "run",
        "--epic",
        "3",
        "--story",
        "3-1",
        "--max-stories",
        "5",
    ]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] == subprocess.DEVNULL


def test_spin_builds_the_bare_argv_when_every_selector_is_none(harness, tmp_path, monkeypatch):
    calls: list[list[str]] = []

    def _fake_popen(argv, **kwargs):
        calls.append(list(argv))
        return _FakeProcess(pid=1)

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    harness.spin(
        tmp_path, epic=None, story=None, max_count=None, log_path=tmp_path / "harness.log"
    )
    assert calls == [["bmad-loop", "run"]]


def test_spin_recovers_the_harness_run_id_from_its_own_redirected_log(
    harness, tmp_path, monkeypatch
):
    """The exact text the installed 0.9.0 ``cli.py::cmd_run`` prints:
    ``f"run {run_id} starting (attach: bmad-loop attach)"``."""

    def _fake_popen(argv, **kwargs):
        kwargs["stdout"].write(
            b"run acme-20260803T054512123Z-ab12cd starting (attach: bmad-loop attach)\n"
        )
        kwargs["stdout"].flush()
        return _FakeProcess(pid=999)

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    result = harness.spin(
        tmp_path, epic=None, story=None, max_count=None, log_path=tmp_path / "harness.log"
    )
    assert result.pid == 999
    assert result.harness_run_id == "acme-20260803T054512123Z-ab12cd"


def test_spin_harness_run_id_is_none_when_the_poll_window_elapses_unconfirmed(
    harness, tmp_path, monkeypatch
):
    """I/O matrix: "harness_run_id unconfirmed" -- the spawn itself still
    counts a success (pid known); this degrade is the caller's own
    MRS-SPIN-004 trigger, not a raised error."""

    def _fake_popen(argv, **kwargs):
        kwargs["stdout"].write(b"some unrelated harness output\n")
        kwargs["stdout"].flush()
        return _FakeProcess(pid=555)

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    result = harness.spin(
        tmp_path, epic=None, story=None, max_count=None, log_path=tmp_path / "harness.log"
    )
    assert result.pid == 555
    assert result.harness_run_id is None


def test_spin_raises_harness_error_when_popen_raises_oserror(harness, tmp_path, monkeypatch):
    def _fake_popen(argv, **kwargs):
        raise FileNotFoundError("no such file: bmad-loop")

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    with pytest.raises(HarnessError, match="cannot launch bmad-loop run"):
        harness.spin(
            tmp_path, epic=None, story=None, max_count=None, log_path=tmp_path / "harness.log"
        )


def test_spin_raises_harness_error_when_the_log_cannot_be_opened(harness, tmp_path):
    # The parent directory does not exist -- open() raises FileNotFoundError.
    log_path = tmp_path / "nonexistent-dir" / "harness.log"
    with pytest.raises(HarnessError, match="cannot open spin log"):
        harness.spin(tmp_path, epic=None, story=None, max_count=None, log_path=log_path)


def test_spin_forces_pythonunbuffered_on_the_child_env(harness, tmp_path, monkeypatch):
    """Review finding (Blind Hunter, verified live): CPython's stdout is
    fully block-buffered once redirected to a regular file rather than a
    tty, and ``bmad-loop run``'s own "starting" print carries no
    ``flush=True`` -- so without forcing this on the CHILD's own env, the
    poll below would only see that line once the (possibly minutes-long)
    engine run exits or its stdio buffer fills, defeating both the poll and
    AD-22's "returns promptly" in any shell that doesn't happen to already
    export ``PYTHONUNBUFFERED`` (unlike the fakes elsewhere in this file,
    which write synchronously and so never exercised this at all)."""
    captured_env: dict = {}

    def _fake_popen(argv, **kwargs):
        captured_env.update(kwargs["env"])
        return _FakeProcess(pid=1)

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    monkeypatch.setenv("SOME_UNRELATED_VAR", "kept")
    harness.spin(
        tmp_path, epic=None, story=None, max_count=None, log_path=tmp_path / "harness.log"
    )
    assert captured_env["PYTHONUNBUFFERED"] == "1"
    # The rest of the parent's own environment is preserved, not replaced --
    # env= on Popen otherwise means "run with NO inherited variables at all".
    assert captured_env["SOME_UNRELATED_VAR"] == "kept"


@pytest.mark.slow
def test_spin_recovers_the_run_id_from_a_real_unbuffered_subprocess(harness, tmp_path, monkeypatch):
    """The regression test the finding above asked for: a REAL child
    process (not a fake writing synchronously in-process) whose own
    ``print()`` carries no ``flush=True`` -- exactly ``bmad-loop run``'s
    own shape -- redirected to a real file exactly like ``spin`` does it.
    Without the ``PYTHONUNBUFFERED`` env fix this reliably times out
    against the (already test-file-pinned) fast poll window; with it, the
    real OS-level write lands promptly and the poll picks it up well inside
    that window."""
    script = tmp_path / "fake_bmad_loop_run.py"
    script.write_text(
        "import time\n"
        "print('run acme-20260803T054512123Z-realpid starting (attach: bmad-loop attach)')\n"
        "time.sleep(2)\n",
        encoding="utf-8",
    )

    # Captured BEFORE patching -- module.subprocess IS the same stdlib
    # module object this test file's own `subprocess` name refers to, so
    # patching Popen on it and then calling `subprocess.Popen` from inside
    # the replacement calls the replacement again (infinite recursion,
    # caught live writing this test).
    real_popen = subprocess.Popen

    def _fake_popen(argv, **kwargs):
        # Only the argv is substituted (the real `["bmad-loop", "run", ...]`
        # binary does not exist in this test environment) -- env,
        # stdout/stderr redirection, and stdin flow through from spin()'s
        # own real call UNMODIFIED, so the env fix under test is the exact
        # same one a real launch would use.
        return real_popen(
            [sys.executable, str(script)],
            stdout=kwargs["stdout"],
            stderr=kwargs["stderr"],
            stdin=kwargs["stdin"],
            env=kwargs["env"],
        )

    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen)
    result = harness.spin(
        tmp_path, epic=None, story=None, max_count=None, log_path=tmp_path / "harness.log"
    )
    assert result.harness_run_id == "acme-20260803T054512123Z-realpid"


# --- attach: exec + inherited stdio + exit-code relay -------------------------


def test_attach_relays_the_real_returncode(harness, tmp_path, monkeypatch):
    calls: list[tuple[list[str], dict]] = []

    def _fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(args=argv, returncode=7)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.attach(tmp_path) == 7
    [(argv, kwargs)] = calls
    assert argv == ["bmad-loop", "attach"]
    assert kwargs["cwd"] == tmp_path
    # Inherits stdio -- no stdout/stderr/stdin override, unlike spin()'s own
    # DEVNULL/redirected-log convention.
    assert "stdout" not in kwargs
    assert "stderr" not in kwargs
    assert "stdin" not in kwargs


def test_attach_raises_harness_error_on_launch_failure(harness, tmp_path, monkeypatch):
    def _fake_run(argv, **kwargs):
        raise FileNotFoundError("no such file: bmad-loop")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    with pytest.raises(HarnessError, match="cannot launch bmad-loop attach"):
        harness.attach(tmp_path)


def test_attach_normalizes_a_negative_signal_returncode(harness, tmp_path, monkeypatch):
    """Review finding (Edge Case Hunter, verified live): a child killed by a
    signal reports a NEGATIVE ``returncode`` (POSIX convention, ``-N`` for
    signal ``N``) -- relayed raw, that gets OS-truncated by
    ``sys.exit``/``SystemExit`` into a different, misleading exit status.
    ``_normalize_returncode`` maps it to the standard ``128 + N`` shell
    convention instead."""

    def _fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=-9)  # SIGKILL

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.attach(tmp_path) == 137


# --- run_foreground: the --foreground counterpart to spin ---------------------


def test_run_foreground_builds_the_expected_argv_and_relays_the_returncode(
    harness, tmp_path, monkeypatch
):
    calls: list[tuple[list[str], dict]] = []

    def _fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(args=argv, returncode=1)

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    code = harness.run_foreground(tmp_path, epic=2, story=None, max_count=None)
    assert code == 1
    [(argv, kwargs)] = calls
    assert argv == ["bmad-loop", "run", "--epic", "2"]
    assert kwargs["cwd"] == tmp_path
    assert "stdout" not in kwargs
    assert "stderr" not in kwargs
    assert "stdin" not in kwargs


def test_run_foreground_raises_harness_error_on_launch_failure(harness, tmp_path, monkeypatch):
    def _fake_run(argv, **kwargs):
        raise FileNotFoundError("boom")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    with pytest.raises(HarnessError, match="cannot launch bmad-loop run"):
        harness.run_foreground(tmp_path, epic=None, story=None, max_count=None)


def test_run_foreground_normalizes_a_negative_signal_returncode(harness, tmp_path, monkeypatch):
    def _fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(args=argv, returncode=-2)  # SIGINT

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.run_foreground(tmp_path, epic=None, story=None, max_count=None) == 130
