"""Story 1.6 -- the CFE import-floor probe: full/partial floor, caching,
the `OSError`/`TimeoutExpired` fold-into-missing path, and
`ensure_import_floor`'s raise/no-raise paths. `subprocess.run` is mocked
throughout (AD-16: no test in this suite requires a real interpreter to
probe).

Story 1.7 extends this file with `ensure_cfe_root`'s raise/no-raise paths
over every `resolve.py` step."""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import pytest

from pyforge.mason import cfe as cfe_module
from pyforge.mason.cfe import (
    CFE_IMPORT_FLOOR, ImportFloorResult, _build_probe_script,
    ensure_cfe_root, ensure_import_floor, probe_import_floor, run_streamed,
)
from pyforge.mason.errors import CfeImportFloorError, CfeUnresolvedError
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
