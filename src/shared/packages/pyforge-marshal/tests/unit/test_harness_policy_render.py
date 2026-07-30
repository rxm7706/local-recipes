"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop`` (Story 1.10,
AD-10/AD-12/AD-35, FR-49/50/51) -- ``render_policy_toml()``/
``write_policy_toml()`` across the full I/O & Edge-Case Matrix: determinism,
all 6 Marshal-mapped keys, FR-51 tier-batching (full/partial/unknown
difficulty), empty ``verify_commands``, rendered-TOML validity, and
``write_policy_toml``'s atomic-overwrite behavior.

Fixture ``EffectivePolicy`` instances are built via ``core.policy.compose()``
(the real composition function), never by hand-constructing the frozen
dataclass -- matching ``test_policy.py``'s own convention.
"""

from __future__ import annotations

import tomllib

import pytest

from pyforge.marshal.adapters.harness_bmadloop import (
    HarnessPolicyWriteError,
    render_policy_toml,
    write_policy_toml,
)
from pyforge.marshal.core.policy import compose


def _compose(**project_overrides):
    effective, findings = compose(project_slug="acme", project=project_overrides, flags={})
    assert findings == ()
    return effective


# --- full composition, all 6 mapped keys ------------------------------------


def test_full_composition_maps_all_six_keys_and_keeps_template_baseline_elsewhere():
    effective = _compose(
        gate_mode="none",
        max_dev_attempts=5,
        max_review_cycles=6,
        max_followup_reviews=7,
        verify_commands=["pytest -q", "ruff check ."],
        worktree_seed_paths=["extra/seed-dir"],
    )
    doc = tomllib.loads(render_policy_toml(effective))

    # the 6 mapped keys
    assert doc["gates"]["mode"] == "none"
    assert doc["limits"]["max_dev_attempts"] == 5
    assert doc["limits"]["max_review_cycles"] == 6
    assert doc["limits"]["max_followup_reviews"] == 7
    assert doc["verify"]["commands"] == ["pytest -q", "ruff check ."]
    assert doc["scm"]["worktree_seed"] == [
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
        "extra/seed-dir",
    ]

    # every other key at template baseline, including the 6 hardcoded
    # repo-wide overrides
    assert doc["review"]["trigger"] == "always"
    assert doc["scm"]["isolation"] == "worktree"
    assert doc["scm"]["merge_strategy"] == "squash"
    assert doc["scm"]["rollback_on_failure"] is True
    assert doc["limits"]["session_timeout_min"] == 180
    assert doc["adapter"]["model"] == "sonnet"
    assert doc["adapter"]["review"]["model"] == "fable"
    # untouched stock defaults, spot-checked
    assert doc["gates"]["retrospective"] == "notify"
    assert doc["review"]["enabled"] is True
    assert doc["sweep"]["auto"] == "never"
    assert doc["dev"]["skill"] == "bmad-dev-auto"
    assert doc["stories"]["source"] == "sprint-status"
    assert doc["mux"] == {}


def test_defaults_only_composition_maps_marshal_defaults():
    """No project overrides at all: the 6 mapped keys reflect Marshal's own
    built-in DEFAULT_POLICY values, not the harness's stock ones."""
    effective = _compose()
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["gates"]["mode"] == "per-story-spec-approval"
    assert doc["limits"]["max_dev_attempts"] == 2
    assert doc["limits"]["max_review_cycles"] == 3
    # 2, deliberately not the harness's stock 1 and not a loosened assertion:
    # DEFAULT_POLICY is the only repo-wide home for a repo-wide decision, and a
    # cap of 1 damped five still-recommended follow-up reviews across three
    # projects into a gitignored ledger (DW-AD23-3). A station layer restating
    # it would be nine copies of one decision -- Story 1.10's review said so.
    assert doc["limits"]["max_followup_reviews"] == 2
    assert doc["verify"]["commands"] == []
    assert doc["scm"]["worktree_seed"] == [
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
    ]


# --- determinism -------------------------------------------------------------


def test_render_is_byte_identical_for_identical_input():
    effective = _compose(gate_mode="none", max_dev_attempts=4)
    first = render_policy_toml(effective, difficulty="hard")
    second = render_policy_toml(effective, difficulty="hard")
    assert first == second


