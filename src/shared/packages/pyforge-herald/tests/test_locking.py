"""``locking.py``'s cross-platform advisory-lock primitive (Story 13.1,
closing ``DW-1-4-2``) -- unit tests for the lock itself, independent of any
particular document-store module (``test_state.py``/``test_progress.py``/
``test_claims.py``/``test_notices.py`` each carry their own regression test
proving the lock actually closes their module's lost-update race).
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from pyforge.herald import locking
from pyforge.herald.errors import HeraldError


def test_locked_serializes_two_threads(tmp_path: Path):
    """Two threads racing for the same lock never interleave: whichever
    acquires first runs its whole (deliberately slow) critical section to
    completion before the other's critical section starts -- proof that
    ``locked`` actually excludes, not just "usually happens to" via thread
    scheduling luck."""
    lock_path = tmp_path / "doc.lock"
    events: list[str] = []

    def worker(name: str) -> None:
        with locking.locked(lock_path):
            events.append(f"{name}-start")
            time.sleep(0.1)
            events.append(f"{name}-end")

    t1 = threading.Thread(target=worker, args=("a",))
    t2 = threading.Thread(target=worker, args=("b",))
    t1.start()
    time.sleep(0.02)  # give t1 a head start acquiring the lock first
    t2.start()
    t1.join()
    t2.join()

    assert events in (
        ["a-start", "a-end", "b-start", "b-end"],
        ["b-start", "b-end", "a-start", "a-end"],
    )


_HOLD_LOCK_SCRIPT = """
import sys
import time
from pathlib import Path
from pyforge.herald import locking

lock_path = Path(sys.argv[1])
with locking.locked(lock_path):
    print("ACQUIRED", flush=True)
    time.sleep(60)
"""


def test_locked_releases_when_the_holding_process_is_killed(tmp_path: Path):
    """The I/O matrix's "process crashes while holding the lock" row: a
    genuine, separate OS process acquires the lock and is then SIGKILLed --
    no ``finally``, no context-manager cleanup, nothing but the OS's own
    process-exit fd cleanup runs. A fresh acquire must still succeed
    promptly, proving the lock is never left stuck-held by a dead holder
    (no stale-lock cleanup needed, matching the spec's own Never list)."""
    lock_path = tmp_path / "doc.lock"
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLD_LOCK_SCRIPT, str(lock_path)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        line = proc.stdout.readline() if proc.stdout is not None else ""
        assert line.strip() == "ACQUIRED", "background process never acquired the lock"

        acquired = threading.Event()

        def _try_acquire() -> None:
            with locking.locked(lock_path):
                acquired.set()

        t = threading.Thread(target=_try_acquire, daemon=True)
        t.start()
        proc.kill()
        proc.wait(timeout=5)
        t.join(timeout=5)
        assert acquired.is_set(), (
            "lock was not released after the holding process was killed"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_locked_raises_herald_error_on_unwritable_parent_directory(tmp_path: Path):
    """A plain file where the lock's parent directory should be must
    surface as ``HeraldError`` naming the lock path, never a raw
    ``OSError`` -- mirrors ``state.py``'s own AD-6 discipline."""
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("plain file")
    lock_path = blocker / "doc.lock"
    with pytest.raises(HeraldError, match=str(lock_path)), locking.locked(lock_path):
        pass
