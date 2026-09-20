"""Unit tests for ``pyforge.marshal.core.policy`` (Story 1.3,
AD-10/AD-16/AD-26/AD-35) -- ``compose()`` across every I/O & Edge-Case
Matrix scenario, provenance per layer, determinism of ``content_hash``,
``seed_view()`` isolation, secret redaction (via a synthetic fixture, since
none of the 14 real fields are secret-shaped), and the "compose() never
raises on malformed CONTENT" guarantee.

``MRS-POLICY-001/002/003`` are real, already-registered codes (Story 1.3's
first real registrations after Story 1.2's two) -- unlike
``test_model.py``'s synthetic-code fixtures, no monkeypatching is needed
here.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.core import policy, verdict
from pyforge.marshal.core.landing import LandingRule
from pyforge.marshal.core.model import Verdict
from pyforge.marshal.core.policy import (
    DEFAULT_POLICY,
    REDACTED_SENTINEL,
    SECRET_KEY_SUFFIXES,
    EffectivePolicy,
    PolicyField,
    PolicyLayer,
    compose,
    is_secret_key,
    redact,
)

# --- PolicyLayer / PolicyField basics ---------------------------------------


def test_policy_layer_members_and_values():
    assert PolicyLayer.DEFAULT.value == "default"
    assert PolicyLayer.PROJECT.value == "project"
    assert PolicyLayer.FLAG.value == "flag"


def test_policy_field_coerces_layer_from_raw_string():
    field = PolicyField(value="x", layer="project", raw_source="x")
    assert field.layer is PolicyLayer.PROJECT


def test_policy_field_rejects_invalid_layer():
    with pytest.raises(ValueError):
        PolicyField(value="x", layer="not-a-layer", raw_source="x")


# --- compose(): the I/O & Edge-Case Matrix -----------------------------------


def test_all_defaults_every_field_is_layer_default():
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    assert effective.verify_commands.layer is PolicyLayer.DEFAULT
    assert effective.merge_subject_template.layer is PolicyLayer.DEFAULT
    assert effective.model_tier_map.layer is PolicyLayer.DEFAULT
    assert effective.worktree_seed_paths.layer is PolicyLayer.DEFAULT
    assert effective.epic_surfaces.layer is PolicyLayer.DEFAULT
    assert effective.landing_rules.layer is PolicyLayer.DEFAULT
    assert effective.landing_merge_strategy.layer is PolicyLayer.DEFAULT
    assert effective.landing_branch_retirement.layer is PolicyLayer.DEFAULT
    assert effective.landing_resync.layer is PolicyLayer.DEFAULT
    for field in effective.seed_view().values():
        assert field.layer is PolicyLayer.DEFAULT


def test_all_defaults_values_match_default_policy():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert effective.verify_commands.value == DEFAULT_POLICY["verify_commands"]
    assert effective.merge_subject_template.value == DEFAULT_POLICY["merge_subject_template"]
    assert effective.model_tier_map.value == DEFAULT_POLICY["model_tier_map"]
    seed = effective.seed_view()
    assert seed["gate_mode"].value == DEFAULT_POLICY["gate_mode"]
    assert seed["frozen_surfaces"].value == DEFAULT_POLICY["frozen_surfaces"]
    assert seed["max_dev_attempts"].value == DEFAULT_POLICY["max_dev_attempts"]
    assert seed["max_review_cycles"].value == DEFAULT_POLICY["max_review_cycles"]
    assert seed["max_followup_reviews"].value == DEFAULT_POLICY["max_followup_reviews"]
    assert seed["idle_threshold_minutes"].value == DEFAULT_POLICY["idle_threshold_minutes"]
    assert seed["max_tokens_per_story"].value == DEFAULT_POLICY["max_tokens_per_story"]
    assert seed["max_tokens_per_run"].value == DEFAULT_POLICY["max_tokens_per_run"]
    assert seed["max_wall_clock_minutes_per_story"].value == DEFAULT_POLICY["max_wall_clock_minutes_per_story"]
    assert seed["max_wall_clock_minutes_per_run"].value == DEFAULT_POLICY["max_wall_clock_minutes_per_run"]


def test_project_overrides_one_key():
    effective, findings = compose(project_slug="acme", project={"gate_mode": "none"}, flags={})
    assert findings == ()
    seed = effective.seed_view()
    assert seed["gate_mode"].value == "none"
    assert seed["gate_mode"].layer is PolicyLayer.PROJECT
    assert seed["gate_mode"].raw_source == "none"
    # every other field is still default
    assert seed["max_dev_attempts"].layer is PolicyLayer.DEFAULT
    assert effective.verify_commands.layer is PolicyLayer.DEFAULT


def test_flag_wins_over_project():
    effective, findings = compose(
        project_slug="acme",
        project={"gate_mode": "none"},
        flags={"gate_mode": "per-epic"},
    )
    assert findings == ()
    gate_mode = effective.seed_view()["gate_mode"]
    assert gate_mode.value == "per-epic"
    assert gate_mode.layer is PolicyLayer.FLAG


def test_unknown_project_key_is_ignored_and_reported():
    effective, findings = compose(project_slug="acme", project={"bogus_key": 1}, flags={})
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MRS-POLICY-001"
    assert finding.path == "project"
    assert "bogus_key" in finding.message
    # the composed policy has no trace of the unknown key
    assert not hasattr(effective, "bogus_key")
    assert "bogus_key" not in effective.seed_view()


def test_unknown_flag_key_is_ignored_and_reported():
    effective, findings = compose(project_slug="acme", project={}, flags={"bogus_key": 1})
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MRS-POLICY-001"
    assert finding.path == "flag"


def test_malformed_gate_mode_falls_back_to_default():
    effective, findings = compose(project_slug="acme", project={}, flags={"gate_mode": "yolo"})
    seed = effective.seed_view()
    assert seed["gate_mode"].value == DEFAULT_POLICY["gate_mode"]
    assert seed["gate_mode"].layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MRS-POLICY-003"
    assert finding.path == "flag"
    assert "gate_mode" in finding.message


def test_negative_attempt_count_falls_back_to_default():
    effective, findings = compose(project_slug="acme", project={"max_dev_attempts": -1}, flags={})
    seed = effective.seed_view()
    assert seed["max_dev_attempts"].value == DEFAULT_POLICY["max_dev_attempts"]
    assert seed["max_dev_attempts"].layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MRS-POLICY-003"
    assert finding.path == "project"


def test_worktree_seed_paths_generation_from_slug():
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    assert effective.worktree_seed_paths.value == (
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
    )
    assert effective.worktree_seed_paths.layer is PolicyLayer.DEFAULT


def test_worktree_seed_paths_appends_project_extras():
    effective, findings = compose(
        project_slug="acme",
        project={"worktree_seed_paths": ["extra/one", "extra/two"]},
        flags={},
    )
    assert findings == ()
    assert effective.worktree_seed_paths.value == (
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
        "extra/one",
        "extra/two",
    )
    assert effective.worktree_seed_paths.layer is PolicyLayer.PROJECT


def test_worktree_seed_paths_never_hardcodes_a_project_name():
    """FR-50: switching projects requires no edit to any shared file --
    proven by the base paths differing purely as a function of slug."""
    acme_effective, _ = compose(project_slug="acme", project={}, flags={})
    widget_effective, _ = compose(project_slug="widget-co", project={}, flags={})
    assert acme_effective.worktree_seed_paths.value != widget_effective.worktree_seed_paths.value
    assert "acme" in acme_effective.worktree_seed_paths.value[0]
    assert "widget-co" in widget_effective.worktree_seed_paths.value[0]


def test_determinism_identical_inputs_produce_identical_hash():
    first, _ = compose(project_slug="acme", project={"gate_mode": "none"}, flags={"max_dev_attempts": 5})
    second, _ = compose(project_slug="acme", project={"gate_mode": "none"}, flags={"max_dev_attempts": 5})
    assert first.content_hash == second.content_hash


def test_different_inputs_produce_different_hash():
    first, _ = compose(project_slug="acme", project={}, flags={})
    second, _ = compose(project_slug="acme", project={"gate_mode": "none"}, flags={})
    assert first.content_hash != second.content_hash


def test_seed_view_returns_all_seventeen_seed_fields():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    seed = effective.seed_view()
    assert set(seed.keys()) == {
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
        "max_parallel",
        "review_on_timeout",
        "review_on_status_contradiction",
        "dev_contract_nudge",
        "operator_enabled",
        "stream_capture_kb",
        "review_min_score",
    }
    assert all(isinstance(field, PolicyField) for field in seed.values())


def test_seed_fields_are_not_reachable_as_public_attributes():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    for key in (
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
        "max_parallel",
        "review_on_timeout",
        "review_on_status_contradiction",
        "dev_contract_nudge",
        "operator_enabled",
        "stream_capture_kb",
    ):
        assert not hasattr(effective, key)


def test_secret_redaction_via_synthetic_field_name():
    """None of the 14 real fields are secret-shaped -- the mechanism is
    proven against a synthetic fixture, mirroring findings.py/verdict.py's
    own "empty registry, mechanism proven synthetically" precedent."""
    assert is_secret_key("GITHUB_TOKEN")
    assert is_secret_key("api_key")
    assert is_secret_key("db_secret")
    assert is_secret_key("admin_password")
    assert not is_secret_key("gate_mode")
    assert redact("GITHUB_TOKEN", "super-secret-value") == REDACTED_SENTINEL
    assert redact("gate_mode", "none") == "none"


def test_none_of_the_real_keys_are_secret_shaped():
    all_keys = {
        "verify_commands",
        "worktree_seed_paths",
        "merge_subject_template",
        "model_tier_map",
        "epic_surfaces",
        "landing_rules",
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
        "review_on_timeout",
        "review_on_status_contradiction",
        "dev_contract_nudge",
        "operator_enabled",
        "stream_capture_kb",
    }
    assert not any(is_secret_key(key) for key in all_keys)


def test_secret_key_suffixes_are_case_insensitive():
    assert is_secret_key("my_token")
    assert is_secret_key("MY_TOKEN")
    assert is_secret_key("My_Token")


def test_secret_key_suffixes_contents():
    assert SECRET_KEY_SUFFIXES == frozenset({"_TOKEN", "_KEY", "_SECRET", "_PASSWORD"})


# --- model_tier_map validation ------------------------------------------------


def test_model_tier_map_valid_shape_accepted():
    effective, findings = compose(
        project_slug="acme",
        project={"model_tier_map": {"easy": {"dev": "haiku", "review": "sonnet"}}},
        flags={},
    )
    assert findings == ()
    assert effective.model_tier_map.value == {"easy": {"dev": "haiku", "review": "sonnet"}}
    assert effective.model_tier_map.layer is PolicyLayer.PROJECT


def test_model_tier_map_cross_provider_inline_table_accepted():
    tier_map = {
        "easy": {
            "dev": {"harness": "gemini", "model": "gemini-3.7-flash"},
        }
    }
    effective, findings = compose(project_slug="acme", project={"model_tier_map": tier_map}, flags={})
    assert findings == ()
    assert effective.model_tier_map.value["easy"]["dev"]["model"] == "gemini-3.7-flash"


def test_model_tier_map_bad_stage_name_falls_back_and_reports():
    effective, findings = compose(
        project_slug="acme",
        project={"model_tier_map": {"easy": {"bogus_stage": "haiku"}}},
        flags={},
    )
    assert effective.model_tier_map.value == DEFAULT_POLICY["model_tier_map"]
    assert effective.model_tier_map.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


def test_model_tier_map_non_string_model_name_falls_back_and_reports():
    effective, findings = compose(
        project_slug="acme",
        project={"model_tier_map": {"easy": {"dev": 123}}},
        flags={},
    )
    assert effective.model_tier_map.value == DEFAULT_POLICY["model_tier_map"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


# --- mcp_servers validation (Story 6.9, AD-43) --------------------------------


def test_mcp_servers_default_is_empty_mapping():
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert effective.mcp_servers.value == {}
    assert effective.mcp_servers.layer is PolicyLayer.DEFAULT
    assert findings == ()


def test_mcp_servers_valid_shape_accepted():
    effective, findings = compose(
        project_slug="acme",
        project={"mcp_servers": {"atlas": {"command": "atlas-mcp", "args": ["--stdio"], "env": {"FOO": "bar"}}}},
        flags={},
    )
    assert findings == ()
    assert effective.mcp_servers.value == {
        "atlas": {"command": "atlas-mcp", "args": ("--stdio",), "env": {"FOO": "bar"}}
    }
    assert effective.mcp_servers.layer is PolicyLayer.PROJECT


def test_mcp_servers_command_only_defaults_args_and_env():
    effective, findings = compose(
        project_slug="acme",
        project={"mcp_servers": {"atlas": {"command": "atlas-mcp"}}},
        flags={},
    )
    assert findings == ()
    assert effective.mcp_servers.value == {"atlas": {"command": "atlas-mcp", "args": (), "env": {}}}


def test_mcp_servers_missing_command_falls_back_and_reports():
    effective, findings = compose(
        project_slug="acme",
        project={"mcp_servers": {"atlas": {"args": ["--stdio"]}}},
        flags={},
    )
    assert effective.mcp_servers.value == DEFAULT_POLICY["mcp_servers"]
    assert effective.mcp_servers.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


def test_mcp_servers_empty_server_name_falls_back_and_reports():
    effective, findings = compose(
        project_slug="acme",
        project={"mcp_servers": {"": {"command": "atlas-mcp"}}},
        flags={},
    )
    assert effective.mcp_servers.value == DEFAULT_POLICY["mcp_servers"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_mcp_servers_unknown_entry_key_falls_back_and_reports():
    effective, findings = compose(
        project_slug="acme",
        project={"mcp_servers": {"atlas": {"command": "atlas-mcp", "bogus": "x"}}},
        flags={},
    )
    assert effective.mcp_servers.value == DEFAULT_POLICY["mcp_servers"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_mcp_servers_non_mapping_falls_back_and_reports():
    effective, findings = compose(project_slug="acme", project={"mcp_servers": "not-a-mapping"}, flags={})
    assert effective.mcp_servers.value == DEFAULT_POLICY["mcp_servers"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_mcp_servers_value_is_deeply_immutable():
    effective, _ = compose(
        project_slug="acme",
        project={"mcp_servers": {"atlas": {"command": "atlas-mcp"}}},
        flags={},
    )
    with pytest.raises(TypeError):
        effective.mcp_servers.value["atlas"] = {"command": "other"}  # type: ignore[index]


# --- context validation (Story 28.1, SPEC-marshal-token-economy CAP-1) --------


def test_context_is_static_not_seed():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert "context" not in effective.seed_view()
    assert isinstance(effective.context, PolicyField)


def test_context_default_is_empty_mapping():
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    assert effective.context.value == {}
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert effective.context.layer is PolicyLayer.DEFAULT


def test_context_valid_shape_accepted():
    effective, findings = compose(
        project_slug="acme",
        project={"context": {"wire": {"enabled": True, "aggressiveness": "high"}}},
        flags={},
    )
    assert findings == ()
    assert effective.context.value == {"wire": {"enabled": True, "aggressiveness": "high"}}
    assert effective.context.layer is PolicyLayer.PROJECT


def test_context_enabled_without_aggressiveness_omits_the_key():
    effective, findings = compose(project_slug="acme", project={"context": {"wire": {"enabled": True}}}, flags={})
    assert findings == ()
    assert effective.context.value == {"wire": {"enabled": True}}


def test_context_rejects_non_mapping_falls_back_and_reports():
    effective, findings = compose(project_slug="acme", project={"context": "not-a-mapping"}, flags={})
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert effective.context.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_context_rejects_unknown_layer_name():
    effective, findings = compose(
        project_slug="acme",
        project={"context": {"bogus-layer": {"enabled": True}}},
        flags={},
    )
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_context_rejects_missing_enabled():
    effective, findings = compose(
        project_slug="acme",
        project={"context": {"wire": {"aggressiveness": "high"}}},
        flags={},
    )
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_context_accepts_auto_enabled_for_wire_layer():
    """Story 46.4: the literal string "auto" is valid ``enabled`` only for
    the ``wire`` layer -- the tri-state resolved later, against the
    concrete harness profile, by ``harness_profile.resolve_wire_enabled``."""
    effective, findings = compose(project_slug="acme", project={"context": {"wire": {"enabled": "auto"}}}, flags={})
    assert findings == ()
    assert effective.context.value == {"wire": {"enabled": "auto"}}
    assert effective.context.layer is PolicyLayer.PROJECT


@pytest.mark.parametrize("layer", [name for name in policy.CONTEXT_LAYER_NAMES if name != "wire"])
def test_context_rejects_auto_enabled_for_non_wire_layers(layer):
    """The "auto" tri-state is ``wire``-only; the other 4 layers keep the
    existing strict-``bool``-only posture."""
    effective, findings = compose(project_slug="acme", project={"context": {layer: {"enabled": "auto"}}}, flags={})
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert effective.context.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1


def test_context_rejects_non_bool_enabled():
    effective, findings = compose(project_slug="acme", project={"context": {"wire": {"enabled": "yes"}}}, flags={})
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_context_rejects_malformed_aggressiveness():
    effective, findings = compose(
        project_slug="acme",
        project={"context": {"wire": {"enabled": True, "aggressiveness": "extreme"}}},
        flags={},
    )
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_context_rejects_unknown_entry_key():
    effective, findings = compose(
        project_slug="acme",
        project={"context": {"wire": {"enabled": True, "bogus": 1}}},
        flags={},
    )
    assert effective.context.value == DEFAULT_POLICY["context"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_context_value_is_deeply_immutable():
    effective, _ = compose(project_slug="acme", project={"context": {"wire": {"enabled": True}}}, flags={})
    with pytest.raises(TypeError):
        effective.context.value["output"] = {"enabled": True}  # type: ignore[index]


# --- resolve_context_layers (Story 28.1's single composition site) -----------


def test_resolve_context_layers_default_all_off():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    resolved = policy.resolve_context_layers(effective)
    assert set(resolved) == set(policy.CONTEXT_LAYER_NAMES)
    for layer in policy.CONTEXT_LAYER_NAMES:
        assert resolved[layer] == {"enabled": False, "aggressiveness": "medium"}


def test_resolve_context_layers_reflects_a_partial_declaration():
    effective, _ = compose(
        project_slug="acme",
        project={"context": {"wire": {"enabled": True, "aggressiveness": "high"}}},
        flags={},
    )
    resolved = policy.resolve_context_layers(effective)
    assert resolved["wire"] == {"enabled": True, "aggressiveness": "high"}
    for layer in policy.CONTEXT_LAYER_NAMES:
        if layer == "wire":
            continue
        assert resolved[layer] == {"enabled": False, "aggressiveness": "medium"}


def test_resolve_context_layers_passes_wire_auto_through_unresolved():
    """Story 46.4: this function runs at policy-composition time, before any
    harness profile is chosen -- ``wire``'s declared ``"auto"`` must pass
    through as the literal string, never force-coerced to ``bool`` (which
    would silently destroy the tri-state, since ``bool("auto")`` is
    ``True``). The other 4 layers still resolve to a real ``bool``."""
    effective, _ = compose(
        project_slug="acme",
        project={
            "context": {
                "wire": {"enabled": "auto"},
                "output": {"enabled": True},
            }
        },
        flags={},
    )
    resolved = policy.resolve_context_layers(effective)
    assert resolved["wire"] == {"enabled": "auto", "aggressiveness": "medium"}
    assert isinstance(resolved["wire"]["enabled"], str)
    assert resolved["output"] == {"enabled": True, "aggressiveness": "medium"}
    assert resolved["output"]["enabled"] is True


def test_resolve_context_layers_wire_explicit_bool_still_resolves_to_bool():
    """A force-override (explicit ``true``/``false``) is unaffected by the
    tri-state pass-through -- it still resolves to a real ``bool``."""
    effective, _ = compose(
        project_slug="acme",
        project={"context": {"wire": {"enabled": True}}},
        flags={},
    )
    resolved = policy.resolve_context_layers(effective)
    assert resolved["wire"] == {"enabled": True, "aggressiveness": "medium"}
    assert resolved["wire"]["enabled"] is True


def test_resolve_context_layers_fills_default_aggressiveness_when_omitted():
    effective, _ = compose(project_slug="acme", project={"context": {"output": {"enabled": True}}}, flags={})
    resolved = policy.resolve_context_layers(effective)
    assert resolved["output"] == {"enabled": True, "aggressiveness": "medium"}


def test_resolve_context_layers_returns_a_fresh_plain_dict():
    """JSON-safe on every call -- both `render_policy_toml` and
    `dispatch_once` hand this straight to `json.dumps`/`tomlkit` without a
    second conversion step (unlike `PolicyField.value`, which is frozen)."""
    effective, _ = compose(project_slug="acme", project={}, flags={})
    resolved = policy.resolve_context_layers(effective)
    assert isinstance(resolved, dict)
    for layer_dict in resolved.values():
        assert isinstance(layer_dict, dict)
    import json as _json

    _json.dumps(resolved)  # must not raise


def test_dispatch_max_parallel_two_on_real_marshal_policy_does_not_fire_scm_clamp():
    """Story 33.8: dispatch.max_parallel=2 composes without MRS-POLICY-007 --
    that advisory applies to scm max_parallel (SEED) only, not dispatch."""
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    if not policy_path.is_file():
        pytest.skip("marshal-policy.toml not present in this checkout")

    parsed = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    effective, findings = compose(project_slug="pyforge-marshal", project=parsed, flags={})
    assert effective.dispatch.value == {"max_parallel": 2}
    codes = {f.code for f in findings}
    assert "MRS-POLICY-007" not in codes


def test_the_real_pyforge_marshal_policy_declares_no_context_block():
    """Story 46.4 regression: the tracked marshal-policy.toml no longer
    force-declares `[context]` at all -- Story 33.2's five-layer enablement
    is superseded by the repo-default `_bmad-output/policy-defaults.toml`
    block (all 5 layers on, `wire` on the `"auto"` tri-state). Per
    `_merge_field`'s wholesale-per-field (not deep-merge) composition, a
    station file declaring ANY part of `[context]` would replace the repo
    default's entire value for that station -- so the station stays
    force-override-only by declaring nothing here at all. See
    `test_dispatch.py::test_compose_policy_on_real_repo_enables_all_context_layers_for_dispatch`
    for the fully-composed (repo-defaults + project) resolution."""
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    if not policy_path.is_file():
        pytest.skip("marshal-policy.toml not present in this checkout")

    parsed = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    assert "context" not in parsed


def test_context_escalation_threshold_defaults_when_absent():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert policy.resolve_compression_escalation_threshold(effective) == 0.8


def test_context_escalation_threshold_reads_declared_value():
    effective, _ = compose(
        project_slug="acme",
        project={"context": {"escalation_threshold": 0.85, "wire": {"enabled": True}}},
        flags={},
    )
    assert policy.resolve_compression_escalation_threshold(effective) == 0.85


def test_context_rejects_malformed_escalation_threshold():
    effective, findings = compose(
        project_slug="acme",
        project={"context": {"escalation_threshold": 1.5, "wire": {"enabled": True}}},
        flags={},
    )
    assert effective.context.value == {}
    assert any(f.code == "MRS-POLICY-002" for f in findings)


# --- scope_violation_mode validation (Story 28.15, CAP-17) --------------------


def test_scope_violation_mode_is_static_not_seed():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert "scope_violation_mode" not in effective.seed_view()
    assert isinstance(effective.scope_violation_mode, PolicyField)


def test_scope_violation_mode_default_is_warn_not_hard():
    """AC1: 'no scope-violation mode declared for a station ... warn
    default' -- an explicit operator decision, not today's prior 'hard'."""
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    assert effective.scope_violation_mode.value == "warn"
    assert effective.scope_violation_mode.value == DEFAULT_POLICY["scope_violation_mode"]
    assert effective.scope_violation_mode.layer is PolicyLayer.DEFAULT


@pytest.mark.parametrize("mode", ["hard", "warn", "off"])
def test_scope_violation_mode_accepts_closed_vocabulary(mode):
    effective, findings = compose(project_slug="acme", project={"scope_violation_mode": mode}, flags={})
    assert findings == ()
    assert effective.scope_violation_mode.value == mode
    assert effective.scope_violation_mode.layer is PolicyLayer.PROJECT


def test_scope_violation_mode_rejects_value_outside_closed_vocabulary():
    effective, findings = compose(project_slug="acme", project={"scope_violation_mode": "yolo"}, flags={})
    assert effective.scope_violation_mode.value == DEFAULT_POLICY["scope_violation_mode"]
    assert effective.scope_violation_mode.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


def test_scope_violation_mode_flag_layer_wins_over_project():
    effective, _ = compose(
        project_slug="acme",
        project={"scope_violation_mode": "hard"},
        flags={"scope_violation_mode": "off"},
    )
    mode = effective.scope_violation_mode
    assert mode.value == "off"
    assert mode.layer is PolicyLayer.FLAG


def test_scope_violation_mode_is_per_station_two_projects_compose_independently():
    """AC5: 'two stations with different declared modes, when each violates
    scope, then each station's mode applies independently' -- composition
    itself is the per-station isolation boundary: each call gets its own
    `project` mapping, so one station's declared mode can never leak into
    another's composed EffectivePolicy."""
    station_a, _ = compose(project_slug="pyforge-a", project={"scope_violation_mode": "hard"}, flags={})
    station_b, _ = compose(project_slug="pyforge-b", project={"scope_violation_mode": "off"}, flags={})
    station_c, _ = compose(project_slug="pyforge-c", project={}, flags={})
    assert station_a.scope_violation_mode.value == "hard"
    assert station_b.scope_violation_mode.value == "off"
    assert station_c.scope_violation_mode.value == "warn"


