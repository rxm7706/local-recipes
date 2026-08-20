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

# .claude/skills/conda-forge-expert/scripts/_paths.py -> repo root (4 levels up)
_REPO_ROOT = Path(__file__).resolve().parents[4]


def get_repo_root() -> Path:
    """Return the monorepo root (parent of ``.claude/``)."""
    return _REPO_ROOT


def get_data_dir() -> Path:
    """Return the skill-scoped data directory: ``.claude/data/conda-forge-expert/``."""
    return _REPO_ROOT / ".claude" / "data" / "conda-forge-expert"
