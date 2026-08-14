"""Unit tests for ``pyforge.marshal.seed.plan.types`` (Story 9.6) -- covers
the spec's I/O & Edge-Case Matrix rows relevant to the types themselves:
round-trip identity (``Action``, ``RepoFingerprint``, and ``Plan``
individually, plus a full ``json.dumps``/``json.loads`` round-trip proving
every tuple field survives its JSON-array detour), the empty-plan case,
tuple-vs-JSON-array conversion in ``to_json_dict``, and ``from_json_dict``
raising ``ValueError`` for every malformed-input shape (a missing key, a
wrong-shaped value, an unrecognized enum value) -- plus the frozen/hashable
dataclass conventions this package's other model types already establish.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.model.manifest import ArtifactClass
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint


def _action(**overrides) -> Action:
    fields = {
        "artifact_id": "agents-md",
        "artifact_class": ArtifactClass.HYBRID_MANAGED_REGION,
        "current_state": ArtifactState.ABSENT,
        "target_state": ArtifactState.PRESENT_CONFORMANT,
        "target_path": "AGENTS.md",
        "chosen_anchor": (("tiers", "## The tiers"), ("portability-contract", None)),
        "rationale": "'AGENTS.md' is absent; materialize it as hybrid-managed-region",
    }
    fields.update(overrides)
    return Action(**fields)


def _fingerprint(**overrides) -> RepoFingerprint:
    fields = {
        "git_head": "abc123",
        "dirty": False,
        "artifact_hashes": (("agents-md", "deadbeef"), ("gitignore", "cafef00d")),
    }
    fields.update(overrides)
    return RepoFingerprint(**fields)


def _plan(**overrides) -> Plan:
    fields = {"actions": (_action(),), "repo_fingerprint": _fingerprint()}
    fields.update(overrides)
    return Plan(**fields)


def _valid_action_dict() -> dict:
    return _action().to_json_dict()


def _valid_fingerprint_dict() -> dict:
    return _fingerprint().to_json_dict()


def _valid_plan_dict() -> dict:
    return _plan().to_json_dict()


# --- Action ------------------------------------------------------------


def test_action_to_json_dict_uses_plain_str_wire_values_for_enum_fields():
    data = _action().to_json_dict()
    assert data["artifact_class"] == "hybrid-managed-region"
    assert type(data["artifact_class"]) is str
    assert data["current_state"] == "absent"
    assert data["target_state"] == "present-conformant"


def test_action_to_json_dict_chosen_anchor_is_a_list_of_two_element_lists():
    data = _action().to_json_dict()
    assert data["chosen_anchor"] == [["tiers", "## The tiers"], ["portability-contract", None]]
    assert all(type(item) is list for item in data["chosen_anchor"])


def test_action_to_json_dict_round_trips_through_json_dumps_and_loads():
    action = _action()
    restored = Action.from_json_dict(json.loads(json.dumps(action.to_json_dict())))
    assert restored == action
    # chosen_anchor must come back as a tuple of tuples, never lists --
    # dataclass equality above already proves this (a list would not equal
    # the original tuple), but the type is asserted directly too since
    # that is the property this test exists to pin.
    assert isinstance(restored.chosen_anchor, tuple)
    assert all(isinstance(pair, tuple) for pair in restored.chosen_anchor)


def test_action_from_json_dict_round_trips_directly_without_a_json_string_detour():
    action = _action()
    assert Action.from_json_dict(action.to_json_dict()) == action


def test_action_with_empty_chosen_anchor_round_trips():
    action = _action(artifact_class=ArtifactClass.COPIED_MANAGED, chosen_anchor=())
    restored = Action.from_json_dict(json.loads(json.dumps(action.to_json_dict())))
    assert restored == action
    assert restored.chosen_anchor == ()


@pytest.mark.parametrize(
    "missing_key",
    [
        "artifact_id",
        "artifact_class",
        "current_state",
        "target_state",
        "target_path",
        "chosen_anchor",
        "rationale",
    ],
)
def test_action_from_json_dict_raises_value_error_naming_a_missing_key(missing_key):
    data = _valid_action_dict()
    del data[missing_key]
    with pytest.raises(ValueError, match=missing_key):
        Action.from_json_dict(data)


def test_action_from_json_dict_raises_value_error_for_an_unrecognized_artifact_class():
    data = _valid_action_dict()
    data["artifact_class"] = "not-a-real-class"
    with pytest.raises(ValueError):
        Action.from_json_dict(data)


def test_action_from_json_dict_raises_value_error_for_an_unrecognized_current_state():
    data = _valid_action_dict()
    data["current_state"] = "not-a-real-state"
    with pytest.raises(ValueError):
        Action.from_json_dict(data)


def test_action_from_json_dict_raises_value_error_for_an_unrecognized_target_state():
    data = _valid_action_dict()
    data["target_state"] = "not-a-real-state"
    with pytest.raises(ValueError):
        Action.from_json_dict(data)


def test_action_from_json_dict_raises_value_error_when_chosen_anchor_is_not_a_list():
    data = _valid_action_dict()
    data["chosen_anchor"] = "not-a-list"
    with pytest.raises(ValueError):
        Action.from_json_dict(data)


def test_action_from_json_dict_raises_value_error_when_a_chosen_anchor_pair_is_not_length_two():
    data = _valid_action_dict()
    data["chosen_anchor"] = [["only-one-element"]]
    with pytest.raises(ValueError):
        Action.from_json_dict(data)


def test_action_from_json_dict_raises_value_error_when_a_region_name_is_not_a_string():
    data = _valid_action_dict()
    data["chosen_anchor"] = [[123, "## anchor"]]
    with pytest.raises(ValueError):
        Action.from_json_dict(data)


def test_action_from_json_dict_raises_value_error_when_data_is_not_a_mapping():
    with pytest.raises(ValueError):
        Action.from_json_dict("not-a-dict")  # type: ignore[arg-type]


def test_action_is_frozen_and_hashable():
    action = _action()
    with pytest.raises(dataclasses.FrozenInstanceError):
        action.artifact_id = "changed"  # type: ignore[misc]
    assert isinstance(hash(action), int)


# --- RepoFingerprint -----------------------------------------------------


def test_fingerprint_to_json_dict_artifact_hashes_is_a_list_of_two_element_lists():
    data = _fingerprint().to_json_dict()
    assert data["artifact_hashes"] == [["agents-md", "deadbeef"], ["gitignore", "cafef00d"]]
    assert all(type(item) is list for item in data["artifact_hashes"])


def test_fingerprint_round_trips_through_json_dumps_and_loads_with_a_real_git_head():
    fingerprint = _fingerprint(git_head="abc123", dirty=True)
    restored = RepoFingerprint.from_json_dict(json.loads(json.dumps(fingerprint.to_json_dict())))
    assert restored == fingerprint


def test_fingerprint_round_trips_with_git_head_none_and_empty_artifact_hashes():
    """The non-git-target-repo shape: ``git_head is None``, ``dirty=True``,
    and no actioned artifacts at all."""
    fingerprint = _fingerprint(git_head=None, dirty=True, artifact_hashes=())
    restored = RepoFingerprint.from_json_dict(json.loads(json.dumps(fingerprint.to_json_dict())))
    assert restored == fingerprint
    assert restored.git_head is None
    assert restored.artifact_hashes == ()


@pytest.mark.parametrize("missing_key", ["git_head", "dirty", "artifact_hashes"])
def test_fingerprint_from_json_dict_raises_value_error_naming_a_missing_key(missing_key):
    data = _valid_fingerprint_dict()
    del data[missing_key]
    with pytest.raises(ValueError, match=missing_key):
        RepoFingerprint.from_json_dict(data)


def test_fingerprint_from_json_dict_raises_value_error_when_dirty_is_not_a_bool():
    data = _valid_fingerprint_dict()
    data["dirty"] = "yes"
    with pytest.raises(ValueError):
        RepoFingerprint.from_json_dict(data)


def test_fingerprint_from_json_dict_raises_value_error_when_dirty_is_an_int_not_a_bool():
    """``bool`` is an ``int`` subtype in Python, and JSON ``0``/``1`` decode
    to plain ``int`` -- must not silently coerce."""
    data = _valid_fingerprint_dict()
    data["dirty"] = 1
    with pytest.raises(ValueError):
        RepoFingerprint.from_json_dict(data)


def test_fingerprint_from_json_dict_raises_value_error_when_git_head_is_not_a_string_or_null():
    data = _valid_fingerprint_dict()
    data["git_head"] = 12345
    with pytest.raises(ValueError):
        RepoFingerprint.from_json_dict(data)


def test_fingerprint_from_json_dict_raises_value_error_when_artifact_hashes_is_not_a_list():
    data = _valid_fingerprint_dict()
    data["artifact_hashes"] = {"agents-md": "deadbeef"}
    with pytest.raises(ValueError):
        RepoFingerprint.from_json_dict(data)


def test_fingerprint_from_json_dict_raises_value_error_when_data_is_not_a_mapping():
    with pytest.raises(ValueError):
        RepoFingerprint.from_json_dict(["not", "a", "dict"])  # type: ignore[arg-type]


def test_fingerprint_is_frozen_and_hashable():
    fingerprint = _fingerprint()
    with pytest.raises(dataclasses.FrozenInstanceError):
        fingerprint.dirty = True  # type: ignore[misc]
    assert isinstance(hash(fingerprint), int)


# --- Plan ------------------------------------------------------------------


def test_empty_plan_is_valid_constructible_and_serializable():
    """AD-60's idempotence signal: ``Plan(actions=(), repo_fingerprint=...)``
    needs no special-casing anywhere -- proven directly here at the type
    layer, independent of ``build_plan`` (covered separately by
    ``test_seed_plan_build.py``)."""
    plan = Plan(actions=(), repo_fingerprint=_fingerprint())
    data = plan.to_json_dict()
    assert data["actions"] == []
    restored = Plan.from_json_dict(json.loads(json.dumps(data)))
    assert restored == plan
    assert restored.actions == ()


def test_plan_with_multiple_actions_round_trips_through_json_dumps_and_loads():
    plan = Plan(
        actions=(
            _action(artifact_id="a", chosen_anchor=()),
            _action(artifact_id="b", chosen_anchor=(("tiers", None),)),
        ),
        repo_fingerprint=_fingerprint(),
    )
    restored = Plan.from_json_dict(json.loads(json.dumps(plan.to_json_dict())))
    assert restored == plan
    assert isinstance(restored.actions, tuple)
    assert all(isinstance(action, Action) for action in restored.actions)


def test_plan_from_json_dict_round_trips_directly_without_a_json_string_detour():
    plan = _plan()
    assert Plan.from_json_dict(plan.to_json_dict()) == plan


@pytest.mark.parametrize("missing_key", ["actions", "repo_fingerprint"])
def test_plan_from_json_dict_raises_value_error_naming_a_missing_key(missing_key):
    data = _valid_plan_dict()
    del data[missing_key]
    with pytest.raises(ValueError, match=missing_key):
        Plan.from_json_dict(data)


def test_plan_from_json_dict_raises_value_error_when_actions_is_not_a_list():
    data = _valid_plan_dict()
    data["actions"] = "not-a-list"
    with pytest.raises(ValueError):
        Plan.from_json_dict(data)


def test_plan_from_json_dict_raises_value_error_when_one_action_is_malformed():
    """A single malformed action inside an otherwise-valid ``actions`` list
    fails the whole load -- proving the per-``Action`` validation actually
    runs during ``Plan.from_json_dict``, not only when ``Action.
    from_json_dict`` is called directly."""
    data = _valid_plan_dict()
    malformed_action = _valid_action_dict()
    del malformed_action["rationale"]
    data["actions"] = [_valid_action_dict(), malformed_action]
    with pytest.raises(ValueError, match="rationale"):
        Plan.from_json_dict(data)


def test_plan_from_json_dict_raises_value_error_when_repo_fingerprint_is_malformed():
    data = _valid_plan_dict()
    malformed_fingerprint = _valid_fingerprint_dict()
    del malformed_fingerprint["dirty"]
    data["repo_fingerprint"] = malformed_fingerprint
    with pytest.raises(ValueError, match="dirty"):
        Plan.from_json_dict(data)


def test_plan_from_json_dict_raises_value_error_for_duplicate_artifact_ids():
    # `from_json_dict` is this module's boundary against UNTRUSTED data (a
    # hand-corrupted `plan.json`) -- `build_plan` only ever emits unique
    # ids (review finding: a duplicate previously loaded silently).
    data = _valid_plan_dict()
    data["actions"] = [
        _action(artifact_id="a").to_json_dict(),
        _action(artifact_id="a").to_json_dict(),
    ]
    with pytest.raises(ValueError, match="unique"):
        Plan.from_json_dict(data)


def test_plan_from_json_dict_raises_value_error_for_out_of_order_artifact_ids():
    # `build_plan` only ever emits `actions` sorted by `artifact_id` (the
    # epics AC's own determinism requirement) -- a hand-corrupted
    # `plan.json` with the two swapped previously loaded silently (review
    # finding).
    data = _valid_plan_dict()
    data["actions"] = [
        _action(artifact_id="zeta").to_json_dict(),
        _action(artifact_id="alpha").to_json_dict(),
    ]
    with pytest.raises(ValueError, match="ordered"):
        Plan.from_json_dict(data)


def test_plan_from_json_dict_raises_value_error_when_data_is_not_a_mapping():
    with pytest.raises(ValueError):
        Plan.from_json_dict([])  # type: ignore[arg-type]


def test_plan_is_frozen_and_hashable():
    plan = _plan()
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.actions = ()  # type: ignore[misc]
    assert isinstance(hash(plan), int)
