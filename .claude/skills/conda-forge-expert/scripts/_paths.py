"""Canonical path resolution for conda-forge-expert scripts (Rule-2 retro, Story 5.5).

Every script needing the skill-scoped data directory or the monorepo root has
historically hand-rolled its own ``Path(__file__)`` parent-walk. As of this
retro, ~30 near-identical copies of a 1-line ``_get_data_dir()`` existed
across ``scripts/*.py``, in three subtly different shapes (with/without
``.resolve()``, and two files at the wrong depth entirely —
``feedstock_context.py``/``feedstock_lookup.py`` computed
``.claude/skills/data/conda-forge-expert`` instead of
``.claude/data/conda-forge-expert``, a live divergence that had already
produced a stray directory someone gitignored rather than root-caused).
``.resolve()`` matters: without it, a parent-walk over a symlinked
invocation path can land one directory off from the real location.

New scripts MUST import ``get_data_dir()`` / ``get_repo_root()`` from here
rather than hand-rolling a parent-walk. Existing correct-but-duplicated
copies are not mass-migrated by this module's introduction — see
CHANGELOG.md's Rule-2 retro entry for the migration note.
"""
from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path | None:
    """Return the monorepo root (parent of ``.claude/``), or ``None`` if this
    file's own location cannot be resolved to enough ancestor components (a
    symlink loop, or this module relocated somewhere with fewer than 4 real
    parents — see the module docstring's "future extraction" note).

    Computed lazily, per call — never at import time — so a resolution
    failure surfaces only to a caller that actually calls this function, not
    as an import-time crash for every script that merely imports this
    module (recipe_optimizer.py's own caller catches this; see its
    `_read_conda_forge_python_floor` docstring).
    """
    try:
        # .claude/skills/conda-forge-expert/scripts/_paths.py -> repo root (4 levels up)
        return Path(__file__).resolve().parents[4]
    except (IndexError, OSError):
        return None


def get_data_dir() -> Path | None:
    """Return the skill-scoped data directory: ``.claude/data/conda-forge-expert/``,
    or ``None`` if `get_repo_root()` could not resolve."""
    root = get_repo_root()
    return None if root is None else root / ".claude" / "data" / "conda-forge-expert"
