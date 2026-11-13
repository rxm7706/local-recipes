"""Marshal's forge repository is the root of record's (Story 115.4, CAP-208).

``pyforge.cutover_root`` names the root of record, and the forge repository
marshal addresses -- ``marshal land``, the dispatch landing, ``deploy
batch-pr`` and ``marshal watch`` -- is that root's. This module is the one
place marshal reads it: ``core/`` stays pure (AD-4), so the read lives here,
and the slug table stays core's constant (``pyforge.core.cutover_root``,
spec-pyforge-core CAP-13); marshal holds no repository slug of its own.

The slug is read at each use, never cached at import, so a flag flip moves
the next call. A malformed flag tree or an unknown root is the forge port's
own :class:`ForgeCommandError`, so each site reports it through the code it
already uses for a forge it cannot reach (MRS-DISP-018, MRS-DEPLOY-014,
MRS-WATCH-004); no finding code is added. With no tree in reach the answer is
core's default root.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.cutover_root import CutoverRootError, root_of_record

from ..ports.forge import ForgeCommandError


def forge_repo(flags_path: Path | str | None = None) -> str:
    """The root of record's forge repository slug (``owner/name``).

    ``flags_path`` is passed to :func:`root_of_record` as is: ``None`` finds the
    tree through ``PYFORGE_FLAGS_PATH`` and the walk-up from the working
    directory, and answers the default root when none is in reach.
    """
    try:
        return root_of_record(flags_path).forge_slug
    except CutoverRootError as exc:
        raise ForgeCommandError(f"cannot read the root of record's forge repository: {exc}") from exc
