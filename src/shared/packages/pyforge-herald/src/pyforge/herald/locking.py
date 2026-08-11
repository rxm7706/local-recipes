"""Cross-platform advisory file lock (Story 13.1, closing ``DW-1-4-2``).

``state.py``, ``progress.py``, ``claims.py``, and ``notices.py`` each do an
unlocked whole-document read-modify-write: load the current JSON/markdown
document, mutate one entry, atomically replace it (temp file + ``os.replace``).
That atomic replace is crash-safety, not concurrency-safety -- two
concurrent writers each load the document before either has replaced it, so
whichever ``os.replace`` runs second silently discards the first writer's
update. This module is the one shared fix those four modules wrap their
read-modify-write span in: an advisory OS-level lock on a sidecar
``<document>.lock`` file, so a second writer blocks and serializes instead
of racing.

**Advisory, not mandatory.** An OS advisory lock only blocks another holder
of the *same* lock -- it does nothing to stop a process that ignores the
lock file entirely (e.g. a text editor hand-editing the document while a
``herald`` command runs). That is an acceptable trade here: every writer in
this codebase goes through this module, and a hand-edit racing a live write
is already an unsupported operating mode (it is exactly what the
``state.py``/``claims.py``/etc. corruption-detection paths exist to catch,
on the assumption hand-edits happen only *between* runs, not during one).

**No staleness handling, deliberately.** An OS-level advisory lock is held
by the *file descriptor*, not a PID or a timestamp -- the kernel releases it
automatically the instant the holding process exits, crashes, or even just
closes the descriptor, so there is no "stale lock file" failure mode a
second writer could get stuck behind. A lock-timeout or staleness check
would only add a way to *break* that guarantee (a slow-but-alive holder
having its lock stolen) without fixing anything the OS does not already fix
for free.

**One sidecar file per document, not one lock for the whole package.** Each
caller passes its own document's lock path (e.g.
``.herald/bridge-state.json.lock``) rather than this module owning a single
global lock -- two callers locking *different* documents (say, a
``state.write`` and a ``progress.upsert`` running concurrently) have no
reason to serialize against each other at all.

**stdlib-only, cross-platform.** ``fcntl.flock`` is POSIX-only; this
package also targets win-64 (a real shipping platform, not just a CI
curiosity), so the platform branch below reaches for ``msvcrt.locking`` on
Windows instead of taking on a third-party dependency (e.g. ``filelock``)
for what the stdlib already covers on both platforms this package ships
for.
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import IO

from . import errors

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def _acquire(fh: IO[bytes]) -> None:
    """Take an exclusive, blocking lock on ``fh``.

    ``msvcrt.locking`` locks a byte *range*, not the whole file, and fails
    if that range extends past the file's current length -- so a
    freshly-created (empty) lock file must be padded to at least one byte
    before the single byte at offset 0 can be locked. ``fcntl.flock`` locks
    the whole open file description regardless of size, so POSIX needs no
    such padding."""
    if sys.platform == "win32":
        fh.seek(0, 2)  # SEEK_END
        if fh.tell() == 0:
            fh.write(b"\0")
            fh.flush()
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)


def _release(fh: IO[bytes]) -> None:
    """Release the lock ``_acquire`` took on ``fh``."""
    if sys.platform == "win32":
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def locked(lock_path: Path) -> Iterator[None]:
    """Hold an exclusive advisory lock on the sidecar file ``lock_path`` for
    the duration of the ``with`` block -- callers wrap their entire
    read-modify-write span (load through atomic replace) in this, never
    just the final write, or the load half of the race would still be
    unguarded.

    Creates ``lock_path``'s parent directory and the lock file itself if
    either is missing (mirrors ``state.write``'s own
    ``mkdir(parents=True, exist_ok=True)`` convention -- the very first
    writer for a document is not an error). Every failure that stops the
    lock from being acquired -- an unwritable parent directory, a lock file
    that cannot be opened, the platform lock call itself failing -- raises
    ``errors.HeraldError`` naming ``lock_path``, matching every other
    structural-failure path in this package (AD-6), rather than leaking a
    raw ``OSError``."""
    could_not_lock = f"lock file {lock_path} could not be acquired"
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = lock_path.open("a+b")
    except OSError as exc:
        raise errors.HeraldError(f"{could_not_lock}: {exc}") from exc
    try:
        try:
            _acquire(fh)
        except OSError as exc:
            raise errors.HeraldError(f"{could_not_lock}: {exc}") from exc
        try:
            yield
        finally:
            _release(fh)
    finally:
        fh.close()
