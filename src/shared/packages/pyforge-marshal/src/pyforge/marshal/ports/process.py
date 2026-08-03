"""``ProcessPort`` -- the subprocess-spawning seam ``cli/gate.py`` depends on
(Story 2.1, architecture spine AD-4/AD-11/AD-17). A Protocol definition only
(Structural Seed: ``ports/`` declares shapes, never implementations);
implemented solely by ``adapters/process_posix.py`` (AD-4). Not an egress
port (AD-34): argv/environment handed to a child process, and that child's
own captured stdout/stderr, never leave Marshal's own trust boundary (they
end up in Marshal's own CLI stdout/envelope, not a durable or third-party
sink) -- AD-34's planned ``core/egress.py`` redaction (a module the
architecture describes but which does not exist in the tree yet) is
explicitly not in scope for this
seam.

One method, ``run``: NEVER raises for a non-zero exit -- unlike every other
port in this package, a failing command is the ordinary, expected shape a
gate evaluation exists to report on, not an exceptional one. Raises
``ProcessError`` only when the process could not be launched (or run to
completion) AT ALL: a missing executable, a permission/launch failure, or a
timeout. This is the one deliberate split from ``VcsPort``'s own
"raises <AdapterError> on any git failure" discipline -- there, a non-zero
exit from ``git`` always means the requested operation did not happen; here,
a non-zero exit IS the requested information.

``core/gate.py`` never calls this Protocol directly (AD-4: ``core/**``
forbids ``subprocess``/``os``/``time``/``adapters`` imports) -- only
``cli/gate.py`` holds a ``ProcessPort`` reference; ``core/gate.py`` consumes
just the ``ProcessResult`` value type this module also defines.

Story 3.4 (the supervisor's own process lifecycle, AD-9/AD-20) adds two
more: ``is_alive`` -- the liveness probe the supervisor's own loop polls
each tick, and the sidecar-spawn precondition ``cli/spin.py`` checks
nothing on (a launch either produces a live pid or raises, so there is
nothing to probe there) -- and ``spawn_detached`` -- a GENERIC detached-
launch primitive, deliberately not specific to ``bmad-loop run``: it is
what both the supervisor's own ``cli/spin.py`` spawn site and, structurally,
any future detached child this package ever needs to launch outside a
session's lifetime share, mirroring ``adapters/harness_bmadloop.py::spin``'s
exact recipe (``Popen(..., start_new_session=True, stdin=DEVNULL,
stdout=stderr=log_file)``, never waited on) rather than growing a SECOND
independent detach mechanism next to that one. Neither method reads a
clock, so ``core/**``'s AD-4 purity is unaffected by their existence here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ProcessResult:
    """One completed process's outcome (Story 2.1): ``returncode`` plus its
    captured ``stdout``/``stderr`` (already-decoded text, matching
    ``adapters/vcs_git.py``'s own ``text=True``/``errors="replace"``
    convention). A constructed ``ProcessResult`` always represents a process
    that actually ran to completion -- a process that could not be launched,
    or that was killed by a timeout, never produces one; see
    ``ProcessPort.run``'s own docstring."""

    returncode: int
    stdout: str
    stderr: str


class ProcessPort(Protocol):
    def run(
        self, argv: Sequence[str], *, cwd: Path, timeout_s: float | None = None
    ) -> ProcessResult:
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
        host -- NEVER raises (Story 3.4's supervisor loop polls this every
        tick against a run it does not own the lifecycle of; a probe that
        cannot answer must degrade, not crash the loop). A probe that finds
        no such process returns ``False``. A process that EXISTS but is not
        one this Marshal invocation owns (a different user's process reusing
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

    def spawn_detached(
        self, argv: Sequence[str], *, cwd: Path, log_path: Path
    ) -> int:
        """Launch ``argv`` as a detached child -- a new session (POSIX
        ``setsid``, never inheriting this process's own controlling
        terminal or process group), stdin closed (``DEVNULL``), stdout AND
        stderr redirected to ``log_path``, and never waited on: this method
        returns as soon as the OS confirms the launch, mirroring
        ``adapters/harness_bmadloop.py::BmadLoopHarness.spin``'s own
        detached-launch recipe exactly rather than growing a second,
        divergent one. Returns the spawned process's pid. Raises
        ``ProcessError`` only when ``argv`` could not be launched at all
        (an empty ``argv``, a missing executable, a permission/launch
        ``OSError``, or ``log_path`` could not be opened for writing) -- the
        SAME split ``run`` documents, since a detached child's own exit
        status is never observed by this call at all, let alone returned.

        ``cwd`` sets the child's working directory ONLY -- never where its
        code is resolved from. A Python child launched here runs its
        interpreter's INSTALLED environment (``PYTHONSAFEPATH``), so a
        stdlib-shadowing module or a same-named package sitting in ``cwd``
        cannot decide what the child imports; see the implementing
        adapter's own comment for the review finding behind that."""
        ...