# --- epic_surfaces validation (Story 2.3, AD-27) ------------------------------


def test_epic_surfaces_is_static_not_seed():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert "epic_surfaces" not in effective.seed_view()
    assert isinstance(effective.epic_surfaces, PolicyField)


def test_epic_surfaces_defaults_to_empty_mapping():
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    assert effective.epic_surfaces.value == {}
    assert effective.epic_surfaces.value == DEFAULT_POLICY["epic_surfaces"]
    assert effective.epic_surfaces.layer is PolicyLayer.DEFAULT


def test_epic_surfaces_valid_shape_accepted():
    effective, findings = compose(
        project_slug="acme",
        project={"epic_surfaces": {"2": ["recipes/x/**", "recipes/y/**"]}},
        flags={},
    )
    assert findings == ()
    assert effective.epic_surfaces.value == {"2": ("recipes/x/**", "recipes/y/**")}
    assert effective.epic_surfaces.layer is PolicyLayer.PROJECT


def test_epic_surfaces_multiple_epics():
    effective, findings = compose(
        project_slug="acme",
        project={"epic_surfaces": {"2": ["a/**"], "3": ["b/**"]}},
        flags={},
    )
    assert findings == ()
    assert effective.epic_surfaces.value == {"2": ("a/**",), "3": ("b/**",)}


