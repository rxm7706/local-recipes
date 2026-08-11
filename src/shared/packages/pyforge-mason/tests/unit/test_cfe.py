"""Story 1.6 -- the CFE import-floor probe: full/partial floor, caching,
the `OSError`/`TimeoutExpired` fold-into-missing path, and
`ensure_import_floor`'s raise/no-raise paths. `subprocess.run` is mocked
throughout (AD-16: no test in this suite requires a real interpreter to
probe).

Story 1.7 extends this file with `ensure_cfe_root`'s raise/no-raise paths
over every `resolve.py` step.

Story 2.1 extends this file with CAPTURE-mode coverage: `_extract_json`'s
tolerant-parsing paths, `_invoke_captured`'s I/O-matrix behavior (mocked),
and `validate_recipe`/`submit_pr` end-to-end against Story 1.9's
`fake_cfe_root` fixture, real subprocess, no mocking (mirroring
`test_fake_cfe_root_fixture.py`'s own style for that half)."""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.mason import cfe as cfe_module
from pyforge.mason.cfe import (
    CFE_IMPORT_FLOOR, _CFE_SCRIPTS, ImportFloorResult, _build_probe_script,
    _extract_json, _invoke_captured, ensure_cfe_root, ensure_import_floor,
    probe_import_floor, run_streamed, submit_pr, validate_recipe,
)
from pyforge.mason.errors import CfeImportFloorError, CfeTimeoutError, CfeUnresolvedError
from pyforge.mason.models import CfeResult
from pyforge.mason.resolve import (
    STEP_CWD_WALK, STEP_ENVIRONMENT, STEP_FLAG, STEP_NOT_FOUND, ResolvedCfeRoot,
)


@pytest.fixture(autouse=True)
def _clear_probe_cache():
    """`probe_import_floor` is `functools.lru_cache`-wrapped for the process
    lifetime; without clearing it here, one test's cached result for a given
    interpreter string would leak into another test reusing that same
    string."""
    probe_import_floor.cache_clear()
    yield
    probe_import_floor.cache_clear()


def _fake_completed(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _all_ok_stdout() -> str:
    return "\n".join(f"{name}:ok" for name in CFE_IMPORT_FLOOR.values())


# --- I/O & Edge-Case Matrix --------------------------------------------------

def test_full_floor_importable_reports_nothing_missing():
    with patch("pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())) as mock_run:
        result = probe_import_floor("/fake/python")

    assert result == ImportFloorResult(interpreter="/fake/python", missing=())
    mock_run.assert_called_once()


def test_partial_floor_missing_reported_in_floor_declared_order():
    # Report the subprocess output in the OPPOSITE order from
    # CFE_IMPORT_FLOOR's declaration, to prove `missing`'s ordering comes
    # from the floor table, not from subprocess-output order.
    stdout_lines = []
    for name in reversed(list(CFE_IMPORT_FLOOR.values())):
        if name in ("truststore", "ruamel.yaml"):
            stdout_lines.append(f"{name}:missing")
        else:
            stdout_lines.append(f"{name}:ok")
    stdout = "\n".join(stdout_lines)

    with patch("pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(stdout)):
        result = probe_import_floor("/fake/python")

    assert result.missing == ("truststore", "ruamel.yaml")


def test_second_probe_of_same_interpreter_uses_cache():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        first = probe_import_floor("/same/python")
        second = probe_import_floor("/same/python")

    assert first == second
    mock_run.assert_called_once()


def test_different_interpreters_are_probed_independently():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        probe_import_floor("/one/python")
        probe_import_floor("/two/python")

    assert mock_run.call_count == 2


def test_interpreter_cannot_be_spawned_reports_every_module_missing():
    with patch("pyforge.mason.cfe.subprocess.run", side_effect=OSError("no such file")):
        result = probe_import_floor("/does/not/exist")

    assert result.missing == tuple(CFE_IMPORT_FLOOR)
    assert result.interpreter == "/does/not/exist"


def test_probe_timeout_reports_every_module_missing():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["python"], timeout=15.0),
    ):
        result = probe_import_floor("/slow/python")

    assert result.missing == tuple(CFE_IMPORT_FLOOR)


def test_ensure_import_floor_raises_when_missing():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        return_value=_fake_completed("yaml:missing\nrequests:ok\npackaging:ok\ntruststore:ok\nruamel.yaml:ok\nconda_forge_metadata:ok"),
    ):
        with pytest.raises(CfeImportFloorError) as excinfo:
            ensure_import_floor("/fake/python")

    assert excinfo.value.missing == ("pyyaml",)
    assert excinfo.value.interpreter == "/fake/python"


def test_ensure_import_floor_returns_none_when_full_floor_present():
    with patch("pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())):
        assert ensure_import_floor("/fake/python") is None


# --- Probe invocation shape (list argv, never shell=True, timeout) --------

def test_probe_invokes_subprocess_with_list_argv_and_no_shell():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        probe_import_floor("/fake/python")

    args, kwargs = mock_run.call_args
    argv = args[0]
    assert argv[0] == "/fake/python"
    assert argv[1] == "-c"
    assert isinstance(argv[2], str)
    assert kwargs.get("shell", False) is False
    assert "timeout" in kwargs
    assert kwargs.get("check") is False


# --- Review pass: probe script actually runs correctly (not just mocked) ---

def test_build_probe_script_actually_runs_correctly_under_a_real_interpreter():
    """`_build_probe_script`'s generated source is never exercised by the
    mocked tests above -- this test runs it for real under `sys.executable`
    (which always has `importlib` and the stdlib modules on the floor:
    `packaging` ships with `pip`/build tooling and is installed in this test
    environment) to prove the generated code is syntactically valid and
    produces the documented `:ok`/`:missing` marker format, not just that
    the mocked parsing logic in `probe_import_floor` is self-consistent."""
    script = _build_probe_script()

    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=15.0, check=False,
    )

    assert completed.stderr == ""
    lines = completed.stdout.splitlines()
    assert len(lines) == len(CFE_IMPORT_FLOOR)
    for import_name, line in zip(CFE_IMPORT_FLOOR.values(), lines):
        assert line in (f"{import_name}:ok", f"{import_name}:missing")


def test_build_probe_script_reports_missing_for_a_module_that_does_not_exist(monkeypatch):
    """A floor entry with no real backing module must produce `:missing`,
    not a raw traceback -- proven against a real interpreter, not a mock."""
    monkeypatch.setattr(
        "pyforge.mason.cfe.CFE_IMPORT_FLOOR",
        {"definitely-not-a-real-package": "definitely_not_a_real_module_xyz"},
    )
    script = _build_probe_script()

    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=15.0, check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.splitlines() == ["definitely_not_a_real_module_xyz:missing"]