def test_render_is_byte_identical_across_separate_compositions_of_the_same_input():
    """Determinism holds across two SEPARATE compose() calls with identical
    args too, not merely two renders of the same EffectivePolicy object."""
    first_effective = _compose(gate_mode="none")
    second_effective = _compose(gate_mode="none")
    assert render_policy_toml(first_effective) == render_policy_toml(second_effective)


# --- FR-51 tier-batching ------------------------------------------------------


def test_tier_batching_full_stage_set():
    effective = _compose(
        model_tier_map={"hard": {"dev": "opus", "review": "fable", "triage": "sonnet"}}
    )
    doc = tomllib.loads(render_policy_toml(effective, difficulty="hard"))
    assert doc["adapter"]["dev"]["model"] == "opus"
    assert doc["adapter"]["review"]["model"] == "fable"
    assert doc["adapter"]["triage"]["model"] == "sonnet"


def test_tier_batching_partial_stage_set_leaves_other_stages_at_baseline():
    effective = _compose(model_tier_map={"hard": {"dev": "opus"}})
    doc = tomllib.loads(render_policy_toml(effective, difficulty="hard"))
    assert doc["adapter"]["dev"]["model"] == "opus"
    # review keeps its template-baseline override; triage gets no table at all
    assert doc["adapter"]["review"]["model"] == "fable"
    assert "triage" not in doc["adapter"]


def test_unknown_difficulty_renders_every_stage_at_baseline():
    effective = _compose(model_tier_map={"hard": {"dev": "opus"}})
    doc = tomllib.loads(render_policy_toml(effective, difficulty="nonexistent"))
    assert "dev" not in doc["adapter"]
    assert "triage" not in doc["adapter"]
    assert doc["adapter"]["review"]["model"] == "fable"


def test_difficulty_none_renders_every_stage_at_baseline():
    effective = _compose(model_tier_map={"hard": {"dev": "opus", "triage": "haiku"}})
    doc = tomllib.loads(render_policy_toml(effective, difficulty=None))
    assert "dev" not in doc["adapter"]
    assert "triage" not in doc["adapter"]
    assert doc["adapter"]["review"]["model"] == "fable"
    assert doc["adapter"]["model"] == "sonnet"


def test_empty_model_tier_map_with_a_difficulty_renders_baseline():
    effective = _compose()
    doc = tomllib.loads(render_policy_toml(effective, difficulty="hard"))
    assert "dev" not in doc["adapter"]
    assert "triage" not in doc["adapter"]
    assert doc["adapter"]["review"]["model"] == "fable"


# --- the harness's stricter attempt-count floor ---------------------------------


def test_render_rejects_zero_max_dev_attempts():
    """Marshal's composition accepts 0 (``_valid_attempt_count`` is >= 0) but
    bmad_loop 0.9.0 rejects limits.max_dev_attempts < 1 at policy load --
    render must refuse rather than write a file that bricks the loop home."""
    effective = _compose(max_dev_attempts=0)
    with pytest.raises(ValueError, match="max_dev_attempts"):
        render_policy_toml(effective)


def test_render_rejects_zero_max_review_cycles():
    effective = _compose(max_review_cycles=0)
    with pytest.raises(ValueError, match="max_review_cycles"):
        render_policy_toml(effective)


def test_zero_max_followup_reviews_renders_fine():
    """0 is legal on BOTH sides for max_followup_reviews -- bmad_loop's floor
    is >= 0 for this key alone."""
    effective = _compose(max_followup_reviews=0)
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["limits"]["max_followup_reviews"] == 0


# --- empty verify_commands ----------------------------------------------------


def test_empty_verify_commands_renders_empty_list():
    effective = _compose(verify_commands=[])
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["verify"]["commands"] == []


# --- rendered text validity ---------------------------------------------------


def test_rendered_text_parses_as_valid_toml_via_tomllib():
    effective = _compose(
        gate_mode="none",
        verify_commands=["pytest -q"],
        model_tier_map={"hard": {"dev": "opus", "review": "fable", "triage": "sonnet"}},
    )
    text = render_policy_toml(effective, difficulty="hard")
    # must not raise
    tomllib.loads(text)


# --- write_policy_toml: the I/O boundary --------------------------------------


def test_write_policy_toml_creates_dir_and_writes_the_rendered_text(tmp_path):
    effective = _compose(gate_mode="none")
    target = write_policy_toml(effective, tmp_path)
    assert target == tmp_path / ".bmad-loop" / "policy.toml"
    assert target.read_text(encoding="utf-8") == render_policy_toml(effective)


