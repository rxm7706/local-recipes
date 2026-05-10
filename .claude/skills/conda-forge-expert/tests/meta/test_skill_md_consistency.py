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
            "conda_forge_server.py",  # MCP server, lives at .claude/tools/
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
        wrapper_dir = SKILL_DIR.parent.parent / "scripts" / "conda-forge-expert"
        existing = {p.name for p in scripts_dir.glob("*.py")}
        existing |= {p.name for p in wrapper_dir.glob("*.py")}

        import re
        # Match either layout:
        #   .claude/skills/conda-forge-expert/scripts/<name>.py   (canonical)
        #   .claude/scripts/conda-forge-expert/<name>.py          (entrypoint wrapper, v6.0.0+)
        referenced = set(re.findall(
            r"(?:skills/conda-forge-expert/scripts|scripts/conda-forge-expert)/([A-Za-z_][A-Za-z0-9_-]*\.py)",
            content,
        ))
        unknown = referenced - existing
        assert not unknown, (
            f"pixi.toml tasks reference scripts that don't exist in either "
            f"the canonical scripts/ dir or the wrapper dir: {unknown}"
        )

    def test_every_user_script_has_a_pixi_task(self):
        """Every user-facing conda-forge-expert script must have a pixi-task
        wrapper. New scripts get added to the wrapper list (or the explicit
        no-task allow-list below if the CLI shape doesn't fit a task)."""
        if not PIXI_TOML.exists():
            pytest.skip("pixi.toml not found at expected location")

        # Scripts that intentionally have no pixi task. Add a NEW entry here
        # only with a written justification.
        no_task_allowlist = {
            # JSON-blob CLI argument doesn't fit the pixi-task metaphor:
            "recipe_editor.py",
            # Internal smoke check, not a user-facing CLI:
            "test-skill.py",
            # MCP-helper scripts: invoked by .claude/tools/conda_forge_server.py
            # (enrich_from_feedstock / get_feedstock_context / lookup_feedstock)
            # via subprocess; users hit them through the MCP tool, not directly.
            "feedstock_context.py",
            "feedstock_enrich.py",
            "feedstock_lookup.py",
        }

        content = PIXI_TOML.read_text()
        scripts_dir = SKILL_DIR / "scripts"
        # Underscore-prefixed scripts (e.g. _http.py, _sbom.py) are internal
        # helpers — never user-facing, never get pixi tasks.
        all_scripts = {
            p.name for p in scripts_dir.glob("*.py")
            if not p.name.startswith("_")
        }

        import re
        wrapped = set(re.findall(
            r"(?:skills/conda-forge-expert/scripts|scripts/conda-forge-expert)/([A-Za-z_][A-Za-z0-9_-]*\.py)",
            content,
        ))

        unwrapped = all_scripts - wrapped - no_task_allowlist
        assert not unwrapped, (
            "These conda-forge-expert scripts have no pixi-task wrapper "
            "and aren't in the no_task_allowlist. Either add a `[feature."
            "local-recipes.tasks.<name>]` entry to pixi.toml, or list them "
            "with a justification in the allow-list inside this test:\n"
            f"  {sorted(unwrapped)}"
        )
