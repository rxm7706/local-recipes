"""pyforge.core.process -- the ONE sanctioned way to invoke a subprocess
(Story 14.4, SPEC-pyforge-core CAP-6): ``ProcessResult``/``ProcessPort``/
``PosixProcess``/``ProcessError``, moved VERBATIM from Marshal's own
``ports/process.py`` (Story 2.1/3.4, AD-4/AD-11/AD-17) +
``adapters/process_posix.py`` (same stories) -- the design CAP-6 chose over
Doctor's simpler ``cli_bridge.run_cli_json``/``run_git`` pair. See
SPEC-pyforge-core's own Design Notes for the rationale: ``ProcessPort``
offers ``is_alive``/``spawn_detached`` (Doctor's two-function API has
neither) and its ``run`` never raises on a non-zero exit -- the same
non-raising, typed-classification philosophy Warden's ``engines.py``
independently already uses -- whereas Doctor's ``run_cli_json`` raises on
ANY non-zero exit, a narrower convenience fitting only its own JSON-fetch
use case.

``pyforge-core`` has no ``ports``/``adapters`` split of its own (unlike
Marshal's hexagonal layout) -- the Protocol, its value type, its sole
implementation, and its exception all live together in this one flat leaf
module, matching every other ``pyforge.core`` primitive's own shape
(``atomic_write.py``, ``verdict.py``, ``errors.py``).

One method matters most, ``run``: NEVER raises for a non-zero exit -- unlike
every other port Marshal's own architecture defines, a failing command is
the ordinary, expected shape a gate evaluation exists to report on, not an
exceptional one. Raises ``ProcessError`` only when the process could not be
launched (or run to completion) AT ALL: a missing executable, a
permission/launch failure, or a timeout.

``is_alive``/``spawn_detached`` (Marshal's Story 3.4, the supervisor's own
process lifecycle) round out the Protocol: ``is_alive`` is the liveness
probe a caller's own tick loop polls, and ``spawn_detached`` is a GENERIC
detached-launch primitive (POSIX ``setsid``, closed stdin, both streams
redirected to a caller-given log path, never waited on) -- callers needing a
second, divergent detach mechanism should not exist; this is the one.

No non-stdlib import (CAP-1's leaf constraint) -- only ``pyforge.core.errors``
(this package's own sibling module) and the stdlib ``os``/``subprocess``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pyforge.core.errors import PyforgeError


@dataclass(frozen=True)
class ProcessResult:
    """One completed process's outcome: ``returncode`` plus its captured
    ``stdout``/``stderr`` (already-decoded text, ``text=True``/
    ``errors="replace"`` convention). A constructed ``ProcessResult`` always
    represents a process that actually ran to completion -- a process that
    could not be launched, or that was killed by a timeout, never produces
    one; see ``ProcessPort.run``'s own docstring."""

    returncode: int
    stdout: str
    stderr: str


class ProcessPort(Protocol):
    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        """Run ``argv`` (already-tokenized, e.g. via ``shlex.split`` --
        this Protocol takes no raw command string, so it can never
        re-interpret shell metacharacters a caller already parsed) with
        ``cwd`` as the working directory, capturing stdout/stderr as text.

        NEVER raises for a non-zero exit -- that is the ordinary "the
        command failed" shape a gate evaluation reports on, not an
        exceptional one. Raises ``ProcessError`` only when ``argv`` could
        not be launched or run to completion at all (the executable does
        not resolve, a permission/launch ``OSError``, or the process
        exceeded ``timeout_s`` when one is given)."""
        ...

    def is_alive(self, pid: int) -> bool:
        """``True`` iff a process with this ``pid`` currently exists on this
        host -- NEVER raises (a caller's own supervisory loop polls this
        every tick against a run it does not own the lifecycle of; a probe
        that cannot answer must degrade, not crash the loop). A probe that
        finds no such process returns ``False``. A process that EXISTS but
        is not one this invocation owns (a different user's process reusing
        the pid, or one this process lacks permission to signal) still
        returns ``True`` -- existence is the only question this method
        answers; ownership is never inferred from a permission failure,
        which is exactly the case a signal-based liveness probe cannot tell
        apart from "gone" without this distinction. "NEVER raises" is
        literal and includes a ``pid`` the host cannot even represent (one
        outside C ``int`` range, which the POSIX probe rejects with a bare
        ``OverflowError`` rather than an ``OSError``): unprobeable is
        reported as ``False``, never as an exception."""
        ...

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, log_path: Path) -> int:
        """Launch ``argv`` as a detached child -- a new session (POSIX
        ``setsid``, never inheriting this process's own controlling
        terminal or process group), stdin closed (``DEVNULL``), stdout AND
        stderr redirected to ``log_path``, and never waited on: this method
        returns as soon as the OS confirms the launch. Returns the spawned
        process's pid. Raises ``ProcessError`` only when ``argv`` could not
        be launched at all (an empty ``argv``, a missing executable, a
        permission/launch ``OSError``, or ``log_path`` could not be opened
        for writing) -- the SAME split ``run`` documents, since a detached
        child's own exit status is never observed by this call at all, let
        alone returned.

        ``cwd`` sets the child's working directory ONLY -- never where its
        code is resolved from. A Python child launched here runs its
        interpreter's INSTALLED environment (``PYTHONSAFEPATH``), so a
        stdlib-shadowing module or a same-named package sitting in ``cwd``
        cannot decide what the child imports; see the implementing
        adapter's own comment for the review finding behind that."""
        ...


