"""Meta: SKILL.md, pixi.toml, and scripts/ stay in sync.

Catches doc drift — when a script is renamed/removed but SKILL.md still
references it, or when SKILL.md mentions a tool that doesn't exist.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
PROJECT_ROOT = Path(
    "/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes"
)
PIXI_TOML = PROJECT_ROOT / "pixi.toml"


@pytest.mark.meta
class TestSkillMdConsistency:
    def test_skill_md_exists(self):
        assert SKILL_MD.exists()

    def test_skill_md_no_dead_rattler_lint_reference(self):
        """Fix #1 retired `rattler-build lint` — SKILL.md should not
        prescribe it as a workflow step (the description in passing is OK)."""
        content = SKILL_MD.read_text()
        # The script no longer uses `rattler-build lint`. SKILL.md may still
        # describe what validate_recipe does conceptually — that's fine.
        # We only fail if SKILL.md instructs to *call* the dead command.
        forbidden = "Run `rattler-build lint`"
        assert forbidden.lower() not in content.lower(), (
            f"SKILL.md still instructs the user to call the retired "
            f"'rattler-build lint' subcommand."
        )

    def test_skill_md_lists_existing_scripts_only(self):
        """Every `<script_name>.py` mentioned in SKILL.md must exist either in
        scripts/ (skill-local) or in the project root (e.g. build-locally.py)."""
        import re

        content = SKILL_MD.read_text()
        scripts_dir = SKILL_DIR / "scripts"
        existing = {p.name for p in scripts_dir.glob("*.py")}

        # Project-level scripts that SKILL.md is allowed to reference
        project_level = {
            "build-locally.py",   # conda-forge/staged-recipes top-level
            "setup.py",
            "script.py",          # rare, generic
        }

        referenced = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_-]*\.py)\b", content))

        unknown = referenced - existing - project_level
        assert not unknown, (
            f"SKILL.md references scripts that don't exist in scripts/ "
            f"and aren't recognised project-level scripts: {unknown}"
        )

    def test_pixi_toml_tasks_reference_existing_scripts(self):
        if not PIXI_TOML.exists():
            pytest.skip("pixi.toml not found at expected location")
        content = PIXI_TOML.read_text()
        scripts_dir = SKILL_DIR / "scripts"
        existing = {p.name for p in scripts_dir.glob("*.py")}

        import re
        # Match `python .claude/skills/conda-forge-expert/scripts/<name>.py`
        # and just `<name>.py` references inside [feature.local-recipes.tasks]
        referenced = set(re.findall(
            r"conda-forge-expert/scripts/([A-Za-z_][A-Za-z0-9_-]*\.py)",
            content,
        ))
        unknown = referenced - existing
        assert not unknown, (
            f"pixi.toml tasks reference scripts that don't exist: {unknown}"
        )
