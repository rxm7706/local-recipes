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
"""

from __future__ import annotations

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
