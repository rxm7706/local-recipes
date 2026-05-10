"""Meta: every v1 recipe.yaml must start with the yaml-language-server directive.

Without this comment, editors lose live JSON-schema validation against
prefix-dev/recipe-format and reviewers can miss schema-level errors. All
generator paths (grayskull/PyPI via the MCP server, recipe-generator.py
templates, rattler-build generate-recipe wrapper, npm scaffolder,
feedstock-migrator) are expected to emit it; this test catches drift if
a new generator path forgets, or a hand-edit drops it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
RECIPES_DIR = REPO_ROOT / "recipes"
EXPECTED_HEADER = (
    "# yaml-language-server: "
    "$schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json"
)


def _is_v1_recipe(path: Path) -> bool:
    """A recipe.yaml is v1 only if it declares ``schema_version:``.

    Some files under ``recipes/<name>/recipe.yaml`` are actually v0/jinja
    (``{% set ... %}`` style) misnamed as recipe.yaml — those are conda-build
    meta.yaml content and the yaml-language-server directive does not apply.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped.startswith("schema_version:")
    return False


def _all_v1_recipe_yamls() -> list[Path]:
    if not RECIPES_DIR.is_dir():
        return []
    return sorted(p for p in RECIPES_DIR.glob("*/recipe.yaml") if _is_v1_recipe(p))


@pytest.mark.parametrize(
    "recipe_path", _all_v1_recipe_yamls(), ids=lambda p: p.parent.name
)
def test_v1_recipe_yaml_has_schema_header(recipe_path: Path) -> None:
    """Every v1 recipes/<name>/recipe.yaml must begin with the yaml-language-server header.

    The header enables editor schema validation. New recipes must include it; the
    MCP grayskull path, recipe-generator.py templates, and feedstock-migrator
    auto-emit it. If this test fails, a generator path or hand-edit dropped it.
    Files that are v0/jinja style (``{% set %}``) are skipped because the
    directive is v1-only.
    """
    text = recipe_path.read_text(encoding="utf-8")
    first_line = text.splitlines()[0] if text else ""
    assert first_line == EXPECTED_HEADER, (
        f"{recipe_path.relative_to(REPO_ROOT)} is missing the yaml-language-server "
        f"schema header on line 1.\n  Expected: {EXPECTED_HEADER}\n  Got:      {first_line!r}"
    )
