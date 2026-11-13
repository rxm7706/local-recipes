"""Story 28.11 (CAP-12) — difficulty-tier routing across providers and pools."""

from __future__ import annotations

import tomllib

import pytest
from pyforge.core.roster import STATIONS, long_form

from pyforge.marshal.adapters.harness_bmadloop import render_policy_toml
from pyforge.marshal.cli.challenge import compose_effective
from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch import resolve_tier_harness
from pyforge.marshal.core.harness_profile import BMADLOOP_ADAPTER_BY_PROFILE
from pyforge.marshal.core.tier_routing import (
    StageCandidate,
    candidate_pool_from_catalog,
    normalize_stage_entries,
    parse_stage_entry,
    resolve_bmadloop_tier_launch,
    resolve_stage_candidate,
    resolve_tier_launch,
    sort_candidates_by_pool_preference,
)

# Story 116.4 (spec-pyforge-marshal:CAP-305): ``test_no_live_tier_renders_a_model_its_adapter_cannot_run`` composes
# every station's tracked ``marshal-policy.toml`` through ``compose_effective``, which resolves them from
# ``repo_root()``; the tree-read guard runs each package-half test off the tree, where it fails. The module holds 20
# tests, so it is marked whole (Story 116.2's rule) and fails, never skips, when a station's policy is absent.
pytestmark = pytest.mark.live_tree

_SAMPLE_CATALOG = {
    "providers": {
        "cursor": {
            "subscription_pool": "cursor-ultra",
            "models": {
                "composer-2.5": {
                    "input_per_million": 0.50,
                    "output_per_million": 2.50,
                },
            },
        },
        "google": {
            "subscription_pool": "gemini-api",
            "models": {
                "gemini-3.7-flash": {
                    "input_per_million": 0.75,
                    "output_per_million": 3.75,
                },
            },
        },
    }
}


def _compose(**project):
    effective, _ = policy.compose(project_slug="acme", project=project, flags={})
    return effective


def test_parse_stage_entry_legacy_string():
    assert parse_stage_entry("haiku") == (StageCandidate(model="haiku"),)


def test_parse_stage_entry_inline_table():
    parsed = parse_stage_entry({"harness": "gemini", "model": "gemini-3.7-flash"})
    assert parsed == (StageCandidate(harness="gemini", model="gemini-3.7-flash"),)


def test_parse_stage_entry_fallthrough_list():
    parsed = parse_stage_entry(
        [
            {"harness": "cursor", "model": "composer-2.5", "pool": "cursor-ultra"},
            {"harness": "gemini", "model": "gemini-3.7-flash"},
        ]
    )
    assert len(parsed) == 2
    assert parsed[0].pool == "cursor-ultra"


def test_policy_accepts_cross_provider_tier_map():
    tier_map = {
        "easy": {
            "dev": {"harness": "gemini", "model": "gemini-3.7-flash"},
            "review": [
                {"harness": "cursor", "model": "composer-2.5"},
                {"harness": "claude", "model": "sonnet-5"},
            ],
        }
    }
    effective, findings = policy.compose(project_slug="acme", project={"model_tier_map": tier_map}, flags={})
    assert findings == ()
    assert effective.model_tier_map.value["easy"]["dev"]["harness"] == "gemini"


def test_sort_candidates_prefers_subscription_pool_first():
    candidates = (
        StageCandidate(harness="gemini", model="unknown-economy-model"),
        StageCandidate(
            harness="cursor",
            model="composer-2.5",
            pool="cursor-ultra",
        ),
    )
    ordered = sort_candidates_by_pool_preference(candidates, _SAMPLE_CATALOG)
    assert ordered[0].harness == "cursor"


def test_candidate_pool_from_catalog():
    pool = candidate_pool_from_catalog(_SAMPLE_CATALOG, harness="cursor", model="composer-2.5")
    assert pool == "cursor-ultra"


def test_review_stage_never_drops_below_first_candidate_model():
    candidates = (
        StageCandidate(harness="cursor", model="composer-2.5", pool="cursor-ultra"),
        StageCandidate(harness="claude", model="composer-2.5"),
    )

    def _reject_cursor(candidate: StageCandidate) -> bool:
        return candidate.harness != "cursor"

    resolved = resolve_stage_candidate(
        candidates,
        is_review=True,
        review_floor_model=None,
        availability_fn=_reject_cursor,
        catalog=_SAMPLE_CATALOG,
    )
    assert resolved is not None
    assert resolved.model == "composer-2.5"
    assert resolved.harness == "claude"


