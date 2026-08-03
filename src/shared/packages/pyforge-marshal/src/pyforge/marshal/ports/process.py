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