class ProcessError(PyforgeError, Exception):
    """Raised when ``argv`` could not be launched or run to completion at
    all: the executable does not resolve, launching it failed for any other
    reason (a permission error, a corrupt binary), the argv list was empty
    (no executable to launch), an argv element carries a ``NUL`` byte
    (``subprocess.run`` raises a raw ``ValueError`` for this), or the process
    exceeded ``timeout_s``. Never lets a raw ``FileNotFoundError``,
    ``IndexError`` (an empty ``argv``), ``ValueError`` (an embedded ``NUL``
    byte), ``subprocess.TimeoutExpired``, or other launch ``OSError`` escape
    this module."""


class PosixProcess:
    """``ProcessPort``'s sole implementation.

    No ``env=`` override to ``subprocess.run``: the child inherits this
    process's own environment exactly -- a caller's own tooling (pixi, an
    activated venv, PATH-resolved binaries) needs the invoking shell's
    environment to resolve at all, and this leaf holds no policy field
    standing in for a curated child environment.

    No default ``timeout_s``: a caller's own command duration is entirely
    caller-defined, so ``run`` defaults to ``None`` (no timeout) rather than
    inventing an arbitrary ceiling.
    """

    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        if not argv:
            # A whitespace-only command shlex.split()s to an empty list --
            # distinct from a shlex.split() ValueError (a caller's own
            # concern before this method is ever called), but equally
            # unlaunchable: there is no argv[0] to exec. Guarded here (not
            # left to raise a raw IndexError from subprocess.run(([]))) so
            # this Protocol's "raises ProcessError only" contract holds for
            # every caller.
            raise ProcessError("cannot launch an empty argv (no executable given)")
        try:
            result = subprocess.run(
                list(argv),
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                # stdin=DEVNULL: a caller invoking this in an unattended
                # context (an operator or CI with no terminal to answer a
                # prompt) must not have a command that unexpectedly reads
                # input block forever waiting on input that can never
                # arrive, on top of this method's own unbounded-by-default
                # timeout_s.
                stdin=subprocess.DEVNULL,
                # check=False, explicit (ruff PLW1510): this method's own
                # contract is "NEVER raises for a non-zero exit" -- a raised
                # CalledProcessError would violate it, so the implicit
                # default is spelled out rather than left to a linter's
                # guess.
                check=False,
            )
        except FileNotFoundError as exc:
            raise ProcessError(f"executable not found: {argv[0]!r} ({exc})") from exc
        except subprocess.TimeoutExpired as exc:
            raise ProcessError(f"command timed out after {timeout_s}s: {' '.join(argv)}") from exc
        except ValueError as exc:
            # subprocess.run raises a plain ValueError -- not an OSError --
            # for an embedded NUL byte in argv, which would otherwise escape
            # this method's own "raises ProcessError only" contract.
            raise ProcessError(f"cannot launch {list(argv)!r}: {exc}") from exc
        except OSError as exc:
            # Launching a command can fail with more than absence: EACCES on
            # a non-executable file, ENOEXEC on a corrupt binary -- all must
            # land in ProcessError, never escape raw.
            raise ProcessError(f"cannot launch {list(argv)!r}: {exc}") from exc
        return ProcessResult(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)

    def is_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            # ESRCH: no process with this pid exists -- the only "gone" case
            # this port promises. A ZOMBIE does NOT land here: an
            # exited-but-unreaped child still holds its pid slot, so
            # `os.kill(pid, 0)` SUCCEEDS on it and this method reports it
            # alive; only reaping (the parent's `wait`, or a reparenting
            # init that reaps) frees the pid and produces ESRCH.
            return False
        except PermissionError:
            # EPERM: a process with this pid exists but this invocation
            # lacks permission to signal it (a different user's process
            # reusing the pid) -- this port's own docstring is explicit that
            # existence, not ownership, is the question, so this is a live
            # process, not an absent one.
            return True
        except OverflowError, ValueError:
            # NOT an OSError: `os.kill` raises a bare `OverflowError` for a
            # pid outside C `int` range (and a `ValueError` for other
            # unconvertible integer inputs), so neither is caught by the
            # clause below. A pid this method cannot even probe is, for this
            # port's two-valued contract, not confirmed alive.
            return False
        except OSError:
            # Any other OSError (e.g. EINVAL for an invalid signal number,
            # unreachable here since 0 is always valid, kept only so this
            # method holds its own "never raises" contract against a future
            # platform quirk) reports the conservative "not confirmed alive"
            # answer rather than escaping raw.
            return False
        return True

    def spawn_detached(self, argv: Sequence[str], *, cwd: Path, log_path: Path) -> int:
        if not argv:
            # Same guard as run() above, and for the identical reason: there
            # is no argv[0] to exec, and this Protocol's "raises ProcessError
            # only" contract must hold for every caller.
            raise ProcessError("cannot launch an empty argv (no executable given)")
        try:
            # Deliberately NOT `with open(...) as log_file:` (ruff SIM115,
            # suppressed below): opening the log and launching the child are
            # two DISTINCT failure modes with two distinct messages (see the
            # `with log_file:` block's own comment a few lines down), so the
            # open must stay outside that block's exception handling.
            log_file = open(log_path, "wb")  # noqa: SIM115
        except (OSError, ValueError) as exc:
            # `ValueError` alongside `OSError`: `open()` raises a plain
            # `ValueError` -- not an `OSError` -- for a path containing an
            # embedded NUL byte, the SAME CPython split this method's own
            # `Popen` call below (and `run()` above) already guards.
            #
            # `log_path` quoted: this message is interpolated verbatim into
            # a caller's own report -- some callers print it unquoted by
            # design, so a raw path here would let a hostile log path forge
            # extra report lines.
            raise ProcessError(f"cannot open log {str(log_path)!r}: {exc}") from exc
        # Opening the log and launching the child are two DISTINCT failure
        # modes with two distinct messages, so the open above stays outside
        # this block's exception handling -- the `with` here exists solely
        # to guarantee the descriptor is closed in THIS (parent) process
        # once the child has its own duplicated copy.
        with log_file:
            try:
                process = subprocess.Popen(
                    list(argv),
                    cwd=cwd,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    # PYTHONUNBUFFERED=1: a child's stdout is fully
                    # block-buffered once redirected to a regular file --
                    # a caller polling this log for early output would
                    # otherwise only see it once the child's stdio buffer
                    # fills or the whole run exits.
                    #
                    # PYTHONSAFEPATH=1: `python -m <pkg>` puts `cwd` on
                    # `sys.path[0]`, and a caller of this method may hand it
                    # a `cwd` whose contents it does not own (an arbitrary
                    # project checkout). A stdlib-shadowing module or a
                    # stray same-named package at that root would otherwise
                    # decide which code the detached child ran. A detached
                    # child must run the interpreter's INSTALLED
                    # environment, never whatever happens to sit in the
                    # directory it was pointed at.
                    env={
                        **os.environ,
                        "PYTHONUNBUFFERED": "1",
                        "PYTHONSAFEPATH": "1",
                    },
                )
            except FileNotFoundError as exc:
                # NOT necessarily "the executable is missing": Popen raises
                # this identical exception when `cwd` itself cannot be
                # chdir'd into (e.g. a removed directory) -- a materially
                # different cause. Neither this method's docstring nor its
                # caller can distinguish the two from the raised exception
                # alone, so the message states only what is actually known.
                raise ProcessError(f"cannot launch {list(argv)!r}: {exc}") from exc
            except ValueError as exc:
                # subprocess.Popen raises a plain ValueError (not an
                # OSError) for an embedded NUL byte in argv -- the same
                # CPython behavior run()'s own identical catch documents.
                raise ProcessError(f"cannot launch {list(argv)!r}: {exc}") from exc
            except OSError as exc:
                raise ProcessError(f"cannot launch {list(argv)!r}: {exc}") from exc
        return process.pid
