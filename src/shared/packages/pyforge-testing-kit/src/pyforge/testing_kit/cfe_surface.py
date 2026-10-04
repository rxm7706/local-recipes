"""The conda-forge-expert (CFE) surface, defined once beside ``branch_diff_guard`` (Story 83.19).

The same surface ``scripts/mason_cfe_surface_check.py`` scans: the CFE skill tree, its
scripts tree and the CFE MCP server. ``branch_diff_guard.unsanctioned_commits`` takes it as
``pathspec=CFE_GIT_PATHSPECS, changelog_path=CFE_CHANGELOG_PATH``.

Marshal's dispatch keeps a runtime mirror (``pyforge.marshal.core.dispatch_cfe_commit``)
because a production station never depends on this test-time kit; marshal's unit suite
fails when that mirror differs from the definitions here.
"""

from __future__ import annotations

CFE_CHANGELOG_PATH = ".claude/skills/conda-forge-expert/CHANGELOG.md"

CFE_SURFACE_PREFIXES: tuple[str, ...] = (
    ".claude/skills/conda-forge-expert/",
    ".claude/scripts/conda-forge-expert/",
)

CFE_SURFACE_FILES: frozenset[str] = frozenset({".claude/tools/conda_forge_server.py"})

# Git pathspecs covering the whole surface (``git log`` / ``git diff``).
CFE_GIT_PATHSPECS: tuple[str, ...] = (
    ".claude/skills/conda-forge-expert",
    ".claude/scripts/conda-forge-expert",
    ".claude/tools/conda_forge_server.py",
)


def is_cfe_surface_path(path: str) -> bool:
    """True when the repo-relative ``path`` is on the CFE surface."""
    normalized = path.replace("\\", "/")
    return normalized in CFE_SURFACE_FILES or normalized.startswith(CFE_SURFACE_PREFIXES)