def test_write_policy_toml_overwrites_preexisting_unrelated_content(tmp_path):
    bmad_loop_dir = tmp_path / ".bmad-loop"
    bmad_loop_dir.mkdir(parents=True)
    target = bmad_loop_dir / "policy.toml"
    target.write_text("this is unrelated pre-existing content\n", encoding="utf-8")

    effective = _compose(gate_mode="per-epic")
    result = write_policy_toml(effective, tmp_path)

    assert result == target
    written = target.read_text(encoding="utf-8")
    assert "unrelated pre-existing content" not in written
    assert written == render_policy_toml(effective)


def test_write_policy_toml_applies_difficulty(tmp_path):
    effective = _compose(model_tier_map={"hard": {"dev": "opus"}})
    target = write_policy_toml(effective, tmp_path, difficulty="hard")
    doc = tomllib.loads(target.read_text(encoding="utf-8"))
    assert doc["adapter"]["dev"]["model"] == "opus"


def test_write_policy_toml_wraps_oserror_in_harness_policy_write_error(tmp_path):
    """A loop_home that is a FILE, not a directory, cannot host a
    `.bmad-loop` subdirectory -- the resulting OSError (NotADirectoryError)
    must be wrapped, never propagate raw."""
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    effective = _compose()
    with pytest.raises(HarnessPolicyWriteError):
        write_policy_toml(effective, blocked)


# --- the CLI seam: nothing reachable called write_policy_toml -----------------
# Story 1.10 shipped render_policy_toml/write_policy_toml with full unit coverage
# and a meta test proving the rendered file stays untracked -- yet no operator
# could produce it: `marshal config` only printed, the writer's sole callers were
# the tests above, and no pixi task called either. Merging the story then deleted
# the tracked file from pyforge-marshal's own loop home, leaving it with no policy
# at all. These tests assert the seam EXISTS, which is the property the original
# suite could not see: a writer proven correct in isolation, that nobody can reach.


def test_conventional_project_policy_path_lands_on_the_repo_root(tmp_path):
    """An off-by-one in `repo_root()` resolves to `<repo>/src` and every
    convention lookup silently misses -- falling back to bare defaults whose
    `verify_commands` is EMPTY, i.e. no gate at all. Caught exactly that during
    implementation, hence this test."""
    from pyforge.marshal.cli import config as config_cli

    root = config_cli.repo_root()
    assert (root / "pixi.toml").is_file(), (
        f"repo_root() resolved to {root}, which has no pixi.toml -- the parent "
        "index is wrong and every project-policy lookup will miss"
    )
    p = config_cli.conventional_project_policy_path("pyforge-marshal")
    assert p == root / (
        "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    )


def test_cli_writes_the_harness_policy_via_the_convention_layer(tmp_path):
    """The whole point: `marshal config --project <slug> --write-harness-policy
    <home>` must find the tracked layer by convention and write a policy carrying
    that project's OWN verify command -- with no --project-policy passed."""
    from pyforge.marshal.cli.main import main

    rc = main([
        "config", "--project", "pyforge-marshal",
        "--write-harness-policy", str(tmp_path), "--format", "json",
    ])
    assert rc == 0, "a clean composition must exit 0"

    written = tmp_path / ".bmad-loop" / "policy.toml"
    assert written.is_file(), "the CLI did not reach write_policy_toml"
    parsed = tomllib.loads(written.read_text(encoding="utf-8"))
    assert parsed["verify"]["commands"] == [
        "pixi run --frozen -e pyforge-marshal pyforge-marshal-test"
    ], "the project layer was not composed in -- verify would be EMPTY (no gate)"
    assert parsed["gates"]["mode"] == "none"
    assert parsed["limits"]["max_followup_reviews"] == 2


def test_cli_refuses_to_write_a_policy_from_an_error_composition(tmp_path):
    """bmad-loop READS this file on its next run, so a composition Marshal could
    not determine the intent of must not become the harness's policy."""
    from pyforge.marshal.cli.main import main

    rc = main([
        "config", "--project", "pyforge-marshal",
        "--set", "max_review_cycles=not-an-int",
        "--write-harness-policy", str(tmp_path), "--format", "json",
    ])
    assert not (tmp_path / ".bmad-loop" / "policy.toml").exists(), (
        "a policy was written despite error-severity findings"
    )
    assert rc != 0
