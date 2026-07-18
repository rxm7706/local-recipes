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
from pyforge.warden.models import LicenseVerdict, SeverityTier, Status


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


def test_waiver_default_expiry_days_default_and_toml_override(tmp_path):
    config, _ = ConfigLoader().load(tmp_path)
    assert config.waiver_default_expiry_days == 14
    _write(
        tmp_path / "pyproject.toml",
        "[tool.pyforge-warden]\nwaiver-default-expiry-days = 30\n",
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.waiver_default_expiry_days == 30


@pytest.mark.parametrize(
    "toml_value", ["0", "-1", '"30"', "30.0", "true", "3651"]
)
def test_wrong_or_out_of_range_waiver_default_expiry_days_raises_config_validation_error(
    tmp_path, toml_value
):
    _write(
        tmp_path / "pyproject.toml",
        f"[tool.pyforge-warden]\nwaiver-default-expiry-days = {toml_value}\n",
    )
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_waiver_default_expiry_days_accepts_the_upper_boundary(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        "[tool.pyforge-warden]\nwaiver-default-expiry-days = 3650\n",
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.waiver_default_expiry_days == 3650


def test_no_cli_flag_parameter_exists_for_waiver_default_expiry_days():
    """TOML-only key (Design Notes): no CLI flag exists for the waiver
    default expiry window either."""
    params = inspect.signature(ConfigLoader.load).parameters
    assert "cli_waiver_default_expiry_days" not in params


# --- ConfigLoader.load: fail-on-kev (Story 6.4) -------------------------------


def test_fail_on_kev_defaults_true(tmp_path):
    config, _ = ConfigLoader().load(tmp_path)
    assert config.fail_on_kev is True


def test_fail_on_kev_toml_override(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        "[tool.pyforge-warden]\nfail-on-kev = false\n",
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.fail_on_kev is False


def test_wrong_typed_fail_on_kev_raises_config_validation_error(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pyforge-warden]\nfail-on-kev = "yes"\n',
    )
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_no_cli_flag_parameter_exists_for_fail_on_kev():
    """TOML-only key (Design Notes): no CLI flag exists for fail-on-kev
    either -- mirrors dep001-block-confidence/waiver-default-expiry-days."""
    params = inspect.signature(ConfigLoader.load).parameters
    assert "cli_fail_on_kev" not in params


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


@pytest.mark.parametrize("value", [0, -1, True, 3651])
def test_effective_config_rejects_invalid_waiver_default_expiry_days_at_construction(
    value,
):
    with pytest.raises(ValueError):
        EffectiveConfig(waiver_default_expiry_days=value)


def test_effective_config_accepts_waiver_default_expiry_days_upper_boundary():
    assert EffectiveConfig(waiver_default_expiry_days=3650).waiver_default_expiry_days == 3650


def test_effective_config_fail_on_kev_defaults_true():
    assert EffectiveConfig().fail_on_kev is True


def test_effective_config_rejects_non_bool_fail_on_kev_at_construction():
    with pytest.raises(ValueError):
        EffectiveConfig(fail_on_kev="true")


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


# --- ConfigLoader.load: allow-licenses/deny-licenses (Story 6.2, FR33) -------


def test_allow_deny_licenses_default_to_empty(tmp_path):
    config, _ = ConfigLoader().load(tmp_path)
    assert config.allow_licenses == ()
    assert config.deny_licenses == ()
    assert config.license_gating is False


def test_toml_comma_separated_string_allow_licenses(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pyforge-warden]\nallow-licenses = "MIT, Apache-2.0"\n',
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.allow_licenses == ("MIT", "Apache-2.0")
    assert config.license_gating is True


def test_toml_list_deny_licenses(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pyforge-warden]\ndeny-licenses = ["GPL-3.0-only", "AGPL-3.0-only"]\n',
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.deny_licenses == ("GPL-3.0-only", "AGPL-3.0-only")
    assert config.license_gating is True


def test_blank_entries_are_dropped_from_a_comma_separated_list(tmp_path):
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pyforge-warden]\nallow-licenses = "MIT, , Apache-2.0,"\n',
    )
    config, _ = ConfigLoader().load(tmp_path)
    assert config.allow_licenses == ("MIT", "Apache-2.0")