# --- Review pass: ensure_import_floor shares probe_import_floor's cache ---

def test_ensure_import_floor_reuses_probe_import_floor_cache():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_fake_completed(_all_ok_stdout())
    ) as mock_run:
        ensure_import_floor("/same/python")
        ensure_import_floor("/same/python")

    mock_run.assert_called_once()


# --- Review pass: a crash partway through the probe script still credits
# modules that printed their marker before the crash ----------------------

def test_nonzero_returncode_with_partial_output_still_credits_printed_modules():
    stdout = "yaml:ok\nrequests:ok\n"  # only 2 of 6 lines printed before a crash
    completed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout=stdout, stderr="Traceback (most recent call last)...",
    )
    with patch("pyforge.mason.cfe.subprocess.run", return_value=completed):
        result = probe_import_floor("/fake/python")

    assert "pyyaml" not in result.missing
    assert "requests" not in result.missing
    assert result.missing == ("packaging", "truststore", "ruamel.yaml", "conda-forge-metadata")


# --- Story 1.7: ensure_cfe_root ----------------------------------------------

@pytest.mark.parametrize("step", [STEP_FLAG, STEP_ENVIRONMENT, STEP_CWD_WALK])
def test_ensure_cfe_root_returns_none_for_every_resolved_step(step, tmp_path):
    resolved = ResolvedCfeRoot(root=tmp_path, step=step)
    assert ensure_cfe_root(resolved) is None


def test_ensure_cfe_root_raises_cfe_unresolved_error_when_not_found():
    resolved = ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)
    with pytest.raises(CfeUnresolvedError):
        ensure_cfe_root(resolved)


def test_ensure_cfe_root_never_re_resolves():
    """`ensure_cfe_root` takes the already-computed `ResolvedCfeRoot` -- it
    must never call `resolve_cfe_root` to re-derive it (spec Never
    boundary).

    Review pass (2026-08-09): this used to monkeypatch
    `pyforge.mason.resolve.resolve_cfe_root`, but `cfe.py` never imports
    that name -- only `ResolvedCfeRoot`/`STEP_NOT_FOUND` -- so the
    monkeypatch exercised nothing and would not catch the realistic
    regression: a future `from .resolve import resolve_cfe_root` added to
    `cfe.py` and called unqualified would bind its own name in `cfe.py`'s
    module namespace, untouched by patching the attribute on the `resolve`
    module. A structural assertion that `cfe.py` never binds that name at
    all is the stronger guard -- it fails the moment such an import is
    added, regardless of whether it is ever called."""
    import pyforge.mason.cfe as cfe_module

    assert not hasattr(cfe_module, "resolve_cfe_root")


# --- Story 1.10: run_streamed -- against real sys.executable child ---------
# ------------------------------- processes, mirroring the real-interpreter -
# ------------------------------- precedent above (AD-16 does not apply to --
# ------------------------------- this file's own real-subprocess tests). --

def test_run_streamed_forwards_stderr_live_not_buffered_to_completion():
    """The child writes one stderr line, sleeps, writes a second stderr
    line, then emits a JSON stdout line. A custom sink timestamps the
    instant it sees the first line; `run_streamed` itself runs in a
    background thread so the test can prove that line was delivered while
    the child was still sleeping -- genuine incremental delivery, not just
    correct final content (capsys can't observe this: it only offers the
    post-hoc aggregate, never an as-it-happens callback).

    Review pass (2026-08-10): this used to assert "`second-line` is not in
    the sink *yet*" from the main thread after waiting on an Event. That
    reads the sink at an arbitrary later moment, so any pause longer than
    the child's sleep between the Event firing and the assertion running (a
    loaded CI box, GIL contention, a parallel suite) failed the test with no
    real defect. The timestamp is captured inside the sink at the moment the
    line arrives, so the proof no longer depends on when the main thread
    happens to be scheduled."""
    child_sleep = 2.0
    script = (
        "import sys, time, json\n"
        "print('first-line', file=sys.stderr, flush=True)\n"
        f"time.sleep({child_sleep})\n"
        "print('second-line', file=sys.stderr, flush=True)\n"
        "print(json.dumps({'ok': True}))\n"
    )

    class _EventSink:
        def __init__(self) -> None:
            self.first_line_seen = threading.Event()
            self.first_line_at: float | None = None
            self.lines: list[str] = []

        def write(self, s: str) -> None:
            self.lines.append(s)
            if "first-line" in s and self.first_line_at is None:
                self.first_line_at = time.monotonic()
                self.first_line_seen.set()

        def flush(self) -> None:
            pass

    sink = _EventSink()
    result: dict = {}

    def _run() -> None:
        rc, out = run_streamed([sys.executable, "-c", script], timeout=30.0, stderr_sink=sink)
        result["rc"] = rc
        result["out"] = out

    started_at = time.monotonic()
    thread = threading.Thread(target=_run)
    thread.start()

    assert sink.first_line_seen.wait(timeout=20.0), "first stderr line never reached the sink"
    # Delivered while the child was still inside its own sleep -- buffering
    # to completion could not produce a first line this early. Measured at
    # arrival, so a slow main thread cannot turn a correct run into a
    # failure; `started_at` predates the interpreter spawn, making this
    # strictly harder to pass than the real streaming latency.
    assert sink.first_line_at is not None
    assert sink.first_line_at - started_at < child_sleep

    thread.join(timeout=30.0)
    assert not thread.is_alive()
    assert result["rc"] == 0
    assert any("second-line" in line for line in sink.lines)
    assert json.loads(result["out"].strip()) == {"ok": True}


def test_run_streamed_returned_stdout_is_isolated_from_masons_own_stdout(capsys):
    """Mason's own real `sys.stdout` must be untouched by a streaming call
    (AD-8/AD-25) -- the child's stdout is only ever returned as a string,
    never printed."""
    script = "print('child-stdout-marker')\n"

    rc, out = run_streamed([sys.executable, "-c", script], timeout=15.0)

    assert rc == 0
    assert "child-stdout-marker" in out
    assert capsys.readouterr().out == ""


