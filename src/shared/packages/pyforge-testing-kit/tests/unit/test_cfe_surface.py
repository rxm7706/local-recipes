"""Unit tests for ``pyforge.testing_kit.cfe_surface`` (Story 83.19)."""

from pyforge.testing_kit.cfe_surface import (
    CFE_CHANGELOG_PATH,
    is_cfe_surface_path,
    partition_paths,
)


def test_is_cfe_surface_path_covers_skill_scripts_and_tool() -> None:
    assert is_cfe_surface_path(".claude/skills/conda-forge-expert/SKILL.md")
    assert is_cfe_surface_path(".claude/scripts/conda-forge-expert/foo.sh")
    assert is_cfe_surface_path(".claude/tools/conda_forge_server.py")
    assert not is_cfe_surface_path("src/shared/packages/pyforge-marshal/src/pyforge/marshal/foo.py")


def test_partition_paths_splits_cfe() -> None:
    non, cfe = partition_paths(
        (
            "README.md",
            ".claude/skills/conda-forge-expert/CHANGELOG.md",
        )
    )
    assert non == ("README.md",)
    assert cfe == (CFE_CHANGELOG_PATH,)
