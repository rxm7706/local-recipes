"""Unit tests -- the ConfigLoader (Story 3.1, FR30): precedence, conflict
reporting, CLI overrides, and typed validation errors.

Pure filesystem reads (tmp_path-written TOML files) -- no subprocess, no
network."""

from __future__ import annotations

import os

import pytest

from pyforge.warden.config import (
    DEFAULT_DEP001_MIN_CONFIDENCE,
    DEFAULT_FAIL_ON,
    DEFAULT_FAIL_UNDER_COVERAGE,
    DEFAULT_HYGIENE_POLICY,
    DEFAULT_VULN_SEVERITY_POLICY,
    ConfigValidationError,
    WardenConfig,
    load_config,
)
from pyforge.warden.models import SeverityTier, Status


def _write(path, name: str, text: str) -> None:
    (path / name).write_text(text, encoding="utf-8")


# --- resolution / precedence --------------------------------------------------


def test_no_config_anywhere_resolves_to_defaults(tmp_path):
    config, conflicts, errors = load_config(tmp_path)
    assert config == WardenConfig.defaults()
    assert conflicts == ()
    assert errors == ()


def test_single_file_config_applies_and_leaves_other_keys_default(tmp_path):
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    config, conflicts, errors = load_config(tmp_path)
    assert config.fail_on is SeverityTier.HIGH
    assert config.dep001_min_confidence == DEFAULT_DEP001_MIN_CONFIDENCE
    assert config.fail_under_coverage == DEFAULT_FAIL_UNDER_COVERAGE
    assert conflicts == ()
    assert errors == ()


def test_pixi_only_config_applies(tmp_path):
    _write(tmp_path, "pixi.toml", '[tool.pyforge-warden]\nfail_under_coverage = 80\n')
    config, conflicts, errors = load_config(tmp_path)
    assert config.fail_under_coverage == 80
    assert conflicts == ()
    assert errors == ()


def test_same_key_conflict_pyproject_wins_and_is_reported(tmp_path):
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    _write(tmp_path, "pixi.toml", '[tool.pyforge-warden]\nfail_on = "low"\n')
    config, conflicts, errors = load_config(tmp_path)
    assert config.fail_on is SeverityTier.HIGH
    assert len(conflicts) == 1
    assert "fail_on" in conflicts[0]
    assert "high" in conflicts[0] or "'high'" in conflicts[0]
    assert errors == ()


def test_different_keys_across_files_both_apply_no_conflict(tmp_path):
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    _write(
        tmp_path, "pixi.toml", '[tool.pyforge-warden]\nfail_under_coverage = 70\n'
    )
    config, conflicts, errors = load_config(tmp_path)
    assert config.fail_on is SeverityTier.HIGH
    assert config.fail_under_coverage == 70
    assert conflicts == ()
    assert errors == ()