def test_run_streamed_timeout_kills_child_and_raises_promptly():
    """A child that outlives `timeout` is killed (no orphan) and
    `subprocess.TimeoutExpired` propagates -- and the call itself returns
    promptly, proving no hang, not just that the exception type is correct."""
    script = "import time\ntime.sleep(30)\n"

    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_streamed([sys.executable, "-c", script], timeout=0.3)
    elapsed = time.monotonic() - start

    # Review pass (2026-08-10): this bound was `< 10.0`, which the un-killed
    # mutant clears by only 0.3s -- it fails at 10.3s purely because the two
    # bounded reader joins cap it at 2 * _JOIN_GRACE_SECONDS, so retuning
    # that constant below 5.0 would let a genuinely orphaned 30-second child
    # sail through green. A killed child releases its pipes immediately, so
    # both joins return at once and the real figure here is ~0.4s; 3.0s is
    # generous for a loaded CI box while staying far under any join-derived
    # ceiling.
    assert elapsed < 3.0


def test_run_streamed_default_sink_resolves_to_current_sys_stderr_at_call_time(capsys):
    """No `stderr_sink` given -- must resolve to `sys.stderr` as it is *at
    call time*, not a module-import-time reference, so it tracks capsys's
    per-test monkeypatching."""
    script = "import sys\nprint('child-stderr-marker', file=sys.stderr, flush=True)\n"

    rc, _out = run_streamed([sys.executable, "-c", script], timeout=15.0)

    assert rc == 0
    assert "child-stderr-marker" in capsys.readouterr().err


# --- Review pass (2026-08-09): non-zero exit propagation, argv/env hardening

def test_run_streamed_propagates_a_nonzero_child_returncode():
    """Half of `run_streamed`'s declared return contract (returncode, stdout)
    was never exercised by a failing child -- every prior test's child exits
    0."""
    script = "import sys\nsys.exit(7)\n"

    rc, _out = run_streamed([sys.executable, "-c", script], timeout=15.0)

    assert rc == 7


def test_run_streamed_rejects_a_bare_str_argv():
    """`argv: Sequence[str]` accepts a bare `str` unguarded by the type
    system alone -- `list("mason build")` explodes into single characters.
    `run_streamed` must reject this shape immediately with a clear error,
    not a confusing `FileNotFoundError` for a one-character "program"."""
    with pytest.raises(TypeError, match="bare str"):
        run_streamed("mason build", timeout=15.0)


def test_run_streamed_env_replaces_not_merges_the_inherited_environment(monkeypatch):
    """`env=` is passed straight to `Popen`, which *replaces* the child's
    environment rather than merging it with the caller's own -- a variable
    only visible in the parent (not explicitly included in `env=`) must NOT
    reach the child."""
    monkeypatch.setenv("MASON_TEST_PARENT_ONLY_VAR", "parent-value")
    script = (
        "import os\n"
        "print('present' if 'MASON_TEST_PARENT_ONLY_VAR' in os.environ else 'absent')\n"
        "print('child-var=' + os.environ.get('MASON_TEST_CHILD_VAR', '<unset>'))\n"
    )

    rc, out = run_streamed(
        [sys.executable, "-c", script],
        timeout=15.0,
        env={"MASON_TEST_CHILD_VAR": "child-value"},
    )

    assert rc == 0
    assert "absent" in out  # the parent-only var did NOT leak through
    assert "child-var=child-value" in out  # the explicitly-passed var did


def test_run_streamed_kills_child_on_a_non_timeout_exception_from_wait(monkeypatch):
    """The "no orphaned process" guarantee must hold for ANY exception
    escaping `proc.wait()`, not only `subprocess.TimeoutExpired` -- proven
    here with a synthetic `KeyboardInterrupt` standing in for the real one a
    user's Ctrl-C would raise."""
    import pyforge.mason.cfe as cfe_module

    killed = {"called": False}
    real_popen = cfe_module.subprocess.Popen

    class _Proc:
        def __init__(self, *args, **kwargs):
            self._proc = real_popen(*args, **kwargs)

        @property
        def stdout(self):
            return self._proc.stdout

        @property
        def stderr(self):
            return self._proc.stderr

        def wait(self, timeout=None):
            if timeout is not None:
                raise KeyboardInterrupt()
            return self._proc.wait()

        def kill(self):
            killed["called"] = True
            self._proc.kill()

    monkeypatch.setattr(cfe_module.subprocess, "Popen", _Proc)

    with pytest.raises(KeyboardInterrupt):
        run_streamed([sys.executable, "-c", "import time; time.sleep(5)"], timeout=15.0)

    assert killed["called"]


# --- Review pass (2026-08-10): empty argv, timeout validation, stdin -------

def test_run_streamed_rejects_an_empty_argv():
    """`argv=[]` passes the bare-str/bytes guard but explodes `Popen([])`
    into an unhelpful `IndexError` -- must be rejected up front with a clear
    error naming the mistake instead."""
    with pytest.raises(ValueError, match="must not be empty"):
        run_streamed([], timeout=15.0)


@pytest.mark.parametrize("bad_timeout", [float("nan"), float("inf"), float("-inf"), 0.0, -5.0])
def test_run_streamed_rejects_a_non_finite_or_non_positive_timeout(bad_timeout):
    """`run_streamed`'s own `timeout` parameter must be validated
    independently of `cli.py`'s `_parse_finite_float` -- a caller (e.g. a
    future `engines/*` mirror) may invoke this function directly, bypassing
    argparse entirely. `nan`/`inf` never expire; zero/negative expire before
    the child has any chance to run."""
    with pytest.raises(ValueError, match="finite, positive"):
        run_streamed([sys.executable, "-c", "pass"], timeout=bad_timeout)


def test_run_streamed_survives_a_broken_stderr_sink():
    """Both reviewers independently found the reader threads had no
    exception handling: a `stderr_sink` that raises on write must not crash
    the daemon reader thread via Python's default excepthook, hang, or make
    `run_streamed` raise a second, unrelated error type -- it degrades
    (whatever reached the sink before the failure stays there, the rest is
    lost) and the function still returns normally."""
    class _BrokenSink:
        def write(self, s: str) -> None:
            raise OSError("sink is broken")

        def flush(self) -> None:
            pass

    script = "import sys\nprint('line', file=sys.stderr, flush=True)\nprint('stdout-marker')\n"

    rc, out = run_streamed(
        [sys.executable, "-c", script], timeout=15.0, stderr_sink=_BrokenSink(),
    )

    assert rc == 0
    assert "stdout-marker" in out


