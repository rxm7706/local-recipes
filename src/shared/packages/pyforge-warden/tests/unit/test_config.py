"""Unit tests -- ``EffectiveConfig`` + ``ConfigLoader`` (Story 3.1): dual-
TOML ``[tool.pyforge-warden]`` load, per-key precedence, and the two
derived policy knobs (``vuln_severity_policy``, ``is_confidence_trusted``).

Every ``ConfigLoader.load`` test writes real files to ``tmp_path`` and
reads them back through the real ``tomllib`` path — no mocking of the TOML
layer.
"""

from __future__ import annotations

import inspect

import pytest

from pyforge.warden.config import (
    ConfigLoader,
    ConfigParseError,
    ConfigValidationError,
    EffectiveConfig,
)
from pyforge.warden.models import SeverityTier, Status


def _write(path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


# --- EffectiveConfig: defaults -----------------------------------------------


def test_effective_config_defaults():
    config = EffectiveConfig()
    assert config.fail_on is SeverityTier.CRITICAL
    assert config.fail_under_coverage == 0.0
    assert config.dep001_block_confidence == "verified"


def test_default_classmethod_matches_the_plain_constructor():
    assert EffectiveConfig.default() == EffectiveConfig()


# --- EffectiveConfig.vuln_severity_policy ------------------------------------


@pytest.mark.parametrize(
    "fail_on,policy_violation_tiers",
    [
        (SeverityTier.CRITICAL, {SeverityTier.CRITICAL}),
        (SeverityTier.HIGH, {SeverityTier.CRITICAL, SeverityTier.HIGH}),
        (
            SeverityTier.MEDIUM,
            {SeverityTier.CRITICAL, SeverityTier.HIGH, SeverityTier.MEDIUM},
        ),
        (
            SeverityTier.LOW,
            {
                SeverityTier.CRITICAL,
                SeverityTier.HIGH,
                SeverityTier.MEDIUM,
                SeverityTier.LOW,
            },
        ),
        (
            SeverityTier.NONE,
            {
                SeverityTier.CRITICAL,
                SeverityTier.HIGH,
                SeverityTier.MEDIUM,
                SeverityTier.LOW,
                SeverityTier.NONE,
            },
        ),
    ],
)
def test_vuln_severity_policy_threshold_for_each_fail_on(fail_on, policy_violation_tiers):
    policy = EffectiveConfig(fail_on=fail_on).vuln_severity_policy
    assert set(policy) == {
        SeverityTier.CRITICAL,
        SeverityTier.HIGH,
        SeverityTier.MEDIUM,
        SeverityTier.LOW,
        SeverityTier.NONE,
    }
    for tier, status in policy.items():
        expected = (
            Status.POLICY_VIOLATION if tier in policy_violation_tiers else Status.WARN
        )
        assert status is expected


@pytest.mark.parametrize(
    "fail_on",
    [tier for tier in SeverityTier if tier is not SeverityTier.UNKNOWN],
)
def test_vuln_severity_policy_never_contains_unknown(fail_on):
    assert SeverityTier.UNKNOWN not in EffectiveConfig(fail_on=fail_on).vuln_severity_policy


def test_default_fail_on_reproduces_the_module_vuln_default_table():
    """At fail_on=CRITICAL (the default), vuln_severity_policy is
    byte-identical to vuln.DEFAULT_VULN_SEVERITY_POLICY (Design Notes)."""
    from pyforge.warden.vuln import DEFAULT_VULN_SEVERITY_POLICY

    assert EffectiveConfig().vuln_severity_policy == dict(DEFAULT_VULN_SEVERITY_POLICY)


# --- EffectiveConfig.is_confidence_trusted -----------------------------------


def test_is_confidence_trusted_none_is_always_trusted():
    assert EffectiveConfig().is_confidence_trusted(None) is True
    assert EffectiveConfig(dep001_block_confidence="likely").is_confidence_trusted(
        None
    ) is True


def test_is_confidence_trusted_verified_threshold_distrusts_likely():
    config = EffectiveConfig(dep001_block_confidence="verified")
    assert config.is_confidence_trusted("verified") is True
    assert config.is_confidence_trusted("likely") is False


def test_is_confidence_trusted_likely_threshold_trusts_both():
    config = EffectiveConfig(dep001_block_confidence="likely")
    assert config.is_confidence_trusted("verified") is True
    assert config.is_confidence_trusted("likely") is True


def test_is_confidence_trusted_unrecognized_string_is_never_trusted():
    config = EffectiveConfig(dep001_block_confidence="likely")
    assert config.is_confidence_trusted("bogus") is False


# --- ConfigLoader.load: source combinations ----------------------------------


def test_load_pyproject_only(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\nfail-on = "high"\n')
    config, warnings = ConfigLoader().load(tmp_path)
    assert config.fail_on is SeverityTier.HIGH
    assert warnings == ()


def test_load_pixi_only(tmp_path):
    _write(tmp_path / "pixi.toml", '[tool.pyforge-warden]\nfail-on = "low"\n')
    config, warnings = ConfigLoader().load(tmp_path)
    assert config.fail_on is SeverityTier.LOW
    assert warnings == ()


def test_load_both_agreeing_no_warning(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\nfail-on = "medium"\n')
    _write(tmp_path / "pixi.toml", '[tool.pyforge-warden]\nfail-on = "medium"\n')
    config, warnings = ConfigLoader().load(tmp_path)
    assert config.fail_on is SeverityTier.MEDIUM
    assert warnings == ()


def test_load_both_conflicting_pyproject_wins_with_one_warning(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\nfail-on = "high"\n')
    _write(tmp_path / "pixi.toml", '[tool.pyforge-warden]\nfail-on = "low"\n')
    config, warnings = ConfigLoader().load(tmp_path)
    assert config.fail_on is SeverityTier.HIGH
    assert len(warnings) == 1
    assert "fail-on" in warnings[0]
    assert "high" in warnings[0]
    assert "low" in warnings[0]


def test_load_both_missing_defaults(tmp_path):
    config, warnings = ConfigLoader().load(tmp_path)
    assert config == EffectiveConfig.default()
    assert warnings == ()


# --- ConfigLoader.load: malformed TOML (file-dependent hard/soft) -----------


def test_load_malformed_pyproject_raises_config_parse_error(tmp_path):
    _write(tmp_path / "pyproject.toml", "[project\nname = 'broken")
    with pytest.raises(ConfigParseError):
        ConfigLoader().load(tmp_path)


def test_load_malformed_pixi_is_a_warning_not_fatal(tmp_path):
    _write(tmp_path / "pixi.toml", "[tool.pyforge-warden\nfail-on = 'high'")
    config, warnings = ConfigLoader().load(tmp_path)
    assert config == EffectiveConfig.default()
    assert len(warnings) == 1
    assert "pixi.toml" in warnings[0]


def test_pixi_non_table_pyforge_warden_shape_is_a_hard_failure_not_a_warning(tmp_path):
    """Only TOML SYNTAX failures get file-dependent (hard/soft) treatment;
    a SHAPE problem (a non-table [tool.pyforge-warden]) is always a hard
    ConfigValidationError, even from pixi.toml (the secondary source)."""
    _write(tmp_path / "pixi.toml", '[tool]\npyforge-warden = "not-a-table"\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


# --- ConfigLoader.load: unrecognized / underscore-spelled keys --------------


@pytest.mark.parametrize("filename", ["pyproject.toml", "pixi.toml"])
def test_unrecognized_key_raises_config_validation_error(tmp_path, filename):
    _write(tmp_path / filename, '[tool.pyforge-warden]\nnot-a-real-key = "x"\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


@pytest.mark.parametrize("filename", ["pyproject.toml", "pixi.toml"])
def test_underscore_spelled_key_is_unrecognized(tmp_path, filename):
    _write(tmp_path / filename, '[tool.pyforge-warden]\nfail_on = "high"\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


# --- ConfigLoader.load: type/range/enum validation per key ------------------


def test_wrong_typed_fail_on_raises_config_validation_error(tmp_path):
    _write(tmp_path / "pyproject.toml", "[tool.pyforge-warden]\nfail-on = 5\n")
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_unknown_fail_on_choice_raises_config_validation_error(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\nfail-on = "extreme"\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_wrong_typed_fail_under_coverage_raises_config_validation_error(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pyforge-warden]\nfail-under-coverage = "50"\n',
    )
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


@pytest.mark.parametrize("value", ["-1", "101"])
def test_out_of_range_fail_under_coverage_raises_config_validation_error(
    tmp_path, value
):
    _write(
        tmp_path / "pyproject.toml",
        f"[tool.pyforge-warden]\nfail-under-coverage = {value}\n",
    )
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_fail_under_coverage_accepts_boundary_values(tmp_path):
    _write(tmp_path / "pyproject.toml", "[tool.pyforge-warden]\nfail-under-coverage = 0\n")
    config, _ = ConfigLoader().load(tmp_path)
    assert config.fail_under_coverage == 0.0
    _write(
        tmp_path / "pyproject.toml", "[tool.pyforge-warden]\nfail-under-coverage = 100\n"
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.fail_under_coverage == 100.0


def test_wrong_typed_dep001_block_confidence_raises_config_validation_error(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        "[tool.pyforge-warden]\ndep001-block-confidence = 5\n",
    )
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_unknown_dep001_block_confidence_choice_raises_config_validation_error(
    tmp_path,
):
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pyforge-warden]\ndep001-block-confidence = "maybe"\n',
    )
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_non_table_tool_section_raises_config_validation_error(tmp_path):
    _write(tmp_path / "pyproject.toml", 'tool = "not-a-table"\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_non_table_pyforge_warden_section_raises_config_validation_error(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool]\npyforge-warden = "not-a-table"\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


# --- ConfigLoader.load: CLI overrides win over both files --------------------


def test_cli_fail_on_overrides_both_files(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\nfail-on = "high"\n')
    _write(tmp_path / "pixi.toml", '[tool.pyforge-warden]\nfail-on = "low"\n')
    config, _ = ConfigLoader().load(tmp_path, cli_fail_on="critical")
    assert config.fail_on is SeverityTier.CRITICAL


def test_cli_fail_under_coverage_overrides_both_files(tmp_path):
    _write(tmp_path / "pyproject.toml", "[tool.pyforge-warden]\nfail-under-coverage = 50\n")
    _write(tmp_path / "pixi.toml", "[tool.pyforge-warden]\nfail-under-coverage = 75\n")
    config, _ = ConfigLoader().load(tmp_path, cli_fail_under_coverage=10.0)
    assert config.fail_under_coverage == 10.0


def test_cli_overrides_apply_even_when_absent_from_either_file(tmp_path):
    config, warnings = ConfigLoader().load(tmp_path, cli_fail_on="none")
    assert config.fail_on is SeverityTier.NONE
    assert warnings == ()


def test_dep001_block_confidence_default_and_toml_override(tmp_path):
    config, _ = ConfigLoader().load(tmp_path)
    assert config.dep001_block_confidence == "verified"
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pyforge-warden]\ndep001-block-confidence = "likely"\n',
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.dep001_block_confidence == "likely"


def test_no_cli_flag_parameter_exists_for_dep001_block_confidence():
    """TOML-only key (Design Notes): epics.md spells CLI flags for exactly
    --fail-on/--fail-under-coverage, never dep001-block-confidence."""
    params = inspect.signature(ConfigLoader.load).parameters
    assert "cli_dep001_block_confidence" not in params


def test_invalid_cli_fail_on_raises_config_validation_error_not_a_bare_value_error(
    tmp_path,
):
    """Review finding: a direct caller bypassing argparse's `choices` must
    still get this module's own typed error, not an untyped ValueError from
    a bare SeverityTier(cli_fail_on) call."""
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path, cli_fail_on="extreme")


def test_invalid_cli_fail_under_coverage_raises_config_validation_error(tmp_path):
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path, cli_fail_under_coverage=150.0)


def test_warnings_gathered_before_a_later_validation_error_are_not_lost(tmp_path):
    """Review finding: a malformed-but-non-fatal pixi.toml warning must
    survive a SUBSEQUENT unrecognized-key ConfigValidationError raised while
    resolving the merged table -- attached to the exception, not silently
    dropped."""
    _write(tmp_path / "pixi.toml", "[tool.pyforge-warden\nfail-on = 'high'")
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\nnot-a-real-key = "x"\n')
    with pytest.raises(ConfigValidationError) as excinfo:
        ConfigLoader().load(tmp_path)
    assert len(excinfo.value.warnings) == 1
    assert "pixi.toml" in excinfo.value.warnings[0]


# --- EffectiveConfig: __post_init__ validation -------------------------------


def test_effective_config_rejects_unknown_severity_tier_at_construction():
    with pytest.raises(ValueError):
        EffectiveConfig(fail_on=SeverityTier.UNKNOWN)


def test_effective_config_rejects_invalid_dep001_block_confidence_at_construction():
    with pytest.raises(ValueError):
        EffectiveConfig(dep001_block_confidence="bogus")


@pytest.mark.parametrize("value", [-1.0, 101.0])
def test_effective_config_rejects_out_of_range_fail_under_coverage_at_construction(
    value,
):
    with pytest.raises(ValueError):
        EffectiveConfig(fail_under_coverage=value)


# --- EffectiveConfig.default_with_cli_overrides ------------------------------


def test_default_with_cli_overrides_applies_both_flags():
    config = EffectiveConfig.default_with_cli_overrides(
        cli_fail_on="high", cli_fail_under_coverage=42.0
    )
    assert config.fail_on is SeverityTier.HIGH
    assert config.fail_under_coverage == 42.0
    assert config.dep001_block_confidence == "verified"


def test_default_with_cli_overrides_no_flags_is_plain_default():
    assert EffectiveConfig.default_with_cli_overrides() == EffectiveConfig.default()


def test_default_with_cli_overrides_rejects_invalid_fail_on():
    with pytest.raises(ConfigValidationError):
        EffectiveConfig.default_with_cli_overrides(cli_fail_on="extreme")
