"""Meta: every recipe-level conda_build_config.yaml must still merge with current pinning.

The Linux build lane (`.github/workflows/test-linux.yml` -> `.scripts/build_steps.sh`
-> `.ci_support/build_all.py`) merges variant configs in this order::

    /opt/conda/conda_build_config.yaml     conda-forge-pinning inside the image
    .ci_support/<CONFIG>.yaml              the platform variant
    recipes/conda_build_config.yaml        repo root-level, if present
    recipes/<name>/conda_build_config.yaml the recipe's own

``conda_build.variants.combine_specs`` resolves ``zip_keys`` from the LAST spec that
declares it and then re-validates EVERY spec against that group. So a stale copy of an
old pinning file does not merely supply stale values -- its ``zip_keys`` is imposed on
the *current* pinning, and the merge dies before a single recipe is rendered::

    ValueError: All entries associated by a zip_key field must be the same length.
    In /opt/conda/conda_build_config.yaml, numpy and python are different (1 and 4)

That was the fifth and last blocker on the Linux lane (2026-09-09). `recipes/`
carried a May-2025 verbatim pinning snapshot whose ``zip_keys`` still grouped
``numpy`` with ``python``; because it sat at the recipes/ ROOT it broke every recipe,
and 14 per-recipe copies of the same vintage each broke their own. All 15 were
deleted -- current pinning supplies the same keys, which is CFE gotcha G47's rule:
a recipe-local CBC is for recipe-SPECIFIC overrides, and a copy of the global
pinning file is always cruft.

This test makes that permanent. It replays the real merge, using the repo-root
``conda_build_config.yaml`` (the tracked verbatim copy of conda-forge-pinning, which
is what the image ships) in place of ``/opt/conda``'s, so a reintroduced snapshot
fails here instead of on a dispatched Linux run.
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
conda_build_variants = pytest.importorskip("conda_build.variants")
conda_build_config_mod = pytest.importorskip("conda_build.config")

REPO_ROOT = Path(__file__).resolve().parents[5]
RECIPES_DIR = REPO_ROOT / "recipes"
PINNING = REPO_ROOT / "conda_build_config.yaml"
PLATFORM_VARIANT = REPO_ROOT / ".ci_support" / "linux64.yaml"


def _combine(paths: list[Path]) -> dict:
    """Run build_all.py's combine_specs() over `paths`, in order."""
    config = conda_build_config_mod.Config()
    specs = OrderedDict()
    for path in paths:
        specs[str(path)] = conda_build_variants.parse_config_file(
            str(path), config, loader=yaml.SafeLoader
        )
    return conda_build_variants.combine_specs(specs, log_output=False)


def _base() -> list[Path]:
    return [PINNING, PLATFORM_VARIANT]


def test_pinning_and_platform_variant_are_present() -> None:
    assert PINNING.is_file(), f"missing the tracked pinning copy at {PINNING}"
    assert PLATFORM_VARIANT.is_file(), f"missing {PLATFORM_VARIANT}"


def test_no_root_level_recipes_conda_build_config() -> None:
    """A CBC at the recipes/ ROOT applies to every recipe -- and hijacks zip_keys.

    build_steps.sh prunes the build copy to the one TEST_RECIPE by deleting sibling
    DIRECTORIES, so a file sitting directly in recipes/ survives that prune and is
    merged into every build. There is no legitimate use for one here: per-recipe
    overrides belong in recipes/<name>/conda_build_config.yaml.
    """
    root_cbc = RECIPES_DIR / "conda_build_config.yaml"
    assert not root_cbc.exists(), (
        "recipes/conda_build_config.yaml is back. It is merged into EVERY recipe's "
        "build and its zip_keys override the container's pinning -- put the keys in "
        "recipes/<name>/conda_build_config.yaml instead."
    )


def test_base_variant_config_merges() -> None:
    combined = _combine(_base())
    assert combined.get("python"), "pinning supplied no python variant"


@pytest.mark.parametrize(
    "cbc",
    sorted(RECIPES_DIR.glob("*/conda_build_config.yaml")),
    ids=lambda p: p.parent.name,
)
def test_recipe_cbc_merges_with_current_pinning(cbc: Path) -> None:
    try:
        _combine(_base() + [cbc])
    except ValueError as exc:
        pytest.fail(
            f"{cbc.relative_to(REPO_ROOT)} cannot merge with current conda-forge "
            f"pinning, so the Linux lane dies before rendering the recipe (CFE G47):\n"
            f"  {exc}\n"
            "If this file is a copy of the global pinning, delete it; keep only "
            "recipe-SPECIFIC keys."
        )