def test_run_streamed_child_stdin_is_not_inherited():
    """The child's stdin must be `subprocess.DEVNULL`, not Mason's own
    stdin -- a delegated operation that unexpectedly prompts for input must
    fail fast (EOF) rather than hang waiting on a stream nothing feeds in a
    non-interactive context."""
    script = (
        "import sys\n"
        "data = sys.stdin.read()\n"
        "print('stdin-read-returned:' + repr(data))\n"
    )

    rc, out = run_streamed([sys.executable, "-c", script], timeout=15.0)

    assert rc == 0
    assert "stdin-read-returned:''" in out


# --- Review pass (2026-08-10): the broken-sink deadlock, pipe hygiene, -----
# --------------------------------- and a non-numeric timeout --------------

def test_run_streamed_broken_stderr_sink_does_not_deadlock_a_noisy_child():
    """The regression that `test_run_streamed_survives_a_broken_stderr_sink`
    above cannot catch: its child emits a single stderr line, so the OS pipe
    buffer never fills and abandoning the pipe costs nothing.

    A child noisy enough to fill the ~64KB stderr buffer exposes the real
    defect. Wrapping the whole read loop in `except Exception: return`
    stopped draining stderr the moment the sink first raised, so the child
    blocked forever on its next write and was SIGKILLed when `timeout`
    expired -- a healthy process destroyed by a broken *output destination*,
    the exact failure mode this primitive exists to prevent. Verified
    against the pre-fix code: `TimeoutExpired` after the full 5s.

    The reader must keep consuming to EOF and discard what it can no longer
    deliver, so this completes in well under `timeout`."""
    class _BrokenSink:
        def __init__(self) -> None:
            self.writes = 0

        def write(self, s: str) -> None:
            self.writes += 1
            raise BrokenPipeError("downstream reader exited (e.g. `... | head -5`)")

        def flush(self) -> None:  # pragma: no cover - never reached
            pass

    script = (
        "import sys\n"
        "for i in range(20000):\n"
        "    sys.stderr.write('noisy stderr line %d ---------------------------\\n' % i)\n"
        "sys.stderr.flush()\n"
        "print('stdout-marker')\n"
    )
    sink = _BrokenSink()

    start = time.monotonic()
    rc, out = run_streamed(
        [sys.executable, "-c", script], timeout=20.0, stderr_sink=sink,
    )
    elapsed = time.monotonic() - start

    assert rc == 0
    assert "stdout-marker" in out
    assert elapsed < 15.0, "the child was throttled by an undrained stderr pipe"
    # The sink was genuinely exercised and genuinely broken -- one failed
    # write, then never written to again.
    assert sink.writes == 1


