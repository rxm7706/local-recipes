"""pyforge.core.atomic_write -- the ONE tmp-file-then-``os.replace`` atomic
write primitive (Story 14.2, SPEC-pyforge-core CAP-2).

Twenty real copies of this pattern were hand-written across six sibling
stations (herald 6, atlas 5, marshal 3, steward 2, scribe 1, warden 3 --
three separate ``write_{kev,endoflife,epss}_cache`` functions in one file)
before this story, each self-aware ("mirrors ``state.write``") but none
sharing code, using three different naming philosophies (pid+thread-id, a
fixed non-unique ``.tmp`` suffix, or ``mkstemp``). This module is the single
implementation every one of those copies now delegates to.

``atomic_write`` is a CALLBACK primitive: ``write_fn(tmp_path)`` populates an
unopened ``mkstemp``-created temp file living in ``path``'s own directory --
never a pre-built bytes/text blob. This subsumes both a pandas
``DataFrame.to_parquet(tmp_path)`` (binary, written by pandas itself) and a
plain text write as one-line wrappers (``atomic_write_bytes``/
``atomic_write_text`` below) without needing a second call shape.

Guarantees:

* The parent directory is created (``mkdir(parents=True, exist_ok=True)``)
  before the temp file, unconditionally -- every call site gets this for
  free, including the two source copies that previously omitted it.
* The temp file is named by ``tempfile.mkstemp`` (``O_EXCL``-backed,
  collision-free even across pid recycling -- strictly safer than every
  hand-rolled pid+thread-id or fixed-suffix scheme it replaces).
* On success, ``os.replace(tmp_path, path)`` -- atomic on the same
  filesystem; a reader never observes a partially written file.
* On ANY failure (from ``write_fn``, from the mode chmod, or from
  ``os.replace`` itself), the temp file is removed best-effort and the
  original exception re-raises UNCHANGED -- no new exception type, so every
  call site's own wrapping (``HeraldError``/``FsError``/
  ``HarnessPolicyWriteError``/``PolicyIOError``, or a raw propagate) keeps
  working exactly as it did before.
* ``mode: int | None`` -- when given, ``os.chmod(tmp_path, mode)`` runs
  BEFORE the replace, so the final file carries exactly ``mode``'s bits.
  When OMITTED (``mode=None``, the default), the final file's permission
  bits are made umask-respecting rather than left at ``mkstemp``'s private
  ``0o600`` -- see ``_umask_respecting_default_mode`` below. The one caller
  that needs an explicit override is ``herald/registry.py``, preserving a
  pre-existing tracked file's permission bits across a rewrite.
"""

from __future__ import annotations

import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path

# Review pass 2: the probe-and-restore pair below is a two-syscall critical
# section on the PROCESS-GLOBAL umask. Once centralized here, it runs on
# every `atomic_write` call that omits `mode=` -- 19 of the 20 migrated call
# sites (only `herald/registry.py` passes an explicit `mode=`), not the 0-1
# that used to touch `os.umask()` before this story
# -- so an unguarded interleaving (`T1:umask(0), T2:umask(0), T1:restore(old),
# T2:restore(0)`) can leave the umask PERMANENTLY corrupted at 0 for the rest
# of the process's lifetime. This lock serializes the critical section across
# threads within this process; `grep -rn "os\.umask" src/shared/packages`
# confirms no other module anywhere in the fleet calls `os.umask()`, so this
# is sufficient to close the race for every real caller (it cannot guard a
# hypothetical third-party library calling `os.umask()` outside this lock --
# POSIX offers no primitive against that regardless of implementation).
_UMASK_PROBE_LOCK = threading.Lock()


def _umask_respecting_default_mode() -> int:
    """Compute the permission bits ``os.open(path, ..., 0o666)`` (or
    ``Path.write_text``/``Path.open("w")``, which the kernel handles the
    same way) would have produced under the CURRENT process umask.

    There is no safe getter-only way to read the umask in POSIX -- the only
    API is ``os.umask(new)``, which sets it and returns the OLD value. This
    is the well-known, brief, single-probe idiom: set to 0 to learn the
    current value, then immediately restore it. The window is a few Python
    bytecodes wide and single-threaded-fast, but it IS process-global for
    its duration -- ``_UMASK_PROBE_LOCK`` (review pass 2) serializes it
    across threads so two concurrent callers can never interleave their
    probe and restore.
    """
    with _UMASK_PROBE_LOCK:
        current_umask = os.umask(0)
        os.umask(current_umask)
    return 0o666 & ~current_umask


def atomic_write(path: Path, write_fn: Callable[[Path], None], *, mode: int | None = None) -> None:
    """Atomically write ``path`` by calling ``write_fn`` on an unopened temp
    path in the same directory, then ``os.replace``-ing it into place.

    ``write_fn`` receives a ``Path`` that already exists (empty, mode 0600)
    and is expected to open/populate it itself (``tmp.write_text(...)``,
    ``tmp.write_bytes(...)``, ``frame.to_parquet(tmp)``, a manual
    ``tmp.open("w")`` + ``json.dump`` -- any of these). Any exception from
    ``write_fn``, from the ``mode`` chmod, or from ``os.replace`` removes the
    temp file (best-effort) and re-raises the SAME exception -- this
    function never introduces a new exception type.

    ``mode`` defaults to ``None``, which does NOT mean "leave mkstemp's
    private ``0o600`` alone" -- it means "compute a umask-respecting default
    internally" (see ``_umask_respecting_default_mode``), so every call site
    that never had to think about permissions before this extraction still
    doesn't have to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        os.close(handle)
        write_fn(tmp_path)
        effective_mode = mode if mode is not None else _umask_respecting_default_mode()
        os.chmod(tmp_path, effective_mode)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_bytes(path: Path, data: bytes, *, mode: int | None = None) -> None:
    """``atomic_write`` for a pre-built ``bytes`` payload."""

    def _write(tmp: Path) -> None:
        tmp.write_bytes(data)

    atomic_write(path, _write, mode=mode)


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8", mode: int | None = None) -> None:
    """``atomic_write`` for a pre-built ``str`` payload."""

    def _write(tmp: Path) -> None:
        tmp.write_text(text, encoding=encoding)

    atomic_write(path, _write, mode=mode)