def test_epic_surfaces_rejects_non_mapping_falls_back_and_reports():
    effective, findings = compose(project_slug="acme", project={"epic_surfaces": "not-a-mapping"}, flags={})
    assert effective.epic_surfaces.value == DEFAULT_POLICY["epic_surfaces"]
    assert effective.epic_surfaces.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_epic_surfaces_rejects_non_string_epic_key():
    effective, findings = compose(project_slug="acme", project={"epic_surfaces": {2: ["a/**"]}}, flags={})
    assert effective.epic_surfaces.value == DEFAULT_POLICY["epic_surfaces"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_epic_surfaces_rejects_empty_string_epic_key():
    effective, findings = compose(project_slug="acme", project={"epic_surfaces": {"": ["a/**"]}}, flags={})
    assert effective.epic_surfaces.value == DEFAULT_POLICY["epic_surfaces"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_epic_surfaces_rejects_non_numeric_epic_key():
    """Review finding (Blind Hunter): a typo'd key like "epic-2" or "2 "
    previously composed successfully with no diagnostic and could never
    match any real epic (str(story_key.epic) is always plain digits) -- a
    permanently dead, silently-inert allowlist entry."""
    effective, findings = compose(project_slug="acme", project={"epic_surfaces": {"epic-2": ["a/**"]}}, flags={})
    assert effective.epic_surfaces.value == DEFAULT_POLICY["epic_surfaces"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_epic_surfaces_rejects_non_str_tuple_value():
    effective, findings = compose(project_slug="acme", project={"epic_surfaces": {"2": "recipes/x/**"}}, flags={})
    assert effective.epic_surfaces.value == DEFAULT_POLICY["epic_surfaces"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_epic_surfaces_rejects_empty_glob_string_in_value():
    effective, findings = compose(project_slug="acme", project={"epic_surfaces": {"2": ["a/**", ""]}}, flags={})
    assert effective.epic_surfaces.value == DEFAULT_POLICY["epic_surfaces"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_epic_surfaces_value_is_deeply_immutable():
    effective, _ = compose(project_slug="acme", project={"epic_surfaces": {"2": ["a/**"]}}, flags={})
    with pytest.raises(TypeError):
        effective.epic_surfaces.value["3"] = ("b/**",)  # type: ignore[index]


def test_epic_surfaces_flag_layer_wins_over_project():
    effective, findings = compose(
        project_slug="acme",
        project={"epic_surfaces": {"2": ["a/**"]}},
        flags={"epic_surfaces": {"2": ["b/**"]}},
    )
    assert findings == ()
    assert effective.epic_surfaces.value == {"2": ("b/**",)}
    assert effective.epic_surfaces.layer is PolicyLayer.FLAG


def test_verify_commands_non_string_entry_falls_back_and_reports():
    effective, findings = compose(project_slug="acme", project={"verify_commands": ["ok", 123]}, flags={})
    assert effective.verify_commands.value == DEFAULT_POLICY["verify_commands"]
    assert effective.verify_commands.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


def test_verify_commands_valid_list_accepted():
    effective, findings = compose(project_slug="acme", project={"verify_commands": ["pytest -q"]}, flags={})
    assert findings == ()
    assert effective.verify_commands.value == ("pytest -q",)
    assert effective.verify_commands.layer is PolicyLayer.PROJECT


# --- landing_rules / landing_merge_strategy / landing_branch_retirement /
# landing_resync validation (Story 4.7, AD-40) --------------------------------


def test_landing_keys_are_static_not_seed():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    for key in (
        "landing_rules",
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
    ):
        assert key not in effective.seed_view()
        assert isinstance(getattr(effective, key), PolicyField)


def test_landing_keys_default_values():
    """The I/O & Edge-Case Matrix's 'no landing keys declared at any layer'
    row."""
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    assert effective.landing_rules.value == ()
    assert effective.landing_merge_strategy.value == "merge"
    assert effective.landing_branch_retirement.value is True
    assert effective.landing_resync.value is True
    for key in (
        "landing_rules",
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
    ):
        assert getattr(effective, key).layer is PolicyLayer.DEFAULT


def test_landing_rules_valid_rule_with_both_label_and_required_check():
    """The I/O & Edge-Case Matrix's 'valid landing_rules with both label and
    required_check set' row."""
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {
                    "name": "both",
                    "trigger_path_glob": "recipes/**",
                    "trigger_mode": "exclude",
                    "label": "maintenance",
                    "required_check": "some-check",
                }
            ]
        },
        flags={},
    )
    assert findings == ()
    assert effective.landing_rules.value == (
        LandingRule(
            name="both",
            trigger_path_glob="recipes/**",
            trigger_mode="exclude",
            label="maintenance",
            required_check="some-check",
            ungated=False,
        ),
    )
    assert effective.landing_rules.layer is PolicyLayer.PROJECT


def test_landing_rules_this_repos_own_two_real_rules():
    """This project's own `marshal-policy.toml` seeds exactly these two
    rules -- proven directly against the same shape, matching the Manual
    check the spec names. `trigger_mode` differs between the two
    (corrected in review, 2026-08-06): `maintenance-label` is "exclude",
    `environment-yaml-sync` is "include" -- the two rules need OPPOSITE
    match directions, which is exactly why `trigger_mode` exists."""
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {
                    "name": "maintenance-label",
                    "trigger_path_glob": "recipes/**",
                    "trigger_mode": "exclude",
                    "label": "maintenance",
                    "ungated": False,
                },
                {
                    "name": "environment-yaml-sync",
                    "trigger_path_glob": "pixi.toml",
                    "trigger_mode": "include",
                    "required_check": "environment-yaml-sync",
                    "ungated": True,
                },
            ]
        },
        flags={},
    )
    assert findings == ()
    assert effective.landing_rules.value == (
        LandingRule(
            name="maintenance-label",
            trigger_path_glob="recipes/**",
            trigger_mode="exclude",
            label="maintenance",
            ungated=False,
        ),
        LandingRule(
            name="environment-yaml-sync",
            trigger_path_glob="pixi.toml",
            trigger_mode="include",
            required_check="environment-yaml-sync",
            ungated=True,
        ),
    )


def test_landing_rules_rejects_rule_with_neither_label_nor_required_check():
    """The I/O & Edge-Case Matrix's 'a rule with neither label nor
    required_check' row: rejected, finding names the layer and the rule."""
    effective, findings = compose(
        project_slug="acme",
        project={"landing_rules": [{"name": "meaningless", "trigger_path_glob": "a/**", "trigger_mode": "exclude"}]},
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert effective.landing_rules.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"
    assert "meaningless" in findings[0].message


def test_landing_rules_rejects_duplicate_name_in_the_same_tuple():
    """The I/O & Edge-Case Matrix's 'a rule with a duplicate name' row."""
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {"name": "dup", "trigger_path_glob": "a/**", "trigger_mode": "exclude", "label": "x"},
                {"name": "dup", "trigger_path_glob": "b/**", "trigger_mode": "exclude", "label": "y"},
            ]
        },
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert "dup" in findings[0].message