def test_run_streamed_closes_both_child_pipes(monkeypatch):
    """`Popen` is not used as a context manager here (the reader threads
    outlive any `with` block), so without an explicit close every call leaks
    two file descriptors until the GC runs -- 18 `ResourceWarning: unclosed
    file` across this file under `-W error::ResourceWarning` before the
    2026-08-10 review pass.

    Asserted on the descriptors themselves, not via `ResourceWarning`
    (review pass, 2026-08-10, second): the earlier version of this test wrapped
    the call in `warnings.catch_warnings()` + `simplefilter("error",
    ResourceWarning)` and could not fail. The warning is emitted by the GC
    when the `TextIOWrapper` is finalized -- after the `with` block has
    exited, and never at all while the `Popen` object is still referenced --
    and arrives as an *unraisable* exception, which pytest downgrades to a
    non-fatal `PytestUnraisableExceptionWarning`. Deleting the close loop
    entirely left it passing, which is how the deadlock that loop introduced
    (see the grandchild test below) reached a third review pass unnoticed.
    """
    created: list[subprocess.Popen] = []
    real_popen = subprocess.Popen

    def _capturing_popen(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        created.append(proc)
        return proc

    monkeypatch.setattr(subprocess, "Popen", _capturing_popen)

    rc, out = run_streamed([sys.executable, "-c", "print('marker')"], timeout=15.0)

    assert rc == 0
    assert "marker" in out
    # Held by `created`, so nothing has been garbage-collected: `closed` here
    # reflects `run_streamed`'s own explicit close, not a finalizer.
    assert len(created) == 1
    assert created[0].stdout is not None and created[0].stdout.closed
    assert created[0].stderr is not None and created[0].stderr.closed


def test_run_streamed_returns_promptly_when_a_grandchild_holds_the_pipes(monkeypatch, tmp_path):
    """A grandchild that inherits the pipe file descriptors and outlives the
    direct child keeps both pipes from ever reaching EOF. `run_streamed` must
    still return, bounded by `_JOIN_GRACE_SECONDS` (review pass, 2026-08-10,
    second).

    This is the scenario `_JOIN_GRACE_SECONDS` was introduced for, and the
    previous pass's unconditional pipe close silently defeated it: `close()`
    takes the `BufferedReader` lock the still-blocked reader thread holds, so
    the main thread waited for exactly the EOF the bounded join had just
    given up on -- an unbounded hang, reproduced at 45s against a child that
    exits instantly, and swallowing `TimeoutExpired` outright on the timeout
    path. Run in a worker thread so a regression fails this test instead of
    hanging the suite.
    """
    monkeypatch.setattr(cfe_module, "_JOIN_GRACE_SECONDS", 0.5)

    created: list[subprocess.Popen] = []
    real_popen = subprocess.Popen

    def _capturing_popen(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        created.append(proc)
        return proc

    monkeypatch.setattr(subprocess, "Popen", _capturing_popen)

    pid_file = tmp_path / "grandchild.pid"
    # The grandchild inherits this child's stdout/stderr (no redirection), so
    # both pipes stay open after the child itself exits.
    script = (
        "import subprocess, sys, pathlib\n"
        f"p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid))\n"
        "sys.stdout.write('child-done\\n')\n"
    )

    result: dict = {}

    def _run() -> None:
        result["value"] = run_streamed([sys.executable, "-c", script], timeout=30.0)

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    worker.join(timeout=20.0)

    try:
        assert not worker.is_alive(), (
            "run_streamed never returned: the bounded reader join was defeated "
            "(closing a pipe whose reader is still blocked waits on that reader's lock)"
        )
        # The direct child exited 0; stdout is empty rather than a true
        # partial capture, exactly as `_JOIN_GRACE_SECONDS` documents.
        assert result["value"][0] == 0
    finally:
        if pid_file.exists():
            with contextlib.suppress(ProcessLookupError, ValueError):
                os.kill(int(pid_file.read_text()), signal.SIGKILL)
        # `run_streamed` deliberately left both pipes open to their
        # still-blocked readers. With the grandchild gone those readers hit
        # EOF and release the buffer lock, so closing here is safe and keeps
        # the suite clean under `-W error::ResourceWarning` -- bounded in a
        # worker thread regardless, so a future regression degrades to a
        # warning rather than hanging the suite.
        def _close_leaked_pipes() -> None:
            for proc in created:
                for stream in (proc.stdout, proc.stderr):
                    if stream is not None:
                        with contextlib.suppress(Exception):
                            stream.close()

        closer = threading.Thread(target=_close_leaked_pipes, daemon=True)
        closer.start()
        closer.join(timeout=5.0)


def test_run_streamed_forwards_every_line_to_a_sink_without_a_flush_method():
    """A sink is only required to be writable. The docstring explicitly
    invites a hand-rolled tee, and one without a `flush` method used to raise
    `AttributeError` on the first line and latch the sink dead for the rest
    of the run -- delivering line 1 of N and silently dropping the rest
    (review pass, 2026-08-10, second)."""

    class _WriteOnlySink:
        def __init__(self) -> None:
            self.lines: list[str] = []

        def write(self, s: str) -> None:
            self.lines.append(s)

    sink = _WriteOnlySink()
    script = (
        "import sys\n"
        "for i in range(5):\n"
        "    print('line-%d' % i, file=sys.stderr, flush=True)\n"
    )

    rc, _ = run_streamed([sys.executable, "-c", script], timeout=15.0, stderr_sink=sink)

    assert rc == 0
    assert "".join(sink.lines).count("line-") == 5


def test_run_streamed_keeps_forwarding_when_only_flush_fails():
    """A failing `flush()` is not proof the sink is gone -- a one-off
    `BlockingIOError` (EAGAIN on a non-blocking stderr) used to latch the
    sink dead permanently after the first line (review pass, 2026-08-10,
    second). A genuinely broken sink still latches, via its failing
    *write* -- proven by
    `test_run_streamed_broken_stderr_sink_does_not_deadlock_a_noisy_child`."""

    class _FlushFailsSink:
        def __init__(self) -> None:
            self.lines: list[str] = []

        def write(self, s: str) -> None:
            self.lines.append(s)

        def flush(self) -> None:
            raise BlockingIOError("EAGAIN")

    sink = _FlushFailsSink()
    script = (
        "import sys\n"
        "for i in range(5):\n"
        "    print('line-%d' % i, file=sys.stderr, flush=True)\n"
    )

    rc, _ = run_streamed([sys.executable, "-c", script], timeout=15.0, stderr_sink=sink)

    assert rc == 0
    assert "".join(sink.lines).count("line-") == 5


def test_run_streamed_rejects_an_exhausted_generator_argv():
    """`not argv` is always `False` for a generator, so an empty one slipped
    past the non-empty guard and reached `Popen([])` -- raising the exact
    `IndexError` that guard exists to replace (review pass, 2026-08-10,
    second). `argv` is now materialized once, before both guards."""
    with pytest.raises(ValueError, match=r"run_streamed\(argv=\.\.\.\)"):
        run_streamed((token for token in []), timeout=15.0)


def test_run_streamed_accepts_a_generator_argv():
    """The materialization above must not break a valid non-`Sized` argv:
    `list()` is called once, and the resulting list -- not the already-
    consumed iterator -- is what reaches `Popen`."""
    argv = (token for token in [sys.executable, "-c", "print('gen-marker')"])

    rc, out = run_streamed(argv, timeout=15.0)

    assert rc == 0
    assert "gen-marker" in out


@pytest.mark.parametrize("bad_timeout", [None, "15", object()])
def test_run_streamed_rejects_a_non_numeric_timeout(bad_timeout):
    """`math.isfinite` alone raised a bare "must be real number, not
    NoneType" naming neither this function nor the parameter (review pass,
    2026-08-10). `timeout=None` is the likely mistake -- it means "wait
    forever" to subprocess's own API, and this function has no such mode."""
    with pytest.raises(TypeError, match=r"run_streamed\(timeout=\.\.\.\)"):
        run_streamed([sys.executable, "-c", "pass"], timeout=bad_timeout)


# --- Review pass (2026-08-10, third): stderr must stream as PRODUCED, not ---
# --- per newline; decoding is pinned; a busy sink is not a dead sink. -------

class _TimestampingSink:
    """Records `(seconds since t0, text)` for every write, so a test can
    assert *when* output arrived, not just that it eventually did."""

    def __init__(self, t0: float) -> None:
        self._t0 = t0
        self.events: list[tuple[float, str]] = []

    def write(self, text: str) -> int:
        self.events.append((time.monotonic() - self._t0, text))
        return len(text)

    def flush(self) -> None:
        pass

    @property
    def text(self) -> str:
        return "".join(text for _, text in self.events)


def test_run_streamed_forwards_stderr_without_waiting_for_a_line_terminator():
    """The AC is "child stderr reaches the sink as produced, not buffered to
    completion" -- but the reader iterated `proc.stderr` line by line, so it
    blocked until the child emitted a `\\n` (review pass, 2026-08-10, third).
    A child that writes a status line *without* a terminator and then works
    silently -- a spinner, a progress bar, `Building... ` before a long
    compile -- delivered nothing at all for the whole pause. Reproduced
    against the pre-fix reader: 200 bytes written at t=0 first reached the
    sink at t=3.01s, together with the terminator that finally released them.

    Every other streaming test in this file uses `print(..., file=sys.stderr)`,
    which always terminates its line -- which is exactly why this path was
    invisible to the suite.
    """
    child_sleep = 3.0
    script = (
        "import sys, time\n"
        "sys.stderr.write('working-no-terminator')\n"
        "sys.stderr.flush()\n"
        f"time.sleep({child_sleep})\n"
        "sys.stderr.write('\\ndone\\n')\n"
    )
    started_at = time.monotonic()
    sink = _TimestampingSink(started_at)

    rc, _ = run_streamed([sys.executable, "-c", script], timeout=30.0, stderr_sink=sink)

    assert rc == 0
    arrivals = [at for at, text in sink.events if "working-no-terminator" in text]
    assert arrivals, "the unterminated status text never reached the sink at all"
    # Deliberately strict: the pre-fix reader delivered this at ~child_sleep.
    # A correct reader delivers it within milliseconds of the child's write.
    assert arrivals[0] < child_sleep / 2, (
        f"unterminated stderr was buffered for {arrivals[0]:.2f}s of a "
        f"{child_sleep}s pause -- it must stream as produced"
    )


def test_run_streamed_preserves_carriage_returns_in_child_stderr():
    """Text-mode universal-newline translation rewrote every `\\r` the child
    emitted into `\\n` (review pass, 2026-08-10, third), turning a build
    tool's single in-place progress line into one scrolling line per update.
    The child's bytes must reach the sink unrewritten."""
    script = (
        "import sys\n"
        "sys.stderr.write('progress 0%\\rprogress 50%\\rprogress 100%\\n')\n"
        "sys.stderr.flush()\n"
    )
    sink = _TimestampingSink(time.monotonic())

    rc, _ = run_streamed([sys.executable, "-c", script], timeout=15.0, stderr_sink=sink)

    assert rc == 0
    assert sink.text == "progress 0%\rprogress 50%\rprogress 100%\n"


def test_run_streamed_decodes_utf8_regardless_of_the_ambient_locale(tmp_path):
    """`Popen` inherited the locale's encoding, so under `LC_ALL=C` -- routine
    in CI containers and `docker run` without `LANG` -- every non-ASCII byte
    of an otherwise valid UTF-8 document came back as replacement characters
    (review pass, 2026-08-10, third). The corruption is silent: the mangled
    text is still valid JSON, so Story 2.1's AD-4 extraction would return a
    quietly wrong answer rather than an error. The encoding is now pinned.

    The locale that matters is the *caller's*, not the child's, so this test
    calls `run_streamed` from a grandparent interpreter launched under
    `LC_ALL=C` rather than setting the child's `env=` -- the latter proves
    nothing, since the decode happens on this side of the pipe. Both scripts
    are written as pure ASCII: CPython cannot even decode a `-c`/source file
    containing non-ASCII text under that locale.
    """
    child = tmp_path / "utf8_child.py"
    child.write_text(
        "import sys\n"
        "sys.stdout.buffer.write(b'{\"n\": \"caf\\xc3\\xa9-na\\xc3\\xafve\"}\\n')\n",
        encoding="ascii",
    )
    host = tmp_path / "utf8_host.py"
    host.write_text(
        "import json, sys\n"
        "from pyforge.mason.cfe import run_streamed\n"
        "rc, out = run_streamed([sys.executable, sys.argv[1]], timeout=30.0)\n"
        # ensure_ascii=True (the default) keeps this report readable back
        # here no matter how badly the grandparent's own stdout is encoded.
        "sys.stdout.write(json.dumps({'rc': rc, 'out': out}))\n",
        encoding="ascii",
    )
    c_locale_env = {
        **os.environ,
        "LC_ALL": "C", "LANG": "C", "LC_CTYPE": "C",
        "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0",
        "PYTHONPATH": os.pathsep.join(p for p in sys.path if p),
    }
    c_locale_env.pop("PYTHONIOENCODING", None)

    completed = subprocess.run(
        [sys.executable, str(host), str(child)],
        env=c_locale_env, capture_output=True, text=True, timeout=60, check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["rc"] == 0
    assert "�" not in report["out"], (
        f"stdout was mangled by the caller's locale: {report['out']!r}"
    )
    assert json.loads(report["out"]) == {"n": "café-naïve"}


def test_run_streamed_keeps_forwarding_after_a_transient_blocking_io_error():
    """A one-off `BlockingIOError` means the sink is *busy*, not gone -- what
    a non-blocking `sys.stderr` under tmux or some CI runners raises when the
    downstream pipe is momentarily full, and it accepts the very next write.
    Latching the sink dead on it silently discarded every remaining line
    (review pass, 2026-08-10, third): reproduced at 1 write attempt and 0 of
    5 lines delivered. The adjacent `flush` handler already reasoned this way
    about the identical exception.

    A genuinely broken sink still latches, via its failing *write* -- pinned
    by `test_run_streamed_broken_stderr_sink_does_not_deadlock_a_noisy_child`.
    """

    class _FirstWriteIsBusySink:
        def __init__(self) -> None:
            self.attempts = 0
            self.chunks: list[str] = []

        def write(self, text: str) -> int:
            self.attempts += 1
            if self.attempts == 1:
                raise BlockingIOError(11, "Resource temporarily unavailable")
            self.chunks.append(text)
            return len(text)

        def flush(self) -> None:
            pass

    # One line per write attempt: the child flushes and pauses between lines
    # so each arrives as its own read, making the dropped-vs-delivered count
    # deterministic rather than dependent on chunk coalescing.
    script = (
        "import sys, time\n"
        "for i in range(5):\n"
        "    sys.stderr.write('line-%d\\n' % i)\n"
        "    sys.stderr.flush()\n"
        "    time.sleep(0.05)\n"
    )
    sink = _FirstWriteIsBusySink()

    rc, _ = run_streamed([sys.executable, "-c", script], timeout=15.0, stderr_sink=sink)

    assert rc == 0
    assert sink.attempts > 1, "the sink was latched dead by a transient error"
    delivered = "".join(sink.chunks)
    # The busy chunk is genuinely lost (retrying would block or spin); every
    # line after it must survive.
    assert "line-4" in delivered
    assert delivered.count("line-") >= 4


def test_run_streamed_rejects_a_none_argv():
    """`list(None)` reported a bare "'NoneType' object is not iterable",
    naming neither the function nor the parameter (review pass, 2026-08-10,
    third) -- the same defect `timeout=None` was already guarded against."""
    with pytest.raises(TypeError, match=r"run_streamed\(argv=\.\.\.\)"):
        run_streamed(None, timeout=15.0)


@pytest.mark.parametrize("bad_sink", [object(), 42, None])
def test_run_streamed_rejects_a_sink_without_a_callable_write(bad_sink, monkeypatch):
    """A sink with no `write` -- or a `sys.stderr` that is `None`, which a
    `pythonw`/detached host hands us -- was silently swallowed by the
    forwarding thread's degrade-don't-crash handling: every line the child
    produced vanished, indistinguishable to the caller from a quiet child
    (review pass, 2026-08-10, third). `flush` stays optional.

    `None` is passed via `sys.stderr` rather than the parameter, since
    `stderr_sink=None` means "use the default" by design.
    """
    if bad_sink is None:
        monkeypatch.setattr(sys, "stderr", None)
        kwargs = {}
    else:
        kwargs = {"stderr_sink": bad_sink}

    with pytest.raises(TypeError, match=r"run_streamed\(stderr_sink=\.\.\.\)"):
        run_streamed([sys.executable, "-c", "pass"], timeout=15.0, **kwargs)


def test_run_streamed_rejects_a_bad_sink_before_spawning_a_child(monkeypatch):
    """The sink guard runs ahead of `Popen`, so a caller's mistake costs no
    process -- and cannot leave one behind."""
    spawned: list[object] = []
    real_popen = subprocess.Popen

    def _recording_popen(*args, **kwargs):
        spawned.append(args)
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(cfe_module.subprocess, "Popen", _recording_popen)

    with pytest.raises(TypeError):
        run_streamed([sys.executable, "-c", "pass"], timeout=15.0, stderr_sink=object())

    assert spawned == []


# --- Story 2.1: _extract_json -----------------------------------------------

def test_extract_json_parses_whole_stdout_when_it_is_valid_json():
    assert _extract_json('{"ok": true}') == {"ok": True}


def test_extract_json_finds_json_after_a_leading_progress_line():
    stdout = "Syncing fork with upstream conda-forge/staged-recipes ...\n{\"ok\": true}\n"
    assert _extract_json(stdout) == {"ok": True}


def test_extract_json_finds_an_indented_json_line_too():
    stdout = "progress\n    {\"ok\": true}\n"
    assert _extract_json(stdout) == {"ok": True}


def test_extract_json_finds_a_json_array_after_a_progress_line():
    stdout = "progress\n[1, 2, 3]\n"
    assert _extract_json(stdout) == [1, 2, 3]


def test_extract_json_returns_none_for_plain_text_with_no_json_anywhere():
    assert _extract_json("just some plain text, nothing structured here\n") is None


def test_extract_json_returns_none_when_a_line_start_match_is_still_not_valid_json():
    # A line starts with '{' but its content never parses as JSON.
    assert _extract_json("noise\n{not: valid, json\n") is None


def test_extract_json_returns_none_for_empty_stdout():
    assert _extract_json("") is None


# --- Story 2.1: _CFE_SCRIPTS table -------------------------------------------

def test_cfe_scripts_table_has_exactly_the_two_story_1_9_fixture_entries():
    """Spec Never boundary: no entry beyond `validate_recipe`/`submit_pr` --
    Story 1.9's fixture only stubs these two, and which script backs each of
    Stories 2.4-2.10 is still open."""
    assert _CFE_SCRIPTS == {
        "validate_recipe": "validate_recipe.py",
        "submit_pr": "submit_pr.py",
    }


# --- Story 2.1: _invoke_captured -- mocked I/O-matrix coverage --------------

def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_invoke_captured_returns_parsed_json_body_on_whole_stdout_json():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        return_value=_completed(returncode=0, stdout='{"passed": true}', stderr=""),
    ):
        result = _invoke_captured(
            "validate_recipe", [], root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
        )

    assert result == CfeResult(
        returncode=0, stdout='{"passed": true}', stderr="", json_body={"passed": True},
    )


def test_invoke_captured_extracts_json_after_a_leading_progress_line():
    stdout = "Syncing fork with upstream conda-forge/staged-recipes ...\n{\"success\": true}\n"
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        return_value=_completed(returncode=0, stdout=stdout, stderr=""),
    ):
        result = _invoke_captured(
            "submit_pr", [], root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
        )

    assert result.json_body == {"success": True}


def test_invoke_captured_reports_json_body_none_for_plain_text_stdout():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        return_value=_completed(returncode=0, stdout="not json at all", stderr=""),
    ):
        result = _invoke_captured(
            "validate_recipe", [], root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
        )

    assert result.json_body is None
    assert result.returncode == 0
    assert result.stdout == "not json at all"


