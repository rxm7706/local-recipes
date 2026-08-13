"""pyforge.core.atomic_write -- the ONE tmp-file-then-``os.replace`` atomic
write primitive (Story 14.2, SPEC-pyforge-core CAP-2).

Eighteen real copies of this pattern were hand-written across six sibling
stations (herald 6, atlas 5, marshal 3, steward 2, scribe 1, warden 1) before
this story, each self-aware ("mirrors ``state.write``") but none sharing
code, using three different naming philosophies (pid+thread-id, a fixed
non-unique ``.tmp`` suffix, or ``mkstemp``). This module is the single
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
from collections.abc import Callable
from pathlib import Path


def _umask_respecting_default_mode() -> int:
    """Compute the permission bits ``os.open(path, ..., 0o666)`` (or
    ``Path.write_text``/``Path.open("w")``, which the kernel handles the
    same way) would have produced under the CURRENT process umask.

    There is no safe getter-only way to read the umask in POSIX -- the only
    API is ``os.umask(new)``, which sets it and returns the OLD value. This
    is the well-known, brief, single-probe idiom: set to 0 to learn the
    current value, then immediately restore it. The window is a few Python
    bytecodes wide and single-threaded-fast, but note it IS process-global
    for its duration (mirrors the standard library's own recommended
    pattern for this exact problem).
    """
    current_umask = os.umask(0)
    os.umask(current_umask)
    return 0o666 & ~current_umask


def atomic_write(
    path: Path, write_fn: Callable[[Path], None], *, mode: int | None = None
) -> None:
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
    atomic_write(path, lambda tmp: tmp.write_bytes(data), mode=mode)


def atomic_write_text(
    path: Path, text: str, *, encoding: str = "utf-8", mode: int | None = None
) -> None:
    """``atomic_write`` for a pre-built ``str`` payload."""
    atomic_write(path, lambda tmp: tmp.write_text(text, encoding=encoding), mode=mode)
