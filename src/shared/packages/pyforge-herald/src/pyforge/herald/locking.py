"""Cross-platform advisory file lock shared by every whole-document
read-modify-write in this package (Story 13.1, closing ``DW-1-4-2``).

``state.py``, ``progress.py``, ``claims.py``, and ``notices.py`` each load a
document, mutate one entry, and atomically replace it via a temp file plus
``os.replace`` -- crash-safe (a reader never observes a half-written file),
but not concurrency-safe: two callers can each load before either has
replaced, and the second writer's ``os.replace`` silently discards the
first writer's update. ``locked`` closes that gap: one small, shared,
stdlib-only, cross-platform advisory lock (``fcntl.flock`` on POSIX,
``msvcrt.locking`` on Windows -- this package targets win-64, so
POSIX-only ``fcntl`` alone is not enough) held across a caller's whole
read-modify-write span, keyed on a sidecar ``<document>.lock`` file next to
the document it protects. Uses a raw ``os.open`` descriptor rather than a
Python-level ``open()`` file object (mirrors
``pyforge.marshal.adapters.fs_local``'s ``acquire_advisory_lock``) -- both
``fcntl.flock`` and ``msvcrt.locking`` operate on the descriptor directly,
so no buffered file object is ever needed.

Deliberately no timeout, no staleness detection, no retry-with-backoff: an
OS-level advisory lock releases automatically the instant the holding
process exits, crashes, or is killed, so there is nothing to detect or
clean up (this story's spec, ``## Boundaries & Constraints`` -> Never). A
second caller simply blocks until the lock is free, however long that
takes -- exactly the serialization behavior the calling modules need, and
no more machinery than that.

Two adjacent hazards worth naming explicitly. The lock is per-document, not
per-record: two writers touching unrelated keys/slugs/stations in the SAME
document still fully serialize rather than proceeding concurrently -- a
deliberate simplicity trade-off, not an oversight. ``locked()`` is also not
reentrant: a second ``locked()`` call on the same ``lock_path`` from the
same thread before the first has exited will block forever (a self-deadlock)
-- ``fcntl``/``msvcrt`` locks are tied to the open file descriptor, not the
thread, so the second call has no way to recognize it already holds the
lock.

Lock-acquisition failures (an unwritable lock-file directory, a lock file
that cannot be opened, the OS-level lock call itself failing) raise
``errors.HeraldError`` naming the lock path, matching every other
structural-failure path in this package (AD-6) rather than leaking a raw
``OSError``.
"""

from __future__ import annotations

import contextlib
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path

from . import errors


def _acquire(fd: int) -> None:
    """Block until an exclusive lock on ``fd`` is held."""
    if sys.platform == "win32":
        import msvcrt

        # msvcrt.locking locks a byte range starting at the descriptor's
        # current position, not the whole file -- seek to a fixed offset
        # (0) so every process contends on the same region regardless of
        # how much the sidecar file has grown from a prior run.
        os.lseek(fd, 0, os.SEEK_SET)
        # Unlike POSIX fcntl.flock(LOCK_EX), which blocks indefinitely,
        # msvcrt.locking(LK_LOCK) only retries internally for about 10
        # seconds before raising OSError -- so a single call cannot
        # deliver this module's documented "no timeout, block however
        # long it takes" contract under sustained contention. Retry the
        # same call in a loop, swallowing the ~10s timeout OSError each
        # time, so this module's actual behavior matches POSIX's
        # indefinite-block semantics regardless of how long the current
        # holder keeps the lock. A short sleep between attempts avoids a
        # tight spin while another process holds the lock.
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            except OSError:
                time.sleep(0.1)
                continue
            else:
                return
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)


def _release(fd: int) -> None:
    """Release the lock ``_acquire`` took."""
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


@contextlib.contextmanager
def locked(lock_path: Path) -> Iterator[None]:
    """Hold an exclusive advisory lock on ``lock_path`` for the ``with``
    block's duration, serializing every other caller locking the same path.

    Creates ``lock_path``'s parent directory and the sidecar lock file
    itself if either is missing -- a caller never has to pre-create the
    ``.herald/`` directory (or whichever directory holds the protected
    document) just to acquire a lock on a document that does not exist yet.
    Every failure along the way -- an unwritable parent directory, a lock
    file that cannot be opened, the OS-level lock call itself failing --
    raises ``errors.HeraldError`` naming ``lock_path`` rather than a raw
    ``OSError`` (AD-6). Release is best-effort: the descriptor is closed
    either way once the ``with`` block exits, and a release failure never
    masks an exception the protected block itself raised."""
    could_not_acquire = f"lock {lock_path} could not be acquired"
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as exc:
        raise errors.HeraldError(f"{could_not_acquire}: {exc}") from exc
    try:
        try:
            _acquire(fd)
        except OSError as exc:
            raise errors.HeraldError(f"{could_not_acquire}: {exc}") from exc
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                _release(fd)
    finally:
        os.close(fd)
