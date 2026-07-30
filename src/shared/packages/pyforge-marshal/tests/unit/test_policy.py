"""Unit tests for ``pyforge.marshal.core.policy`` (Story 1.3,
AD-10/AD-16/AD-26/AD-35) -- ``compose()`` across every I/O & Edge-Case
Matrix scenario, provenance per layer, determinism of ``content_hash``,
``seed_view()`` isolation, secret redaction (via a synthetic fixture, since
none of the 9 real fields are secret-shaped), and the "compose() never
raises on malformed CONTENT" guarantee.

``MRS-POLICY-001/002/003`` are real, already-registered codes (Story 1.3's
first real registrations after Story 1.2's two) -- unlike
``test_model.py``'s synthetic-code fixtures, no monkeypatching is needed
here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.core import policy, verdict
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


def test_project_overrides_one_key():
    effective, findings = compose(
        project_slug="acme", project={"gate_mode": "none"}, flags={}
    )
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
    effective, findings = compose(
        project_slug="acme", project={"max_dev_attempts": -1}, flags={}
    )
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
    first, _ = compose(
        project_slug="acme", project={"gate_mode": "none"}, flags={"max_dev_attempts": 5}
    )
    second, _ = compose(
        project_slug="acme", project={"gate_mode": "none"}, flags={"max_dev_attempts": 5}
    )
    assert first.content_hash == second.content_hash


def test_different_inputs_produce_different_hash():
    first, _ = compose(project_slug="acme", project={}, flags={})
    second, _ = compose(project_slug="acme", project={"gate_mode": "none"}, flags={})
    assert first.content_hash != second.content_hash


def test_seed_view_returns_all_five_seed_fields():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    seed = effective.seed_view()
    assert set(seed.keys()) == {
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
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
    ):
        assert not hasattr(effective, key)


def test_secret_redaction_via_synthetic_field_name():
    """None of the 9 real fields are secret-shaped -- the mechanism is
    proven against a synthetic fixture, mirroring findings.py/verdict.py's
    own "empty registry, mechanism proven synthetically" precedent."""
    assert is_secret_key("GITHUB_TOKEN")
    assert is_secret_key("api_key")
    assert is_secret_key("db_secret")
    assert is_secret_key("admin_password")
    assert not is_secret_key("gate_mode")
    assert redact("GITHUB_TOKEN", "super-secret-value") == REDACTED_SENTINEL
    assert redact("gate_mode", "none") == "none"


def test_none_of_the_real_nine_fields_are_secret_shaped():
    all_keys = {
        "verify_commands",
        "worktree_seed_paths",
        "merge_subject_template",
        "model_tier_map",
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
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


def test_verify_commands_non_string_entry_falls_back_and_reports():
    effective, findings = compose(
        project_slug="acme", project={"verify_commands": ["ok", 123]}, flags={}
    )
    assert effective.verify_commands.value == DEFAULT_POLICY["verify_commands"]
    assert effective.verify_commands.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"
    assert findings[0].path == "project"


def test_verify_commands_valid_list_accepted():
    effective, findings = compose(
        project_slug="acme", project={"verify_commands": ["pytest -q"]}, flags={}
    )
    assert findings == ()
    assert effective.verify_commands.value == ("pytest -q",)
    assert effective.verify_commands.layer is PolicyLayer.PROJECT


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
            _seed=seed,
        )


def test_effective_policy_rejects_incomplete_seed_mapping():
    with pytest.raises(ValueError):
        EffectivePolicy(
            verify_commands=PolicyField(value=(), layer="default", raw_source=()),
            worktree_seed_paths=PolicyField(value=(), layer="default", raw_source=()),
            merge_subject_template=PolicyField(value="x", layer="default", raw_source="x"),
            model_tier_map=PolicyField(value={}, layer="default", raw_source={}),
            _seed={"gate_mode": PolicyField(value="none", layer="default", raw_source="none")},
        )


def test_effective_policy_rejects_non_policy_field_seed_value():
    with pytest.raises(ValueError):
        EffectivePolicy(
            verify_commands=PolicyField(value=(), layer="default", raw_source=()),
            worktree_seed_paths=PolicyField(value=(), layer="default", raw_source=()),
            merge_subject_template=PolicyField(value="x", layer="default", raw_source="x"),
            model_tier_map=PolicyField(value={}, layer="default", raw_source={}),
            _seed={
                "gate_mode": "none",
                "frozen_surfaces": PolicyField(value=(), layer="default", raw_source=()),
                "max_dev_attempts": PolicyField(value=2, layer="default", raw_source=2),
                "max_review_cycles": PolicyField(value=3, layer="default", raw_source=3),
                "max_followup_reviews": PolicyField(value=1, layer="default", raw_source=1),
            },
        )


def test_effective_policy_seed_is_a_read_only_mapping_proxy():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    with pytest.raises(TypeError):
        effective.seed_view()["gate_mode"] = PolicyField(  # type: ignore[index]
            value="none", layer="default", raw_source="none"
        )


# --- schema hygiene -----------------------------------------------------------


def test_schema_file_declares_the_nine_keys():
    package_dir = Path(pyforge.marshal.__file__).resolve().parent
    schema = json.loads(
        (package_dir / "schemas" / "policy.json").read_text(encoding="utf-8")
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "verify_commands",
        "worktree_seed_paths",
        "merge_subject_template",
        "model_tier_map",
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
    }
    assert set(schema["properties"].keys()) == set(schema["required"])


# --- review-pass regressions (2026-07-30) ------------------------------------


def test_content_hash_differs_when_only_the_winning_layer_differs():
    """Two compositions with the IDENTICAL effective value for gate_mode but
    a DIFFERENT winning layer (project override vs. an identical-valued
    flag override) must not collide on content_hash -- otherwise
    materialize()'s write-once check would silently keep stale provenance
    under a hash that no longer reflects which layer actually won."""
    from_project, _ = compose(
        project_slug="acme", project={"gate_mode": "none"}, flags={}
    )
    from_flag, _ = compose(
        project_slug="acme", project={}, flags={"gate_mode": "none"}
    )
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
    finding = policy_module._malformed_finding(
        "MRS-POLICY-002", "api_token", "project", "sk-live-secretvalue"
    )
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
