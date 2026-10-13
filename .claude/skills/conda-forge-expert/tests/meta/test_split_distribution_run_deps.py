"""G107 regression net: a noarch:python recipe must not depend on the module-less half
of a split distribution.

conda-forge `unicorn` is the C library and `python-unicorn` the bindings. A recipe that
lists the bare name still solves and lints, and works only while some other dependency
happens to pull the bindings in (mason Story 29.1: `recipes/pwndbg` listed `unicorn` and
relied on pwntools).

The pairs come from `pypi_conda_mappings/custom.yaml`. An entry whose `reason` starts with
``G107:`` maps a PyPI name to bindings under a different conda name, and the PyPI name, as a
conda name, is the wrong half. Only entries marked `lint_wrong_half: true` are linted: the
wrong half can be a legitimate dependency in its own right. `playwright` is the Node CLI
that tools shelling out to it need, and `playwright-python` itself depends on it, so that
pair is declared but not linted.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

_SKILL_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SKILL_DIR.parents[2]
_CUSTOM = _SKILL_DIR / "pypi_conda_mappings" / "custom.yaml"
_RECIPES = _REPO_ROOT / "recipes"


def _split_pairs(*, linted_only: bool = True) -> dict[str, str]:
    """{wrong-half conda name: bindings conda name} from the G107 overrides."""
    data = yaml.safe_load(_CUSTOM.read_text(encoding="utf-8")) or {}
    pairs: dict[str, str] = {}
    for pypi_name, info in data.items():
        if not isinstance(info, dict) or not str(info.get("reason", "")).startswith("G107:"):
            continue
        if linted_only and info.get("lint_wrong_half") is not True:
            continue
        bindings = str(info.get("conda_name", ""))
        if bindings and bindings != pypi_name:
            pairs[str(pypi_name)] = bindings
    return pairs


def _dep_names(items) -> list[str]:
    names: list[str] = []
    for item in items or []:
        if isinstance(item, str):
            m = re.match(r"\s*([A-Za-z0-9_.\-]+)", item)
            if m:
                names.append(m.group(1).lower())
        elif isinstance(item, dict):
            for branch in ("then", "else"):
                sub = item.get(branch)
                names.extend(_dep_names(sub if isinstance(sub, list) else [sub] if sub else []))
    return names


def _noarch_python_run_lists(recipe: dict) -> list[list[str]]:
    blocks = [recipe, *[o for o in recipe.get("outputs") or [] if isinstance(o, dict)]]
    top_noarch = (recipe.get("build") or {}).get("noarch")
    lists = []
    for block in blocks:
        noarch = (block.get("build") or {}).get("noarch", top_noarch)
        run = (block.get("requirements") or {}).get("run")
        if noarch == "python" and run:
            lists.append(_dep_names(run))
    return lists


def test_g107_pairs_are_declared() -> None:
    every = _split_pairs(linted_only=False)
    assert every.get("unicorn") == "python-unicorn", every
    assert every.get("playwright") == "playwright-python", every
    assert _split_pairs() == {"unicorn": "python-unicorn"}


def test_no_noarch_python_recipe_depends_on_the_wrong_half() -> None:
    pairs = _split_pairs()
    offenders: list[str] = []
    for path in sorted(_RECIPES.glob("**/recipe.yaml")):
        try:
            recipe = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue  # the parse audit owns unparseable recipes
        if not isinstance(recipe, dict):
            continue
        for names in _noarch_python_run_lists(recipe):
            for wrong, bindings in pairs.items():
                if wrong in names and bindings not in names:
                    offenders.append(f"{path.relative_to(_REPO_ROOT)}: run lists `{wrong}`, not `{bindings}`")
    assert not offenders, "G107 split-distribution wrong half in run deps:\n" + "\n".join(offenders)
