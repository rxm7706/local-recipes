"""Cross-platform advisory file lock for ``state.py``'s whole-document
read-modify-writes (Story 13.1, closing ``DW-1-4-2``).

Story 13.1 introduced this for four modules; Story 13.3 moved
``progress.py``/``claims.py``/``notices.py`` onto one shared SQLite
database, whose own ``BEGIN IMMEDIATE`` transaction (``db.transaction``) is
their lock now. ``state.py`` -- still a JSON document at
``.herald/bridge-state.json``, deliberately out of that story's surface --
is this module's one remaining caller. The reasoning below is unchanged;
read "the caller" for what used to be a list of four.

Scope is that module only. ``registry.register`` and
``deck_pipeline._atomic_write_text`` are whole-document read-modify-writes
too and are deliberately NOT covered here -- they were outside this story's
surface, and their own docstrings still record that concurrent writers are
unaddressed. Do not read this module as a package-wide guarantee.

A caller loads a document, mutates one entry, and atomically replaces it
via a temp file plus
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

Lock *teardown* failures deliberately do not, and that asymmetry is worth
stating plainly because this story's spec asks for both directions. Release
and close both run in a ``finally`` after the guarded block, where raising
would replace whatever exception that block itself raised -- turning an
accurate "claims.json could not be written" into a misleading "close
failed", and leaking a raw ``OSError`` out of a module documenting
``HeraldError`` as its only failure mode. Both are therefore suppressed:
the AD-6 intent behind the spec's bullet (never surface a raw ``OSError``)
is honored, its literal "raise on release failure" is not. The trade-off is
that a release failure is silent; in practice ``flock(LOCK_UN)`` /
``msvcrt.locking(LK_UNLCK)`` fail only on an already-invalid descriptor,
and the immediately following close (or, failing that, process exit)
releases the lock regardless.
"""

from __future__ import annotations

import contextlib
import errno
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
        #
        # Only the contention timeout (EDEADLOCK, what LK_LOCK raises after
        # its ~10s of internal retries) is retried. A permanent failure --
        # EACCES, EBADF, EINVAL, or a volume that does not support byte-range
        # locking at all -- is re-raised so `locked` can wrap it as a
        # HeraldError. Retrying those forever would hang the process at 10Hz
        # with no output and no error, and would make this module's
        # documented AD-6 acquisition-failure contract unreachable on
        # Windows.
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            except OSError as exc:
                if exc.errno != errno.EDEADLOCK:
                    raise
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


def lock_path_for(document_path: Path) -> Path:
    """The sidecar ``<document>.lock`` path protecting ``document_path`` --
    the one place that convention is spelled out, so every caller derives it
    identically.

    Refuses a path with an empty name (``Path("/")``, ``Path(".")``) with
    ``errors.HeraldError`` rather than letting ``Path.with_name``'s raw
    ``ValueError`` escape: a caller passing one of those has handed in a
    directory where a document was expected, and every other structural
    refusal in this package surfaces as a ``HeraldError`` (AD-6).
    ``Path("..")`` is NOT refused -- its ``name`` is ``".."``, not empty, so
    ``with_name`` accepts it and there is no ``ValueError`` to pre-empt."""
    if not document_path.name:
        raise errors.HeraldError(f"{document_path} is not a file path, so no lock file can be derived for it")
    return document_path.with_name(document_path.name + ".lock")


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
    ``OSError`` (AD-6). Teardown is best-effort: the descriptor is closed
    either way once the ``with`` block exits, and neither the release nor
    the close can mask an exception the protected block itself raised, or
    surface as a raw ``OSError`` from a call that otherwise succeeded."""
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
        # Suppressed for the same reason `_release` is: a teardown failure
        # (EIO on an odd filesystem, EBADF) must not replace the real
        # exception the guarded block raised, nor leak a raw `OSError` out
        # of a call this module documents as raising `HeraldError` only
        # (AD-6). On Linux the fd is freed even when `close` reports an
        # error, so nothing leaks there. Windows gives no such guarantee,
        # so a failing close there could strand this descriptor -- and with
        # it the byte-range lock -- until the process exits; that is
        # accepted as the lesser harm against masking the guarded block's
        # real exception, and it resolves on exit like every other lock
        # this module takes.
        with contextlib.suppress(OSError):
            os.close(fd)
