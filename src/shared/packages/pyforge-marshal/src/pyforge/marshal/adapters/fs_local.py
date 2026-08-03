"""``LocalFs`` -- the sole implementation of ``ports.FsPort`` (Story 1.4,
AD-4/AD-11), over ``os``/``pathlib``. Every write is
temp-path-then-``os.replace`` (atomic on the same filesystem), mirroring
``adapters/harness_bmadloop.py::write_policy_toml``'s and
``cli/config.py::materialize``'s own idiom, generalized from
``scripts/bmad-switch``'s hardcoded ``_bmad-output/*`` paths to plain
``Path`` arguments.

Story 1.5 adds ``ensure_dir``/``remove_empty_dir``, porting
``bmad-switch.ensure_tier3_backlink``'s ``mkdir(parents=True,
exist_ok=True)``/empty-dir-removal primitives the same way.

Story 1.6 adds ``resolve_path`` -- a thin wrapper over
``pathlib.Path.resolve()`` (non-strict by default, so it never requires
``path`` to exist), with the same "wrap OSError into FsError" convention as
every other method here -- and ``exists``, a thin wrapper over
``pathlib.Path.exists()`` with the same suppress-OSError-to-``False``
convention as ``is_dir``.

Story 1.7 adds ``copy_file`` -- real-bytes ``shutil.copy2`` (preserves
mtime/permissions), not the temp-file-then-``os.replace`` dance the other
writers here use: seeding a gitignored adapter config is a plain
copy-when-absent (the caller already checked absence), not a repoint of a
name already in use by a live reader.

Story 2.6 adds ``write_redacted_atomic`` -- ``ports.record.RecordPort``'s
sole implementation (AD-34). It delegates entirely to ``write_text_atomic``:
no new write mechanics, only a type boundary that accepts a
``core.egress.Redacted`` payload instead of a bare ``str``.

Story 3.1 adds ``append_line``/``create_dir_exclusive`` -- AD-30's/AD-25's
physical protocols, both genuinely new write mechanics (a raw ``os.write()``
on an ``O_APPEND`` descriptor; a bare ``mkdir()``), unlike every prior
method added here since Story 1.4, which all delegate to or vary the same
temp-file-then-``os.replace`` idiom. It also adds
``DirectoryAlreadyExistsError``, a distinguishable ``FsError`` subtype for
``create_dir_exclusive``'s collision case.
"""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path

from ..core.egress import Redacted


class FsError(Exception):
    """Raised by any ``LocalFs`` method on I/O failure -- reads and writes
    alike (review finding: the class began life as ``FsWriteError``, a
    misnomer once ``read_text``/``read_symlink_target`` raised it too): an
    unreadable or undecodable path (other than simple absence), an
    unwritable parent directory, or a ``repoint_symlink_atomic`` target that
    is a real file/directory rather than a symlink. Never lets a raw
    ``OSError`` or ``UnicodeDecodeError`` escape this module."""


class DirectoryAlreadyExistsError(FsError):
    """Raised by ``create_dir_exclusive`` when ``path`` already exists
    (Story 3.1, AD-25): ``mkdir`` is exclusive by definition, so a run
    directory collision is a hard finding, never an append. A distinguishable
    ``FsError`` subtype -- not folded into the generic message -- so a
    caller can structurally tell a collision apart from any other I/O
    failure, matching ``remove_empty_dir``'s own "safe refusal vs. real
    failure" split."""


def _tmp_sibling(path: Path) -> Path:
    """A pid+thread-id-suffixed temp path beside ``path``: no two LIVE
    writers can ever share this name (same pid + same native thread id is
    the same thread). A stale leftover CAN reuse the name after pid
    recycling, so ``write_text_atomic`` unlinks any pre-existing file at
    this path before its ``O_EXCL`` open -- safe precisely because any
    file already there cannot belong to a live writer."""
    return path.with_name(f".{path.name}.tmp.pid{os.getpid()}.t{threading.get_native_id()}")


