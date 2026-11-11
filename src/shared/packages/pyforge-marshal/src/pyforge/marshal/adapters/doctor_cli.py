"""THE ONLY module permitted to run Doctor's spec-surface command (Story 115.2, spec-pyforge-marshal CAP-261 (b)).

Follows ``adapters/steward_cli.py`` discipline: run one command through the injected
``ProcessPort`` with a timeout, turn every failure into a reason, and raise nothing. The landing
reaches Doctor's spec-surface verdict through Doctor's documented command module -- the one the
``spec-surface-check`` pixi task runs, ``python -m pyforge.doctor.sources spec-surface`` -- and
never by importing ``pyforge.doctor``. ``BOOTSTRAP`` puts the worktree's own Doctor source first
on ``sys.path`` and runs that module as ``__main__``, so the verdict is the checked-out branch's
own Doctor. ``ProcessPort.run`` carries no environment parameter, hence the bootstrap rather than
``PYTHONPATH``.

Doctor's exit domain is ``{0, 2, 130}``: 0 when no row FAILs, 2 when one does (``drift`` is a
FAIL), and argparse also exits 2, with nothing on stdout. So stdout that parses as a JSON list of
rows is the verdict for exit 0 and for exit 2; anything else -- any other exit code, stdout that
is empty or not a JSON list, a row without ``check``/``message``/``evidence`` -- is
``Unavailable``. Doctor's prose is never parsed.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from pyforge.core.process import ProcessError, ProcessPort

__all__ = (
    "BOOTSTRAP",
    "DOCTOR_SOURCE_REL",
    "SurfaceRow",
    "Unavailable",
    "Verdict",
    "read_spec_surface",
    "spec_surface_argv",
)

#: The worktree-relative Doctor source tree the bootstrap puts first on ``sys.path``.
DOCTOR_SOURCE_REL = "src/shared/packages/pyforge-doctor/src"

#: Doctor's documented command module, the one the ``spec-surface-check`` task runs.
_DOCTOR_COMMAND_MODULE = "pyforge.doctor.sources"

#: Run with the worktree as cwd: the worktree's Doctor source goes to ``sys.path[0]``, then
#: Doctor's command module runs as ``__main__`` with ``sys.argv`` set by ``alter_sys``.
BOOTSTRAP = (
    "import os, runpy, sys; "
    f"sys.path.insert(0, os.path.join(os.getcwd(), *{tuple(DOCTOR_SOURCE_REL.split('/'))!r})); "
    f"runpy.run_module({_DOCTOR_COMMAND_MODULE!r}, run_name='__main__', alter_sys=True)"
)

_SPEC_SURFACE_ARGV_TAIL = ("spec-surface", "--json")

_DOCTOR_VERDICT_TIMEOUT_S = 300.0

#: Doctor's exit codes that carry a verdict on stdout: 0 (no FAIL row) and 2 (a FAIL row).
_VERDICT_EXIT_CODES = frozenset({0, 2})


@dataclass(frozen=True)
class SurfaceRow:
    """One row of Doctor's spec-surface verdict: the ``check``, ``message`` and ``evidence``
    keys of ``Finding.to_json_dict()``. Any other key in the row is ignored."""

    check: str
    message: str
    evidence: Mapping[str, object]


@dataclass(frozen=True)
class Verdict:
    """Doctor's spec-surface verdict: every row it printed, and the exit code (0 or 2)."""

    rows: tuple[SurfaceRow, ...]
    returncode: int


@dataclass(frozen=True)
class Unavailable:
    """No verdict could be read; ``reason`` says why."""

    reason: str


def spec_surface_argv() -> tuple[str, ...]:
    return (sys.executable, "-c", BOOTSTRAP, *_SPEC_SURFACE_ARGV_TAIL)


def _last_stderr_line(stderr: str) -> str:
    """The last non-blank stderr line: where a traceback names its exception and argparse its error."""
    for line in reversed(stderr.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return "<no stderr>"


def _row(item: object) -> SurfaceRow | None:
    if not isinstance(item, dict):
        return None
    check = item.get("check")
    message = item.get("message")
    evidence = item.get("evidence")
    if not isinstance(check, str) or not isinstance(message, str) or not isinstance(evidence, dict):
        return None
    return SurfaceRow(check=check, message=message, evidence=MappingProxyType(dict(evidence)))


def read_spec_surface(worktree: Path, process: ProcessPort) -> Verdict | Unavailable:
    """Run the worktree's own Doctor ``spec-surface --json`` and read its verdict. Never raises."""
    argv = spec_surface_argv()
    try:
        result = process.run(argv, cwd=worktree, timeout_s=_DOCTOR_VERDICT_TIMEOUT_S)
    except ProcessError as exc:
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            return Unavailable(f"doctor spec-surface timed out after {_DOCTOR_VERDICT_TIMEOUT_S}s")
        return Unavailable(f"doctor spec-surface could not run ({exc})")
    stderr_last = _last_stderr_line(result.stderr or "")
    if result.returncode not in _VERDICT_EXIT_CODES:
        return Unavailable(f"doctor spec-surface exited {result.returncode}: {stderr_last}")
    stdout = (result.stdout or "").strip()
    if not stdout:
        return Unavailable(f"doctor spec-surface exited {result.returncode} with no verdict on stdout: {stderr_last}")
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return Unavailable(f"doctor spec-surface exited {result.returncode} and its stdout is not JSON")
    if not isinstance(parsed, list):
        return Unavailable(f"doctor spec-surface exited {result.returncode} and its stdout is not a JSON list")
    rows: list[SurfaceRow] = []
    for index, item in enumerate(parsed):
        row = _row(item)
        if row is None:
            return Unavailable(
                f"doctor spec-surface row {index} is not a finding (check, message and evidence are required)"
            )
        rows.append(row)
    return Verdict(rows=tuple(rows), returncode=result.returncode)