def test_invoke_captured_non_zero_returncode_with_json_body_is_data_not_raised():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        return_value=_completed(
            returncode=1, stdout='{"error": "bad recipe"}', stderr="traceback...",
        ),
    ):
        result = _invoke_captured(
            "validate_recipe", [], root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
        )

    assert result.returncode == 1
    assert result.json_body == {"error": "bad recipe"}
    assert result.stderr == "traceback..."


def test_invoke_captured_timeout_expired_raises_cfe_timeout_error_naming_script_and_timeout():
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["python", "validate_recipe.py"], timeout=5.0),
    ):
        with pytest.raises(CfeTimeoutError) as excinfo:
            _invoke_captured(
                "validate_recipe", [], root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
            )

    assert excinfo.value.script == "validate_recipe"
    assert excinfo.value.timeout == 5.0


def test_invoke_captured_timeout_leaves_no_orphaned_process_per_subprocess_runs_own_contract():
    """`subprocess.run`'s own `timeout=` handling kills and reaps the child
    before raising `TimeoutExpired` -- `_invoke_captured` adds no cleanup of
    its own (spec Always boundary), so this asserts only that the
    translation happens without swallowing or re-wrapping any other
    exception type."""
    with patch(
        "pyforge.mason.cfe.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["python"], timeout=5.0),
    ):
        with pytest.raises(CfeTimeoutError):
            _invoke_captured(
                "submit_pr", [], root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
            )


