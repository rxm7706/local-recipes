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
rather than hand-rolling a parent-walk. The existing copies are not
mass-migrated by this module's introduction — see CHANGELOG.md's Rule-2 retro
entry for the migration note. They are not merely duplicated, either: ~35
files under ``scripts/`` still carry an un-``.resolve()``d parent-walk, so a
large share of them is wrong by this module's own constraint. Migrate one
whenever you are already editing its file.
"""
from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path | None:
    """Return the monorepo root -- the nearest ancestor of this file that
    carries BOTH ``pixi.toml`` and a ``.claude/`` directory -- or ``None`` if no
    ancestor does (a symlink loop, or this module relocated outside any
    checkout).

    A marker walk, not a fixed-depth ``parents[N]``: this module is copied
    verbatim into the compiled CFE slices (``.claude/skills/cfe-<slice>/<ver>/
    <slice>/scripts/``, two levels deeper), where ``parents[4]`` landed on
    ``.claude/skills/`` and every consumer silently computed paths one level
    short -- the exact "known path-depth bug" the slice-2 equivalence harness
    pinned on ``gen_yml_reference.py``. Requiring both markers keeps the walk
    from stopping at a station package (``src/shared/packages/*`` carry a
    ``pixi.toml`` but no ``.claude/``); a nested worktree under
    ``.claude/worktrees/<x>/`` resolves to its own root, as before.

    Computed lazily, per call — never at import time — so a resolution
    failure surfaces only to a caller that actually calls this function, not
    as an import-time crash for every script that merely imports this module.

    **``None`` is a real return value, not a theoretical one: every caller
    must handle it.** It is never raised, so nothing downstream catches it
    for you — an unguarded ``get_data_dir() / "x"`` at module scope is a
    ``TypeError`` at import, which is the very crash the lazy contract exists
    to avoid. The four in-tree callers each handle it explicitly:
    ``recipe_optimizer.py`` falls back to its documented default,
    ``feedstock_context.py``/``feedstock_lookup.py`` disable their (optional)
    on-disk cache, and ``bootstrap_data.py`` exits with a diagnostic.
    """
    try:
        for candidate in Path(__file__).resolve().parents:
            if (candidate / "pixi.toml").is_file() and (candidate / ".claude").is_dir():
                return candidate
        return None
    except (IndexError, OSError):
        return None


def get_data_dir() -> Path | None:
    """Return the skill-scoped data directory: ``.claude/data/conda-forge-expert/``,
    or ``None`` if `get_repo_root()` could not resolve."""
    root = get_repo_root()
    return None if root is None else root / ".claude" / "data" / "conda-forge-expert"
