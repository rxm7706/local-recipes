"""Story 28.11 (CAP-12) — difficulty-tier routing across providers and pools."""

from __future__ import annotations

import tomllib

from pyforge.marshal.adapters.harness_bmadloop import render_policy_toml
from pyforge.marshal.core import policy
from pyforge.marshal.core.tier_routing import (
    StageCandidate,
    candidate_pool_from_catalog,
    parse_stage_entry,
    resolve_stage_candidate,
    resolve_tier_launch,
    sort_candidates_by_pool_preference,
)

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