# --- Story 2.1: _invoke_captured -- invocation shape ------------------------

def test_invoke_captured_runs_interpreter_script_path_then_args_as_list_argv():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_completed(stdout="{}"),
    ) as mock_run:
        _invoke_captured(
            "validate_recipe", ["--json", "recipes/foo"],
            root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
        )

    args, kwargs = mock_run.call_args
    argv = args[0]
    expected_script = str(
        Path("/fake/root") / ".claude" / "scripts" / "conda-forge-expert" / "validate_recipe.py"
    )
    assert argv == ["/fake/python", expected_script, "--json", "recipes/foo"]
    assert kwargs.get("shell", False) is False
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["timeout"] == 5.0
    assert kwargs.get("check") is False
    assert kwargs.get("capture_output") is True
    # Review pass (2026-08-11): pins the spec's Never-boundary claim that
    # credential isolation (Story 2.3) is already satisfied today because
    # `env` is never passed -- `subprocess.run`'s own default (`env=None`)
    # inherits the parent process environment unmodified. A future edit
    # that "helpfully" adds an explicit `env=os.environ.copy()` would
    # otherwise pass every other assertion in this test unnoticed.
    assert "env" not in kwargs or kwargs["env"] is None


@pytest.mark.parametrize("bad_timeout", [float("nan"), float("inf"), float("-inf"), 0.0, -5.0])
def test_invoke_captured_rejects_a_non_finite_or_non_positive_timeout(bad_timeout):
    with pytest.raises(ValueError, match="finite, positive"):
        _invoke_captured(
            "validate_recipe", [],
            root=Path("/fake/root"), interpreter="/fake/python", timeout=bad_timeout,
        )