def test_resolve_stage_candidate_returns_none_when_nothing_is_available():
    """2026-09-12 (dispatch-tier-routing-fails-safe): when every declared
    candidate for a stage fails ``availability_fn``, the function must
    return ``None`` -- never fabricate an answer by falling back to a
    candidate nothing confirmed available. The prior "never block" fallback
    is exactly how an unverified candidate (a Cursor model with no
    resolvable harness) could be resolved and then written into a real
    launch's adapter config despite failing every check. ``resolve_tier_
    launch``'s own ``if resolved is None: continue`` already treats this
    identically to "no candidates for this stage": the difficulty override
    is dropped and the stage falls back to the un-tiered baseline."""
    candidates = (StageCandidate(harness="cursor", model="composer-2.5"),)

    resolved = resolve_stage_candidate(
        candidates,
        is_review=False,
        review_floor_model=None,
        availability_fn=lambda candidate: False,
        catalog=_SAMPLE_CATALOG,
    )
    assert resolved is None


def test_resolve_stage_candidate_review_returns_none_when_nothing_is_available():
    """Same as above for the review stage's floor-preference path -- an
    unavailable floor candidate must not be forced through either."""
    candidates = (StageCandidate(harness="cursor", model="composer-2.5"),)

    resolved = resolve_stage_candidate(
        candidates,
        is_review=True,
        review_floor_model=None,
        availability_fn=lambda candidate: False,
        catalog=_SAMPLE_CATALOG,
    )
    assert resolved is None


def test_resolve_tier_launch_journals_models_and_pools():
    effective = _compose(
        model_tier_map={
            "easy": {
                "dev": {"harness": "cursor", "model": "composer-2.5"},
                "review": {"harness": "cursor", "model": "composer-2.5"},
            }
        },
        model_cost_catalog=_SAMPLE_CATALOG,
        harness_preference=["cursor"],
    )
    resolution = resolve_tier_launch(effective, "easy")
    assert resolution.resolved_models == {
        "dev": "composer-2.5",
        "review": "composer-2.5",
    }
    assert resolution.harness_profile == "cursor"
    assert resolution.serving_pools["dev"] == "cursor-ultra"


def test_transient_session_log_skips_first_preference_harness():
    effective = _compose(
        model_tier_map={
            "easy": {
                "dev": [
                    {"harness": "cursor", "model": "composer-2.5"},
                    {"harness": "gemini", "model": "gemini-3.7-flash"},
                ]
            }
        },
        model_cost_catalog=_SAMPLE_CATALOG,
        harness_preference=["cursor", "gemini"],
    )
    resolution = resolve_tier_launch(
        effective,
        "easy",
        session_log="Error: rate limit exceeded for this account",
    )
    assert resolution.harness_profile == "gemini"
    assert resolution.resolved_models["dev"] == "gemini-3.7-flash"


def test_render_policy_toml_differs_with_cross_provider_tier_resolution():
    base = _compose(harness_preference=["claude"])
    populated = _compose(
        harness_preference=["claude"],
        model_tier_map={
            "easy": {
                "dev": {"harness": "gemini", "model": "gemini-3.7-flash"},
                "review": {"harness": "claude", "model": "sonnet-5"},
            }
        },
    )
    empty_render = render_policy_toml(base, difficulty="easy")
    resolution = resolve_tier_launch(populated, "easy")
    tiered_render = render_policy_toml(
        populated,
        difficulty="easy",
        tier_resolution=resolution,
    )
    assert empty_render != tiered_render
    parsed = tomllib.loads(tiered_render)
    assert parsed["adapter"]["name"] == "gemini"
    assert parsed["adapter"]["dev"]["model"] == "gemini-3.7-flash"
    assert parsed["adapter"]["review"]["model"] == "sonnet-5"


def test_legacy_string_tier_map_still_renders():
    effective = _compose(
        model_tier_map={"heavy": {"dev": "opus", "review": "opus"}},
        harness_preference=["claude"],
    )
    resolution = resolve_tier_launch(effective, "heavy")
    text = render_policy_toml(effective, difficulty="heavy", tier_resolution=resolution)
    parsed = tomllib.loads(text)
    assert parsed["adapter"]["dev"]["model"] == "opus"
    assert parsed["adapter"]["review"]["model"] == "opus"


def test_unmapped_difficulty_applies_no_override_for_spin_path():
    effective = _compose(
        model_tier_map={"medium": {"dev": "sonnet-5"}},
        harness_preference=["claude"],
    )
    resolution = resolve_tier_launch(effective, "unknown")
    assert resolution.resolved_models == {}