def test_same_key_same_value_across_files_is_not_a_conflict(tmp_path):
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    _write(tmp_path, "pixi.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    config, conflicts, errors = load_config(tmp_path)
    assert config.fail_on is SeverityTier.HIGH
    assert conflicts == ()
    assert errors == ()


def test_cli_override_wins_over_both_files(tmp_path):
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    config, _, errors = load_config(tmp_path, cli_fail_on="critical")
    assert config.fail_on is SeverityTier.CRITICAL
    assert errors == ()


def test_cli_override_applies_with_no_config_file_at_all(tmp_path):
    config, _, errors = load_config(
        tmp_path, cli_fail_on="low", cli_fail_under_coverage=50
    )
    assert config.fail_on is SeverityTier.LOW
    assert config.fail_under_coverage == 50
    assert errors == ()


def test_no_table_present_is_not_an_absent_file_error(tmp_path):
    # A pyproject.toml with unrelated content (no [tool.pyforge-warden] at
    # all) must resolve exactly like a missing file, never a validation
    # error over an absent table.
    _write(tmp_path, "pyproject.toml", '[project]\nname = "demo"\n')
    config, conflicts, errors = load_config(tmp_path)
    assert config == WardenConfig.defaults()
    assert conflicts == ()
    assert errors == ()


# --- typed validation errors --------------------------------------------------
#
# A per-key problem (wrong type, out-of-vocabulary enum, unrecognized key)
# is collected as a message and that ONE key falls back to its default --
# it never aborts resolution of the other keys (review finding, 2026-07-17:
# a CLI override for a DIFFERENT key must survive an unrelated bad key).
# Only a STRUCTURAL failure (the table itself isn't a table) still raises.


def test_wrong_type_fail_on_is_reported_and_falls_back_to_default(tmp_path):
    _write(tmp_path, "pyproject.toml", "[tool.pyforge-warden]\nfail_on = 123\n")
    config, _, errors = load_config(tmp_path)
    assert config.fail_on is DEFAULT_FAIL_ON
    assert len(errors) == 1
    assert "fail_on" in errors[0]


def test_bad_enum_value_fail_on_is_reported_and_falls_back_to_default(tmp_path):
    _write(
        tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "extreme"\n'
    )
    config, _, errors = load_config(tmp_path)
    assert config.fail_on is DEFAULT_FAIL_ON
    assert len(errors) == 1
    assert "fail_on" in errors[0]


def test_out_of_range_fail_under_coverage_is_reported_and_falls_back(tmp_path):
    _write(
        tmp_path,
        "pyproject.toml",
        "[tool.pyforge-warden]\nfail_under_coverage = 150\n",
    )
    config, _, errors = load_config(tmp_path)
    assert config.fail_under_coverage == DEFAULT_FAIL_UNDER_COVERAGE
    assert len(errors) == 1
    assert "fail_under_coverage" in errors[0]


def test_negative_fail_under_coverage_is_reported_and_falls_back(tmp_path):
    _write(
        tmp_path,
        "pyproject.toml",
        "[tool.pyforge-warden]\nfail_under_coverage = -1\n",
    )
    config, _, errors = load_config(tmp_path)
    assert config.fail_under_coverage == DEFAULT_FAIL_UNDER_COVERAGE
    assert len(errors) == 1


def test_bool_fail_under_coverage_is_rejected(tmp_path):
    # bool is a subclass of int in Python -- must not silently coerce.
    _write(
        tmp_path,
        "pyproject.toml",
        "[tool.pyforge-warden]\nfail_under_coverage = true\n",
    )
    config, _, errors = load_config(tmp_path)
    assert config.fail_under_coverage == DEFAULT_FAIL_UNDER_COVERAGE
    assert len(errors) == 1


def test_bad_dep001_min_confidence_is_reported_and_falls_back(tmp_path):
    _write(
        tmp_path,
        "pyproject.toml",
        '[tool.pyforge-warden]\ndep001_min_confidence = "maybe"\n',
    )
    config, _, errors = load_config(tmp_path)
    assert config.dep001_min_confidence == DEFAULT_DEP001_MIN_CONFIDENCE
    assert len(errors) == 1
    assert "dep001_min_confidence" in errors[0]


def test_unrecognized_key_is_reported_and_other_keys_still_apply(tmp_path):
    _write(
        tmp_path,
        "pyproject.toml",
        '[tool.pyforge-warden]\nfail_on_ = "high"\nfail_on = "low"\n',
    )
    config, _, errors = load_config(tmp_path)
    # The unrecognized key is reported but a RECOGNIZED sibling key still
    # resolves normally -- one bad key must never poison the whole table.
    assert config.fail_on is SeverityTier.LOW
    assert len(errors) == 1
    assert "fail_on_" in errors[0]


def test_cli_override_survives_an_unrelated_bad_key_in_the_file(tmp_path):
    # The regression this fix targets: an explicit, valid CLI override for
    # one key must never be silently discarded because a DIFFERENT key in
    # the file is malformed.
    _write(
        tmp_path,
        "pyproject.toml",
        '[tool.pyforge-warden]\ndep001_min_confidence = "bogus"\n',
    )
    config, _, errors = load_config(tmp_path, cli_fail_on="high")
    assert config.fail_on is SeverityTier.HIGH
    assert config.dep001_min_confidence == DEFAULT_DEP001_MIN_CONFIDENCE
    assert len(errors) == 1
    assert "dep001_min_confidence" in errors[0]


def test_conflict_survives_an_unrelated_bad_key_in_the_file(tmp_path):
    # A real, already-detected same-key conflict must not be lost just
    # because a different key also fails validation in the same run.
    _write(
        tmp_path,
        "pyproject.toml",
        '[tool.pyforge-warden]\nfail_on = "high"\ndep001_min_confidence = "bogus"\n',
    )
    _write(tmp_path, "pixi.toml", '[tool.pyforge-warden]\nfail_on = "low"\n')
    config, conflicts, errors = load_config(tmp_path)
    assert config.fail_on is SeverityTier.HIGH
    assert len(conflicts) == 1
    assert "fail_on" in conflicts[0]
    assert len(errors) == 1
    assert "dep001_min_confidence" in errors[0]


def test_non_table_tool_pyforge_warden_raises_config_validation_error(tmp_path):
    # A structural failure (the table itself isn't a table) has no
    # sensible per-key fallback -- this is the one case that still raises.
    _write(tmp_path, "pyproject.toml", 'tool.pyforge-warden = "oops"\n')
    with pytest.raises(ConfigValidationError):
        load_config(tmp_path)


def test_malformed_toml_is_treated_as_absent_config_not_a_validation_error(tmp_path):
    # A structurally-broken TOML document is extraction's own concern
    # (unparsable-manifest) -- config.py must not raise a SECOND, different
    # error kind for the identical root cause (see _read_tool_table's
    # docstring). Config resolution silently falls back to defaults.
    _write(tmp_path, "pyproject.toml", "[tool.pyforge-warden\nfail_on = \n")
    config, conflicts, errors = load_config(tmp_path)
    assert config == WardenConfig.defaults()
    assert conflicts == ()
    assert errors == ()


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_unreadable_file_is_treated_as_absent_config_not_a_validation_error(
    tmp_path,
):
    if os.geteuid() == 0:
        pytest.skip("root ignores file permission bits")
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    (tmp_path / "pyproject.toml").chmod(0)
    try:
        config, conflicts, errors = load_config(tmp_path)
    finally:
        (tmp_path / "pyproject.toml").chmod(0o644)
    assert config == WardenConfig.defaults()
    assert conflicts == ()
    assert errors == ()


# --- WardenConfig direct-construction validation ---------------------------


def test_warden_config_rejects_bad_dep001_min_confidence_directly():
    with pytest.raises(ValueError, match="dep001_min_confidence"):
        WardenConfig(dep001_min_confidence="bogus")


def test_warden_config_rejects_bad_fail_on_directly():
    with pytest.raises(ValueError, match="fail_on"):
        WardenConfig(fail_on="extreme")  # type: ignore[arg-type]


# --- dep001_min_confidence -----------------------------------------------------


def test_dep001_min_confidence_widened_to_likely(tmp_path):
    _write(
        tmp_path,
        "pyproject.toml",
        '[tool.pyforge-warden]\ndep001_min_confidence = "likely"\n',
    )
    config, _, _ = load_config(tmp_path)
    assert config.dep001_min_confidence == "likely"


# --- derived tables --------------------------------------------------------


def test_default_fail_on_yields_the_unmodified_default_vuln_table(tmp_path):
    config, _, _ = load_config(tmp_path)
    assert config.fail_on is DEFAULT_FAIL_ON
    assert config.vuln_severity_policy == DEFAULT_VULN_SEVERITY_POLICY


def test_fail_on_high_escalates_high_to_policy_violation(tmp_path):
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "high"\n')
    config, _, _ = load_config(tmp_path)
    assert config.vuln_severity_policy[SeverityTier.CRITICAL] is Status.POLICY_VIOLATION
    assert config.vuln_severity_policy[SeverityTier.HIGH] is Status.POLICY_VIOLATION
    assert config.vuln_severity_policy[SeverityTier.MEDIUM] is Status.WARN
    assert config.vuln_severity_policy[SeverityTier.LOW] is Status.WARN
    assert config.vuln_severity_policy[SeverityTier.NONE] is Status.WARN
    # UNKNOWN is never a table member -- see module docstring.
    assert SeverityTier.UNKNOWN not in config.vuln_severity_policy


def test_fail_on_low_escalates_every_known_tier(tmp_path):
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "low"\n')
    config, _, _ = load_config(tmp_path)
    for tier in (
        SeverityTier.CRITICAL,
        SeverityTier.HIGH,
        SeverityTier.MEDIUM,
        SeverityTier.LOW,
    ):
        assert config.vuln_severity_policy[tier] is Status.POLICY_VIOLATION
    assert config.vuln_severity_policy[SeverityTier.NONE] is Status.WARN


def test_hygiene_policy_is_always_the_default_table(tmp_path):
    # v1 exposes no per-DEP-code override -- config.py's relocation is a
    # data-ownership move only (see module docstring).
    _write(tmp_path, "pyproject.toml", '[tool.pyforge-warden]\nfail_on = "low"\n')
    config, _, _ = load_config(tmp_path)
    assert config.hygiene_policy == DEFAULT_HYGIENE_POLICY


# --- WardenConfig.defaults() --------------------------------------------------


def test_defaults_factory_matches_the_module_level_constants():
    config = WardenConfig.defaults()
    assert config.fail_on is DEFAULT_FAIL_ON
    assert config.dep001_min_confidence == DEFAULT_DEP001_MIN_CONFIDENCE
    assert config.fail_under_coverage == DEFAULT_FAIL_UNDER_COVERAGE
    assert config.hygiene_policy == DEFAULT_HYGIENE_POLICY
    assert config.vuln_severity_policy == DEFAULT_VULN_SEVERITY_POLICY


def test_warden_config_is_frozen():
    config = WardenConfig.defaults()
    with pytest.raises(AttributeError):
        config.fail_on = SeverityTier.LOW  # type: ignore[misc]


def test_relocated_default_tables_are_immutable():
    with pytest.raises(TypeError):
        DEFAULT_HYGIENE_POLICY["DEP001"] = Status.WARN  # type: ignore[index]
    with pytest.raises(TypeError):
        DEFAULT_VULN_SEVERITY_POLICY[SeverityTier.CRITICAL] = Status.WARN  # type: ignore[index]