class LocalFs:
    """Sole implementation of BOTH ``ports.FsPort`` and -- since Story 2.6 --
    the egress-classified ``ports.RecordPort`` (``write_redacted_atomic``).

    That dual role is deliberate (one atomic-write mechanism, two typed
    entry points) but it means the AD-34 egress boundary on this class is
    exactly one method call wide: ``write_text_atomic`` reaches the same
    durable sink accepting a bare ``str``. Tracked in ``deferred-work.md``
    (the ``FsPort``/``VcsPort`` classification entry); named here because
    this docstring is where a reader learns what the adapter implements."""

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
        tmp_path = _tmp_sibling(path)
        try:
            # Mirrors scripts/bmad-switch's repoint_links: refuse to clobber
            # a real (non-symlink) file/directory -- that would destroy
            # content rather than move a pointer. is_symlink() probes first
            # (lstat, never follows the link), and BOTH probes sit inside
            # the try: on Python 3.12 either raises PermissionError from an
            # unsearchable ancestor, and exists() additionally follows a
            # symlink into its (possibly unreadable) target -- previously
            # the guard ran before the try and escaped as a raw traceback
            # (review finding).
            if not path.is_symlink() and path.exists():
                raise FsError(
                    f"{path} is a real file/directory, not a symlink -- refusing to replace it"
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            if tmp_path.is_symlink() or tmp_path.exists():
                tmp_path.unlink()
            os.symlink(target, tmp_path)
            os.replace(tmp_path, path)  # atomic; replaces any prior symlink in place
        except OSError as exc:
            # The cleanup probe itself must not raise a second, raw
            # exception out of this handler (same 3.12 pathlib class as
            # above); tmp_path is this process's private name, so an
            # unconditional unlink is safe.
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
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

    def ensure_dir(self, path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FsError(f"cannot create directory {path}: {exc}") from exc

    def exists(self, path: Path) -> bool:
        # Same suppress-OSError-to-False convention as is_dir above: an
        # unreadable ancestor reports "not usably present", never a raw
        # traceback. Follows symlinks (pathlib semantics) -- callers probe
        # read_symlink_target first; see the port docstring.
        try:
            return path.exists()
        except OSError:
            return False

    def resolve_path(self, path: Path) -> Path:
        # strict=False (the default): a broken/dangling target is exactly
        # the violation marshal homes' Tier-3 check exists to name, not an
        # error to raise on -- see this method's own port docstring.
        try:
            return path.resolve()
        except OSError as exc:
            raise FsError(f"cannot resolve {path}: {exc}") from exc

    def remove_empty_dir(self, path: Path) -> bool:
        # Mirrors scripts/bmad-switch's ensure_tier3_backlink: `any(iterdir())`
        # distinguishes "real but empty" (removed, returns True) from "real
        # and occupied" (left alone, returns False -- not raised, so the
        # caller can tell this safe refusal apart from a real I/O failure
        # structurally, rather than by matching a message string; see
        # ports/fs.py's docstring).
        try:
            if any(path.iterdir()):
                return False
            path.rmdir()
            return True
        except OSError as exc:
            raise FsError(f"cannot remove directory {path}: {exc}") from exc

    def copy_file(self, src: Path, dst: Path) -> None:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except OSError as exc:
            raise FsError(f"cannot copy {src} to {dst}: {exc}") from exc

    def write_redacted_atomic(self, path: Path, payload: Redacted) -> None:
        """``RecordPort``'s sole implementation (Story 2.6): delegates
        entirely to ``write_text_atomic`` -- the same atomic write; the
        only difference is the accepted TYPE (``Redacted``, never a bare
        ``str``), enforced structurally by ``ports/record.py``'s own
        annotation and the AD-34 meta-test. Raises ``TypeError`` if
        ``payload`` is not a ``Redacted`` instance (a contract violation --
        review finding, verified live: without this check, a caller passing
        e.g. a bare ``str`` or ``None`` crashed with a raw
        ``AttributeError`` on ``payload.text``, not the ``FsError``
        contract this method's own docstring promised). ``path`` is guarded
        the same way for the same reason (follow-up review finding, verified
        live: the original guarded only one of the two parameters, so a
        ``str`` path still escaped as ``AttributeError: 'str' object has no
        attribute 'parent'``). A ``Path`` with no file name (``Path("/")``,
        ``Path(".")``) raises ``FsError`` (follow-up review finding, verified
        live: ``_tmp_sibling`` raised its own ``ValueError: PosixPath('/')
        has an empty name``, which ``write_text_atomic``'s ``except OSError``
        does not catch, so it escaped both failure modes this method and
        ``ports/record.py`` document). Otherwise raises ``FsError`` on
        failure, identical to ``write_text_atomic``."""
        if not isinstance(path, Path):
            raise TypeError(f"path must be a Path, got {path!r}")
        if not isinstance(payload, Redacted):
            # The TYPE only, never the value: a `Redacted` is safe to print
            # but a wrongly-typed payload is exactly the unredacted object
            # this port exists to refuse, and an exception message escapes as
            # a raw traceback (`cli/main.py` catches only SystemExit /
            # KeyboardInterrupt) into the harness log. Review finding.
            raise TypeError(
                f"payload must be a Redacted instance, got {type(payload).__name__}"
            )
        if not path.name:
            raise FsError(f"cannot write {path}: path has no file name")
        self.write_text_atomic(path, payload.text)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        """AD-30's one serialized append protocol (Story 3.1): a single
        ``os.write()`` of ``line``'s UTF-8 bytes plus a trailing newline, on
        a descriptor opened ``O_WRONLY | O_APPEND | O_CREAT`` (mode
        ``0o666``, matching ``_tmp_sibling``'s existing mode), ``fsync``ed
        only when ``fsync=True``, then closed -- no buffered stream
        (``open()``/``fdopen()``) is held open across the call, so two
        uncoordinated writers targeting the same path can never interleave a
        partial line. Does NOT create ``path``'s parent directory (unlike
        ``write_text_atomic``): a missing run directory is a real
        precondition failure here, not something to auto-create around (see
        ``create_dir_exclusive``).

        Raises ``FsError`` if ``line`` contains an embedded newline (review
        finding: this primitive's entire contract is "one physical line per
        call" -- a caller-supplied string that already contains ``\\n``
        would silently split into multiple physical lines with no error) or
        if the OS reports a short write (review finding: POSIX permits
        ``write()`` to consume fewer bytes than requested even for a regular
        file; retrying the remainder would risk a second, unretried writer's
        complete line landing in between the two partial writes of this
        call, which is worse than failing loudly -- so a short write is
        surfaced as a hard failure instead, never silently completed or
        silently truncated).

        This method's concurrency guarantee is a LOCAL-filesystem property
        of ``O_APPEND`` (POSIX write(2)); it is not guaranteed atomic on
        every network filesystem (e.g. classic NFS), where two writers can
        still interleave. Marshal's canonical Tier-3 store is a local path
        on the host running the loop home (review finding: this caveat was
        previously undocumented)."""
        if "\n" in line:
            raise FsError(f"cannot append to {path}: line must not contain an embedded newline")
        try:
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o666)
            try:
                data = (line + "\n").encode("utf-8")
                written = os.write(fd, data)
                if written != len(data):
                    raise OSError(
                        f"short write: wrote {written} of {len(data)} bytes -- "
                        "never retried (see this method's own docstring)"
                    )
                if fsync:
                    os.fsync(fd)
            finally:
                os.close(fd)
        except OSError as exc:
            raise FsError(f"cannot append to {path}: {exc}") from exc

    def create_dir_exclusive(self, path: Path) -> None:
        """AD-25's ``mkdir``, not ``O_EXCL`` (Story 3.1, F-31): a bare
        ``path.mkdir()`` with no ``parents=True``/``exist_ok`` --
        ``mkdir(2)`` already fails ``EEXIST``. Raises
        ``DirectoryAlreadyExistsError`` when ``path`` already exists,
        leaving it untouched; any other ``OSError`` raises plain
        ``FsError``."""
        try:
            path.mkdir()
        except FileExistsError as exc:
            raise DirectoryAlreadyExistsError(f"{path} already exists") from exc
        except OSError as exc:
            raise FsError(f"cannot create directory {path}: {exc}") from exc