def test_dispatch_fallback_uses_medium_tier():
    effective = _compose(
        model_tier_map={"medium": {"dev": "sonnet-5"}},
        harness_preference=["claude"],
    )
    resolution = resolve_tier_launch(effective, "unknown", allow_unmapped_fallback=True)
    assert resolution.resolved_models["dev"] == "sonnet-5"


_CURSOR_STAGE = {"harness": "cursor", "model": "composer-2.5-fast"}


def test_a_bmadloop_launch_resolves_no_stage_on_a_harness_with_no_adapter():
    """Story 33.16 AC1: bmad-loop has no Cursor or Devin adapter, so the journal's ``resolved_models`` stays empty."""
    for harness in ("cursor", "devin"):
        effective = _compose(
            harness_preference=[harness],
            model_tier_map={
                "heavy": {"dev": {"harness": harness, "model": "x"}, "review": {"harness": harness, "model": "x"}}
            },
        )
        launch = resolve_bmadloop_tier_launch(effective, "heavy")
        assert launch.stages == {}
        assert launch.resolved_models == {}


def test_a_bmadloop_launch_keeps_a_harness_with_an_adapter():
    effective = _compose(
        harness_preference=["cursor"],
        model_tier_map={"frontier": {"dev": {"harness": "claude", "model": "claude-fable-5-1"}}},
    )
    launch = resolve_bmadloop_tier_launch(effective, "frontier")
    assert launch.resolved_models == {"dev": "claude-fable-5-1"}
    assert launch.adapter_name == "claude"


def test_a_bmadloop_launch_falls_through_to_the_next_launchable_candidate():
    """Story 33.16 AC2."""
    effective = _compose(
        harness_preference=["cursor"],
        model_tier_map={
            "heavy": {
                "dev": [_CURSOR_STAGE, {"harness": "claude", "model": "claude-sonnet-5-5"}],
                "review": [_CURSOR_STAGE, {"harness": "claude", "model": "opus"}],
            }
        },
    )
    launch = resolve_bmadloop_tier_launch(effective, "heavy")
    assert launch.resolved_models == {"dev": "claude-sonnet-5-5"}, "review holds to its first candidate's model"
    assert launch.adapter_name == "claude"


def test_dispatch_still_resolves_the_cursor_model():
    """Story 33.16 AC6: ``marshal factory dispatch`` launches Cursor itself, so only a bmad-loop launch drops it."""
    effective = _compose(harness_preference=["cursor"], model_tier_map={"heavy": {"dev": _CURSOR_STAGE}})
    assert resolve_tier_harness(effective, difficulty="heavy").resolved_models == {"dev": "composer-2.5-fast"}


def _spin_render(effective, difficulty):
    """The adapter name and every stage model of the policy spin writes."""
    launch = resolve_bmadloop_tier_launch(effective, difficulty)
    adapter = tomllib.loads(
        render_policy_toml(effective, difficulty=difficulty, adapter=launch.adapter_name, tier_resolution=launch)
    )["adapter"]
    stages = (adapter.get("dev") or adapter, adapter["review"], adapter.get("triage", {}))
    return adapter["name"], {stage["model"] for stage in stages if "model" in stage}


def _launchable_models(stages):
    return {
        candidate.model
        for candidates in normalize_stage_entries(stages).values()
        for candidate in candidates
        if candidate.harness in BMADLOOP_ADAPTER_BY_PROFILE
    }


def test_no_live_tier_renders_a_model_its_adapter_cannot_run():
    """Story 33.16 AC5: every tier of all eight live policies renders the baselines or a stage bmad-loop can launch, so
    a Cursor model reds here whatever its shape, a bare string included, and with or without a catalog."""
    for slug in (long_form(station) for station in STATIONS):
        effective = compose_effective(slug)
        tier_map = effective.model_tier_map.value
        assert tier_map, f"{slug} composed no tier map, so this test would prove nothing for it"
        _, baselines = _spin_render(effective, None)
        for difficulty, stages in tier_map.items():
            adapter, models = _spin_render(effective, difficulty)
            assert adapter in BMADLOOP_ADAPTER_BY_PROFILE.values(), (slug, difficulty)
            assert models <= baselines | _launchable_models(stages), (slug, difficulty)
    marshal = compose_effective("pyforge-marshal")
    assert _spin_render(marshal, "frontier")[1] == _launchable_models(marshal.model_tier_map.value["frontier"])
