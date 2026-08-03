"""``PosixProcess`` -- the sole implementation of ``ports.ProcessPort``
(Story 2.1, AD-4/AD-11): every process this package spawns to run a
policy-declared verify command lives here, via the stdlib ``subprocess``
module. Mirrors ``adapters/vcs_git.py``'s own ``_run()`` helper almost
exactly -- same ``capture_output``/``text``/``encoding="utf-8"``/
``errors="replace"`` decoding discipline (that module's own docstring
carries the full rationale for each choice; this module inherits it rather
than restating it) -- with the one behavioral split ``ports/process.py``
documents: a non-zero exit is returned, never raised, since it is the
ordinary shape a gate evaluation reports on.

No ``env=`` override to ``subprocess.run``: the child inherits Marshal's own
process environment exactly (matching ``vcs_git.py::_run``, which passes no
``env=`` either) -- a verify command's own tooling (pixi, an activated venv,
PATH-resolved binaries) needs the invoking shell's environment to resolve at
all, and Marshal has no policy field standing in for a curated child
environment; inventing one here would be speculative surface nothing in the
spec asked for (Simplicity First).

No default ``timeout_s``: unlike ``adapters/vcs_git.py``'s two fixed query/
checkout timeout tiers, a verify command's own duration is entirely
project-defined (this repo's own ``pyforge-marshal-test`` verify command can
legitimately run for minutes) -- Marshal has no policy field for a
per-command timeout budget today, so ``run`` defaults to ``None`` (no
timeout) rather than inventing an arbitrary ceiling.

Story 3.4 adds ``is_alive``/``spawn_detached`` -- the supervisor's own
liveness-probe and generic detached-spawn seam. ``is_alive`` is a bare
``os.kill(pid, 0)`` (POSIX's own "does this pid exist" idiom -- signal ``0``
is never actually delivered, only the kernel's existence/permission check
runs), translating its two failure modes into the two-valued answer this
port's own docstring promises rather than a raised exception either way.
``spawn_detached`` mirrors ``adapters/harness_bmadloop.py::BmadLoopHarness.
spin``'s own ``Popen``/log-file/``start_new_session`` recipe almost exactly
(this module cannot import that one -- adapters never import each other,
AD-4) -- MINUS that method's own harness-run-id log poll, which is specific
to ``bmad-loop run``'s own stdout convention and has no place in a generic
primitive.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from ..ports.process import ProcessResult


class ProcessError(Exception):
    """Raised when ``argv`` could not be launched or run to completion at
    all: the executable does not resolve, launching it failed for any other
    reason (a permission error, a corrupt binary), the argv list was empty
    (no executable to launch), an argv element carries a ``NUL`` byte
    (``subprocess.run`` raises a raw ``ValueError`` for this -- e.g. a
    verify command string containing a TOML ``\\u0000`` escape survives
    ``shlex.split`` as an ordinary character), or the process exceeded
    ``timeout_s``. Never lets a raw ``FileNotFoundError``, ``IndexError``
    (an empty ``argv``), ``ValueError`` (an embedded ``NUL`` byte),
    ``subprocess.TimeoutExpired``, or other launch ``OSError`` escape this
    module -- mirrors ``adapters/vcs_git.py``'s own ``VcsCommandError``
    translation."""


class PosixProcess:
    """``ports.ProcessPort``'s sole implementation."""

    def run(
        self, argv: Sequence[str], *, cwd: Path, timeout_s: float | None = None
    ) -> ProcessResult:
        if not argv:
            # A whitespace-only verify command shlex.split()s to an empty
            # list -- distinct from a shlex.split() ValueError (which
            # cli/gate.py catches before this method is ever called), but
            # equally unlaunchable: there is no argv[0] to exec. Guarded
            # here (not just left to raise a raw IndexError from
            # subprocess.run(([])) so this Protocol's "raises ProcessError
            # only" contract holds for every caller, not only the one
            # cli/gate.py itself already protects against.
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
                # stdin=DEVNULL (review finding): gate evaluate runs in an
                # unattended context (an operator or CI with no terminal to
                # answer a prompt) -- inheriting Marshal's own stdin would
                # let a verify command that unexpectedly reads input (an
                # accidental interactive prompt) block forever waiting on
                # input that can never arrive, on top of this method's own
                # unbounded-by-default timeout_s.
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise ProcessError(f"executable not found: {argv[0]!r} ({exc})") from exc
        except subprocess.TimeoutExpired as exc:
            raise ProcessError(
                f"command timed out after {timeout_s}s: {' '.join(argv)}"
            ) from exc
        except ValueError as exc:
            # subprocess.run raises a plain ValueError -- not an OSError --
            # for an embedded NUL byte in argv (review finding: this
            # otherwise escaped every except clause here, violating this
            # method's own "raises ProcessError only" contract and
            # cli/gate.py's own uncaught-exception guarantee).
            raise ProcessError(f"cannot launch {list(argv)!r}: {exc}") from exc
        except OSError as exc:
            # Launching a command can fail with more than absence: EACCES on
            # a non-executable file, ENOEXEC on a corrupt binary -- all must
            # land in ProcessError, never escape raw (mirrors vcs_git.py's
            # identical _run() catch).
            raise ProcessError(f"cannot launch {list(argv)!r}: {exc}") from exc
        return ProcessResult(
            returncode=result.returncode, stdout=result.stdout, stderr=result.stderr
        )

    def is_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            # ESRCH: no process with this pid exists -- the only "gone" case
            # this port promises. NOTE (review finding, verified live): a
            # ZOMBIE does NOT land here. An exited-but-unreaped child still
            # holds its pid slot, so `os.kill(pid, 0)` SUCCEEDS on it and
            # this method reports it alive; only reaping (the parent's
            # `wait`, or a reparenting init that reaps) frees the pid and
            # produces ESRCH. This comment used to claim the opposite.
            return False
        except PermissionError:
            # EPERM: a process with this pid exists but this Marshal
            # invocation lacks permission to signal it (a different user's
            # process reusing the pid) -- this port's own docstring is
            # explicit that existence, not ownership, is the question, so
            # this is a live process, not an absent one.
            return True
        except (OverflowError, ValueError):
            # NOT an OSError (review finding): `os.kill` raises a bare
            # `OverflowError` for a pid outside C `int` range (and a
            # `ValueError` for other unconvertible integer inputs), so
            # neither is caught by the clause below. `main()`'s own argv
            # guard rejects only a NON-POSITIVE pid, so a malformed
            # invocation carrying an absurdly large pid reached here and
            # killed the supervisor with a raw traceback AFTER its
            # `supervisor-attach` entry was already journaled -- a dangling
            # attach with no matching detach, exactly the silent supervisor
            # death AD-9 says must never happen. A pid this method cannot
            # even probe is, for this port's two-valued contract, not
            # confirmed alive.
            return False
        except OSError:
            # Any other OSError (e.g. EINVAL for an invalid signal number,
            # unreachable here since 0 is always valid, kept only so this
            # method holds its own "never raises" contract against a future
            # platform quirk this file's author did not anticipate) reports
            # the conservative "not confirmed alive" answer rather than
            # escaping raw -- mirrors this module's own run()'s "raise
            # ProcessError, never a bare exception" discipline, one step
            # further: this method's contract has no exception slot at all.
            return False
        return True

    def spawn_detached(
        self, argv: Sequence[str], *, cwd: Path, log_path: Path
    ) -> int:
        if not argv:
            # Same guard as run() above, and for the identical reason: there
            # is no argv[0] to exec, and this Protocol's "raises ProcessError
            # only" contract must hold for every caller, not just the ones
            # that happen to pre-validate a non-empty argv themselves.
            raise ProcessError("cannot launch an empty argv (no executable given)")
        try:
            log_file = open(log_path, "wb")
        except (OSError, ValueError) as exc:
            # `ValueError` alongside `OSError` (review finding): `open()`
            # raises a plain `ValueError` -- not an `OSError` -- for a path
            # containing an embedded NUL byte, the SAME CPython split this
            # method's own `Popen` call below (and `run()` above, and both
            # `observer_mux.py` methods) already guards. Left uncaught here
            # it escaped this port's documented "raises ProcessError only"
            # contract as a raw traceback through `cli/spin.py`'s own
            # `except ProcessError` -- and does so at the one point where a
            # live, already-launched harness process exists, so the crash
            # would strand a running run with no outcome record.
            raise ProcessError(f"cannot open log {log_path}: {exc}") from exc
        # Mirrors harness_bmadloop.py::spin's own split: opening the log and
        # launching the child are two DISTINCT failure modes with two
        # distinct messages, so the open above stays outside this block's
        # exception handling -- the `with` here exists solely to guarantee
        # the descriptor is closed in THIS (parent) process once the child
        # has its own duplicated copy, exactly like that method's own
        # comment explains.
        with log_file:
            try:
                process = subprocess.Popen(
                    list(argv),
                    cwd=cwd,
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file,
                    # PYTHONUNBUFFERED=1 (review finding): this method's own
                    # docstring -- and its caller, cli/spin.py's supervisor-
                    # spawn step -- describe it as mirroring
                    # harness_bmadloop.py::spin's detach recipe "exactly",
                    # but that method forces this env var specifically
                    # because a child's stdout is fully block-buffered once
                    # redirected to a regular file. This generic primitive
                    # had no caller who needed it yet (the supervisor writes
                    # no stdout today), but leaving it off a seam other
                    # future callers will reuse risks silently reintroducing
                    # the exact bug that env var was added to fix.
                    #
                    # PYTHONSAFEPATH=1 (review finding, verified live):
                    # `python -m <pkg>` puts `cwd` on `sys.path[0]`, and
                    # every caller of this method passes a `cwd` it does not
                    # own the contents of -- `cli/spin.py` passes the LOOP
                    # HOME, an arbitrary project checkout. A stdlib-shadowing
                    # module or a stray `pyforge/` directory at that root
                    # therefore decided which code the detached child ran:
                    # it died at import with a raw `ModuleNotFoundError` (or
                    # silently ran the wrong module) while the parent had
                    # already been handed a pid and reported success. A
                    # detached child must run the interpreter's INSTALLED
                    # environment, never whatever happens to sit in the
                    # directory it was pointed at.
                    env={
                        **os.environ,
                        "PYTHONUNBUFFERED": "1",
                        "PYTHONSAFEPATH": "1",
                    },
                )
            except FileNotFoundError as exc:
                # NOT necessarily "the executable is missing" (review
                # finding): Popen raises this identical exception when `cwd`
                # itself cannot be chdir'd into (e.g. a removed loop-home
                # directory) -- a materially different cause this message
                # used to misreport. Neither this method's docstring nor its
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
