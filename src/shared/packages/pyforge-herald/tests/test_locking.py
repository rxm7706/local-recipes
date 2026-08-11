"""``locking.py``'s advisory file lock primitive (Story 13.1, DW-1-4-2).

These tests exercise the lock in isolation, independent of any of the four
storage modules that use it -- each module's own concurrency regression
test (``test_state.py``/``test_progress.py``/``test_claims.py``/
``test_notices.py``) proves the *wiring*; these tests prove the
*primitive* the I/O matrix's own rows describe: two concurrent writers
serialize, the lock releases cleanly when its holder is done (normally, or
via a hard process exit that skips Python-level cleanup entirely), and an
unwritable lock-file parent directory fails structurally."""

from __future__ import annotations

import multiprocessing
import os
import threading
import time
from pathlib import Path

import pytest
from pyforge.herald.errors import HeraldError
from pyforge.herald.locking import locked


def _hold_lock_then_hard_exit(lock_path: Path) -> None:
    """Child-process target for
    ``test_lock_releases_when_a_process_exits_without_running_python_cleanup``.

    Module-level (not a closure) so it can be pickled to hand off to the
    child process regardless of the platform's default
    ``multiprocessing`` start method."""
    cm = locked(lock_path)
    cm.__enter__()  # acquired; deliberately never __exit__'d
    os._exit(1)


def test_two_threads_serialize_rather_than_race(tmp_path: Path):
    """Forced deterministic interleaving: both threads reach ``locked()``
    at the same instant (a ``threading.Barrier``), then each holds the lock
    across a short, deliberate sleep. If the lock did not serialize them,
    the two critical sections would overlap -- the shared ``events`` log
    would show an ``*-enter`` immediately followed by the OTHER thread's
    ``*-enter`` before the first thread's ``*-exit``."""
    lock_path = tmp_path / "doc.json.lock"
    barrier = threading.Barrier(2)
    events: list[str] = []
    events_guard = threading.Lock()

    def worker(name: str) -> None:
        barrier.wait()
        with locked(lock_path):
            with events_guard:
                events.append(f"{name}-enter")
            time.sleep(0.05)
            with events_guard:
                events.append(f"{name}-exit")

    threads = [
        threading.Thread(target=worker, args=("a",)),
        threading.Thread(target=worker, args=("b",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert not any(t.is_alive() for t in threads)

    assert events in (
        ["a-enter", "a-exit", "b-enter", "b-exit"],
        ["b-enter", "b-exit", "a-enter", "a-exit"],
    )


def test_lock_releases_cleanly_when_the_holder_exits_normally(tmp_path: Path):
    lock_path = tmp_path / "doc.json.lock"
    with locked(lock_path):
        pass
    # A second acquisition must not block -- if the first `with` failed to
    # release, this would hang forever (an flock/msvcrt lock blocks
    # indefinitely rather than raising).
    acquired = threading.Event()

    def worker() -> None:
        with locked(lock_path):
            acquired.set()

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=5)
    assert acquired.is_set()


def test_lock_releases_when_a_process_exits_without_running_python_cleanup(
    tmp_path: Path,
):
    """The I/O matrix's 'process crashes while holding the lock' row: a
    child process takes the lock and then hard-exits via ``os._exit`` --
    which, unlike a normal return or even an unhandled exception, skips
    ``finally`` blocks entirely, so ``locked``'s own release code never
    runs. The OS must still release the lock when the process's file
    descriptors are torn down, or the parent's own acquisition below would
    hang.

    Uses the ``fork`` start method explicitly: the default start method's
    ``forkserver``/``spawn`` control channel is a unix socket, which this
    suite's own ``deny_network`` fixture (``conftest.py``) patches
    ``socket.socket.connect`` to reject outright -- unrelated to what this
    test is proving, and ``fork`` needs no such channel."""
    lock_path = tmp_path / "doc.json.lock"

    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(target=_hold_lock_then_hard_exit, args=(lock_path,))
    proc.start()
    proc.join(timeout=5)
    assert not proc.is_alive()

    acquired = threading.Event()

    def worker() -> None:
        with locked(lock_path):
            acquired.set()

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=5)
    assert acquired.is_set()


def test_unwritable_lock_parent_directory_raises_herald_error(tmp_path: Path):
    """Mirrors ``state.py``'s own 'plain file where a directory belongs'
    test pattern: a plain file sitting at the lock path's intended parent
    means ``mkdir`` cannot create it, and ``locked`` must fail structurally
    rather than leak a raw ``OSError``."""
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("not a directory")
    lock_path = blocker / "doc.json.lock"
    with pytest.raises(HeraldError, match=str(lock_path)), locked(lock_path):
        pass