@pytest.mark.parametrize("key", ["allow-licenses", "deny-licenses"])
def test_wrong_typed_license_list_raises_config_validation_error(tmp_path, key):
    _write(tmp_path / "pyproject.toml", f"[tool.pyforge-warden]\n{key} = 42\n")
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


@pytest.mark.parametrize("key", ["allow-licenses", "deny-licenses"])
def test_mixed_type_list_raises_config_validation_error(tmp_path, key):
    _write(tmp_path / "pyproject.toml", f'[tool.pyforge-warden]\n{key} = ["MIT", 1]\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


# --- Fix 5 (review finding, 2026-07-18): an explicitly-configured license --
# list that resolves to zero usable entries must raise, never silently
# no-op license_gating.


@pytest.mark.parametrize("key", ["allow-licenses", "deny-licenses"])
def test_blank_string_license_list_raises_config_validation_error(tmp_path, key):
    """``--deny-licenses ""`` (an explicit, empty string) must raise --
    silently producing an empty tuple would leave license_gating=False
    while the user believes they configured a gate."""
    _write(tmp_path / "pyproject.toml", f'[tool.pyforge-warden]\n{key} = ""\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


@pytest.mark.parametrize("key", ["allow-licenses", "deny-licenses"])
def test_all_comma_license_list_raises_config_validation_error(tmp_path, key):
    """``--deny-licenses " , "`` (blank/all-comma) resolves to zero usable
    tokens after stripping -- same treatment as an empty string."""
    _write(tmp_path / "pyproject.toml", f'[tool.pyforge-warden]\n{key} = " , "\n')
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


@pytest.mark.parametrize("key", ["allow-licenses", "deny-licenses"])
def test_empty_list_license_list_raises_config_validation_error(tmp_path, key):
    """An explicit empty TOML list (``[]``) is the same "configured but
    empty" case as a blank string."""
    _write(tmp_path / "pyproject.toml", f"[tool.pyforge-warden]\n{key} = []\n")
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path)


def test_cli_deny_licenses_blank_raises_config_validation_error(tmp_path):
    """The CLI-override path is gated the same way as the TOML path --
    ``--deny-licenses "  "`` explicitly passed but blank must raise, not
    silently resolve to an unconfigured gate."""
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path, cli_deny_licenses="  ")


def test_cli_allow_licenses_blank_raises_config_validation_error(tmp_path):
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path, cli_allow_licenses="")


