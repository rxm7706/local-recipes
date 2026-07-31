"""``LocalFs`` -- the sole implementation of ``ports.FsPort`` (Story 1.4,
AD-4/AD-11), over ``os``/``pathlib``. Every write is
temp-path-then-``os.replace`` (atomic on the same filesystem), mirroring
``adapters/harness_bmadloop.py::write_policy_toml``'s and
``cli/config.py::materialize``'s own idiom, generalized from
``scripts/bmad-switch``'s hardcoded ``_bmad-output/*`` paths to plain
``Path`` arguments.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path


class FsError(Exception):
    """Raised by any ``LocalFs`` method on I/O failure -- reads and writes
    alike (review finding: the class began life as ``FsWriteError``, a
    misnomer once ``read_text``/``read_symlink_target`` raised it too): an
    unreadable or undecodable path (other than simple absence), an
    unwritable parent directory, or a ``repoint_symlink_atomic`` target that
    is a real file/directory rather than a symlink. Never lets a raw
    ``OSError`` or ``UnicodeDecodeError`` escape this module."""


def _tmp_sibling(path: Path) -> Path:
    """A pid+thread-id-suffixed temp path beside ``path``: no two LIVE
    writers can ever share this name (same pid + same native thread id is
    the same thread). A stale leftover CAN reuse the name after pid
    recycling, so ``write_text_atomic`` unlinks any pre-existing file at
    this path before its ``O_EXCL`` open -- safe precisely because any
    file already there cannot belong to a live writer."""
    return path.with_name(f".{path.name}.tmp.pid{os.getpid()}.t{threading.get_native_id()}")


class LocalFs:
    """``ports.FsPort``'s sole implementation."""

    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        # UnicodeDecodeError is a ValueError, not an OSError -- without the
        # explicit catch, a corrupt (non-UTF-8) marker file would escape as
        # a raw traceback instead of an envelope finding (review finding).
        except (OSError, UnicodeDecodeError) as exc:
            raise FsError(f"cannot read {path}: {exc}") from exc

    def write_text_atomic(self, path: Path, content: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = _tmp_sibling(path)
            # A stale leftover from a crashed, pid-recycled run would make
            # the O_EXCL open below fail forever (review finding) -- any
            # file already at this name is guaranteed stale, so clear it.
            tmp_path.unlink(missing_ok=True)
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(content)
                os.replace(tmp_path, path)
            except BaseException:
                tmp_path.unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise FsError(f"cannot write {path}: {exc}") from exc

    def read_symlink_target(self, path: Path) -> Path | None:
        # is_symlink() sits INSIDE the try: on Python 3.12 (this package's
        # floor) pathlib propagates a PermissionError from an unsearchable
        # ancestor instead of returning False (review finding).
        try:
            if not path.is_symlink():
                return None
            return Path(os.readlink(path))
        except OSError as exc:
            raise FsError(f"cannot read symlink {path}: {exc}") from exc

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        # Mirrors scripts/bmad-switch's repoint_links: refuse to clobber a
        # real (non-symlink) file/directory -- that would destroy content
        # rather than move a pointer.
        if path.exists() and not path.is_symlink():
            raise FsError(
                f"{path} is a real file/directory, not a symlink -- refusing to replace it"
            )
        tmp_path = _tmp_sibling(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if tmp_path.is_symlink() or tmp_path.exists():
                tmp_path.unlink()
            os.symlink(target, tmp_path)
            os.replace(tmp_path, path)  # atomic; replaces any prior symlink in place
        except OSError as exc:
            if tmp_path.is_symlink():
                tmp_path.unlink(missing_ok=True)
            raise FsError(f"cannot repoint symlink {path} -> {target}: {exc}") from exc

    def is_dir(self, path: Path) -> bool:
        # Suppress OSError to False (Python 3.13+ pathlib semantics,
        # backported for the 3.12 floor): an unreadable ancestor must report
        # "not a usable directory" through the envelope, not crash raw
        # (review finding). Callers treat False as the safe answer.
        try:
            return path.is_dir()
        except OSError:
            return False
