"""Story 1.6 -- the CFE import-floor probe: full/partial floor, caching,
the `OSError`/`TimeoutExpired` fold-into-missing path, and
`ensure_import_floor`'s raise/no-raise paths. `subprocess.run` is mocked
throughout (AD-16: no test in this suite requires a real interpreter to
probe).

Story 1.7 extends this file with `ensure_cfe_root`'s raise/no-raise paths
over every `resolve.py` step."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import pytest

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
    line, then emits a JSON stdout line. A custom sink sets a
    `threading.Event` the instant it sees the first line; `run_streamed`
    itself runs in a background thread so the test can assert the event
    fires *before* the child has had time to also emit its second line or
    exit -- proving genuine incremental delivery, not just correct final
    content (capsys can't observe this: it only offers the post-hoc
    aggregate, never an as-it-happens callback)."""
    script = (
        "import sys, time, json\n"
        "print('first-line', file=sys.stderr, flush=True)\n"
        "time.sleep(1.0)\n"
        "print('second-line', file=sys.stderr, flush=True)\n"
        "print(json.dumps({'ok': True}))\n"
    )

    class _EventSink:
        def __init__(self) -> None:
            self.first_line_seen = threading.Event()
            self.lines: list[str] = []

        def write(self, s: str) -> None:
            self.lines.append(s)
            if "first-line" in s:
                self.first_line_seen.set()

        def flush(self) -> None:
            pass

    sink = _EventSink()
    result: dict = {}

    def _run() -> None:
        rc, out = run_streamed([sys.executable, "-c", script], timeout=15.0, stderr_sink=sink)
        result["rc"] = rc
        result["out"] = out

    thread = threading.Thread(target=_run)
    thread.start()

    assert sink.first_line_seen.wait(timeout=10.0), "first stderr line never reached the sink"
    # The child's own time.sleep(1.0) hasn't elapsed yet -- if this were
    # buffered to completion, the second line would already be present too.
    assert not any("second-line" in line for line in sink.lines)

    thread.join(timeout=15.0)
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

    assert elapsed < 10.0


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