def test_cli_allow_licenses_overrides_both_files(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\nallow-licenses = "MIT"\n')
    _write(tmp_path / "pixi.toml", '[tool.pyforge-warden]\nallow-licenses = "ISC"\n')
    config, _ = ConfigLoader().load(tmp_path, cli_allow_licenses="Apache-2.0")
    assert config.allow_licenses == ("Apache-2.0",)


def test_cli_deny_licenses_overrides_both_files(tmp_path):
    _write(tmp_path / "pyproject.toml", '[tool.pyforge-warden]\ndeny-licenses = "MIT"\n')
    _write(tmp_path / "pixi.toml", '[tool.pyforge-warden]\ndeny-licenses = "ISC"\n')
    config, _ = ConfigLoader().load(tmp_path, cli_deny_licenses="GPL-3.0-only")
    assert config.deny_licenses == ("GPL-3.0-only",)


def test_license_gating_true_iff_either_list_is_non_empty():
    assert EffectiveConfig().license_gating is False
    assert EffectiveConfig(allow_licenses=("MIT",)).license_gating is True
    assert EffectiveConfig(deny_licenses=("GPL-3.0-only",)).license_gating is True


def test_license_policy_maps_denied_and_unknown_to_warn():
    policy = EffectiveConfig().license_policy
    assert policy == {
        LicenseVerdict.DENIED: Status.WARN,
        LicenseVerdict.UNKNOWN: Status.WARN,
    }


def test_effective_config_rejects_non_tuple_allow_licenses_at_construction():
    with pytest.raises(ValueError):
        EffectiveConfig(allow_licenses=["MIT"])  # a list, not a tuple


def test_effective_config_rejects_empty_string_entry_at_construction():
    with pytest.raises(ValueError):
        EffectiveConfig(deny_licenses=("",))


def test_default_with_cli_overrides_applies_license_flags():
    config = EffectiveConfig.default_with_cli_overrides(
        cli_allow_licenses="MIT,Apache-2.0", cli_deny_licenses="GPL-3.0-only"
    )
    assert config.allow_licenses == ("MIT", "Apache-2.0")
    assert config.deny_licenses == ("GPL-3.0-only",)


# --- Follow-up review pass (2026-07-18): entry validity ----------------------


@pytest.mark.parametrize("key", ["allow-licenses", "deny-licenses"])
@pytest.mark.parametrize("bad_entry", ["GPLv3", "BSD", "Apache 2.0", "()"])
def test_invalid_spdx_toml_entry_raises_config_validation_error(
    tmp_path, key, bad_entry
):
    """A configured entry that cannot normalize as SPDX could never match
    any resolved license — the gate would read active (gating: true) while
    being structurally unable to fire. Fail at load, like the
    zero-usable-entries check already does."""
    _write(
        tmp_path / "pyproject.toml",
        f'[tool.pyforge-warden]\n{key} = "{bad_entry}"\n',
    )
    with pytest.raises(ConfigValidationError, match="never match"):
        ConfigLoader().load(tmp_path)


def test_invalid_spdx_cli_entry_raises_config_validation_error(tmp_path):
    with pytest.raises(ConfigValidationError, match="GPLv3"):
        ConfigLoader().load(tmp_path, cli_deny_licenses="GPLv3")
    with pytest.raises(ConfigValidationError):
        ConfigLoader().load(tmp_path, cli_allow_licenses="()")


def test_one_invalid_entry_among_valid_ones_still_raises(tmp_path):
    with pytest.raises(ConfigValidationError, match="GPLv3"):
        ConfigLoader().load(tmp_path, cli_deny_licenses="MIT, GPLv3")


def test_license_ref_with_grant_and_compound_entries_are_accepted(tmp_path):
    """The full valid-entry surface: single ids, compound expressions,
    WITH grants, and SPDX's user-defined LicenseRef-* references."""
    config, _ = ConfigLoader().load(
        tmp_path,
        cli_deny_licenses=(
            "LicenseRef-Proprietary, MIT OR Apache-2.0, "
            "GPL-2.0-only WITH Classpath-exception-2.0"
        ),
    )
    assert config.deny_licenses == (
        "LicenseRef-Proprietary",
        "MIT OR Apache-2.0",
        "GPL-2.0-only WITH Classpath-exception-2.0",
    )


def test_effective_config_rejects_blank_entry_at_construction():
    """A whitespace-only entry used to construct fine and flip
    license_gating True over a token _normalize_tokens silently empties —
    inconsistent with _coerce_license_list's stripped-token guarantee."""
    with pytest.raises(ValueError):
        EffectiveConfig(deny_licenses=(" ",))


def test_license_policy_property_matches_module_default_table():
    """config.license_policy and license.DEFAULT_LICENSE_POLICY are two
    independently-declared copies of the same table with no consumer until
    Story 6.5 — this cross-check is the only thing keeping them from
    silently drifting apart before then."""
    from pyforge.warden.license import DEFAULT_LICENSE_POLICY

    assert EffectiveConfig().license_policy == dict(DEFAULT_LICENSE_POLICY)
