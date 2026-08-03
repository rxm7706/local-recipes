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
  ``FsError`` on any I/O failure.

Story 1.5's ``tier3_backlink`` step (``cli/init.py``) adds two more
primitives, ported from ``bmad-switch.ensure_tier3_backlink``:

- ``ensure_dir`` -- ``mkdir(parents=True, exist_ok=True)``: idempotent,
  raises ``FsError`` on failure.
- ``remove_empty_dir`` -- returns ``True`` (removed) for a real, empty
  directory, or ``False`` (left untouched) for a real, non-empty one, so
  the caller can tell a safe refusal (``MRS-INIT-005``) apart from a real
  I/O failure (``FsError`` -> ``MRS-INIT-004``) structurally rather than by
  string-matching a message (see the spec's Design Notes).

Story 1.6 (``marshal homes``, FR-4) adds ``resolve_path``: the realpath
primitive its Tier-3 isolation check needs to compare a home's local backlink
against the canonical store BY REALPATH rather than the raw (typically
relative) symlink target string ``read_symlink_target`` returns -- closing a
gap the raw-string comparison ``cli/init.py``'s own ``tier3_backlink`` step
still has (see that story's spec Design Notes for why the gap stays open
there). It also adds ``exists``: the occupancy probe ``marshal homes`` needs
to tell "genuinely nothing at this path" (benign absence) apart from "a real,
non-symlink file or directory occupies it" (a violation to name) at the two
symlink locations it checks -- ``is_dir`` alone cannot see a regular-file
occupant (review finding).

Story 1.7 (``marshal preflight``, AD-21) adds ``copy_file``: seeding an
adapter's gitignored config into a loop home needs REAL bytes, never a
symlink (Design Notes -- a symlinked ``.claude/settings.json`` would mean an
edit inside the home silently mutates the main checkout's copy), so this is
a distinct primitive from ``repoint_symlink_atomic`` rather than a second
call to it.

Story 3.1 (the run journal writer, AD-25/AD-28/AD-30) adds two more
primitives: ``append_line`` -- AD-30's one serialized append protocol, a
single ``os.write()`` on an ``O_APPEND``-opened descriptor with no buffered
stream held open, so two uncoordinated writers can never interleave a
partial line -- and ``create_dir_exclusive`` -- AD-25's ``mkdir``, exclusive
by definition, so a run-directory collision is a hard finding, never an
append.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FsPort(Protocol):
    def read_text(self, path: Path) -> str | None:
        """The file's UTF-8 text, or ``None`` if ``path`` does not exist.
        Raises ``FsError`` for any other read failure (e.g. a
        permission error, or ``path`` naming a directory)."""
        ...

    def write_text_atomic(self, path: Path, content: str) -> None:
        """Write ``content`` to ``path`` via a temp-file-then-``os.replace``
        sequence, creating parent directories as needed. Raises
        ``FsError`` on failure."""
        ...

    def read_symlink_target(self, path: Path) -> Path | None:
        """The raw target of the symlink at ``path``, or ``None`` if
        ``path`` does not exist or is not a symlink."""
        ...

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        """Atomically make ``path`` a symlink pointing at ``target``
        (temp-symlink-then-``os.replace``), creating parent directories as
        needed. Refuses (raises ``FsError``) if ``path`` exists and is
        a real file/directory rather than a symlink -- that would destroy
        real content instead of moving a pointer."""
        ...

    def is_dir(self, path: Path) -> bool:
        """``True`` if ``path`` exists and is a directory."""
        ...

    def exists(self, path: Path) -> bool:
        """``True`` if ``path`` exists in any non-symlink-aware sense
        (mirrors ``pathlib.Path.exists()``: follows a symlink, so a
        DANGLING symlink reports ``False``). Callers that need to
        distinguish a symlink from a real occupant must probe
        ``read_symlink_target`` first -- ``marshal homes``'s occupancy
        checks (Story 1.6) do exactly that, then use this to catch a real
        file OR directory squatting where a symlink belongs."""
        ...

    def ensure_dir(self, path: Path) -> None:
        """Create ``path`` (and any missing parents) as a directory if it
        does not already exist. Idempotent -- a no-op when ``path`` is
        already a directory. Raises ``FsError`` on any I/O failure."""
        ...

    def remove_empty_dir(self, path: Path) -> bool:
        """Remove ``path`` and return ``True`` if it is a real directory
        with zero entries. Returns ``False`` and leaves ``path`` untouched
        if it is a real directory containing entries -- a safe refusal, not
        a failure. Raises ``FsError`` on any other I/O failure (e.g. ``path``
        does not exist, is not a directory at all, or is a symlink -- even
        one pointing at an empty directory: removal refuses to operate
        through a link, so callers must check for a symlink first)."""
        ...

    def resolve_path(self, path: Path) -> Path:
        """The full realpath of ``path``: every symlink resolved, normalized
        to an absolute path (mirrors ``os.path.realpath``). Non-strict --
        ``path`` (or any component of it) need not exist; a target that
        doesn't fully exist still resolves as far as possible rather than
        raising, since a broken/dangling backlink is exactly the violation
        ``marshal homes``'s Tier-3 realpath check (Story 1.6, FR-4) needs to
        name, not an error to abort the whole command on. This includes a
        symlink LOOP and a permission-denied ancestor: confirmed live
        (CPython's ``Path.resolve(strict=False)`` swallows both and returns
        a best-effort path rather than raising -- review finding, this
        module previously overclaimed an ``FsError`` here) -- either
        degrades to a realpath that will not match the expected canonical
        target, so the caller's ordinary equality comparison still surfaces
        it as a mismatch finding rather than this method raising. ``FsError``
        is reserved for the same convention as every other ``FsPort``
        method, kept for defense in depth against a future/alternate
        resolver that DOES raise, but is not currently reachable via the
        two scenarios above."""
        ...

    def copy_file(self, src: Path, dst: Path) -> None:
        """Copy ``src`` to ``dst`` as REAL bytes (never a symlink), creating
        ``dst``'s parent directories as needed. No exists-guard baked in --
        unconditionally overwrites/creates ``dst``; the caller decides
        skip-vs-copy (AD-21, reconcile-then-act) BEFORE calling this, exactly
        like ``remove_empty_dir``'s split between "safe refusal" and this
        port's own I/O. Raises ``FsError`` on any failure (``src`` missing,
        naming a directory, or unreadable; ``dst``'s parent unwritable)."""
        ...

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        """AD-30's one serialized append protocol: a single ``os.write()``
        of ``(line + "\\n").encode("utf-8")`` on a descriptor opened
        ``O_WRONLY | O_APPEND | O_CREAT`` (mode ``0o666``, matching
        ``_tmp_sibling``'s existing mode), ``fsync``ed only when
        ``fsync=True``, then closed -- no buffered stream (``open()``/
        ``fdopen()``) is ever held open across appends, so two uncoordinated
        writers can never interleave a partial line. Does **not** create
        ``path``'s parent directory (unlike ``write_text_atomic``): the run
        directory's existence is itself a meaningful precondition (see
        ``create_dir_exclusive`` below), so a missing parent is a real
        ``FsError``, not an auto-create. Raises ``FsError`` if ``line``
        contains an embedded newline, if the OS reports a short write (never
        silently retried -- see the implementation's own docstring for why),
        or on any other I/O failure. The concurrency guarantee is a
        LOCAL-filesystem property of ``O_APPEND``; not guaranteed atomic on
        every network filesystem."""
        ...

    def create_dir_exclusive(self, path: Path) -> None:
        """A bare ``path.mkdir()`` (no ``parents=True``, no ``exist_ok``) --
        AD-25's ``mkdir``, not ``O_EXCL``: directories are already exclusive
        via ``mkdir(2)``'s own ``EEXIST``. Raises
        ``DirectoryAlreadyExistsError`` (a distinguishable ``FsError``
        subtype, defined on ``adapters.fs_local``) when ``path`` already
        exists -- a collision is a hard finding, never an append, and
        ``path`` is left untouched. Any other ``OSError`` raises plain
        ``FsError``."""
        ...
