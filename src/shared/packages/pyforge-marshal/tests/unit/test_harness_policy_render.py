"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop`` (Story 1.10,
AD-10/AD-12/AD-35, FR-49/50/51) -- ``render_policy_toml()``/
``write_policy_toml()`` across the full I/O & Edge-Case Matrix: determinism,
all 6 Marshal-mapped bmad-loop-adjacent scalar knobs (Story 25.4's original
5, plus Story 31.3's (CAP-4) ``review_min_score`` as the 6th), FR-51
tier-batching (full/partial/unknown
difficulty), empty ``verify_commands``, rendered-TOML validity, and
``write_policy_toml``'s atomic-overwrite behavior.

Fixture ``EffectivePolicy`` instances are built via ``core.policy.compose()``
(the real composition function), never by hand-constructing the frozen
dataclass -- matching ``test_policy.py``'s own convention.
"""

from __future__ import annotations

import tomllib

import pytest
import tomlkit

from pyforge.marshal.adapters.harness_bmadloop import (
    _SURFACE_RECONCILE_COMMAND,
    HarnessPolicyWriteError,
    _load_model_cost_catalog,
    _plain_json,
    _read_policy_adapter_and_model,
    _token_counts_from_task,
    _usage_dollar_fields,
    _write_model_cost_catalog_sidecar,
    render_policy_toml,
    write_policy_document,
    write_policy_toml,
)
from pyforge.marshal.core.policy import compose
from pyforge.marshal.ports.harness import LayerSavings

_SAMPLE_CATALOG = {
    "providers": {
        "cursor": {
            "subscription_pool": "cursor-ultra",
            "models": {
                "composer-2.5": {"input_per_million": 0.50, "output_per_million": 2.50},
            },
        },
    },
}


def _compose(**project_overrides):
    effective, findings = compose(project_slug="acme", project=project_overrides, flags={})
    assert findings == ()
    return effective


# --- full composition, all 11 mapped keys ------------------------------------


def test_full_composition_maps_all_twelve_keys_and_keeps_template_baseline_elsewhere():
    effective = _compose(
        gate_mode="none",
        max_dev_attempts=5,
        max_review_cycles=6,
        max_followup_reviews=7,
        verify_commands=["pytest -q", "ruff check ."],
        worktree_seed_paths=["extra/seed-dir"],
        review_on_timeout="salvage-if-done",
        review_on_status_contradiction="retry",
        dev_contract_nudge=False,
        operator_enabled=False,
        stream_capture_kb=64,
        review_min_score=90,
    )
    doc = tomllib.loads(render_policy_toml(effective))

    # the 6 original mapped keys
    assert doc["gates"]["mode"] == "none"
    assert doc["limits"]["max_dev_attempts"] == 5
    assert doc["limits"]["max_review_cycles"] == 6
    assert doc["limits"]["max_followup_reviews"] == 7
    # S-13.7: the station's own commands, THEN the appended surface guard.
    assert doc["verify"]["commands"] == ["pytest -q", "ruff check .", _SURFACE_RECONCILE_COMMAND]
    assert doc["scm"]["worktree_seed"] == [
        "_bmad-output/projects/acme/implementation-artifacts",
        "_bmad/custom/.active-project",
        "extra/seed-dir",
    ]
    # Story 25.4's 5 bmad-loop 0.10/0.11 knobs: the project override values,
    # each at its exact TOML scalar type (`is False`: int 0 must not pass).
    assert doc["review"]["on_timeout"] == "salvage-if-done"
    assert doc["review"]["on_status_contradiction"] == "retry"
    assert doc["limits"]["dev_contract_nudge"] is False
    assert doc["operator"]["enabled"] is False
    assert doc["verify"]["stream_capture_kb"] == 64
    assert not isinstance(doc["verify"]["stream_capture_kb"], bool)
    # Story 31.3's 6th knob: same exact-type discipline.
    assert doc["review"]["min_score"] == 90
    assert not isinstance(doc["review"]["min_score"], bool)

    # every other key at template baseline, including the 6 hardcoded
    # repo-wide overrides
    assert doc["review"]["trigger"] == "recommended"
    assert doc["scm"]["isolation"] == "worktree"
    assert doc["scm"]["merge_strategy"] == "squash"
    assert doc["scm"]["rollback_on_failure"] is True
    assert doc["limits"]["session_timeout_min"] == 180
    assert doc["adapter"]["model"] == "sonnet"
    assert doc["adapter"]["review"]["model"] == "opus"
    # untouched stock defaults, spot-checked
    assert doc["gates"]["retrospective"] == "notify"
    assert doc["review"]["enabled"] is True
    assert doc["sweep"]["auto"] == "never"
    assert doc["dev"]["skill"] == "bmad-dev-auto"
    assert doc["stories"]["source"] == "sprint-status"
    assert doc["mux"] == {}


def test_defaults_only_composition_maps_marshal_defaults():
    """No project overrides at all: the 11 mapped keys reflect Marshal's own
    built-in DEFAULT_POLICY values, not the harness's stock ones (Story
    25.4's five deliberately MATCH stock, so their assertions double as the
    matrix's 'Defaults render' row -- exact TOML scalar types included:
    `is True` so int 1 can never pass, int-not-bool for the capture cap)."""
    effective = _compose()
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["gates"]["mode"] == "per-story-spec-approval"
    assert doc["limits"]["max_dev_attempts"] == 2
    assert doc["limits"]["max_review_cycles"] == 3
    # Story 25.4 (CAP-4): the five bmad-loop 0.10/0.11 knobs at their
    # deliberate repo defaults (all matching bmad_loop 0.11.0 stock).
    assert doc["review"]["on_timeout"] == "retry"
    assert doc["review"]["on_status_contradiction"] == "escalate"
    assert doc["limits"]["dev_contract_nudge"] is True
    assert doc["operator"]["enabled"] is True
    assert doc["verify"]["stream_capture_kb"] == 256
    assert not isinstance(doc["verify"]["stream_capture_kb"], bool)
    # Story 31.3 (CAP-4): the tea-test-review lens's default, upstream's
    # own example value (spec-bmad-suite-lifecycle open question 2).
    assert doc["review"]["min_score"] == 80
    assert not isinstance(doc["review"]["min_score"], bool)
    # 2, deliberately not the harness's stock 1 and not a loosened assertion:
    # DEFAULT_POLICY is the only repo-wide home for a repo-wide decision, and a
    # cap of 1 damped five still-recommended follow-up reviews across three
    # projects into a gitignored ledger (DW-AD23-3). A station layer restating
    # it would be nine copies of one decision -- Story 1.10's review said so.
    assert doc["limits"]["max_followup_reviews"] == 2
    # S-13.7: never empty — a station that declares no tests still reconciles
    # the surface it drifts, or the loop could skip reconciliation by
    # declaring nothing.
    assert doc["verify"]["commands"] == [_SURFACE_RECONCILE_COMMAND]
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
    effective = _compose(model_tier_map={"hard": {"dev": "opus", "review": "fable", "triage": "sonnet"}})
    doc = tomllib.loads(render_policy_toml(effective, difficulty="hard"))
    assert doc["adapter"]["dev"]["model"] == "opus"
    assert doc["adapter"]["review"]["model"] == "fable"
    assert doc["adapter"]["triage"]["model"] == "sonnet"


def test_tier_batching_partial_stage_set_leaves_other_stages_at_baseline():
    effective = _compose(model_tier_map={"hard": {"dev": "opus"}})
    doc = tomllib.loads(render_policy_toml(effective, difficulty="hard"))
    assert doc["adapter"]["dev"]["model"] == "opus"
    # review keeps its template-baseline override; triage gets no table at all
    assert doc["adapter"]["review"]["model"] == "opus"
    assert "triage" not in doc["adapter"]


def test_unknown_difficulty_renders_every_stage_at_baseline():
    effective = _compose(model_tier_map={"hard": {"dev": "opus"}})
    doc = tomllib.loads(render_policy_toml(effective, difficulty="nonexistent"))
    assert "dev" not in doc["adapter"]
    assert "triage" not in doc["adapter"]
    assert doc["adapter"]["review"]["model"] == "opus"


def test_difficulty_none_renders_every_stage_at_baseline():
    effective = _compose(model_tier_map={"hard": {"dev": "opus", "triage": "haiku"}})
    doc = tomllib.loads(render_policy_toml(effective, difficulty=None))
    assert "dev" not in doc["adapter"]
    assert "triage" not in doc["adapter"]
    assert doc["adapter"]["review"]["model"] == "opus"
    assert doc["adapter"]["model"] == "sonnet"


def test_empty_model_tier_map_with_a_difficulty_renders_baseline():
    effective = _compose()
    doc = tomllib.loads(render_policy_toml(effective, difficulty="hard"))
    assert "dev" not in doc["adapter"]
    assert "triage" not in doc["adapter"]
    assert doc["adapter"]["review"]["model"] == "opus"


def test_tier_batching_never_writes_a_stage_model_catalogued_under_a_different_provider():
    """2026-09-12 (dispatch-tier-routing-fails-safe): a bare-string
    ``model_tier_map`` stage entry has no declared ``harness``, so it
    always launches under whichever adapter this render resolves to
    (``[adapter].name``, here the template's ``claude`` baseline, since
    ``harness_preference`` is left at its own default). When the cost
    catalog identifies that model's declared provider as something OTHER
    than the resolved adapter's own provider, writing it anyway would
    launch a real adapter binary with a model it was never meant to
    receive -- the exact hybrid, invalid dispatch this fix closes (a
    Cursor model, `composer-2.5-fast`, silently landing on `claude`
    because `harness_preference` (`cursor`-only) has no bmad-loop
    counterpart). The stage must fall through to the template's own
    baseline instead, not be left absent -- `[adapter.review]`'s baseline
    override still applies unconditionally regardless of this guard."""
    effective = _compose(
        model_tier_map={"heavy": {"dev": "composer-2.5-fast"}},
        model_cost_catalog=_SAMPLE_CATALOG_WITH_FAST,
    )
    doc = tomllib.loads(render_policy_toml(effective, difficulty="heavy"))
    assert "dev" not in doc["adapter"]
    assert doc["adapter"]["model"] == "sonnet"
    assert doc["adapter"]["review"]["model"] == "opus"


def test_tier_batching_still_applies_a_stage_model_catalogued_under_the_resolved_adapters_own_provider():
    """Sibling of the mismatch test above: a tier-mapped model DOES apply
    when the cost catalog names it under the SAME provider as the adapter
    that will actually launch (here ``claude`` -> ``anthropic``) -- the
    guard only ever filters a genuine cross-provider mismatch, never a
    legitimately-tiered same-adapter model."""
    effective = _compose(
        model_tier_map={"heavy": {"dev": "sonnet-5"}},
        model_cost_catalog={
            "providers": {
                "anthropic": {
                    "models": {
                        "sonnet-5": {"input_per_million": 2.0, "output_per_million": 10.0},
                    },
                },
            },
        },
    )
    doc = tomllib.loads(render_policy_toml(effective, difficulty="heavy"))
    assert doc["adapter"]["dev"]["model"] == "sonnet-5"


_SAMPLE_CATALOG_WITH_FAST = {
    "providers": {
        "cursor": {
            "subscription_pool": "cursor-ultra",
            "models": {
                "composer-2.5-fast": {
                    "input_per_million": 3.0,
                    "output_per_million": 15.0,
                },
            },
        },
    },
}


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


# --- Story 25.4's knobs: overrides, zero capture, the real 0.11 load gate -----


def test_stream_capture_kb_zero_renders_zero():
    """Matrix row 'Zero capture': 0 = capture nothing is legal on both
    sides (bmad-loop 0.11's own load floor is >= 0) and renders as the int
    0, never a bool."""
    effective = _compose(stream_capture_kb=0)
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["verify"]["stream_capture_kb"] == 0
    assert not isinstance(doc["verify"]["stream_capture_kb"], bool)


def test_rendered_defaults_pass_the_installed_bmad_loop_load():
    """The AC's real gate, run against the INSTALLED harness: bmad_loop
    0.11's own ``loads()`` (the same strict/coercive loaders `bmad-loop
    validate` exercises) must accept the rendered file whole -- including
    ``_limit_bool``'s strict boolean check on ``limits.dev_contract_nudge``
    -- and carry every one of the five knobs at its composed value. Every
    member of BOTH review-knob vocabularies round-trips through the
    installed loader across the three loads below (on_timeout: retry /
    salvage-if-done / defer; on_status_contradiction: escalate / retry). A
    direct ``bmad_loop`` import is fine IN A TEST: AD-3's import-linter
    contract binds the installed package's modules, not test code (the same
    bounds ``test_harness_bmadloop_preflight.py`` already relies on).

    Story 31.3's ``review.min_score`` is asserted separately below via
    ``hasattr`` rather than a value comparison: ``bmad_loop`` 0.11's own
    ``ReviewPolicy`` dataclass has no ``min_score`` field at all (verified
    against the installed package source), so the key is silently ignored
    at load, never surfaced on the parsed object -- exactly the "inert
    extra key" behavior this story's own design relies on (the rendered
    value is never READ or CONSUMED by the harness itself, per AD-4 --
    it is still a real, rendered TOML key, just an inert one to bmad_loop's
    own loader)."""
    bmad_loop_policy = pytest.importorskip("bmad_loop.policy")

    loaded = bmad_loop_policy.loads(render_policy_toml(_compose()))
    assert loaded.review.on_timeout == "retry"
    assert loaded.review.on_status_contradiction == "escalate"
    assert loaded.limits.dev_contract_nudge is True
    assert loaded.operator.enabled is True
    assert loaded.verify.stream_capture_kb == 256
    assert not hasattr(loaded.review, "min_score")

    overridden = bmad_loop_policy.loads(
        render_policy_toml(
            _compose(
                review_on_timeout="salvage-if-done",
                review_on_status_contradiction="retry",
                dev_contract_nudge=False,
                operator_enabled=False,
                stream_capture_kb=0,
            )
        )
    )
    assert overridden.review.on_timeout == "salvage-if-done"
    assert overridden.review.on_status_contradiction == "retry"
    assert overridden.limits.dev_contract_nudge is False
    assert overridden.operator.enabled is False
    assert overridden.verify.stream_capture_kb == 0

    deferred = bmad_loop_policy.loads(render_policy_toml(_compose(review_on_timeout="defer")))
    assert deferred.review.on_timeout == "defer"


def test_enum_frozensets_mirror_the_installed_bmad_loop_vocabularies():
    """The drift guard for the mirrored vocabularies (review finding):
    ``core/policy.py``'s two frozensets CLAIM to mirror the installed
    bmad_loop's own module constants verbatim -- assert equality against
    the live installed package, so a future bmad-loop bump that widens or
    respells either vocabulary reds this test instead of surfacing as a
    load-time PolicyError in a loop home."""
    bmad_loop_policy = pytest.importorskip("bmad_loop.policy")
    from pyforge.marshal.core import policy as policy_module

    assert policy_module._REVIEW_ON_TIMEOUT_MODES == frozenset(bmad_loop_policy.REVIEW_ON_TIMEOUT_MODES)
    assert policy_module._REVIEW_ON_STATUS_CONTRADICTION_MODES == frozenset(
        bmad_loop_policy.REVIEW_ON_STATUS_CONTRADICTION_MODES
    )


# --- empty verify_commands ----------------------------------------------------


def test_empty_verify_commands_renders_empty_list():
    effective = _compose(verify_commands=[])
    doc = tomllib.loads(render_policy_toml(effective))
    # S-13.7: never empty — a station that declares no tests still reconciles
    # the surface it drifts, or the loop could skip reconciliation by
    # declaring nothing.
    assert doc["verify"]["commands"] == [_SURFACE_RECONCILE_COMMAND]


# --- Story 28.1: the [context] block (SPEC-marshal-token-economy CAP-1) ------


def test_context_absent_renders_no_context_table():
    """The AC's own byte-identical guarantee: no declaration at all (the
    DEFAULT_POLICY empty-mapping default) must render NO [context] table,
    matching pre-Story-28.1 output exactly."""
    text = render_policy_toml(_compose())
    assert "context" not in text
    doc = tomllib.loads(text)
    assert "context" not in doc


def test_context_declared_renders_all_five_layers():
    from pyforge.marshal.core import policy

    effective = _compose(context={"wire": {"enabled": True, "aggressiveness": "high"}})
    doc = tomllib.loads(render_policy_toml(effective))
    resolved = policy.resolve_context_layers(effective)
    assert set(doc["context"]) == set(policy.CONTEXT_LAYER_NAMES)
    for layer in policy.CONTEXT_LAYER_NAMES:
        assert doc["context"][layer]["enabled"] == resolved[layer]["enabled"]
        assert doc["context"][layer]["aggressiveness"] == resolved[layer]["aggressiveness"]
    assert doc["context"]["wire"] == {"enabled": True, "aggressiveness": "high"}
    assert doc["context"]["output"] == {"enabled": False, "aggressiveness": "medium"}


def test_context_partial_declaration_defaults_remaining_layers_off():
    effective = _compose(context={"planning-graph": {"enabled": True}})
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["context"]["planning-graph"] == {"enabled": True, "aggressiveness": "medium"}
    assert doc["context"]["wire"] == {"enabled": False, "aggressiveness": "medium"}


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


# --- write_policy_document: Story 3.12's narrow single-key patch write ---------


def test_write_policy_document_writes_a_mutated_doc_and_preserves_comments(tmp_path):
    """The whole point: an already-on-disk document (read via
    ``tomlkit.parse``), mutated in place, is written back WITHOUT
    re-deriving it from an ``EffectivePolicy`` -- every comment and every
    other key survives untouched."""
    effective = compose(project_slug="acme", project={}, flags={})[0]
    text = render_policy_toml(effective)
    doc = tomlkit.parse(text)
    doc["adapter"]["model"] = "opus"

    target = write_policy_document(doc, tmp_path)

    assert target == tmp_path / ".bmad-loop" / "policy.toml"
    written = target.read_text(encoding="utf-8")
    assert tomllib.loads(written)["adapter"]["model"] == "opus"
    # The trailing inline comment on that same line survives the patch.
    assert "repo-wide override" in written
    # Every other key is untouched -- proven by re-parsing and comparing
    # against the ORIGINAL render with only the one key patched.
    original = tomllib.loads(text)
    original["adapter"]["model"] = "opus"
    assert tomllib.loads(written) == original


def test_write_policy_document_overwrites_preexisting_unrelated_content(tmp_path):
    bmad_loop_dir = tmp_path / ".bmad-loop"
    bmad_loop_dir.mkdir(parents=True)
    target = bmad_loop_dir / "policy.toml"
    target.write_text("this is unrelated pre-existing content\n", encoding="utf-8")
    doc = tomlkit.parse(render_policy_toml(compose(project_slug="acme", project={}, flags={})[0]))

    result = write_policy_document(doc, tmp_path)

    assert result == target
    written = target.read_text(encoding="utf-8")
    assert "unrelated pre-existing content" not in written


def test_write_policy_document_wraps_oserror_in_harness_policy_write_error(tmp_path):
    """Mirrors ``write_policy_toml``'s identical contract -- a loop_home
    that is a FILE, not a directory, cannot host a ``.bmad-loop``
    subdirectory."""
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    doc = tomlkit.parse(render_policy_toml(compose(project_slug="acme", project={}, flags={})[0]))

    with pytest.raises(HarnessPolicyWriteError):
        write_policy_document(doc, blocked)


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
    assert p == root / ("_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml")


def test_cli_writes_the_harness_policy_via_the_convention_layer(tmp_path):
    """The whole point: `marshal config --project <slug> --write-harness-policy
    <home>` must find the tracked layer by convention and write a policy carrying
    that project's OWN verify command -- with no --project-policy passed."""
    from pyforge.marshal.cli.main import main

    rc = main(
        [
            "config",
            "--project",
            "pyforge-marshal",
            "--write-harness-policy",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    assert rc == 0, "a clean composition must exit 0"

    written = tmp_path / ".bmad-loop" / "policy.toml"
    assert written.is_file(), "the CLI did not reach write_policy_toml"
    parsed = tomllib.loads(written.read_text(encoding="utf-8"))
    # Still an EXACT list, deliberately -- this assertion is the only thing standing
    # between a mis-composed layer and a run with no gate, so it is not loosened to a
    # membership check. The list grew to two on 2026-07-31 when marshal absorbed the
    # pyforge-genesis installer as epics 7-12: marshal's own suite cannot gate a story
    # that builds pyforge-genesis (it would pass regardless -- the same false green the
    # 2026-07-30 audit found on six loop homes running warden's suite), so the station
    # layer carries pyforge-deps-test as a second entry. That check discovers
    # src/shared/packages/pyforge-* BY GLOB, so it covers a package the day it lands.
    assert parsed["verify"]["commands"] == [
        "pixi run --frozen -e pyforge-marshal pyforge-marshal-test",
        "pixi run --frozen -e pyforge-ci pyforge-deps-test",
        # S-13.7 (2026-08-09): the repo-wide surface guard, APPENDED at render.
        # Kept inside the exact list on purpose -- this assertion is what stands
        # between a mis-composed layer and a run with no gate, and the guard is
        # now part of what "gated" means.
        _SURFACE_RECONCILE_COMMAND,
    ], "the project layer was not composed in -- verify would be EMPTY (no gate)"
    assert parsed["gates"]["mode"] == "none"
    assert parsed["limits"]["max_followup_reviews"] == 2


def test_cli_refuses_to_write_a_policy_from_an_error_composition(tmp_path):
    """bmad-loop READS this file on its next run, so a composition Marshal could
    not determine the intent of must not become the harness's policy."""
    from pyforge.marshal.cli.main import main

    rc = main(
        [
            "config",
            "--project",
            "pyforge-marshal",
            "--set",
            "max_review_cycles=not-an-int",
            "--write-harness-policy",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    assert not (tmp_path / ".bmad-loop" / "policy.toml").exists(), (
        "a policy was written despite error-severity findings"
    )
    assert rc != 0


def test_the_surface_guard_survives_a_project_layer_that_sets_its_own_verify():
    """S-13.7 (FR-174). `verify_commands` composes LAST-WINS across the four
    layers, and all eight stations set their own — so a repo-wide default would
    be silently dropped by every one of them. Appending at render is what makes
    the guard un-droppable, and this test is the proof."""
    doc = tomllib.loads(render_policy_toml(_compose(verify_commands=["pytest -q"])))
    assert doc["verify"]["commands"][-1] == _SURFACE_RECONCILE_COMMAND
    assert "pytest -q" in doc["verify"]["commands"], "the station's own gate must survive too"


def test_rendering_twice_does_not_duplicate_the_surface_guard():
    """`marshal config --write-harness-policy` is run repeatedly by design (every
    preflight, every loop-home refresh). A guard that accumulated on each render
    would have bmad-loop run the same check N times and grow the file forever."""
    once = tomllib.loads(render_policy_toml(_compose(verify_commands=["pytest -q"])))["verify"]["commands"]
    twice = tomllib.loads(render_policy_toml(_compose(verify_commands=list(once))))["verify"]["commands"]
    assert twice.count(_SURFACE_RECONCILE_COMMAND) == 1, twice
    assert twice == once, "re-rendering an already-rendered policy must be a no-op"


def test_the_guard_never_hands_the_loop_write_baseline():
    """A producer that can stamp its own baseline is exactly the laundering
    S-13.2 exists to end: the loop must RECONCILE by naming the paths it
    changed, never accept its own drift as correct."""
    assert "--write-baseline" not in _SURFACE_RECONCILE_COMMAND


# --- Story 22.8 (FR-193 CAP-8): [adapter].name derives from harness_preference


def test_default_preference_renders_byte_identically():
    """The default preference's first counterpart-bearing entry is claude --
    deliberately equal to the template baseline (see DEFAULT_POLICY's own
    comment) -- so the derive path assigns nothing and every pre-22.8
    caller's render is byte-identical, template comment included."""
    text = render_policy_toml(_compose())
    assert 'name = "claude"               # claude | codex | gemini' in text


def test_preference_led_by_a_counterpart_bearing_profile_renders_its_adapter():
    effective = _compose(harness_preference=["gemini", "claude"])
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["adapter"]["name"] == "gemini"


def test_cursor_led_preference_falls_through_to_the_next_counterpart():
    """cursor has no bmad_loop adapter -- the derivation falls through to
    the next preference entry rather than writing an unknown name that
    would brick the loop home's next run at profile resolution."""
    effective = _compose(harness_preference=["cursor", "copilot"])
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["adapter"]["name"] == "copilot"


def test_no_counterpart_preference_keeps_the_template_default():
    effective = _compose(harness_preference=["cursor", "devin"])
    doc = tomllib.loads(render_policy_toml(effective))
    assert doc["adapter"]["name"] == "claude"


def test_explicit_adapter_argument_still_wins_over_the_preference():
    effective = _compose(harness_preference=["gemini"])
    doc = tomllib.loads(render_policy_toml(effective, adapter="codex"))
    assert doc["adapter"]["name"] == "codex"


def test_cli_write_harness_policy_warns_when_no_counterpart_exists(tmp_path):
    """MRS-POLICY-008 (Story 22.8): a preference with no bmad-loop
    counterpart still renders (template default adapter) but the operator is
    TOLD their expressed preference did not reach the bmad-loop engine."""
    import json as json_module

    from pyforge.marshal.cli.main import main

    policy_toml = tmp_path / "project-policy.toml"
    policy_toml.write_text('harness_preference = ["cursor", "devin"]\n', encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = main(
            [
                "config",
                "--project",
                "acme",
                "--project-policy",
                str(policy_toml),
                "--write-harness-policy",
                str(home),
                "--format",
                "json",
            ]
        )
    assert rc == 0, "a WARN advisory must not block the render"
    payload = json_module.loads(buffer.getvalue())
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-POLICY-008" in codes
    written = home / ".bmad-loop" / "policy.toml"
    parsed = tomllib.loads(written.read_text(encoding="utf-8"))
    assert parsed["adapter"]["name"] == "claude", "template default must stand"


# --- model-cost-catalog sidecar (Story 28.10, CAP-11) ------------------------


def test_plain_json_recursively_coerces_mappings_and_sequences():
    assert _plain_json({"a": (1, 2), "b": {"c": "d"}}) == {"a": [1, 2], "b": {"c": "d"}}


def test_plain_json_passes_through_scalars():
    assert _plain_json(3) == 3
    assert _plain_json("x") == "x"


def test_write_model_cost_catalog_sidecar_writes_when_catalog_declared(tmp_path):
    effective = _compose(model_cost_catalog=_SAMPLE_CATALOG)
    _write_model_cost_catalog_sidecar(effective, tmp_path)
    sidecar = tmp_path / ".bmad-loop" / "marshal-model-cost-catalog.json"
    assert sidecar.is_file()
    assert _load_model_cost_catalog(tmp_path) == _SAMPLE_CATALOG


def test_write_model_cost_catalog_sidecar_removes_stale_sidecar_when_catalog_absent(
    tmp_path,
):
    sidecar_dir = tmp_path / ".bmad-loop"
    sidecar_dir.mkdir()
    sidecar = sidecar_dir / "marshal-model-cost-catalog.json"
    sidecar.write_text("{}", encoding="utf-8")

    _write_model_cost_catalog_sidecar(_compose(), tmp_path)

    assert not sidecar.exists()


def test_write_model_cost_catalog_sidecar_removal_is_a_noop_when_nothing_to_remove(
    tmp_path,
):
    _write_model_cost_catalog_sidecar(_compose(), tmp_path)
    assert not (tmp_path / ".bmad-loop" / "marshal-model-cost-catalog.json").exists()


def test_load_model_cost_catalog_returns_none_when_sidecar_missing(tmp_path):
    assert _load_model_cost_catalog(tmp_path) is None


def test_load_model_cost_catalog_returns_none_when_sidecar_is_not_a_declared_catalog(
    tmp_path,
):
    sidecar_dir = tmp_path / ".bmad-loop"
    sidecar_dir.mkdir()
    (sidecar_dir / "marshal-model-cost-catalog.json").write_text("{}", encoding="utf-8")
    assert _load_model_cost_catalog(tmp_path) is None


def test_read_policy_adapter_and_model_returns_none_none_when_policy_missing(tmp_path):
    assert _read_policy_adapter_and_model(tmp_path) == (None, None)


def test_read_policy_adapter_and_model_reads_the_dev_model_override(tmp_path):
    loop_dir = tmp_path / ".bmad-loop"
    loop_dir.mkdir()
    (loop_dir / "policy.toml").write_text(
        '[adapter]\nname = "claude"\n[adapter.dev]\nmodel = "opus"\n',
        encoding="utf-8",
    )
    assert _read_policy_adapter_and_model(tmp_path) == ("claude", "opus")


def test_read_policy_adapter_and_model_falls_back_to_the_top_level_model(tmp_path):
    loop_dir = tmp_path / ".bmad-loop"
    loop_dir.mkdir()
    (loop_dir / "policy.toml").write_text('[adapter]\nname = "claude"\nmodel = "sonnet"\n', encoding="utf-8")
    assert _read_policy_adapter_and_model(tmp_path) == ("claude", "sonnet")


def test_read_policy_adapter_and_model_returns_none_none_without_an_adapter_table(
    tmp_path,
):
    loop_dir = tmp_path / ".bmad-loop"
    loop_dir.mkdir()
    (loop_dir / "policy.toml").write_text("other = 1\n", encoding="utf-8")
    assert _read_policy_adapter_and_model(tmp_path) == (None, None)


# --- token counts + usage-dollar fields (Story 28.10, CAP-11) ----------------


class _FakeTokens:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeTask:
    def __init__(self, tokens=None):
        self.tokens = tokens


def test_token_counts_from_task_returns_none_when_task_has_no_tokens():
    assert _token_counts_from_task(_FakeTask(tokens=None)) is None


def test_token_counts_from_task_coerces_missing_fields_to_zero():
    counts = _token_counts_from_task(_FakeTask(tokens=_FakeTokens(input_tokens=10)))
    assert counts.input_tokens == 10
    assert counts.output_tokens == 0
    assert counts.cache_read_tokens == 0
    assert counts.cache_creation_tokens == 0


def test_token_counts_from_task_reads_all_four_fields():
    tokens = _FakeTokens(input_tokens=1, output_tokens=2, cache_read_tokens=3, cache_creation_tokens=4)
    counts = _token_counts_from_task(_FakeTask(tokens=tokens))
    assert (counts.input_tokens, counts.output_tokens) == (1, 2)
    assert (counts.cache_read_tokens, counts.cache_creation_tokens) == (3, 4)


def _tokens(**overrides):
    from pyforge.marshal.core.model_cost import TokenCounts

    base = dict(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=0,
        cache_creation_tokens=0,
    )
    base.update(overrides)
    return TokenCounts(**base)


def test_usage_dollar_fields_none_when_adapter_has_no_provider():
    cost, savings = _usage_dollar_fields(
        catalog=_SAMPLE_CATALOG,
        adapter_name="devin",
        model_name="composer-2.5",
        story_tokens=_tokens(),
        layer_savings=None,
    )
    assert (cost, savings) == (None, None)


def test_usage_dollar_fields_none_when_story_tokens_absent():
    cost, savings = _usage_dollar_fields(
        catalog=_SAMPLE_CATALOG,
        adapter_name="cursor",
        model_name="composer-2.5",
        story_tokens=None,
        layer_savings=None,
    )
    assert (cost, savings) == (None, None)


def test_usage_dollar_fields_none_when_model_has_no_declared_price():
    cost, savings = _usage_dollar_fields(
        catalog=_SAMPLE_CATALOG,
        adapter_name="cursor",
        model_name="not-a-priced-model",
        story_tokens=_tokens(),
        layer_savings=None,
    )
    assert (cost, savings) == (None, None)


def test_usage_dollar_fields_computes_cost_with_no_layer_savings():
    cost, savings = _usage_dollar_fields(
        catalog=_SAMPLE_CATALOG,
        adapter_name="cursor",
        model_name="composer-2.5",
        story_tokens=_tokens(),
        layer_savings=None,
    )
    assert cost == pytest.approx(0.50 + 2.50)
    assert savings is None


def test_usage_dollar_fields_computes_savings_across_every_layer_shape():
    layer_savings = LayerSavings(
        output_compression_saved=100,
        wire_compression_saved="unavailable",
        graph_hits_vs_file_reads=(4, 1),
        derived_context_cache_hits=7,
        planning_graph_tokens_saved=500,
    )
    cost, savings = _usage_dollar_fields(
        catalog=_SAMPLE_CATALOG,
        adapter_name="cursor",
        model_name="composer-2.5",
        story_tokens=_tokens(),
        layer_savings=layer_savings,
    )
    assert cost == pytest.approx(3.0)
    assert savings is not None
    assert "planning_graph_tokens_saved" in savings


def test_usage_dollar_fields_string_graph_stat_is_recorded_verbatim():
    layer_savings = LayerSavings(graph_hits_vs_file_reads="degraded: index missing")
    _cost, savings = _usage_dollar_fields(
        catalog=_SAMPLE_CATALOG,
        adapter_name="cursor",
        model_name="composer-2.5",
        story_tokens=_tokens(),
        layer_savings=layer_savings,
    )
    # Only planning_graph_tokens_saved prices into a dollar figure today; a
    # bare string stat with nothing priced yields no savings dict.
    assert savings is None


def test_usage_dollar_fields_savings_none_when_layer_savings_is_all_none():
    _cost, savings = _usage_dollar_fields(
        catalog=_SAMPLE_CATALOG,
        adapter_name="cursor",
        model_name="composer-2.5",
        story_tokens=_tokens(),
        layer_savings=LayerSavings(),
    )
    assert savings is None
