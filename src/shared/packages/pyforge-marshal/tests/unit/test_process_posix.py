"""Unit tests for ``pyforge.marshal.adapters.process_posix`` (Story 2.1,
AD-4/AD-11) -- ``PosixProcess`` against REAL, trivial, fast subprocesses,
matching this package's own "real I/O against tmp_path, not heavy mocking"
convention (see ``test_vcs_git.py``'s identical approach for ``GitVcs``).

Story 3.4 adds ``is_alive``/``spawn_detached`` coverage, same convention:
real, trivial child processes (this test's own interpreter's pid for
``is_alive``; a real detached ``sys.executable`` child for
``spawn_detached``) rather than mocking ``os.kill``/``subprocess.Popen``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

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


# --- is_alive (Story 3.4): never raises, existence-only ------------------------


def test_is_alive_true_for_this_process_itself(process):
    assert process.is_alive(os.getpid()) is True


def test_is_alive_false_for_a_reaped_process(process, tmp_path):
    """A child that has exited AND been reaped (``wait()``) no longer has a
    process-table entry -- the clearest "gone" case ``os.kill(pid, 0)`` can
    report.

    Follow-up review finding: this docstring used to claim the case was
    reachable "without depending on PID reuse timing". It is not --
    ``wait()`` frees the pid, so on a busy host the kernel may hand it to an
    unrelated process before the assertion runs, and ``is_alive`` would then
    correctly answer ``True``. The window is very small (nothing else here
    forks), so this stays as the practical "gone" characterization it always
    was; the docstring no longer asserts an immunity it does not have."""
    child = subprocess.Popen([sys.executable, "-c", "pass"], cwd=tmp_path)
    child.wait()
    assert process.is_alive(child.pid) is False


def test_is_alive_true_when_permission_denied(process, monkeypatch):
    """Review-anticipated case (this port's own docstring): a process that
    EXISTS but this invocation lacks permission to signal (``EPERM``) still
    answers ``True`` -- existence, not ownership, is the question. Exercised
    via monkeypatch since provoking a real ``EPERM`` needs a process owned
    by a different user, not reliably available in a test environment."""
    import pyforge.marshal.adapters.process_posix as process_posix_module

    def _raise_eperm(pid, sig):
        raise PermissionError("Operation not permitted")

    monkeypatch.setattr(process_posix_module.os, "kill", _raise_eperm)
    assert process.is_alive(1) is True


def test_is_alive_false_for_a_pid_outside_c_int_range(process):
    """Follow-up review finding (both reviewers): ``os.kill`` raises a bare
    ``OverflowError`` -- NOT an ``OSError`` -- for a pid larger than C
    ``int``, so it escaped every clause here and broke this method's
    "NEVER raises" contract. It was reachable in production:
    ``supervisor/__main__.py::main`` guards only a NON-POSITIVE pid, so a
    malformed invocation carrying an absurd pid crashed the sidecar with a
    raw traceback AFTER its ``supervisor-attach`` entry was journaled --
    leaving a dangling attach with no detach, the exact silent supervisor
    death AD-9 forbids."""
    assert process.is_alive(2**31) is False
    assert process.is_alive(2**70) is False


def test_is_alive_false_on_an_unexpected_oserror(process, monkeypatch):
    """Defense in depth (this method's own "never raises" contract): any
    OTHER ``OSError`` degrades to the conservative ``False`` rather than
    escaping raw -- there is no exception slot in this method's contract for
    a caller to catch."""
    import pyforge.marshal.adapters.process_posix as process_posix_module

    def _raise_other(pid, sig):
        raise OSError("some unexpected failure")

    monkeypatch.setattr(process_posix_module.os, "kill", _raise_other)
    assert process.is_alive(1) is False


# --- spawn_detached (Story 3.4): detached launch + log redirection -----------


def test_spawn_detached_launches_and_redirects_both_streams_to_the_log(
    process, tmp_path
):
    log_path = tmp_path / "spawned.log"
    marker = tmp_path / "marker.txt"
    script = (
        "import sys, pathlib\n"
        "print('stdout line')\n"
        "print('stderr line', file=sys.stderr)\n"
        f"pathlib.Path({str(marker)!r}).write_text('done', encoding='utf-8')\n"
    )
    pid = process.spawn_detached(
        [sys.executable, "-c", script], cwd=tmp_path, log_path=log_path
    )
    assert isinstance(pid, int) and pid > 0

    deadline = time.monotonic() + 5.0
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert marker.exists(), "the detached child never ran to completion"

    log_text = log_path.read_text(encoding="utf-8")
    assert "stdout line" in log_text
    assert "stderr line" in log_text


def test_spawn_detached_child_does_not_import_from_its_cwd(process, tmp_path):
    """Follow-up review finding, reproduced live: ``cwd`` sets the child's
    working directory, but WITHOUT ``PYTHONSAFEPATH`` it also lands on the
    child's ``sys.path[0]`` -- and every caller hands this method a ``cwd``
    whose contents it does not own (``cli/spin.py`` passes the loop home, an
    arbitrary project checkout). A stdlib-shadowing module there therefore
    chose what the detached child ran, while the parent had already been
    handed a pid and reported success.

    Asserts the EFFECT, not just the kwarg: a hostile ``json.py`` sits in
    the child's own cwd and must not be what it imports."""
    (tmp_path / "json.py").write_text(
        "raise SystemExit('shadowed stdlib json was imported')\n", encoding="utf-8"
    )
    marker = tmp_path / "imported-from.txt"
    script = (
        "import json, pathlib\n"
        f"pathlib.Path({str(marker)!r}).write_text(json.__file__, encoding='utf-8')\n"
    )
    log_path = tmp_path / "shadow.log"

    process.spawn_detached([sys.executable, "-c", script], cwd=tmp_path, log_path=log_path)

    deadline = time.monotonic() + 5.0
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert marker.exists(), (
        "the detached child never completed -- it most likely imported the "
        f"shadowing json.py in its cwd; log: {log_path.read_text(encoding='utf-8')}"
    )
    assert str(tmp_path) not in marker.read_text(encoding="utf-8")


def test_spawn_detached_raises_process_error_for_a_missing_executable(
    process, tmp_path
):
    with pytest.raises(ProcessError):
        process.spawn_detached(
            ["definitely-not-a-real-binary-xyz"],
            cwd=tmp_path,
            log_path=tmp_path / "spawned.log",
        )


def test_spawn_detached_raises_process_error_for_empty_argv(process, tmp_path):
    with pytest.raises(ProcessError):
        process.spawn_detached([], cwd=tmp_path, log_path=tmp_path / "spawned.log")


def test_spawn_detached_raises_process_error_when_the_log_cannot_be_opened(
    process, tmp_path
):
    log_path = tmp_path / "nonexistent-dir" / "spawned.log"
    with pytest.raises(ProcessError, match="cannot open log"):
        process.spawn_detached(
            [sys.executable, "-c", "pass"], cwd=tmp_path, log_path=log_path
        )


def test_spawn_detached_quotes_the_log_path_in_its_error_message(process, tmp_path):
    """Review finding: this message is interpolated verbatim into
    ``MRS-SPIN-007``'s own message, which ``cli/spin.py::_render_text``
    prints UNQUOTED by design -- so a raw path here reopens the
    report-forgery hole that finding's own ``{str(supervisor_log)!r}``
    closes. Every other message in this module already reprs its
    interpolated value (``{list(argv)!r}``, ``{argv[0]!r}``)."""
    log_path = tmp_path / "no-such-dir" / "a\nfindings:\n  FORGED.log"
    with pytest.raises(ProcessError) as excinfo:
        process.spawn_detached(
            [sys.executable, "-c", "pass"], cwd=tmp_path, log_path=log_path
        )
    assert "\n" not in str(excinfo.value)


def test_spawn_detached_wraps_an_embedded_null_byte(process, tmp_path):
    """Mirrors ``run``'s own identical NUL-byte coverage: ``subprocess.Popen``
    raises a plain ``ValueError`` (not an ``OSError``) for a NUL byte in
    argv -- this method's own "raises ProcessError only" contract must hold
    for this launch path too."""
    with pytest.raises(ProcessError, match="cannot launch"):
        process.spawn_detached(
            [sys.executable, "-c", "print('hi\x00there')"],
            cwd=tmp_path,
            log_path=tmp_path / "spawned.log",
        )


def test_spawn_detached_wraps_an_embedded_null_byte_in_the_log_path(process, tmp_path):
    """Follow-up review finding: the ``open(log_path, "wb")`` that precedes
    the ``Popen`` had only an ``OSError`` clause, but ``open()`` raises a
    plain ``ValueError`` for a path carrying an embedded NUL -- the SAME
    CPython split already guarded at the sibling ``Popen`` call above, at
    ``run``'s own call, and in both ``observer_mux`` methods. Left uncaught
    it escaped this port's "raises ProcessError only" contract straight
    through ``cli/spin.py``'s own ``except ProcessError``, at the one point
    where a live harness process already exists."""
    with pytest.raises(ProcessError, match="cannot open log"):
        process.spawn_detached(
            [sys.executable, "-c", "pass"],
            cwd=tmp_path,
            log_path=tmp_path / "spawned\x00.log",
        )


class _FakeSpawnedProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_spawn_detached_calls_popen_with_the_detach_recipe(process, tmp_path, monkeypatch):
    """Mirrors ``adapters/harness_bmadloop.py::BmadLoopHarness.spin``'s own
    argv-shape assertions (``test_harness_bmadloop_spin.py``) -- proving
    THIS generic primitive uses the identical ``Popen`` kwargs rather than a
    second, divergent detach recipe."""
    import pyforge.marshal.adapters.process_posix as process_posix_module

    calls: list[tuple[list[str], dict]] = []

    def _fake_popen(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return _FakeSpawnedProcess(pid=9999)

    monkeypatch.setattr(process_posix_module.subprocess, "Popen", _fake_popen)
    log_path = tmp_path / "spawned.log"

    pid = process.spawn_detached(["some-command", "arg1"], cwd=tmp_path, log_path=log_path)

    assert pid == 9999
    [(argv, kwargs)] = calls
    assert argv == ["some-command", "arg1"]
    assert kwargs["cwd"] == tmp_path
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] == subprocess.DEVNULL
    # Both streams point at the SAME open log file handle.
    assert kwargs["stdout"] is kwargs["stderr"]
    assert Path(kwargs["stdout"].name) == log_path
    # PYTHONUNBUFFERED=1 (review finding): this method's own docstring says
    # it mirrors harness_bmadloop.py::spin's detach recipe "exactly", and
    # that method forces this env var specifically because a child's stdout
    # is fully block-buffered once redirected to a regular file -- omitting
    # it here would silently reintroduce that same bug for any future
    # caller of this now-generic primitive.
    assert kwargs["env"]["PYTHONUNBUFFERED"] == "1"
    # PYTHONSAFEPATH=1 (follow-up review finding, verified live): `python
    # -m <pkg>` puts `cwd` on `sys.path[0]`, and every caller of this method
    # hands it a `cwd` whose contents it does not own -- cli/spin.py passes
    # the LOOP HOME, an arbitrary project checkout. Without this, a
    # stdlib-shadowing module or a stray `pyforge/` directory at that root
    # decided what the detached child imported: it died at import with a raw
    # ModuleNotFoundError (or silently ran the wrong module) while the
    # parent had already been handed a pid and reported success.
    assert kwargs["env"]["PYTHONSAFEPATH"] == "1"
    # The child still inherits every OTHER ambient variable -- this is an
    # addition to os.environ, never a replacement of it.
    assert kwargs["env"]["PATH"] == os.environ["PATH"]


def test_spawn_detached_reports_a_generic_message_for_a_bad_cwd_or_missing_executable(
    process, tmp_path, monkeypatch
):
    """Review finding: ``Popen`` raises the identical ``FileNotFoundError``
    both when ``argv[0]`` cannot be resolved AND when ``cwd`` itself cannot
    be chdir'd into -- this method cannot tell the two apart from the
    exception alone, so its message must not overclaim "executable not
    found" for a failure that could just as well be a bad ``cwd``."""
    import pyforge.marshal.adapters.process_posix as process_posix_module

    def _raise_file_not_found(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(process_posix_module.subprocess, "Popen", _raise_file_not_found)
    with pytest.raises(ProcessError) as excinfo:
        process.spawn_detached(
            ["whatever"], cwd=tmp_path, log_path=tmp_path / "spawned.log"
        )
    assert "executable not found" not in str(excinfo.value)
    assert "cannot launch" in str(excinfo.value)


def test_spawn_detached_wraps_a_generic_launch_oserror(process, tmp_path, monkeypatch):
    import pyforge.marshal.adapters.process_posix as process_posix_module

    def _raise_eacces(*args, **kwargs):
        raise PermissionError("exec format error")

    monkeypatch.setattr(process_posix_module.subprocess, "Popen", _raise_eacces)
    with pytest.raises(ProcessError, match="cannot launch"):
        process.spawn_detached(
            ["whatever"], cwd=tmp_path, log_path=tmp_path / "spawned.log"
        )
