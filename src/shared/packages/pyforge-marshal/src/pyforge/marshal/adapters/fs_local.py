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


class FsWriteError(Exception):
    """Raised by any ``LocalFs`` method on I/O failure: an unreadable path
    (other than simple absence), an unwritable parent directory, or a
    ``repoint_symlink_atomic`` target that is a real file/directory rather
    than a symlink. Never lets a raw ``OSError`` escape this module."""


def _tmp_sibling(path: Path) -> Path:
    """A pid+thread-id-suffixed temp path beside ``path`` -- the same
    collision-safety reasoning as ``cli/config.py::materialize``'s own temp
    file: no two live writers can ever share this name, and a stale leftover
    from an earlier (differently-pid'd) run never collides with it."""
    return path.with_name(f".{path.name}.tmp.pid{os.getpid()}.t{threading.get_native_id()}")


class LocalFs:
    """``ports.FsPort``'s sole implementation."""

    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise FsWriteError(f"cannot read {path}: {exc}") from exc

    def write_text_atomic(self, path: Path, content: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = _tmp_sibling(path)
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(content)
                os.replace(tmp_path, path)
            except BaseException:
                tmp_path.unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise FsWriteError(f"cannot write {path}: {exc}") from exc

    def read_symlink_target(self, path: Path) -> Path | None:
        if not path.is_symlink():
            return None
        try:
            return Path(os.readlink(path))
        except OSError as exc:
            raise FsWriteError(f"cannot read symlink {path}: {exc}") from exc

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        # Mirrors scripts/bmad-switch's repoint_links: refuse to clobber a
        # real (non-symlink) file/directory -- that would destroy content
        # rather than move a pointer.
        if path.exists() and not path.is_symlink():
            raise FsWriteError(
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
            raise FsWriteError(f"cannot repoint symlink {path} -> {target}: {exc}") from exc

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()
