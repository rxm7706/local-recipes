"""Unit tests for ``pyforge.marshal.adapters.process_posix`` (Story 2.1,
AD-4/AD-11) -- ``PosixProcess`` against REAL, trivial, fast subprocesses,
matching this package's own "real I/O against tmp_path, not heavy mocking"
convention (see ``test_vcs_git.py``'s identical approach for ``GitVcs``).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyforge.marshal.adapters.process_posix import PosixProcess, ProcessError
from pyforge.marshal.ports.process import ProcessResult


@pytest.fixture
def process() -> PosixProcess:
    return PosixProcess()


# --- a passing command ---------------------------------------------------------


def test_run_returns_process_result_for_a_passing_command(process, tmp_path):
    result = process.run([sys.executable, "-c", "print('hi')"], cwd=tmp_path)
    assert isinstance(result, ProcessResult)
    assert result.returncode == 0
    assert result.stdout == "hi\n"
    assert result.stderr == ""


# --- a failing command: never raises, reports the real exit code -------------


def test_run_reports_a_nonzero_exit_without_raising(process, tmp_path):
    result = process.run(
        [sys.executable, "-c", "import sys; sys.exit(3)"], cwd=tmp_path
    )
    assert result.returncode == 3


def test_run_captures_stderr(process, tmp_path):
    result = process.run(
        [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n')"], cwd=tmp_path
    )
    assert result.stderr == "boom\n"
    assert result.returncode == 0


# --- cwd is honored --------------------------------------------------------------


def test_run_uses_the_given_cwd(process, tmp_path):
    (tmp_path / "marker.txt").write_text("here\n", encoding="utf-8")
    result = process.run(
        [
            sys.executable,
            "-c",
            "import pathlib; print(pathlib.Path('marker.txt').read_text().strip())",
        ],
        cwd=tmp_path,
    )
    assert result.stdout.strip() == "here"


# --- a missing executable: raises ProcessError, never a raw exception -------


def test_run_raises_process_error_for_a_missing_executable(process, tmp_path):
    with pytest.raises(ProcessError):
        process.run(["definitely-not-a-real-binary-xyz"], cwd=tmp_path)


def test_run_raises_process_error_for_empty_argv(process, tmp_path):
    """A whitespace-only verify command shlex.split()s to an empty list --
    there is no argv[0] to exec. Guarded so this Protocol's "raises
    ProcessError only" contract holds for every caller, not just the one
    cli/gate.py already protects against by catching shlex.split's own
    ValueError first."""
    with pytest.raises(ProcessError):
        process.run([], cwd=tmp_path)


# --- a timeout: raises ProcessError, never a raw TimeoutExpired -------------


def test_run_raises_process_error_on_timeout(process, tmp_path):
    with pytest.raises(ProcessError, match="timed out"):
        process.run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            cwd=tmp_path,
            timeout_s=0.2,
        )


def test_run_has_no_timeout_by_default(process, tmp_path):
    """No default timeout_s (unlike vcs_git.py's two fixed tiers): a verify
    command's own duration is entirely project-defined."""
    result = process.run([sys.executable, "-c", "pass"], cwd=tmp_path)
    assert result.returncode == 0


# --- undecodable output degrades instead of raising -------------------------


def test_run_replaces_undecodable_output(process, tmp_path):
    result = process.run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xff')"],
        cwd=tmp_path,
    )
    assert result.stdout == "�"


# --- launch-failure translation (mirrors vcs_git.py's own _run coverage) ----


def test_run_wraps_missing_executable_launch_failure(process, tmp_path, monkeypatch):
    import pyforge.marshal.adapters.process_posix as process_posix_module

    def _raise_not_found(*args, **kwargs):
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(process_posix_module.subprocess, "run", _raise_not_found)
    with pytest.raises(ProcessError, match="not found"):
        process.run(["whatever"], cwd=tmp_path)


def test_run_wraps_a_generic_launch_oserror(process, tmp_path, monkeypatch):
    import pyforge.marshal.adapters.process_posix as process_posix_module

    def _raise_eacces(*args, **kwargs):
        raise PermissionError("exec format error")

    monkeypatch.setattr(process_posix_module.subprocess, "run", _raise_eacces)
    with pytest.raises(ProcessError, match="cannot launch"):
        process.run(["whatever"], cwd=tmp_path)


def test_run_wraps_a_hung_process(process, tmp_path, monkeypatch):
    import pyforge.marshal.adapters.process_posix as process_posix_module

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["whatever"], timeout=1.0)

    monkeypatch.setattr(process_posix_module.subprocess, "run", _raise_timeout)
    with pytest.raises(ProcessError, match="timed out"):
        process.run(["whatever"], cwd=tmp_path)


# --- an embedded NUL byte: raises ProcessError, never a raw ValueError ------


def test_run_wraps_an_embedded_null_byte(process, tmp_path):
    """Review finding: subprocess.run raises a plain ValueError (not an
    OSError) for a NUL byte in argv -- e.g. a TOML `\\u0000` escape survives
    shlex.split as an ordinary character. Uncaught, this violated `run`'s
    own "raises ProcessError only" contract and escaped `marshal gate
    evaluate` as a raw traceback outside its guaranteed exit-code domain."""
    with pytest.raises(ProcessError, match="cannot launch"):
        process.run([sys.executable, "-c", "print('hi\x00there')"], cwd=tmp_path)


# --- stdin is redirected, never inherited -----------------------------------


def test_run_does_not_block_on_stdin(process, tmp_path):
    """Review finding: an unattended `gate evaluate` invocation has no
    terminal to answer a prompt -- a verify command that unexpectedly reads
    stdin must see EOF immediately (DEVNULL), never hang waiting on input
    that can never arrive."""
    result = process.run(
        [sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"],
        cwd=tmp_path,
        timeout_s=5.0,
    )
    assert result.stdout.strip() == "''"


# --- argv is never shell-interpreted (AD-17's allowlist-only guarantee) ----


def test_run_never_interprets_shell_metacharacters(process, tmp_path):
    """Review finding: this adapter's entire security posture rests on
    `subprocess.run` never being called with `shell=True` -- true today by
    construction, but nothing previously exercised a shell-metacharacter-
    bearing argument to prove it stays inert. A command containing `;`/`&&`/
    a backtick must be passed to the target program as ONE literal
    argument, never split or re-interpreted by a shell."""
    marker = tmp_path / "should-not-exist"
    payload = f"; touch {marker} #"
    result = process.run(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", payload],
        cwd=tmp_path,
    )
    assert result.stdout.strip() == payload
    assert not marker.exists()
