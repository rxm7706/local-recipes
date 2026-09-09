"""spec-39-4-optional-pixi-feature-bundle-cap-4: the opt-in `bmad-suite-full`
pixi feature (CAP-4 of spec-bmad-suite-metapackage).

Structural (tomllib) checks: the feature exists with the right channel + floor,
`local-recipes` does not compose it, `local-recipes`'s own explicit `bmad-*`
member pins are untouched, and `feature.bmad-ui` (dashboards) is unaffected.
Plus an optional live-solver guard (`pixi lock --check`) that skips cleanly
when `pixi` is not on PATH -- never a false failure in a pixi-less CI shard.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# The explicit bmad-* member pins carried under
# [feature.local-recipes.dependencies] (baseline_revision
# a35b7d5e59b731ef6bc7b9c42bb96c148cc57521; bmad-method-wds-expansion left the set
# 2026-09-05 when upstream deprecated it and bmad-eval-quality took its suite seat).
# No story may remove or replace any of them -- the factory default keeps every
# explicit pin for pipeline-truth / doctor drift granularity.
#
# bmad-eval-quality JOINED this set 2026-09-09 (mason Story 14.1). It had been
# parked in the linux-64/osx-arm64 target tables for exactly one reason -- the
# channel carried only the `__unix` noarch variant, so a win-64 solve could not
# resolve it. Both variants of 1.3.0 are published now, so the platform split was
# retired and the pin became platform-agnostic; `test_eval_quality_pin_lives_in_
# the_shared_table` below asserts the new placement.
#
# (Two more active suite members, bmad-module-skill-forge and mybmad-dashboard,
# live in [feature.local-recipes.target.linux-64.dependencies] and
# [feature.bmad-ui.dependencies] respectively -- out of this AC's scope.)
BASELINE_LOCAL_RECIPES_BMAD_PINS = {
    "bmad-method",
    "bmad-builder",
    "bmad-creative-intelligence-suite",
    "bmad-dashboard",
    "bmad-eval-quality",
    "bmad-loop",
    "bmad-method-test-architecture-enterprise",
    "bmad-module-template",
    "bmad-utility-skills",
    "bmad-labs-skills",
    "bmad-manticore",
}

# feature.bmad-ui's dependency table, byte-identical to the baseline this
# story must not touch (spec's own AC).
BASELINE_BMAD_UI_DEPENDENCIES = {
    "bmad-dashboard": ">=1.2.2.dev0",
    "mybmad-dashboard": ">=0.1.0.dev0",
}


def _data() -> dict:
    return tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))


def test_bmad_suite_full_feature_declares_selfexplainml_and_a_calver_floor() -> None:
    feat = _data()["feature"]["bmad-suite-full"]
    assert "SelfExplainML" in feat["channels"]
    assert "conda-forge" in feat["channels"]

    deps = feat["dependencies"]
    assert deps["bmad-suite"] == ">=2026.9.5"


def test_bmad_suite_full_feature_is_linux_64_only_and_does_not_duplicate_member_pins() -> None:
    """Platform-selectors matrix row: the feature scopes itself to linux-64
    (bmad-module-skill-forge's SelfExplainML build is linux-64-only) instead
    of duplicating that skip per member -- so bmad-suite-full's own
    dependency table must carry only the metapackage + its python floor,
    never an individual bmad-* member pin.
    """
    feat = _data()["feature"]["bmad-suite-full"]
    assert feat["platforms"] == ["linux-64"]

    deps = feat["dependencies"]
    member_pins = {k for k in deps if k.startswith("bmad") and k != "bmad-suite"}
    assert not member_pins, f"bmad-suite-full duplicates per-member pin(s): {member_pins}"


def test_install_matrix_documents_the_greenfield_one_pin_path() -> None:
    """Greenfield-docs matrix row: install-matrix.md must name the feature
    and show a one-pin install example, or the section counts as absent.
    """
    text = (REPO / "_bmad-output/projects/pyforge-steward/planning-artifacts"
            "/specs/spec-bmad-suite-channel-product/install-matrix.md").read_text(encoding="utf-8")
    assert "Greenfield one-pin" in text
    assert "bmad-suite-full" in text
    assert "pixi install -e bmad-suite-full" in text or "pixi add --feature bmad-suite-full" in text


def test_local_recipes_env_does_not_compose_bmad_suite_full() -> None:
    data = _data()
    assert "bmad-suite-full" not in data["environments"]["local-recipes"]


def test_local_recipes_bmad_member_pins_are_unchanged() -> None:
    deps = _data()["feature"]["local-recipes"]["dependencies"]
    present_bmad_keys = {k for k in deps if k.startswith("bmad")}

    missing = BASELINE_LOCAL_RECIPES_BMAD_PINS - present_bmad_keys
    assert not missing, f"pre-existing bmad-* pin(s) removed from local-recipes: {missing}"
    # No new bmad-* pin was slipped in here either -- this story only adds the
    # opt-in bmad-suite-full feature, never a new explicit member pin.
    assert present_bmad_keys == BASELINE_LOCAL_RECIPES_BMAD_PINS


def test_bmad_ui_feature_is_untouched() -> None:
    feat = _data()["feature"]["bmad-ui"]
    assert feat["dependencies"] == BASELINE_BMAD_UI_DEPENDENCIES
    assert "bmad-suite" not in feat["dependencies"]


def test_bmad_suite_full_environment_composes_only_its_own_feature() -> None:
    env = _data()["environments"]["bmad-suite-full"]
    assert env["features"] == ["bmad-suite-full"]
    assert env.get("no-default-feature") is True


@pytest.mark.skipif(shutil.which("pixi") is None, reason="pixi not on PATH")
@pytest.mark.skipif(
    os.environ.get("PIXI_ENVIRONMENT_NAME") == "pyforge-ci",
    reason="pyforge-ci's pyforge-deps-test sweep is documented pure-stdlib/no-network "
    "(see test_openteams_handoffs.py's module docstring); pixi is on PATH there too "
    "(feature.python pins it), so the shutil.which guard alone would not skip",
)
def test_pixi_lock_check_resolves_the_bmad_suite_full_environment() -> None:
    """Live solver proof (CI-capable hardware only): the lean bmad-suite-full
    environment actually resolves. `pixi lock` in this workspace's pinned
    pixi (0.78.0) has no per-environment `-e` selector, so this locks/verifies
    the whole workspace lock file rather than only the new environment --
    `--check` still fails loudly if bmad-suite-full (or anything else) can't
    solve against the committed pixi.lock.
    """
    proc = subprocess.run(
        ["pixi", "lock", "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, (
        f"pixi lock --check failed (stdout={proc.stdout!r} stderr={proc.stderr!r})"
    )


def test_eval_quality_pin_lives_in_the_shared_table() -> None:
    """Mason Story 14.1 (2026-09-09) reverses Story 45.1's platform split.

    45.1 put this pin in the linux-64 / osx-arm64 target tables for one reason:
    the channel carried only the ``__unix`` noarch variant, so a win-64 solve of
    the local-recipes feature could not resolve it. Both variants of 1.3.0 are
    now published (``__unix`` heeef243_0 and ``__win`` h2fd06db_0, confirmed in
    the SERVED repodata), which was the story's own stated precondition for the
    pin "leaving the target tables" -- so the split has no reason to exist and
    the pin is platform-agnostic again.

    The floor deliberately tracks the newest PUBLISHED build, not the newest the
    recipe builds: ``recipes/bmad-eval-quality`` is at 1.4.0, but a floor above
    what the channel serves reds every solve. Raise it in the same change that
    publishes 1.4.0.
    """
    feat = _data()["feature"]["local-recipes"]
    assert feat["dependencies"]["bmad-eval-quality"] == ">=1.3.0"
    assert "bmad-method-wds-expansion" not in feat["dependencies"]
    for plat in ("linux-64", "osx-arm64", "win-64"):
        deps = feat["target"].get(plat, {}).get("dependencies", {})
        assert "bmad-eval-quality" not in deps, plat