def test_landing_rules_rejects_non_list():
    effective, findings = compose(project_slug="acme", project={"landing_rules": "not-a-list"}, flags={})
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_landing_rules_rejects_empty_name():
    effective, findings = compose(
        project_slug="acme",
        project={"landing_rules": [{"name": "", "trigger_path_glob": "a/**", "trigger_mode": "exclude", "label": "x"}]},
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_landing_rules_rejects_empty_trigger_path_glob():
    effective, findings = compose(
        project_slug="acme",
        project={"landing_rules": [{"name": "x", "trigger_path_glob": "", "trigger_mode": "exclude", "label": "x"}]},
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_landing_rules_rejects_unknown_field_in_rule():
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {
                    "name": "x",
                    "trigger_path_glob": "a/**",
                    "trigger_mode": "exclude",
                    "label": "x",
                    "bogus": "y",
                }
            ]
        },
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_landing_rules_rejects_non_bool_ungated():
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {
                    "name": "x",
                    "trigger_path_glob": "a/**",
                    "trigger_mode": "exclude",
                    "label": "x",
                    "ungated": "yes",
                }
            ]
        },
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_landing_rules_flag_layer_wins_over_project():
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [{"name": "p", "trigger_path_glob": "a/**", "trigger_mode": "exclude", "label": "x"}]
        },
        flags={"landing_rules": [{"name": "f", "trigger_path_glob": "b/**", "trigger_mode": "include", "label": "y"}]},
    )
    assert findings == ()
    assert effective.landing_rules.value == (
        LandingRule(name="f", trigger_path_glob="b/**", trigger_mode="include", label="y"),
    )
    assert effective.landing_rules.layer is PolicyLayer.FLAG


# --- landing_rules: trigger_mode validation (bad_spec fix, 2026-08-06) -------


def test_landing_rules_rejects_missing_trigger_mode():
    """`trigger_mode` has no default -- a rule that omits it entirely is
    malformed, the same as any other missing required field."""
    effective, findings = compose(
        project_slug="acme",
        project={"landing_rules": [{"name": "x", "trigger_path_glob": "a/**", "label": "y"}]},
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


@pytest.mark.parametrize("bad_mode", ["both", "EXCLUDE", "", None, 1, ["exclude"]])
def test_landing_rules_rejects_trigger_mode_outside_closed_vocabulary(bad_mode):
    """Same closed-vocabulary validation shape as `landing_merge_strategy`'s
    own `_valid_merge_strategy`."""
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {
                    "name": "x",
                    "trigger_path_glob": "a/**",
                    "trigger_mode": bad_mode,
                    "label": "y",
                }
            ]
        },
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


@pytest.mark.parametrize("mode", ["exclude", "include"])
def test_landing_rules_accepts_both_trigger_modes(mode):
    effective, findings = compose(
        project_slug="acme",
        project={"landing_rules": [{"name": "x", "trigger_path_glob": "a/**", "trigger_mode": mode, "label": "y"}]},
        flags={},
    )
    assert findings == ()
    assert effective.landing_rules.value[0].trigger_mode == mode


# --- landing_rules: ungated requires required_check (review finding P3) -----


def test_landing_rules_rejects_ungated_without_required_check():
    """`ungated=True` on a label-only rule is a nonsensical combination:
    "ungated" describes a check that can't be suppressed by a label, which
    is meaningless without a check."""
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {
                    "name": "x",
                    "trigger_path_glob": "a/**",
                    "trigger_mode": "exclude",
                    "label": "y",
                    "ungated": True,
                }
            ]
        },
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_landing_rules_accepts_ungated_with_required_check():
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {
                    "name": "x",
                    "trigger_path_glob": "a/**",
                    "trigger_mode": "include",
                    "required_check": "some-check",
                    "ungated": True,
                }
            ]
        },
        flags={},
    )
    assert findings == ()
    assert effective.landing_rules.value[0].ungated is True


# --- landing_rules: malformed finding names the specific bad rule (P6) ------


def test_landing_rules_malformed_finding_names_the_specific_bad_rule():
    """With several rules in the list, the finding must point at the ONE
    malformed entry by name, not just dump the entire raw list -- a human
    scanning the message for the bad rule among several valid siblings
    needs a direct pointer."""
    effective, findings = compose(
        project_slug="acme",
        project={
            "landing_rules": [
                {"name": "good1", "trigger_path_glob": "a/**", "trigger_mode": "exclude", "label": "x"},
                {"name": "bad-one", "trigger_path_glob": "b/**", "trigger_mode": "exclude"},
                {"name": "good2", "trigger_path_glob": "c/**", "trigger_mode": "exclude", "label": "y"},
            ]
        },
        flags={},
    )
    assert effective.landing_rules.value == DEFAULT_POLICY["landing_rules"]
    assert len(findings) == 1
    assert "bad-one" in findings[0].message
    assert "good1" not in findings[0].message
    assert "good2" not in findings[0].message


@pytest.mark.parametrize("strategy", ["merge", "squash", "rebase"])
def test_landing_merge_strategy_accepts_closed_vocabulary(strategy):
    effective, findings = compose(project_slug="acme", project={"landing_merge_strategy": strategy}, flags={})
    assert findings == ()
    assert effective.landing_merge_strategy.value == strategy
    assert effective.landing_merge_strategy.layer is PolicyLayer.PROJECT


def test_landing_merge_strategy_rejects_value_outside_closed_vocabulary():
    """The I/O & Edge-Case Matrix's 'landing_merge_strategy outside the
    closed vocabulary' row."""
    effective, findings = compose(project_slug="acme", project={"landing_merge_strategy": "fast-forward"}, flags={})
    assert effective.landing_merge_strategy.value == DEFAULT_POLICY["landing_merge_strategy"]
    assert effective.landing_merge_strategy.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


@pytest.mark.parametrize("key", ["landing_branch_retirement", "landing_resync"])
def test_landing_bool_keys_accept_valid_bool(key):
    effective, findings = compose(project_slug="acme", project={key: False}, flags={})
    assert findings == ()
    assert getattr(effective, key).value is False
    assert getattr(effective, key).layer is PolicyLayer.PROJECT


@pytest.mark.parametrize("key", ["landing_branch_retirement", "landing_resync"])
@pytest.mark.parametrize("bad_value", ["true", 1, 0, None, [], {}])
def test_landing_bool_keys_reject_non_bool_values(key, bad_value):
    effective, findings = compose(project_slug="acme", project={key: bad_value}, flags={})
    assert getattr(effective, key).value == DEFAULT_POLICY[key]
    assert getattr(effective, key).layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_landing_rules_value_is_a_tuple_of_landing_rule_instances():
    effective, _ = compose(
        project_slug="acme",
        project={
            "landing_rules": [{"name": "x", "trigger_path_glob": "a/**", "trigger_mode": "exclude", "label": "y"}]
        },
        flags={},
    )
    assert isinstance(effective.landing_rules.value, tuple)
    assert all(isinstance(rule, LandingRule) for rule in effective.landing_rules.value)


def test_content_hash_handles_a_nonempty_landing_rules():
    """Guards content_hash against crashing on a LandingRule-holding field --
    json.dumps cannot natively serialize a dataclass instance, so
    core/policy.py's `_to_plain` must convert it first."""
    effective, _ = compose(
        project_slug="acme",
        project={
            "landing_rules": [{"name": "x", "trigger_path_glob": "a/**", "trigger_mode": "exclude", "label": "y"}]
        },
        flags={},
    )
    assert isinstance(effective.content_hash, str) and len(effective.content_hash) == 64


# --- landing_resync_commands validation (Story 4.5, AD-40) -------------------
# Validated IDENTICALLY to verify_commands (`_valid_str_tuple`) -- mirrors
# that key's own tests above almost verbatim.


def test_landing_resync_commands_is_static_not_seed():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert effective.landing_resync_commands.value == ()
    assert effective.landing_resync_commands.layer is PolicyLayer.DEFAULT


def test_landing_resync_commands_valid_list_accepted():
    effective, findings = compose(
        project_slug="acme",
        project={"landing_resync_commands": ["marshal deploy promote"]},
        flags={},
    )
    assert findings == ()
    assert effective.landing_resync_commands.value == ("marshal deploy promote",)
    assert effective.landing_resync_commands.layer is PolicyLayer.PROJECT


def test_landing_resync_commands_non_string_entry_falls_back_and_reports():
    effective, findings = compose(project_slug="acme", project={"landing_resync_commands": ["ok", 123]}, flags={})
    assert effective.landing_resync_commands.value == DEFAULT_POLICY["landing_resync_commands"]
    assert effective.landing_resync_commands.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


def test_landing_resync_commands_rejects_empty_string_entry():
    effective, findings = compose(project_slug="acme", project={"landing_resync_commands": [""]}, flags={})
    assert effective.landing_resync_commands.value == ()
    assert findings[0].code == "MRS-POLICY-002"


# --- idle_threshold_minutes validation (Story 3.5, FR-12) --------------------


def test_idle_threshold_minutes_project_override_applies():
    effective, findings = compose(project_slug="acme", project={"idle_threshold_minutes": 10}, flags={})
    assert findings == ()
    field = effective.seed_view()["idle_threshold_minutes"]
    assert field.value == 10
    assert field.layer is PolicyLayer.PROJECT


def test_idle_threshold_minutes_accepts_a_fractional_value():
    """Unlike the int-only attempt-count fields, a fractional minute value
    is accepted -- useful for a synthetic sub-minute threshold no
    whole-number value could express."""
    effective, findings = compose(project_slug="acme", project={"idle_threshold_minutes": 0.5}, flags={})
    assert findings == ()
    assert effective.seed_view()["idle_threshold_minutes"].value == 0.5


