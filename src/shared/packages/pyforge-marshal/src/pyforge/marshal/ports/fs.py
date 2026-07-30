"""``FsPort`` -- the filesystem seam ``cli/init.py`` depends on (Story 1.4,
architecture spine AD-11). A Protocol definition only (Structural Seed:
``ports/`` declares shapes, never implementations); implemented solely by
``adapters/fs_local.py`` (AD-4). Not an egress port: every path stays inside
the local filesystem.

Five methods, each a direct port of one piece of ``scripts/bmad-switch``'s
marker/symlink primitives (the design reference named by this story's
spec), generalized from that script's hardcoded ``_bmad-output/*`` paths to
plain ``Path`` arguments so ``cli/init.py`` can drive them against a
provisioned loop home instead of the repo root ``bmad-switch`` assumes:

- ``read_text``/``is_dir`` -- read-only probes (mirrors ``read_marker`` and
  the script's own ``.is_dir()`` checks); ``read_text`` returns ``None``
  rather than raising when the path is absent, matching
  ``bmad-switch.read_marker``'s own "missing file -> None" contract.
- ``read_symlink_target`` -- mirrors ``read_link_slugs``'s
  ``os.readlink``: returns the raw (typically relative) target, or ``None``
  if ``path`` is not a symlink.
- ``write_text_atomic``/``repoint_symlink_atomic`` -- the two writes, both
  temp-file/temp-link-then-``os.replace`` (mirrors ``cli/config.py``'s
  ``materialize``/``adapters/harness_bmadloop.py``'s own atomic-write idiom,
  and ``bmad-switch.repoint_links``'s identical tmp-symlink dance). Raises
  ``FsWriteError`` on any I/O failure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FsPort(Protocol):
    def read_text(self, path: Path) -> str | None:
        """The file's UTF-8 text, or ``None`` if ``path`` does not exist.
        Raises ``FsWriteError`` for any other read failure (e.g. a
        permission error, or ``path`` naming a directory)."""
        ...

    def write_text_atomic(self, path: Path, content: str) -> None:
        """Write ``content`` to ``path`` via a temp-file-then-``os.replace``
        sequence, creating parent directories as needed. Raises
        ``FsWriteError`` on failure."""
        ...

    def read_symlink_target(self, path: Path) -> Path | None:
        """The raw target of the symlink at ``path``, or ``None`` if
        ``path`` does not exist or is not a symlink."""
        ...

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        """Atomically make ``path`` a symlink pointing at ``target``
        (temp-symlink-then-``os.replace``), creating parent directories as
        needed. Refuses (raises ``FsWriteError``) if ``path`` exists and is
        a real file/directory rather than a symlink -- that would destroy
        real content instead of moving a pointer."""
        ...

    def is_dir(self, path: Path) -> bool:
        """``True`` if ``path`` exists and is a directory."""
        ...
