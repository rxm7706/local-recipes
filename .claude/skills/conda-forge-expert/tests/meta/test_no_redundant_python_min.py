"""Meta-test: no committed recipe carries `context.python_min:` at the default
conda-forge floor.

v8.13.0 — closes the operator-flagged drift surfaced 2026-06-11. Layer 3 of the
3-layer enforcement design: the generator (Wave A) writes the canonical form
for new recipes; the optimizer (Wave B SEL-004) flags hand-edits or migrations;
this meta-test catches what survives into the committed corpus.

The floor is read dynamically from
`.pixi/envs/local-recipes/conda_build_config.yaml`'s `python_min:` list
(materialised from conda-forge-pinning). When the floor moves, this test
moves with it.

The allowlist is **temporary**: it covers the 60 recipes that pre-dated this
enforcement and is emptied by Wave C of the same sprint. Any entry remaining
in the allowlist after Wave C indicates incomplete cleanup. New recipes are
NEVER allowed to be added — the test fails fast for any new drift.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[5]
_RECIPES_DIR = _REPO_ROOT / "recipes"
_PINNING_CONFIG = _REPO_ROOT / ".pixi/envs/local-recipes/conda_build_config.yaml"
_PINNING_PYTHON_MIN_RE = re.compile(
    r"^python_min:\s*\n(?:[ \t]*#[^\n]*\n)*[ \t]*-\s*['\"]?(?P<value>\d+\.\d+)['\"]?",
    re.MULTILINE,
)
_CONTEXT_PYTHON_MIN_RE = re.compile(
    r"^[ \t]+python_min:[ \t]+['\"]?(?P<value>\d+\.\d+)['\"]?[ \t]*$",
    re.MULTILINE,
)


def _read_conda_forge_python_floor() -> str:
    """Read floor dynamically; fall back to ``3.10`` if pinning file is missing."""
    if not _PINNING_CONFIG.exists():
        return "3.10"
    try:
        text = _PINNING_CONFIG.read_text(encoding="utf-8")
    except OSError:
        return "3.10"
    m = _PINNING_PYTHON_MIN_RE.search(text)
    return m.group("value") if m else "3.10"


# Temporary allowlist — Wave C of v8.13.0 sprint clears this. Each entry is the
# recipe directory name under `recipes/`. Once a recipe lands here, the meta-test
# accepts the drift; the entry should be removed (alongside dropping the line
# from the recipe) as Wave C progresses. CI must remain green throughout the
# sweep.
_WAVE_C_ALLOWLIST: frozenset[str] = frozenset()


def _scan_recipes_for_redundant_python_min(floor: str) -> list[tuple[str, str]]:
    """Return [(recipe_name, value), ...] for every recipe whose context.python_min
    equals (redundant) or is below (invalid) the conda-forge floor."""
    drifted: list[tuple[str, str]] = []
    if not _RECIPES_DIR.exists():
        return drifted
    try:
        floor_tuple = tuple(int(p) for p in floor.split("."))
    except ValueError:
        return drifted
    for recipe_yaml in _RECIPES_DIR.glob("*/recipe.yaml"):
        recipe_name = recipe_yaml.parent.name
        try:
            text = recipe_yaml.read_text(encoding="utf-8")
        except OSError:
            continue
        # Scan only within the context: block (above package: or other top-level)
        ctx_match = re.search(r"^context:\s*\n((?:[ \t]+[^\n]*\n)*)", text, re.MULTILINE)
        if ctx_match is None:
            continue
        ctx_text = ctx_match.group(1)
        for m in _CONTEXT_PYTHON_MIN_RE.finditer(ctx_text):
            value = m.group("value")
            try:
                value_tuple = tuple(int(p) for p in value.split("."))
            except ValueError:
                continue
            if value_tuple <= floor_tuple:
                drifted.append((recipe_name, value))
    return drifted


def test_no_redundant_or_below_floor_python_min_in_context() -> None:
    """No committed recipe should declare `context.python_min:` at or below the
    conda-forge floor.

    Allowlist (Wave C of v8.13.0 cleanup) shrinks toward empty; once empty, the
    test is enforcing on the full corpus.
    """
    floor = _read_conda_forge_python_floor()
    drifted = _scan_recipes_for_redundant_python_min(floor)
    unallowed = [(name, value) for name, value in drifted if name not in _WAVE_C_ALLOWLIST]
    if unallowed:
        formatted = "\n".join(
            f"  - {name}: python_min: \"{value}\" (floor is \"{floor}\")"
            for name, value in unallowed
        )
        pytest.fail(
            "Found recipes with `context.python_min:` at or below the conda-forge "
            f"floor ({floor}) — these are non-canonical per SKILL.md § Python "
            "Version Policy item 6. Remove the line from `context:`; "
            f"conda-forge-pinning supplies the floor.\n"
            f"See `feedback_omit_python_min_at_default_floor.md` for the convention.\n\n"
            f"{formatted}"
        )


def test_allowlist_subset_of_drifted() -> None:
    """Every allowlist entry must still be drifted. Stale entries get removed."""
    floor = _read_conda_forge_python_floor()
    drifted_names = {name for name, _ in _scan_recipes_for_redundant_python_min(floor)}
    stale = sorted(_WAVE_C_ALLOWLIST - drifted_names)
    assert not stale, (
        f"Wave C allowlist has stale entries (no longer drifted): {stale}. "
        f"Remove them from `_WAVE_C_ALLOWLIST` in {__file__}."
    )
