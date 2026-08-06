"""Unit tests for ``pyforge.marshal.core.landing`` (Story 4.7, AD-40):
``LandingRule``'s shape and ``rule_applies``'s per-``trigger_mode`` match,
proven against this repo's own two real rules (``CLAUDE.md``'s PR CI gates
section) plus the full I/O & Edge-Case Matrix the story spec names.

``trigger_mode`` was **corrected in review, 2026-08-06**: the original
shipped code implemented only ONE match direction (glob-exclusion), correct
for ``maintenance-label`` but backwards for ``environment-yaml-sync``, which
needs the OPPOSITE (glob-inclusion) semantics. See ``core/landing.py``'s
module docstring for the full story.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core.landing import LandingRule, rule_applies

# --- LandingRule shape --------------------------------------------------------


def test_landing_rule_is_frozen():
    rule = LandingRule(
        name="x", trigger_path_glob="a/**", trigger_mode="exclude", label="maintenance"
    )
    assert rule.name == "x"
    assert rule.trigger_path_glob == "a/**"
    assert rule.trigger_mode == "exclude"
    assert rule.label == "maintenance"
    assert rule.required_check is None
    assert rule.ungated is False
    with pytest.raises(AttributeError):
        rule.name = "y"  # type: ignore[misc]


def test_landing_rule_defaults():
    rule = LandingRule(name="x", trigger_path_glob="a/**", trigger_mode="exclude")
    assert rule.label is None
    assert rule.required_check is None
    assert rule.ungated is False


def test_landing_rule_equality_is_by_value():
    a = LandingRule(
        name="x", trigger_path_glob="a/**", trigger_mode="exclude", label="maintenance"
    )
    b = LandingRule(
        name="x", trigger_path_glob="a/**", trigger_mode="exclude", label="maintenance"
    )
    assert a == b


# --- rule_applies: trigger_mode="exclude" (the maintenance-label shape) -------


def test_rule_applies_fires_when_a_path_is_outside_the_glob():
    """This repo's own real `maintenance-label` rule: fires on ANY change
    outside `recipes/**`."""
    rule = LandingRule(
        name="maintenance-label",
        trigger_path_glob="recipes/**",
        trigger_mode="exclude",
        label="maintenance",
    )
    assert rule_applies(rule, ("docs/foo.md",)) is True
    assert rule_applies(rule, ("recipes/x/recipe.yaml", "docs/foo.md")) is True


def test_rule_does_not_apply_when_every_path_matches_the_glob():
    rule = LandingRule(
        name="maintenance-label",
        trigger_path_glob="recipes/**",
        trigger_mode="exclude",
        label="maintenance",
    )
    assert rule_applies(rule, ("recipes/x/recipe.yaml",)) is False
    assert rule_applies(rule, ("recipes/x/recipe.yaml", "recipes/y/meta.yaml")) is False


def test_rule_never_applies_to_an_empty_changed_paths_exclude_mode():
    rule = LandingRule(
        name="x", trigger_path_glob="recipes/**", trigger_mode="exclude", label="maintenance"
    )
    assert rule_applies(rule, ()) is False


# --- rule_applies: trigger_mode="include" (the environment-yaml-sync shape) ---


def test_environment_yaml_sync_rule_fires_only_on_pixi_toml():
    """This repo's own real `environment-yaml-sync` rule: an exact-name
    glob, not a directory wildcard, and `trigger_mode="include"` -- fires
    ONLY when `pixi.toml` is among the changed paths, the opposite of the
    shipped (buggy) behavior this test's docstring name always claimed."""
    rule = LandingRule(
        name="environment-yaml-sync",
        trigger_path_glob="pixi.toml",
        trigger_mode="include",
        required_check="environment-yaml-sync",
        ungated=True,
    )
    assert rule_applies(rule, ("pixi.toml",)) is True
    assert rule_applies(rule, ("recipes/x/recipe.yaml",)) is False
    assert rule_applies(rule, ("pixi.toml", "recipes/x/recipe.yaml")) is True


def test_rule_never_applies_to_an_empty_changed_paths_include_mode():
    rule = LandingRule(
        name="environment-yaml-sync",
        trigger_path_glob="pixi.toml",
        trigger_mode="include",
        required_check="environment-yaml-sync",
        ungated=True,
    )
    assert rule_applies(rule, ()) is False


def test_rule_applies_include_mode_does_not_fire_on_a_non_matching_path_only():
    rule = LandingRule(
        name="x", trigger_path_glob="pixi.toml", trigger_mode="include", label="l"
    )
    assert rule_applies(rule, ("docs/foo.md", "recipes/x/recipe.yaml")) is False


# --- case-sensitivity (review finding P2) -------------------------------------


def test_rule_applies_matches_case_sensitively_regardless_of_host_os():
    """Repository paths are case-sensitive at the git level regardless of
    the host OS -- `fnmatch.fnmatch` normalizes case per
    `os.path.normcase`, which would make the same policy match differently
    on Linux CI versus a case-insensitive filesystem. `rule_applies` must
    use `fnmatch.fnmatchcase` instead."""
    include_rule = LandingRule(
        name="x", trigger_path_glob="PIXI.TOML", trigger_mode="include", label="l"
    )
    assert rule_applies(include_rule, ("pixi.toml",)) is False
    assert rule_applies(include_rule, ("PIXI.TOML",)) is True

    exclude_rule = LandingRule(
        name="y", trigger_path_glob="RECIPES/**", trigger_mode="exclude", label="l"
    )
    # "recipes/x/recipe.yaml" does NOT case-sensitively match "RECIPES/**",
    # so it counts as "outside" the glob and the exclude rule fires.
    assert rule_applies(exclude_rule, ("recipes/x/recipe.yaml",)) is True
    assert rule_applies(exclude_rule, ("RECIPES/x/recipe.yaml",)) is False
