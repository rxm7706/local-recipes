"""Verification-refusal fix turn orchestration (Story 85.1, CAP-286).

Impure edge: flag read and process wait. Pure decision/prompt in
``core/dispatch_verify_fix.py``; harness launch lives in the dispatch supervisor
via ``BmadBuildHarness.dispatch_verify_fix``.
"""

from __future__ import annotations

import os
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.flags import FlagConfigError, read_boolean
from pyforge.core.process import ProcessPort

from .core.dispatch_verify_fix import VERIFY_FIX_LOOP_FLAG_KEY


@dataclass(frozen=True)
class ProcessWaitResult:
    exited: bool
    returncode: int | None


def verify_fix_loop_enabled(*, repo_root: Path) -> tuple[bool, str | None]:
    """Read the fix-loop flag; ``(False, reason)`` when the flag tree is invalid."""
    flags_path = repo_root / "src/platform/config/flags.json"
    try:
        return read_boolean(VERIFY_FIX_LOOP_FLAG_KEY, default=False, flags_path=flags_path), None
    except FlagConfigError as exc:
        return False, str(exc)


def wait_for_process(
    process: ProcessPort,
    pid: int,
    *,
    timeout_s: float,
    poll_s: float = 1.0,
    on_poll: Callable[[], None] | None = None,
) -> ProcessWaitResult:
    """Wait until ``pid`` exits or ``timeout_s`` elapses.

    Uses ``waitpid(WNOHANG)`` so an exited-but-unreaped child is not treated
    as still alive (Story 85.1 review H2).
    """
    del process  # liveness is judged via waitpid, not PosixProcess.is_alive
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            reaped, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return ProcessWaitResult(exited=True, returncode=None)
        except OSError:
            return ProcessWaitResult(exited=False, returncode=None)
        if reaped == pid:
            return ProcessWaitResult(exited=True, returncode=os.waitstatus_to_exitcode(status))
        if on_poll is not None:
            on_poll()
        time.sleep(poll_s)
    try:
        reaped, status = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return ProcessWaitResult(exited=True, returncode=os.waitstatus_to_exitcode(status))
    except (ChildProcessError, OSError):
        pass
    return ProcessWaitResult(exited=False, returncode=None)


def terminate_process_group(pid: int) -> None:
    """Signal the session leader's process group (Story 85.1 review M4)."""
    try:
        pgid = os.getpgid(pid)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