@pytest.mark.parametrize(
    "bad_value",
    [
        0,
        -5,
        -0.5,
        "25",
        None,
        True,
        False,
        # Review finding: `nan` already failed the `> 0` test (IEEE 754 makes
        # every comparison against it false), but `inf` PASSED it -- and TOML
        # 1.0 spells `inf` natively, so a project's own marshal-policy.toml
        # could set it. An infinite threshold composed cleanly, rendered as
        # the effective value, and then silently disabled the idle ladder for
        # every supervised run forever (elapsed/inf floor-divides to rung
        # NONE). A knob that can be set to a value which quietly turns the
        # feature off with no diagnostic is worse than one that refuses it.
        float("inf"),
        float("-inf"),
        float("nan"),
        # Follow-up review finding: FINITE here, infinite where it is used.
        # Every consumer converts this field to seconds, and `1e308 * 60.0`
        # is `inf` -- so this value passed the validator, composed cleanly,
        # rendered as the effective policy, and was then rejected by the
        # supervisor's own `threshold_s` guard one process later. The
        # sidecar exits 1 immediately and silently (its stderr goes only to
        # supervisor.log) while `spin` has already printed a
        # `supervisor_pid` and exited 0 -- the operator is told the run is
        # supervised when nothing is watching it. Rejecting it here makes it
        # the ordinary, visible malformed-value finding instead.
        1e308,
    ],
)
def test_idle_threshold_minutes_rejects_non_positive_or_non_numeric_values(bad_value):
    effective, findings = compose(project_slug="acme", project={"idle_threshold_minutes": bad_value}, flags={})
    assert effective.seed_view()["idle_threshold_minutes"].value == DEFAULT_POLICY["idle_threshold_minutes"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


# --- budget ceilings validation (Story 3.6, FR-13) ----------------------------
# The 4 new keys reuse `_valid_positive_number` verbatim -- the SAME
# validator `idle_threshold_minutes` above already exercises -- so this
# section mirrors that one's shape rather than re-deriving the bad-value
# matrix from scratch.

_BUDGET_CEILING_KEYS = (
    "max_tokens_per_story",
    "max_tokens_per_run",
    "max_wall_clock_minutes_per_story",
    "max_wall_clock_minutes_per_run",
)


@pytest.mark.parametrize("key", _BUDGET_CEILING_KEYS)
def test_budget_ceiling_project_override_applies(key):
    effective, findings = compose(project_slug="acme", project={key: 10}, flags={})
    assert findings == ()
    field = effective.seed_view()[key]
    assert field.value == 10
    assert field.layer is PolicyLayer.PROJECT


@pytest.mark.parametrize("key", _BUDGET_CEILING_KEYS)
def test_budget_ceiling_accepts_a_fractional_value(key):
    effective, findings = compose(project_slug="acme", project={key: 0.5}, flags={})
    assert findings == ()
    assert effective.seed_view()[key].value == 0.5


@pytest.mark.parametrize("key", _BUDGET_CEILING_KEYS)
@pytest.mark.parametrize(
    "bad_value",
    [0, -5, -0.5, "25", None, True, False, float("inf"), float("-inf"), float("nan"), 1e308],
)
def test_budget_ceiling_rejects_non_positive_or_non_numeric_values(key, bad_value):
    effective, findings = compose(project_slug="acme", project={key: bad_value}, flags={})
    assert effective.seed_view()[key].value == DEFAULT_POLICY[key]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


@pytest.mark.parametrize("key", _BUDGET_CEILING_KEYS)
def test_budget_ceiling_rejects_an_arbitrary_precision_int_without_raising(key):
    """Review finding: an int too large to convert to a C double made
    ``compose()`` RAISE ``OverflowError`` out of ``math.isfinite`` instead of
    returning the ordinary malformed-value finding.

    ``tomllib`` does not enforce TOML's own 64-bit integer bound, so a
    project's ``marshal-policy.toml`` carrying a long digit string reaches
    the validator as an arbitrary-precision Python ``int``. That is a far
    more plausible way to write these four keys -- they are TOKEN COUNTS, and
    "effectively unlimited" invites mashing digits -- than it ever was for
    ``idle_threshold_minutes``, a minutes value.

    The blast radius is what makes this worth a test rather than a shrug:
    ``cli/spin.py::run_spin`` calls ``compose()`` only AFTER ``harness.spin()``
    has launched the run and journaled its ``run-launch`` outcome, so the
    escaping traceback left a LIVE, UNSUPERVISED harness behind a non-zero
    exit -- inviting a retrying caller to double-dispatch the story the live
    run was already working. ``compose()``'s contract is that malformed
    CONTENT never raises; this pins it for the one input class that broke
    it."""
    huge = int("9" * 400)
    assert huge > 0  # it is not the sign check that must reject this

    effective, findings = compose(project_slug="acme", project={key: huge}, flags={})

    assert effective.seed_view()[key].value == DEFAULT_POLICY[key]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


def test_budget_ceiling_default_values():
    """50M/500M tokens, 24h/48h wall-clock -- pinned here so a future
    accidental edit to ``DEFAULT_POLICY`` is caught by a failing test, not
    silently.

    RE-CALIBRATED in review. The first pass picked 4M/40M/240/600 by
    analogy without measuring, and every one landed BELOW ordinary observed
    behaviour on this factory (46 of 53 real stories exceeded the 4M
    per-story token ceiling; the story that introduced these ceilings cost
    12.9M), so a supervised run would have breached and stopped itself in
    its first story. See ``DEFAULT_POLICY``'s own comment for the measured
    corpus each value is derived from."""
    assert DEFAULT_POLICY["max_tokens_per_story"] == 50_000_000
    assert DEFAULT_POLICY["max_tokens_per_run"] == 500_000_000
    assert DEFAULT_POLICY["max_wall_clock_minutes_per_story"] == 1_440
    assert DEFAULT_POLICY["max_wall_clock_minutes_per_run"] == 2_880


def test_budget_ceiling_defaults_clear_the_observed_workload():
    """The calibration CONTRACT, not just the literals (review finding): a
    ceiling that trips on ordinary work is worse than no ceiling, because it
    stops healthy runs and trains operators to raise it blindly. Measured
    maxima across 30 real bmad-loop runs / 53 completed stories on this
    factory, each of which a default must sit clear of with headroom."""
    observed_max_story_tokens = 21_700_000
    observed_max_run_tokens = 111_600_000
    observed_max_story_minutes = 519
    observed_max_run_minutes = 1_041

    assert DEFAULT_POLICY["max_tokens_per_story"] > observed_max_story_tokens
    assert DEFAULT_POLICY["max_tokens_per_run"] > observed_max_run_tokens
    assert DEFAULT_POLICY["max_wall_clock_minutes_per_story"] > observed_max_story_minutes
    assert DEFAULT_POLICY["max_wall_clock_minutes_per_run"] > observed_max_run_minutes


# --- max_parallel validation and the clamp-advisory finding (Story 3.13,
# FR-184) -- the spec's own I/O & Edge-Case Matrix, one test per row. ---------


def test_max_parallel_default_value_is_one():
    """Pinned so a future accidental edit to DEFAULT_POLICY is caught by a
    failing test: 1 matches both bmad_loop 0.9.0's own ScmPolicy.max_parallel
    default and Marshal's own rendered .bmad-loop/policy.toml."""
    assert DEFAULT_POLICY["max_parallel"] == 1


def test_max_parallel_default_no_advisory():
    """Matrix row 'Default': no max_parallel key set anywhere -- resolves to
    1, no MRS-POLICY-007 advisory."""
    effective, findings = compose(project_slug="acme", project={}, flags={})
    field = effective.seed_view()["max_parallel"]
    assert field.value == 1
    assert field.layer is PolicyLayer.DEFAULT
    assert findings == ()


def test_max_parallel_requested_above_one_preserves_value_and_fires_clamp_advisory():
    """Matrix row 'Requested >1': marshal-policy.toml sets max_parallel = 4
    -- resolves to 4 (the value is PRESERVED, never silently floored by
    Marshal itself), and a registered WARN finding names both the requested
    value and bmad_loop 0.9.0's own unbuilt Phase 5 scheduler as cause. The
    verdict stays in the OK half of the lattice (WARN only)."""
    effective, findings = compose(project_slug="acme", project={"max_parallel": 4}, flags={})
    field = effective.seed_view()["max_parallel"]
    assert field.value == 4
    assert field.layer is PolicyLayer.PROJECT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-007"
    assert findings[0].severity.value == "warn"
    assert "max_parallel=4" in findings[0].message
    assert "bmad_loop" in findings[0].message
    assert "Phase 5" in findings[0].message
    assert verdict.compute_verdict(findings) == Verdict.WARN


def test_max_parallel_exactly_one_explicit_no_advisory():
    """Matrix row 'Exactly 1': max_parallel = 1 explicitly -- resolves to 1,
    no advisory (matches the harness's own effective behavior, so nothing
    is reported)."""
    effective, findings = compose(project_slug="acme", project={"max_parallel": 1}, flags={})
    field = effective.seed_view()["max_parallel"]
    assert field.value == 1
    assert field.layer is PolicyLayer.PROJECT
    assert findings == ()


@pytest.mark.parametrize("bad_value", ["four", 0, True, False, -1, 3.5, None])
def test_max_parallel_malformed_values_fall_back_via_existing_machinery(bad_value):
    """Matrix row 'Malformed': a non-int, a bool (int(True)=1 would silently
    coerce), zero, or a negative value all fall back to the default of 1 via
    the existing MRS-POLICY-003 malformed-seed-value finding -- and, since
    the RESOLVED value is exactly 1 (never > 1), MRS-POLICY-007 never fires
    alongside it."""
    effective, findings = compose(project_slug="acme", project={"max_parallel": bad_value}, flags={})
    assert effective.seed_view()["max_parallel"].value == DEFAULT_POLICY["max_parallel"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"
    codes = {f.code for f in findings}
    assert "MRS-POLICY-007" not in codes


def test_max_parallel_accepts_a_large_valid_int():
    """The validator's floor is 1, not a ceiling -- an operator declaring
    intent for a future, larger fan-out width must compose cleanly too."""
    effective, findings = compose(project_slug="acme", project={"max_parallel": 16}, flags={})
    assert effective.seed_view()["max_parallel"].value == 16
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-007"


def test_max_parallel_rejects_an_arbitrary_precision_int_without_raising():
    """Review finding: mirrors ``test_budget_ceiling_rejects_an_arbitrary_
    precision_int_without_raising`` -- an int too large to convert to a C
    double would make ``_max_parallel_clamp_finding``'s own f-string
    formatting raise ``compose()``'s malformed-CONTENT-never-raises contract
    breaks for a value built by non-string arithmetic. Not reachable via a
    real ``marshal-policy.toml`` (``tomllib``'s own parser hits the same
    digit limit first), but ``_valid_parallel_count`` is the only int-typed
    seed validator that did not already mirror this guard."""
    huge = int("9" * 400)
    assert huge > 1  # it is not the >= 1 floor that must reject this

    effective, findings = compose(project_slug="acme", project={"max_parallel": huge}, flags={})

    assert effective.seed_view()["max_parallel"].value == DEFAULT_POLICY["max_parallel"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


def test_max_parallel_is_seed_reachable_only_via_seed_view():
    """max_parallel is SEED (AD-26) like every other operator-tunable
    numeric ceiling -- reachable only through seed_view(), never a public
    EffectivePolicy attribute."""
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert not hasattr(effective, "max_parallel")
    assert "max_parallel" in effective.seed_view()


# --- the 5 bmad-loop 0.10/0.11 knobs (Story 25.4, CAP-4) ----------------------
# One section per matrix row of the spec's I/O & Edge-Case Matrix: defaults,
# project-override wins, illegal enum values, coercible type mismatches
# (rejected marshal-side BEFORE bmad-loop 0.11's own stricter/coercive
# loaders ever see them), the legal zero capture, and the negative capture.

_BMAD_LOOP_KNOB_DEFAULTS = {
    "review_on_timeout": "retry",
    "review_on_status_contradiction": "escalate",
    "dev_contract_nudge": True,
    "operator_enabled": True,
    "stream_capture_kb": 256,
}


def test_bmad_loop_knob_defaults_match_stock():
    """Matrix row 'Defaults render' (composition half): all five knobs at
    their DELIBERATE repo defaults -- each matching bmad_loop 0.11.0 stock
    -- pinned here so a future accidental edit to DEFAULT_POLICY is caught
    by a failing test, not silently. Identity-asserted for the bools
    (``is True``): int 1 must never satisfy this."""
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    seed = effective.seed_view()
    assert seed["review_on_timeout"].value == "retry"
    assert seed["review_on_status_contradiction"].value == "escalate"
    assert seed["dev_contract_nudge"].value is True
    assert seed["operator_enabled"].value is True
    assert seed["stream_capture_kb"].value == 256
    assert not isinstance(seed["stream_capture_kb"].value, bool)
    for key in _BMAD_LOOP_KNOB_DEFAULTS:
        assert seed[key].layer is PolicyLayer.DEFAULT
        assert DEFAULT_POLICY[key] == _BMAD_LOOP_KNOB_DEFAULTS[key]


@pytest.mark.parametrize(
    ("key", "override"),
    [
        ("review_on_timeout", "salvage-if-done"),
        ("review_on_timeout", "defer"),
        ("review_on_status_contradiction", "retry"),
        ("dev_contract_nudge", False),
        ("operator_enabled", False),
        ("stream_capture_kb", 64),
    ],
)
def test_bmad_loop_knob_project_override_wins(key, override):
    """Matrix row 'Project override wins': a marshal-policy.toml-shaped
    mapping setting each knob to a legal non-default carries layer=PROJECT
    and the override value."""
    effective, findings = compose(project_slug="acme", project={key: override}, flags={})
    assert findings == ()
    field = effective.seed_view()[key]
    assert field.value == override
    assert field.layer is PolicyLayer.PROJECT


def test_bmad_loop_knob_flag_layer_wins_over_project():
    """The flags layer still composes uniformly for programmatic callers
    (AD-16's 'no per-key reordering') even though `--set` refuses these
    keys at the CLI boundary."""
    effective, findings = compose(
        project_slug="acme",
        project={"review_on_timeout": "defer"},
        flags={"review_on_timeout": "salvage-if-done"},
    )
    assert findings == ()
    field = effective.seed_view()["review_on_timeout"]
    assert field.value == "salvage-if-done"
    assert field.layer is PolicyLayer.FLAG


@pytest.mark.parametrize(
    ("key", "bad_value"),
    [
        # Matrix row 'Bad enum value'.
        ("review_on_timeout", "yolo"),
        ("review_on_timeout", "escalate"),  # the OTHER knob's vocabulary
        ("review_on_status_contradiction", "salvage-if-done"),  # ditto, reversed
        ("review_on_status_contradiction", "yolo"),
        # Matrix row 'Coercible type mismatch': each would be absorbed (or
        # refused only at load) by bmad-loop's own loaders -- marshal
        # rejects them first with a clear finding.
        ("review_on_timeout", 1),
        ("review_on_status_contradiction", None),
        ("dev_contract_nudge", 1),
        ("dev_contract_nudge", "true"),
        ("dev_contract_nudge", None),
        ("operator_enabled", "true"),
        ("operator_enabled", 1),
        ("stream_capture_kb", True),
        ("stream_capture_kb", False),
        ("stream_capture_kb", "256"),
        ("stream_capture_kb", 3.5),
        # Matrix row 'Negative capture'.
        ("stream_capture_kb", -1),
    ],
)
def test_bmad_loop_knob_malformed_value_falls_back_and_reports(key, bad_value):
    """MRS-POLICY-003 names the key and the layer; the prior layer's value
    (here the default) stands, so rendering never emits the bad value."""
    effective, findings = compose(project_slug="acme", project={key: bad_value}, flags={})
    field = effective.seed_view()[key]
    assert field.value == DEFAULT_POLICY[key]
    assert field.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"
    assert key in findings[0].message


def test_bmad_loop_knob_malformed_flag_keeps_valid_project_value():
    """The 'excluded, not poisoned' semantics hold for the new knobs too: a
    malformed flag value must not discard an otherwise-valid project-layer
    decision."""
    effective, findings = compose(
        project_slug="acme",
        project={"stream_capture_kb": 64},
        flags={"stream_capture_kb": "lots"},
    )
    field = effective.seed_view()["stream_capture_kb"]
    assert field.value == 64
    assert field.layer is PolicyLayer.PROJECT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "flag"


def test_stream_capture_kb_rejects_an_arbitrary_precision_int_without_raising():
    """Review finding: mirrors ``test_max_parallel_rejects_an_arbitrary_
    precision_int_without_raising`` -- an int too large to convert to a C
    double must come back as the ordinary MRS-POLICY-003 finding, never
    compose cleanly and then blow up ``content_hash``'s ``json.dumps`` or
    tomlkit's render against Python's int-to-str digit limit. Not reachable
    via a real ``marshal-policy.toml`` (``tomllib`` hits the same digit
    limit first), only via a direct programmatic ``compose()`` call."""
    huge = int("9" * 400)
    assert huge > 0  # it is not the >= 0 floor that must reject this

    effective, findings = compose(project_slug="acme", project={"stream_capture_kb": huge}, flags={})

    assert effective.seed_view()["stream_capture_kb"].value == DEFAULT_POLICY["stream_capture_kb"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


def test_stream_capture_kb_zero_is_legal():
    """Matrix row 'Zero capture': 0 = capture nothing is a legitimate
    policy on both sides (bmad-loop 0.11's own load floor is >= 0)."""
    effective, findings = compose(project_slug="acme", project={"stream_capture_kb": 0}, flags={})
    assert findings == ()
    field = effective.seed_view()["stream_capture_kb"]
    assert field.value == 0
    assert field.layer is PolicyLayer.PROJECT


# --- review_min_score (Story 31.3, CAP-4) ------------------------------------


def test_review_min_score_defaults_to_eighty():
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    field = effective.seed_view()["review_min_score"]
    assert field.value == 80
    assert field.layer is PolicyLayer.DEFAULT


@pytest.mark.parametrize("value", [0, 1, 80, 99, 100])
def test_review_min_score_accepts_the_full_legal_range(value):
    effective, findings = compose(project_slug="acme", project={"review_min_score": value}, flags={})
    assert findings == ()
    field = effective.seed_view()["review_min_score"]
    assert field.value == value
    assert field.layer is PolicyLayer.PROJECT


@pytest.mark.parametrize("value", [-1, 101, 1000])
def test_review_min_score_rejects_out_of_range_ints(value):
    """Matrix row: out of [0, 100] falls back to the default, reported as
    MRS-POLICY-003 (a malformed SEED field), never raised."""
    effective, findings = compose(project_slug="acme", project={"review_min_score": value}, flags={})
    assert effective.seed_view()["review_min_score"].value == DEFAULT_POLICY["review_min_score"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


def test_review_min_score_rejects_bool_even_though_bool_is_an_int_subclass():
    """`True`/`False` must never compose as 1/0 -- same strict int-not-bool
    discipline as every other numeric SEED knob (`_valid_stream_capture_kb`,
    `_valid_attempt_count`)."""
    effective, findings = compose(project_slug="acme", project={"review_min_score": True}, flags={})
    assert effective.seed_view()["review_min_score"].value == DEFAULT_POLICY["review_min_score"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


def test_review_min_score_rejects_a_numeric_string():
    effective, findings = compose(project_slug="acme", project={"review_min_score": "80"}, flags={})
    assert effective.seed_view()["review_min_score"].value == DEFAULT_POLICY["review_min_score"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "project"


# --- the "excluded, not poisoned" fallback semantics -------------------------


def test_invalid_flag_does_not_discard_a_valid_project_override():
    """Stated design assumption (see core/policy.py's module docstring): an
    invalid flag-layer value excludes only that layer's contribution -- it
    must not silently discard an otherwise-valid project-layer decision by
    reverting all the way to Marshal's built-in default."""
    effective, findings = compose(
        project_slug="acme",
        project={"gate_mode": "none"},
        flags={"gate_mode": "bogus"},
    )
    gate_mode = effective.seed_view()["gate_mode"]
    assert gate_mode.value == "none"
    assert gate_mode.layer is PolicyLayer.PROJECT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"
    assert findings[0].path == "flag"


# --- compose() never raises on malformed input -------------------------------


@pytest.mark.parametrize(
    "project,flags",
    [
        ({"gate_mode": 123}, {}),
        ({"gate_mode": None}, {}),
        ({"max_dev_attempts": "not-an-int"}, {}),
        ({"max_dev_attempts": True}, {}),
        ({"max_dev_attempts": 3.5}, {}),
        ({"merge_subject_template": ""}, {}),
        ({"merge_subject_template": 123}, {}),
        ({"verify_commands": "not-a-list"}, {}),
        ({"verify_commands": 123}, {}),
        ({"model_tier_map": "not-a-mapping"}, {}),
        ({"frozen_surfaces": [1, 2, 3]}, {}),
        ({}, {"gate_mode": 123}),
        ({}, {"max_review_cycles": -5}),
        ({}, {"worktree_seed_paths": "not-a-list"}),
        ({"landing_rules": "not-a-list"}, {}),
        ({"landing_rules": [{"name": "x"}]}, {}),
        ({"landing_merge_strategy": "fast-forward"}, {}),
        ({"landing_branch_retirement": "yes"}, {}),
        ({}, {"landing_resync": None}),
    ],
)
def test_compose_never_raises_on_malformed_layer_content(project, flags):
    effective, findings = compose(project_slug="acme", project=project, flags=flags)
    assert isinstance(effective, EffectivePolicy)
    assert len(findings) >= 1


def test_compose_rejects_non_str_project_slug():
    with pytest.raises(TypeError):
        compose(project_slug=123, project={}, flags={})  # type: ignore[arg-type]


def test_compose_rejects_bare_str_project():
    with pytest.raises(TypeError):
        compose(project_slug="acme", project="gate_mode=none", flags={})  # type: ignore[arg-type]


def test_compose_rejects_bare_str_flags():
    with pytest.raises(TypeError):
        compose(project_slug="acme", project={}, flags="gate_mode=none")  # type: ignore[arg-type]


def test_compose_rejects_non_mapping_project():
    with pytest.raises(TypeError):
        compose(project_slug="acme", project=["not", "a", "mapping"], flags={})  # type: ignore[arg-type]


# --- findings classify Verdict.UNEVALUABLE -----------------------------------


def test_malformed_findings_classify_unevaluable():
    _, findings = compose(project_slug="acme", project={"bogus": 1}, flags={"gate_mode": "x"})
    assert len(findings) == 2
    assert verdict.compute_verdict(findings) == Verdict.UNEVALUABLE


@pytest.mark.parametrize("code", ["MRS-POLICY-001", "MRS-POLICY-002", "MRS-POLICY-003"])
def test_every_policy_code_classifies_unevaluable(code):
    assert verdict.classify(code) == Verdict.UNEVALUABLE


# --- EffectivePolicy direct-construction validation --------------------------


def test_effective_policy_rejects_non_policy_field_static_attribute():
    seed = compose(project_slug="acme", project={}, flags={})[0].seed_view()
    with pytest.raises(ValueError):
        EffectivePolicy(
            verify_commands="not-a-policy-field",  # type: ignore[arg-type]
            worktree_seed_paths=PolicyField(value=(), layer="default", raw_source=()),
            merge_subject_template=PolicyField(value="x", layer="default", raw_source="x"),
            model_tier_map=PolicyField(value={}, layer="default", raw_source={}),
            epic_surfaces=PolicyField(value={}, layer="default", raw_source={}),
            landing_rules=PolicyField(value=(), layer="default", raw_source=()),
            landing_merge_strategy=PolicyField(value="merge", layer="default", raw_source="merge"),
            landing_branch_retirement=PolicyField(value=True, layer="default", raw_source=True),
            landing_resync=PolicyField(value=True, layer="default", raw_source=True),
            landing_base_branch=PolicyField(value="main", layer="default", raw_source="main"),
            landing_resync_commands=PolicyField(value=(), layer="default", raw_source=()),
            mcp_servers=PolicyField(value={}, layer="default", raw_source={}),
            harness_preference=PolicyField(value=(), layer="default", raw_source=()),
            context=PolicyField(value={}, layer="default", raw_source={}),
            scope_violation_mode=PolicyField(value="warn", layer="default", raw_source="warn"),
            model_cost_catalog=PolicyField(value={}, layer="default", raw_source={}),
            dispatch=PolicyField(value={"max_parallel": 1}, layer="default", raw_source={"max_parallel": 1}),
            _seed=seed,
        )


def test_effective_policy_rejects_incomplete_seed_mapping():
    with pytest.raises(ValueError):
        EffectivePolicy(
            verify_commands=PolicyField(value=(), layer="default", raw_source=()),
            worktree_seed_paths=PolicyField(value=(), layer="default", raw_source=()),
            merge_subject_template=PolicyField(value="x", layer="default", raw_source="x"),
            model_tier_map=PolicyField(value={}, layer="default", raw_source={}),
            epic_surfaces=PolicyField(value={}, layer="default", raw_source={}),
            landing_rules=PolicyField(value=(), layer="default", raw_source=()),
            landing_merge_strategy=PolicyField(value="merge", layer="default", raw_source="merge"),
            landing_branch_retirement=PolicyField(value=True, layer="default", raw_source=True),
            landing_resync=PolicyField(value=True, layer="default", raw_source=True),
            landing_base_branch=PolicyField(value="main", layer="default", raw_source="main"),
            landing_resync_commands=PolicyField(value=(), layer="default", raw_source=()),
            mcp_servers=PolicyField(value={}, layer="default", raw_source={}),
            harness_preference=PolicyField(value=(), layer="default", raw_source=()),
            context=PolicyField(value={}, layer="default", raw_source={}),
            scope_violation_mode=PolicyField(value="warn", layer="default", raw_source="warn"),
            model_cost_catalog=PolicyField(value={}, layer="default", raw_source={}),
            dispatch=PolicyField(value={"max_parallel": 1}, layer="default", raw_source={"max_parallel": 1}),
            _seed={"gate_mode": PolicyField(value="none", layer="default", raw_source="none")},
        )


def test_effective_policy_rejects_non_policy_field_seed_value():
    with pytest.raises(ValueError):
        EffectivePolicy(
            verify_commands=PolicyField(value=(), layer="default", raw_source=()),
            worktree_seed_paths=PolicyField(value=(), layer="default", raw_source=()),
            merge_subject_template=PolicyField(value="x", layer="default", raw_source="x"),
            model_tier_map=PolicyField(value={}, layer="default", raw_source={}),
            epic_surfaces=PolicyField(value={}, layer="default", raw_source={}),
            landing_rules=PolicyField(value=(), layer="default", raw_source=()),
            landing_merge_strategy=PolicyField(value="merge", layer="default", raw_source="merge"),
            landing_branch_retirement=PolicyField(value=True, layer="default", raw_source=True),
            landing_resync=PolicyField(value=True, layer="default", raw_source=True),
            landing_base_branch=PolicyField(value="main", layer="default", raw_source="main"),
            landing_resync_commands=PolicyField(value=(), layer="default", raw_source=()),
            mcp_servers=PolicyField(value={}, layer="default", raw_source={}),
            harness_preference=PolicyField(value=(), layer="default", raw_source=()),
            context=PolicyField(value={}, layer="default", raw_source={}),
            scope_violation_mode=PolicyField(value="warn", layer="default", raw_source="warn"),
            model_cost_catalog=PolicyField(value={}, layer="default", raw_source={}),
            dispatch=PolicyField(value={"max_parallel": 1}, layer="default", raw_source={"max_parallel": 1}),
            _seed={
                # All 16 seed keys present (an INCOMPLETE mapping would
                # raise for that reason instead, never reaching the
                # per-value type check this test exists to exercise) --
                # exactly one value ("gate_mode") is a bare str, not a
                # PolicyField.
                "gate_mode": "none",
                "frozen_surfaces": PolicyField(value=(), layer="default", raw_source=()),
                "max_dev_attempts": PolicyField(value=2, layer="default", raw_source=2),
                "max_review_cycles": PolicyField(value=3, layer="default", raw_source=3),
                "max_followup_reviews": PolicyField(value=1, layer="default", raw_source=1),
                "idle_threshold_minutes": PolicyField(value=25, layer="default", raw_source=25),
                "max_tokens_per_story": PolicyField(value=50_000_000, layer="default", raw_source=50_000_000),
                "max_tokens_per_run": PolicyField(value=500_000_000, layer="default", raw_source=500_000_000),
                "max_wall_clock_minutes_per_story": PolicyField(value=240, layer="default", raw_source=240),
                "max_wall_clock_minutes_per_run": PolicyField(value=600, layer="default", raw_source=600),
                "max_parallel": PolicyField(value=1, layer="default", raw_source=1),
                "review_on_timeout": PolicyField(value="retry", layer="default", raw_source="retry"),
                "review_on_status_contradiction": PolicyField(value="escalate", layer="default", raw_source="escalate"),
                "dev_contract_nudge": PolicyField(value=True, layer="default", raw_source=True),
                "operator_enabled": PolicyField(value=True, layer="default", raw_source=True),
                "stream_capture_kb": PolicyField(value=256, layer="default", raw_source=256),
            },
        )


def test_effective_policy_seed_is_a_read_only_mapping_proxy():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    with pytest.raises(TypeError):
        effective.seed_view()["gate_mode"] = PolicyField(  # type: ignore[index]
            value="none", layer="default", raw_source="none"
        )


# --- schema hygiene -----------------------------------------------------------


def test_schema_file_declares_the_thirty_three_keys():
    package_dir = Path(pyforge.marshal.__file__).resolve().parent
    schema = json.loads((package_dir / "schemas" / "policy.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "verify_commands",
        "worktree_seed_paths",
        "merge_subject_template",
        "model_tier_map",
        "epic_surfaces",
        "landing_rules",
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
        "landing_base_branch",
        "landing_resync_commands",
        "mcp_servers",
        "harness_preference",
        "context",
        "scope_violation_mode",
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
        "max_parallel",
        "review_on_timeout",
        "review_on_status_contradiction",
        "dev_contract_nudge",
        "operator_enabled",
        "stream_capture_kb",
        "review_min_score",
        "model_cost_catalog",
        "dispatch",
    }
    assert set(schema["properties"].keys()) == set(schema["required"])


# --- review-pass regressions (2026-07-30) ------------------------------------


def test_content_hash_differs_when_only_the_winning_layer_differs():
    """Two compositions with the IDENTICAL effective value for gate_mode but
    a DIFFERENT winning layer (project override vs. an identical-valued
    flag override) must not collide on content_hash -- otherwise
    materialize()'s write-once check would silently keep stale provenance
    under a hash that no longer reflects which layer actually won."""
    from_project, _ = compose(project_slug="acme", project={"gate_mode": "none"}, flags={})
    from_flag, _ = compose(project_slug="acme", project={}, flags={"gate_mode": "none"})
    assert from_project.seed_view()["gate_mode"].value == "none"
    assert from_flag.seed_view()["gate_mode"].value == "none"
    assert from_project.seed_view()["gate_mode"].layer != from_flag.seed_view()["gate_mode"].layer
    assert from_project.content_hash != from_flag.content_hash


def test_model_tier_map_value_is_deeply_immutable():
    effective, _ = compose(
        project_slug="acme",
        project={"model_tier_map": {"hard": {"dev": "opus"}}},
        flags={},
    )
    with pytest.raises(TypeError):
        effective.model_tier_map.value["hard"] = {"dev": "sonnet"}  # type: ignore[index]
    with pytest.raises(TypeError):
        effective.model_tier_map.value["hard"]["dev"] = "sonnet"  # type: ignore[index]


def test_model_tier_map_default_is_also_frozen():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    assert effective.model_tier_map.value == {}
    with pytest.raises(TypeError):
        effective.model_tier_map.value["hard"] = {"dev": "opus"}  # type: ignore[index]


def test_content_hash_handles_a_nonempty_model_tier_map():
    """Guards against content_hash crashing on the one nested-Mapping field
    once it holds real data (JSON can't natively serialize MappingProxyType
    -- content_hash must convert it first)."""
    effective, _ = compose(
        project_slug="acme",
        project={"model_tier_map": {"hard": {"dev": "opus", "review": "fable"}}},
        flags={},
    )
    assert isinstance(effective.content_hash, str) and len(effective.content_hash) == 64


def test_malformed_finding_redacts_a_secret_shaped_key(monkeypatch):
    """`_malformed_finding()`'s message must not leak a malformed raw value
    for a secret-shaped key. No REAL policy key is secret-shaped, so this
    monkeypatches the closed key/validator sets to synthetically exercise a
    secret-shaped field going through the exact same malformed-value path
    every real field uses."""
    import pyforge.marshal.core.policy as policy_module

    monkeypatch.setattr(policy_module, "_STATIC_KEYS", frozenset({"api_token"}))
    monkeypatch.setattr(policy_module, "_ALL_KEYS", frozenset({"api_token"}))
    finding = policy_module._malformed_finding("MRS-POLICY-002", "api_token", "project", "sk-live-secretvalue")
    assert "sk-live-secretvalue" not in finding.message
    assert REDACTED_SENTINEL in finding.message


def test_unknown_key_finding_names_the_key_and_layer():
    _, findings = compose(project_slug="acme", project={"bogus_key": 1}, flags={})
    assert any(f.code == "MRS-POLICY-001" and f.path == "project" for f in findings)


# --- follow-up review regressions (2026-07-30, second pass) -------------------


def test_missing_slug_emits_warn_finding_and_omits_project_path():
    """Spec: 'missing -> a registered finding, still prints defaults'.
    MRS-POLICY-005 classifies Verdict.WARN so a bare no-active-project
    invocation stays exit-0, and the project-derived seed path is OMITTED --
    never generated as `_bmad-output/projects//implementation-artifacts`."""
    effective, findings = compose(project_slug="", project={}, flags={})
    assert effective.worktree_seed_paths.value == ("_bmad/custom/.active-project",)
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-005"
    assert findings[0].severity.value == "warn"
    assert verdict.compute_verdict(findings) == Verdict.WARN


@pytest.mark.parametrize("bad_slug", ["../evil", "a/b", ".", "..", "has space", "a\\b"])
def test_malformed_slug_emits_error_finding_and_omits_project_path(bad_slug):
    """A slug that cannot be one safe path segment is MRS-POLICY-006
    (unevaluable -- the operator explicitly supplied garbage, matching the
    malformed --set precedent) and never enters a generated path."""
    effective, findings = compose(project_slug=bad_slug, project={}, flags={})
    assert effective.worktree_seed_paths.value == ("_bmad/custom/.active-project",)
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-006"
    assert verdict.compute_verdict(findings) == Verdict.UNEVALUABLE


def test_slug_finding_classifications():
    assert verdict.classify("MRS-POLICY-005") == Verdict.WARN
    assert verdict.classify("MRS-POLICY-006") == Verdict.UNEVALUABLE


def test_content_hash_stable_after_caller_mutates_inputs():
    """raw_source must be a SNAPSHOT, not an alias of the caller's own
    containers: mutating the passed-in project mapping's values after
    compose() must not change content_hash -- otherwise a later
    materialize() of the SAME EffectivePolicy writes under a different name,
    defeating AD-35's write-once content-addressing."""
    commands = ["pytest -q"]
    tier_map = {"hard": {"dev": "opus"}}
    project = {"verify_commands": commands, "model_tier_map": tier_map}
    effective, _ = compose(project_slug="acme", project=project, flags={})
    hash_before = effective.content_hash

    commands.append("rm -rf /")
    tier_map["hard"]["dev"] = "haiku"
    project["verify_commands"] = ["something-else"]

    assert effective.content_hash == hash_before
    # and the recorded provenance still shows the original raw values
    assert tuple(effective.verify_commands.raw_source) == ("pytest -q",)
    assert effective.model_tier_map.raw_source["hard"]["dev"] == "opus"


def test_raw_source_is_not_mutable_through_the_policy_field():
    """The consumer-side half of the same guarantee: raw_source itself is
    frozen (MappingProxyType/tuple), so a caller holding the composed policy
    cannot mutate what content_hash computes through the raw_source
    attribute either."""
    effective, _ = compose(
        project_slug="acme",
        project={"model_tier_map": {"hard": {"dev": "opus"}}},
        flags={},
    )
    with pytest.raises(TypeError):
        effective.model_tier_map.raw_source["hard"] = {"dev": "haiku"}  # type: ignore[index]
    with pytest.raises(TypeError):
        effective.model_tier_map.raw_source["hard"]["dev"] = "haiku"  # type: ignore[index]


# --- third review pass regressions (2026-07-30) -------------------------------


@pytest.mark.parametrize(
    "bad_extras",
    [
        ["../escape"],
        ["/etc/passwd"],
        [""],
        ["a//b"],
        ["a/./b"],
        ["trailing/"],
        ["ok/path", "../also-checked"],
    ],
)
def test_worktree_seed_extras_reject_unclean_or_escaping_paths(bad_extras):
    """The slug guard's traversal defense must hold for BOTH ways content
    enters worktree_seed_paths: extras arriving via the project layer are
    shape-validated as clean RELATIVE paths (no empty/'.'/'..' segments, no
    absolute paths) -- a rejected list is reported (MRS-POLICY-002) and the
    field falls back to the generated base, never composing a
    traversal-shaped or absolute seed path."""
    effective, findings = compose(project_slug="acme", project={"worktree_seed_paths": bad_extras}, flags={})
    assert effective.worktree_seed_paths.value == (
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
    )
    assert effective.worktree_seed_paths.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


def test_worktree_seed_extras_accept_clean_relative_paths():
    effective, findings = compose(
        project_slug="acme",
        project={"worktree_seed_paths": ["extra/seed-dir", "another.file"]},
        flags={},
    )
    assert findings == ()
    assert effective.worktree_seed_paths.value == (
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
        "extra/seed-dir",
        "another.file",
    )
    assert effective.worktree_seed_paths.layer is PolicyLayer.PROJECT


def test_verify_commands_rejects_empty_string_entry():
    """An empty verify command is no command at all -- same rule the scalar
    merge_subject_template already applies to the empty string."""
    effective, findings = compose(project_slug="acme", project={"verify_commands": ["pytest -q", ""]}, flags={})
    assert effective.verify_commands.value == DEFAULT_POLICY["verify_commands"]
    assert effective.verify_commands.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_frozen_surfaces_rejects_empty_string_entry():
    effective, findings = compose(project_slug="acme", project={"frozen_surfaces": [""]}, flags={})
    assert effective.seed_view()["frozen_surfaces"].value == DEFAULT_POLICY["frozen_surfaces"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-003"


# --- fourth review pass regressions (2026-07-30) ------------------------------


@pytest.mark.parametrize(
    "bad_entry",
    ["..\\evil", "C:\\x", "a\x00b", "~/.ssh", "has space", "a\nb"],
    ids=["backslash-traversal", "drive-letter", "nul-byte", "tilde", "space", "newline"],
)
def test_worktree_seed_extras_reject_entries_outside_the_path_charset(bad_entry):
    """The extras validator claims the slug guard's threat model, so it must
    enforce the slug guard's CHARSET too: segment checks alone split on `/`
    only, letting backslash traversal, drive letters, NUL bytes (a later
    Path() consumer dies on an embedded null), `~` (escapes the worktree
    under any expanduser), and whitespace compose cleanly."""
    effective, findings = compose(project_slug="acme", project={"worktree_seed_paths": [bad_entry]}, flags={})
    assert effective.worktree_seed_paths.value == (
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
    )
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_malformed_finding_does_not_claim_a_fallback_that_did_not_happen():
    """project supplies a VALID gate_mode, a flag then supplies a malformed
    one: the excluded-not-poisoned semantics retain the project value, so
    the finding text must not assert 'falling back to the Marshal default'
    -- the effective value printed one line away would contradict it."""
    effective, findings = compose(project_slug="acme", project={"gate_mode": "none"}, flags={"gate_mode": "bogus"})
    gate_mode = effective.seed_view()["gate_mode"]
    assert gate_mode.value == "none"
    assert gate_mode.layer is PolicyLayer.PROJECT
    assert len(findings) == 1
    assert "ignored" in findings[0].message
    assert "default" not in findings[0].message


@pytest.mark.parametrize(
    "tier_map",
    [{"": {"dev": "opus"}}, {"hard": {"dev": ""}}],
    ids=["empty-difficulty", "empty-model"],
)
def test_model_tier_map_rejects_empty_difficulty_and_model_names(tier_map):
    """An empty difficulty class or model name is no instance of the concept
    at all -- the same empty-string rule every other string field already
    enforces (an Epic 3/4 stage resolution would inherit it silently)."""
    effective, findings = compose(project_slug="acme", project={"model_tier_map": tier_map}, flags={})
    assert effective.model_tier_map.value == DEFAULT_POLICY["model_tier_map"]
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_slug_longer_than_name_max_is_malformed():
    """A slug over 255 characters is a path segment no target filesystem
    accepts -- shape validation reports it at compose time instead of
    deferring an ENAMETOOLONG to every later consumer."""
    effective, findings = compose(project_slug="a" * 256, project={}, flags={})
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-006"
    assert effective.worktree_seed_paths.value == ("_bmad/custom/.active-project",)


def test_slug_at_exactly_name_max_is_accepted():
    effective, findings = compose(project_slug="a" * 255, project={}, flags={})
    assert findings == ()
    assert ("a" * 255) in effective.worktree_seed_paths.value[0]


def test_policy_field_snapshots_mutable_value_at_construction():
    """Direct construction is public API: __post_init__ must freeze VALUE
    exactly as it freezes raw_source, or a caller-held list/dict mutated
    after construction silently changes content_hash -- re-opening the
    AD-35 mutability hole for every non-compose() construction path."""
    source = ["a"]
    field = PolicyField(value=source, layer="default", raw_source=source)
    source.append("b")
    assert field.value == ("a",)
    assert field.raw_source == ("a",)
    with pytest.raises(TypeError):
        PolicyField(value={"k": "v"}, layer="default", raw_source={}).value["k"] = "x"  # type: ignore[index]


def test_effective_policy_repr_redacts_secret_shaped_fields(monkeypatch):
    """The dataclass-generated repr printed every raw value -- an unredacted
    egress through any traceback/log/debugger. The custom __repr__ routes
    every value/raw_source through redact() keyed on the field name (proven
    synthetically: none of the 14 real fields is secret-shaped)."""
    monkeypatch.setattr(policy, "SECRET_KEY_SUFFIXES", frozenset({"_MODE"}))
    effective, _ = compose(project_slug="acme", project={"gate_mode": "none"}, flags={})
    text = repr(effective)
    assert REDACTED_SENTINEL in text
    assert "'none'" not in text
    # non-secret fields still repr their real values
    assert "acme" in text


# --- GATE_MODE_AUTONOMY_LABELS (Story 2.5, FR-24) -----------------------------


def test_gate_mode_autonomy_labels_keys_equal_gate_modes_exactly():
    """The mapping is keyed by exactly `_GATE_MODES`'s 3 values -- neither
    more (e.g. the unbuilt L5 'Observer' row) nor fewer."""
    assert set(policy.GATE_MODE_AUTONOMY_LABELS.keys()) == policy._GATE_MODES
    assert len(policy.GATE_MODE_AUTONOMY_LABELS) == 3


@pytest.mark.parametrize("mode", sorted(policy._GATE_MODES))
def test_gate_mode_autonomy_labels_entry_shape(mode):
    """Every entry is `{"level": ..., "name": ..., "meaning": ...}` -- three
    non-empty string keys, data rather than an interpolated prose string."""
    entry = policy.GATE_MODE_AUTONOMY_LABELS[mode]
    assert set(entry.keys()) == {"level", "name", "meaning"}
    for key in ("level", "name", "meaning"):
        assert isinstance(entry[key], str)
        assert entry[key] != ""


def test_gate_mode_autonomy_labels_verbatim_fr24_text():
    """The verbatim FR-24/glossary label text (level + name); the exact
    mapping this story's Always section names."""
    labels = policy.GATE_MODE_AUTONOMY_LABELS
    assert labels["per-story-spec-approval"]["level"] == "L2"
    assert labels["per-story-spec-approval"]["name"] == "Task-Based / Operator"
    assert labels["per-epic"]["level"] == "L3"
    assert labels["per-epic"]["name"] == "Conditional / Context Gates"
    assert labels["none"]["level"] == "L4"
    assert labels["none"]["name"] == "Approver"


# --- Story 22.8 (FR-193 CAP-8): harness_preference + the wired repo layer ----


def test_harness_preference_default_is_the_neutral_five_profile_order():
    effective, findings = compose(project_slug="acme", project={}, flags={})
    assert findings == ()
    field = effective.harness_preference
    assert field.value == ("claude", "cursor", "copilot", "gemini", "devin")
    assert field.layer == PolicyLayer.DEFAULT


def test_harness_preference_composes_from_the_project_layer():
    effective, findings = compose(project_slug="acme", project={"harness_preference": ["gemini"]}, flags={})
    assert findings == ()
    assert effective.harness_preference.value == ("gemini",)
    assert effective.harness_preference.layer == PolicyLayer.PROJECT


@pytest.mark.parametrize(
    "bad",
    [
        "claude",  # bare str, not a list
        ["claude", "claude"],  # duplicate entry
        ["claude", ""],  # empty entry
        ["cl aude"],  # charset violation
        ["../evil"],  # path-shaped
        [".."],  # pure-dot
    ],
)
def test_harness_preference_malformed_layer_is_excluded(bad):
    effective, findings = compose(project_slug="acme", project={"harness_preference": bad}, flags={})
    assert [f.code for f in findings] == ["MRS-POLICY-002"]
    assert effective.harness_preference.layer == PolicyLayer.DEFAULT


def test_repo_defaults_layer_wins_over_default_and_loses_to_project():
    """Story 22.8 wires compose()'s documented-but-ignored repo_defaults
    parameter (Story 1.10's promise): repo beats code default, project
    beats repo, and provenance names the layer."""
    repo_only, findings = compose(
        project_slug="acme",
        repo_defaults={"harness_preference": ["claude", "copilot"]},
        project={},
        flags={},
    )
    assert findings == ()
    assert repo_only.harness_preference.value == ("claude", "copilot")
    assert repo_only.harness_preference.layer == PolicyLayer.REPO_DEFAULTS
    assert repo_only.harness_preference.layer.value == "repo_defaults"

    project_wins, _ = compose(
        project_slug="acme",
        repo_defaults={"harness_preference": ["claude", "copilot"]},
        project={"harness_preference": ["gemini"]},
        flags={},
    )
    assert project_wins.harness_preference.value == ("gemini",)
    assert project_wins.harness_preference.layer == PolicyLayer.PROJECT


def test_repo_defaults_layer_applies_to_seed_fields_too():
    effective, findings = compose(
        project_slug="acme",
        repo_defaults={"max_followup_reviews": 4},
        project={},
        flags={},
    )
    assert findings == ()
    field = effective.seed_view()["max_followup_reviews"]
    assert field.value == 4
    assert field.layer == PolicyLayer.REPO_DEFAULTS


def test_repo_defaults_unknown_key_names_the_repo_layer():
    _, findings = compose(project_slug="acme", repo_defaults={"bogus_key": 1}, project={}, flags={})
    assert [f.code for f in findings] == ["MRS-POLICY-001"]
    assert "repo_defaults" in findings[0].message


def test_repo_defaults_malformed_value_is_excluded_for_that_layer_only():
    effective, findings = compose(
        project_slug="acme",
        repo_defaults={"gate_mode": "bogus"},
        project={"gate_mode": "none"},
        flags={},
    )
    assert [f.code for f in findings] == ["MRS-POLICY-003"]
    assert "repo_defaults" in findings[0].message
    assert effective.seed_view()["gate_mode"].value == "none"


def test_repo_defaults_rejects_a_bare_str():
    with pytest.raises(TypeError):
        compose(
            project_slug="acme",
            repo_defaults="gate_mode=none",  # type: ignore[arg-type]
            project={},
            flags={},
        )


def test_content_hash_distinguishes_repo_defaults_provenance():
    """Same effective value, different winning layer (repo vs project) --
    must not collide, the exact discrimination content_hash exists for."""
    via_repo, _ = compose(
        project_slug="acme",
        repo_defaults={"harness_preference": ["gemini"]},
        project={},
        flags={},
    )
    via_project, _ = compose(
        project_slug="acme",
        project={"harness_preference": ["gemini"]},
        flags={},
    )
    assert via_repo.harness_preference.value == via_project.harness_preference.value
    assert via_repo.content_hash != via_project.content_hash