@pytest.mark.parametrize("bad_timeout", [None, "120", object(), True])
def test_invoke_captured_rejects_a_non_numeric_timeout(bad_timeout):
    with pytest.raises(TypeError, match=r"_invoke_captured\(timeout=\.\.\.\)"):
        _invoke_captured(
            "validate_recipe", [],
            root=Path("/fake/root"), interpreter="/fake/python", timeout=bad_timeout,
        )


@pytest.mark.parametrize("bad_args", [None, "--json recipes/foo", b"--json"])
def test_invoke_captured_rejects_a_bare_str_bytes_or_none_args(bad_args):
    # Review pass (2026-08-11): mirrors run_streamed's own established
    # argv guard -- a bare str/bytes handed to `*args` below would explode
    # into one-character argv elements instead of raising a clear error.
    with pytest.raises(TypeError, match=r"_invoke_captured\(args=\.\.\.\)"):
        _invoke_captured(
            "validate_recipe", bad_args,
            root=Path("/fake/root"), interpreter="/fake/python", timeout=5.0,
        )


# --- Story 2.1: validate_recipe / submit_pr -- per-operation default timeouts

def test_validate_recipe_defaults_to_a_120_second_timeout():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_completed(stdout="{}"),
    ) as mock_run:
        validate_recipe([], root=Path("/fake/root"), interpreter="/fake/python")

    assert mock_run.call_args.kwargs["timeout"] == 120.0


def test_submit_pr_defaults_to_a_300_second_timeout():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_completed(stdout="{}"),
    ) as mock_run:
        submit_pr([], root=Path("/fake/root"), interpreter="/fake/python")

    assert mock_run.call_args.kwargs["timeout"] == 300.0


def test_validate_recipe_honors_an_explicit_timeout_override():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_completed(stdout="{}"),
    ) as mock_run:
        validate_recipe([], root=Path("/fake/root"), interpreter="/fake/python", timeout=7.5)

    assert mock_run.call_args.kwargs["timeout"] == 7.5


def test_submit_pr_honors_an_explicit_timeout_override():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_completed(stdout="{}"),
    ) as mock_run:
        submit_pr([], root=Path("/fake/root"), interpreter="/fake/python", timeout=1.5)

    assert mock_run.call_args.kwargs["timeout"] == 1.5


def test_validate_recipe_invokes_its_own_table_entry_not_submit_prs():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_completed(stdout="{}"),
    ) as mock_run:
        validate_recipe([], root=Path("/fake/root"), interpreter="/fake/python")

    argv = mock_run.call_args.args[0]
    assert argv[1].endswith("validate_recipe.py")


def test_submit_pr_invokes_its_own_table_entry_not_validate_recipes():
    with patch(
        "pyforge.mason.cfe.subprocess.run", return_value=_completed(stdout="{}"),
    ) as mock_run:
        submit_pr([], root=Path("/fake/root"), interpreter="/fake/python")

    argv = mock_run.call_args.args[0]
    assert argv[1].endswith("submit_pr.py")


# --- Story 2.1: real end-to-end against Story 1.9's fake_cfe_root fixture --
# --- (no mocking -- mirrors test_fake_cfe_root_fixture.py's own style) -----

_FIXTURE_ENV_VARS = ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE")


def _clear_fixture_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_invoke_captured` passes no `env=` to `subprocess.run` (it inherits
    the ambient process environment unmodified -- spec Never boundary), so a
    stray `MASON_FIXTURE_*` variable already set in the runner's own shell
    could otherwise silently override one of these tests' expectations."""
    for var in _FIXTURE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_validate_recipe_against_fake_cfe_root_matches_the_fixtures_canned_json(
    fake_cfe_root, monkeypatch,
):
    _clear_fixture_env(monkeypatch)

    result = validate_recipe([], root=fake_cfe_root, interpreter=sys.executable, timeout=15.0)

    assert result.returncode == 0
    assert result.json_body == {
        "passed": True, "errors": [], "warnings": [], "info": [], "rattler_lint_ran": True,
    }


def test_submit_pr_against_fake_cfe_root_matches_the_fixtures_canned_json(
    fake_cfe_root, monkeypatch,
):
    _clear_fixture_env(monkeypatch)

    result = submit_pr([], root=fake_cfe_root, interpreter=sys.executable, timeout=15.0)

    assert result.returncode == 0
    assert result.json_body == {
        "success": True,
        "recipe": "example-recipe",
        "branch": "add-example-recipe",
        "github_user": "example-user",
        "pr_url": "https://github.com/example/example/pull/1",
        "message": "PR created: https://github.com/example/example/pull/1",
    }


def test_submit_pr_against_fake_cfe_root_tolerates_a_leading_progress_line(
    fake_cfe_root, monkeypatch,
):
    _clear_fixture_env(monkeypatch)
    monkeypatch.setenv(
        "MASON_FIXTURE_PROGRESS_LINE", "Syncing fork with upstream conda-forge/staged-recipes ...",
    )

    result = submit_pr([], root=fake_cfe_root, interpreter=sys.executable, timeout=15.0)

    assert result.returncode == 0
    assert result.json_body == {
        "success": True,
        "recipe": "example-recipe",
        "branch": "add-example-recipe",
        "github_user": "example-user",
        "pr_url": "https://github.com/example/example/pull/1",
        "message": "PR created: https://github.com/example/example/pull/1",
    }


def test_validate_recipe_against_fake_cfe_root_with_nonzero_exit_returns_data_not_raise(
    fake_cfe_root, monkeypatch,
):
    _clear_fixture_env(monkeypatch)
    monkeypatch.setenv("MASON_FIXTURE_EXIT_CODE", "1")

    result = validate_recipe([], root=fake_cfe_root, interpreter=sys.executable, timeout=15.0)

    assert result.returncode == 1
    assert result.json_body == {
        "passed": True, "errors": [], "warnings": [], "info": [], "rattler_lint_ran": True,
    }


def test_validate_recipe_against_fake_cfe_root_with_plain_text_stdout_reports_json_body_none(
    fake_cfe_root, monkeypatch,
):
    _clear_fixture_env(monkeypatch)
    monkeypatch.setenv("MASON_FIXTURE_STDOUT", "plain text, not json")

    result = validate_recipe([], root=fake_cfe_root, interpreter=sys.executable, timeout=15.0)

    assert result.returncode == 0
    assert result.json_body is None
    assert "plain text, not json" in result.stdout
