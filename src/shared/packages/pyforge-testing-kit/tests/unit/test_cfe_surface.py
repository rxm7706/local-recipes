"""Unit tests for ``pyforge.testing_kit.cfe_surface`` (Story 83.19)."""

import pytest

from pyforge.testing_kit.cfe_surface import (
    CFE_CHANGELOG_PATH,
    CFE_GIT_PATHSPECS,
    CFE_SURFACE_FILES,
    CFE_SURFACE_PREFIXES,
    is_cfe_surface_path,
)


@pytest.mark.parametrize(
    ("path", "on_surface"),
    [
        (".claude/skills/conda-forge-expert/SKILL.md", True),
        (".claude/skills/conda-forge-expert/CHANGELOG.md", True),
        (".claude/scripts/conda-forge-expert/foo.sh", True),
        (".claude/tools/conda_forge_server.py", True),
        (".claude\\skills\\conda-forge-expert\\SKILL.md", True),
        (".claude/skills/conda-forge-expert-other/SKILL.md", False),
        (".claude/tools/conda_forge_server.py.bak", False),
        ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/foo.py", False),
    ],
)
def test_is_cfe_surface_path(path: str, on_surface: bool) -> None:
    assert is_cfe_surface_path(path) is on_surface


def test_the_git_pathspecs_cover_exactly_the_classified_surface() -> None:
    # A pathspec a guard passes to git and the prefix/file classifier dispatch uses must name
    # the same surface, or a commit could be excluded by one and missed by the other.
    assert set(CFE_GIT_PATHSPECS) == {p.rstrip("/") for p in CFE_SURFACE_PREFIXES} | CFE_SURFACE_FILES
    assert CFE_CHANGELOG_PATH.startswith(CFE_SURFACE_PREFIXES[0])
