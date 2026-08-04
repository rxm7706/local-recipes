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
    assert seed["idle_threshold_minutes"].value == DEFAULT_POLICY["idle_threshold_minutes"]
    assert seed["max_tokens_per_story"].value == DEFAULT_POLICY["max_tokens_per_story"]
    assert seed["max_tokens_per_run"].value == DEFAULT_POLICY["max_tokens_per_run"]
    assert (
        seed["max_wall_clock_minutes_per_story"].value
        == DEFAULT_POLICY["max_wall_clock_minutes_per_story"]
    )
    assert (
        seed["max_wall_clock_minutes_per_run"].value
        == DEFAULT_POLICY["max_wall_clock_minutes_per_run"]
    )


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


def test_seed_view_returns_all_ten_seed_fields():
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


def test_none_of_the_real_fourteen_fields_are_secret_shaped():
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
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
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


# --- idle_threshold_minutes validation (Story 3.5, FR-12) --------------------


def test_idle_threshold_minutes_project_override_applies():
    effective, findings = compose(
        project_slug="acme", project={"idle_threshold_minutes": 10}, flags={}
    )
    assert findings == ()
    field = effective.seed_view()["idle_threshold_minutes"]
    assert field.value == 10
    assert field.layer is PolicyLayer.PROJECT


def test_idle_threshold_minutes_accepts_a_fractional_value():
    """Unlike the int-only attempt-count fields, a fractional minute value
    is accepted -- useful for a synthetic sub-minute threshold no
    whole-number value could express."""
    effective, findings = compose(
        project_slug="acme", project={"idle_threshold_minutes": 0.5}, flags={}
    )
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
    effective, findings = compose(
        project_slug="acme", project={"idle_threshold_minutes": bad_value}, flags={}
    )
    assert effective.seed_view()["idle_threshold_minutes"].value == DEFAULT_POLICY[
        "idle_threshold_minutes"
    ]
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


def test_budget_ceiling_default_values():
    """The spec's own Design Notes assumption: 4M/40M tokens,
    4h/10h wall-clock -- pinned here so a future accidental edit to
    ``DEFAULT_POLICY`` is caught by a failing test, not silently."""
    assert DEFAULT_POLICY["max_tokens_per_story"] == 4_000_000
    assert DEFAULT_POLICY["max_tokens_per_run"] == 40_000_000
    assert DEFAULT_POLICY["max_wall_clock_minutes_per_story"] == 240
    assert DEFAULT_POLICY["max_wall_clock_minutes_per_run"] == 600


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
                # All 10 seed keys present (an INCOMPLETE mapping would
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
                "max_tokens_per_story": PolicyField(
                    value=4_000_000, layer="default", raw_source=4_000_000
                ),
                "max_tokens_per_run": PolicyField(
                    value=40_000_000, layer="default", raw_source=40_000_000
                ),
                "max_wall_clock_minutes_per_story": PolicyField(
                    value=240, layer="default", raw_source=240
                ),
                "max_wall_clock_minutes_per_run": PolicyField(
                    value=600, layer="default", raw_source=600
                ),
            },
        )


def test_effective_policy_seed_is_a_read_only_mapping_proxy():
    effective, _ = compose(project_slug="acme", project={}, flags={})
    with pytest.raises(TypeError):
        effective.seed_view()["gate_mode"] = PolicyField(  # type: ignore[index]
            value="none", layer="default", raw_source="none"
        )


# --- schema hygiene -----------------------------------------------------------


def test_schema_file_declares_the_fourteen_keys():
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
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
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
    effective, findings = compose(
        project_slug="acme", project={"worktree_seed_paths": bad_extras}, flags={}
    )
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
    effective, findings = compose(
        project_slug="acme", project={"verify_commands": ["pytest -q", ""]}, flags={}
    )
    assert effective.verify_commands.value == DEFAULT_POLICY["verify_commands"]
    assert effective.verify_commands.layer is PolicyLayer.DEFAULT
    assert len(findings) == 1
    assert findings[0].code == "MRS-POLICY-002"


def test_frozen_surfaces_rejects_empty_string_entry():
    effective, findings = compose(
        project_slug="acme", project={"frozen_surfaces": [""]}, flags={}
    )
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
    effective, findings = compose(
        project_slug="acme", project={"worktree_seed_paths": [bad_entry]}, flags={}
    )
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
    effective, findings = compose(
        project_slug="acme", project={"gate_mode": "none"}, flags={"gate_mode": "bogus"}
    )
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
    effective, findings = compose(
        project_slug="acme", project={"model_tier_map": tier_map}, flags={}
    )
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
