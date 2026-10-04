"""CFE surface path literals shared with ``branch_diff_guard`` and dispatch (Story 83.19).

Mirrors ``scripts/mason_cfe_surface_check.py``'s surface definition — one owner
for path classification, not a second copy in marshal."""

from __future__ import annotations

CFE_CHANGELOG_PATH = ".claude/skills/conda-forge-expert/CHANGELOG.md"

CFE_SURFACE_PREFIXES = (
    ".claude/skills/conda-forge-expert/",
    ".claude/scripts/conda-forge-expert/",
)

CFE_SURFACE_FILES = frozenset({".claude/tools/conda_forge_server.py"})

# Git pathspecs covering the whole surface (``git log`` / ``git diff``).
CFE_GIT_PATHSPECS: tuple[str, ...] = (
    ".claude/skills/conda-forge-expert",
    ".claude/scripts/conda-forge-expert",
    ".claude/tools/conda_forge_server.py",
)

# Meta-test guard default: skill tree only (historical pathspec string).
CFE_UNSANCTIONED_PATHSPEC = CFE_GIT_PATHSPECS[0]

RULE2_RETRO_SUBJECT_HINT = (
    "subject starts `retro:` or `retro(<scope>):` and the CFE CHANGELOG.md moves in the same commit"
)


def is_cfe_surface_path(path: str) -> bool:
    """True when ``path`` is repo-relative and on the CFE surface."""
    normalized = path.replace("\\", "/")
    return normalized in CFE_SURFACE_FILES or any(normalized.startswith(p) for p in CFE_SURFACE_PREFIXES)


def partition_paths(paths: tuple[str, ...] | list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split repo-relative paths into (non_cfe, cfe), each sorted."""
    non_cfe: list[str] = []
    cfe: list[str] = []
    for path in paths:
        if is_cfe_surface_path(path):
            cfe.append(path)
        else:
            non_cfe.append(path)
    return tuple(sorted(non_cfe)), tuple(sorted(cfe))
