"""Verification-refusal fix turn orchestration (Story 85.1, CAP-286).

Impure edge: flag read and process wait. Pure decision/prompt in
``core/dispatch_verify_fix.py``; harness launch lives in the dispatch supervisor
via ``BmadBuildHarness.dispatch_verify_fix``.
"""

from __future__ import annotations

import time
from pathlib import Path

from pyforge.core.flags import read_boolean
from pyforge.core.process import ProcessPort

from .core.dispatch_verify_fix import VERIFY_FIX_LOOP_FLAG_KEY


def verify_fix_loop_enabled(*, repo_root: Path) -> bool:
    del repo_root  # flags resolve from platform config, not repo-local overlay
    return read_boolean(VERIFY_FIX_LOOP_FLAG_KEY, default=False, flags_path=None)


def wait_for_process(
    process: ProcessPort,
    pid: int,
    *,
    timeout_s: float,
    poll_s: float = 1.0,
) -> bool:
    """Wait until ``pid`` exits or ``timeout_s`` elapses. Returns True if exited."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not process.is_alive(pid):
            return True
        time.sleep(poll_s)
    return not process.is_alive(pid)
