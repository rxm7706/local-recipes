"""Difficulty-tier launch routing across harness profiles and pools (Story 28.11,
CAP-12).

Pure functions over ``model_tier_map`` + ``model_cost_catalog`` — the ONE
FR-51 seam extension. Launch-time only; never changes a model mid-run.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .harness_profile import bmadloop_adapter_for_preference
from .harness_session import classify_session_log, is_transient_harness_session_outcome
from .model_cost import catalog_declared, resolve_model_price

if TYPE_CHECKING:
    from .policy import EffectivePolicy

_STAGE_NAMES: tuple[str, ...] = ("dev", "review", "triage")

# Harness profile name -> ``model_cost_catalog`` provider key.
PROFILE_TO_PROVIDER: dict[str, str] = {
    "claude": "anthropic",
    "cursor": "cursor",
    "gemini": "google",
    "copilot": "openai",
}


@dataclass(frozen=True)
class StageCandidate:
    """One (harness profile, model) preference with optional pool hint."""

    model: str
    harness: str | None = None
    pool: str | None = None


@dataclass(frozen=True)
class ResolvedStage:
    """A resolved stage after pool-preference ordering and fallthrough."""

    model: str
    harness: str | None = None
    pool: str | None = None
    adapter_name: str | None = None


@dataclass(frozen=True)
class TierLaunchResolution:
    """Launch-time tier routing outcome journaled by spin and dispatch."""

    stages: dict[str, ResolvedStage]
    harness_profile: str | None
    adapter_name: str | None
    serving_pools: dict[str, str | None]
    resolved_models: dict[str, str]

    @classmethod
    def from_preference_only(cls, preference: Sequence[str]) -> TierLaunchResolution:
        adapter = bmadloop_adapter_for_preference(preference)
        return cls(
            stages={},
            harness_profile=None,
            adapter_name=adapter,
            serving_pools={},
            resolved_models={},
        )


def parse_stage_entry(raw: object) -> tuple[StageCandidate, ...]:
    """Parse one stage entry: legacy str, inline table, or fallthrough list."""
    if isinstance(raw, str):
        if not raw:
            raise ValueError("empty model name")
        return (StageCandidate(model=raw),)
    if isinstance(raw, Mapping):
        return (_parse_candidate_mapping(raw),)
    if isinstance(raw, (list, tuple)):
        if not raw:
            raise ValueError("empty candidate list")
        return tuple(_parse_candidate_mapping(item) for item in raw)
    raise ValueError(f"unsupported stage entry type: {type(raw)!r}")


def normalize_stage_entries(
    stages: Mapping[str, object],
) -> dict[str, tuple[StageCandidate, ...]]:
    """Expand a difficulty's raw stage map into parsed candidate tuples."""
    result: dict[str, tuple[StageCandidate, ...]] = {}
    for stage, raw in stages.items():
        if stage not in _STAGE_NAMES:
            continue
        try:
            result[stage] = parse_stage_entry(raw)
        except ValueError:
            continue
    return result


def candidate_pool_from_catalog(
    catalog: object,
    *,
    harness: str | None,
    model: str,
) -> str | None:
    """Declared subscription pool for a (harness, model) pair, if any."""
    if not catalog_declared(catalog) or not isinstance(catalog, Mapping):
        return None
    provider = _provider_for_harness(harness)
    if provider is None:
        return None
    price = resolve_model_price(catalog, provider=provider, model=model)
    if price is None:
        return None
    return price.subscription_pool


def sort_candidates_by_pool_preference(
    candidates: Sequence[StageCandidate],
    catalog: object,
) -> tuple[StageCandidate, ...]:
    """Subscription-marked pools first; preserve order within each tier."""
    if not candidates:
        return ()

    def _is_subscription(candidate: StageCandidate) -> bool:
        if candidate.pool is not None:
            return True
        pool = candidate_pool_from_catalog(catalog, harness=candidate.harness, model=candidate.model)
        return pool is not None

    indexed = list(enumerate(candidates))
    indexed.sort(key=lambda pair: (0 if _is_subscription(pair[1]) else 1, pair[0]))
    return tuple(candidate for _, candidate in indexed)


def resolve_stage_candidate(
    candidates: Sequence[StageCandidate],
    *,
    is_review: bool,
    review_floor_model: str | None,
    availability_fn: Callable[[StageCandidate], bool],
    catalog: object,
) -> ResolvedStage | None:
    """Pick the first available candidate; review prefers the floor model.

    Returns ``None`` when nothing declared for this stage is genuinely
    available -- the caller (``resolve_tier_launch``) already treats that
    identically to "no candidates for this stage": the difficulty override
    is dropped and the stage falls back to whatever the base, un-tiered
    policy already declares. This function used to fabricate an answer
    anyway ("never block — fall back to the first declared candidate"),
    which is exactly how a Cursor-only model (``composer-2.5-fast``, no
    ``harness`` key) could be resolved and then written into the launched
    adapter's own stage config even though nothing about it was ever
    confirmed available (2026-09-12, dispatch-tier-routing-fails-safe). A
    stage silently missing its override is always safer than one silently
    carrying an unverified one."""
    if not candidates:
        return None
    floor = review_floor_model if is_review else None
    if is_review:
        floor = candidates[0].model

    ordered = sort_candidates_by_pool_preference(candidates, catalog)
    for candidate in ordered:
        if is_review and floor is not None and candidate.model != floor:
            continue
        if availability_fn(candidate):
            return _resolved_from_candidate(candidate, catalog)
    return None


def resolve_tier_difficulty(
    policy: EffectivePolicy,
    difficulty: str | None,
    *,
    allow_unmapped_fallback: bool = False,
) -> str | None:
    """Map a story difficulty to a ``model_tier_map`` key (FR-51).

    Spin keeps the Story 6.1 rule: an unmapped declared difficulty applies
    no override. Factory dispatch may fall back to ``default``/``medium``/
    ``standard``/first-key when ``allow_unmapped_fallback`` is true.
    """
    tier_map = policy.model_tier_map.value
    if not isinstance(tier_map, Mapping) or not tier_map:
        return None
    if difficulty is not None and difficulty in tier_map:
        return difficulty
    if not allow_unmapped_fallback:
        return None
    for fallback in ("default", "medium", "standard"):
        if fallback in tier_map:
            return fallback
    return next(iter(tier_map))


def resolve_tier_launch(
    policy: EffectivePolicy,
    difficulty: str | None,
    *,
    session_log: str | None = None,
    check_profile: Callable[[str], bool] | None = None,
    excluded_harnesses: frozenset[str] | None = None,
    allow_unmapped_fallback: bool = False,
) -> TierLaunchResolution:
    """Resolve difficulty -> (harness, model) pairs for launch."""
    preference = tuple(policy.harness_preference.value)
    chosen = resolve_tier_difficulty(policy, difficulty, allow_unmapped_fallback=allow_unmapped_fallback)
    if chosen is None:
        return TierLaunchResolution.from_preference_only(preference)

    tier_map = policy.model_tier_map.value
    raw_stages = tier_map.get(chosen)
    if not isinstance(raw_stages, Mapping):
        return TierLaunchResolution.from_preference_only(preference)

    excluded = set(excluded_harnesses or ())
    if session_log and is_transient_harness_session_outcome(classify_session_log(session_log)):
        if preference:
            excluded.add(preference[0])

    catalog = policy.model_cost_catalog.value

    def _available(candidate: StageCandidate) -> bool:
        if candidate.harness is None:
            return True
        if candidate.harness in excluded:
            return False
        if check_profile is not None and not check_profile(candidate.harness):
            return False
        return True

    stage_entries = normalize_stage_entries(raw_stages)
    stages: dict[str, ResolvedStage] = {}
    serving_pools: dict[str, str | None] = {}
    resolved_models: dict[str, str] = {}

    for stage in _STAGE_NAMES:
        candidates = stage_entries.get(stage)
        if not candidates:
            continue
        resolved = resolve_stage_candidate(
            candidates,
            is_review=(stage == "review"),
            review_floor_model=None,
            availability_fn=_available,
            catalog=catalog,
        )
        if resolved is None:
            continue
        stages[stage] = resolved
        resolved_models[stage] = resolved.model
        serving_pools[stage] = resolved.pool

    dev = stages.get("dev")
    harness_profile = dev.harness if dev is not None and dev.harness else None

    if dev is not None and dev.harness is not None:
        adapter_name = bmadloop_adapter_for_preference([dev.harness])
    else:
        adapter_name = bmadloop_adapter_for_preference(preference)

    return TierLaunchResolution(
        stages=stages,
        harness_profile=harness_profile,
        adapter_name=adapter_name,
        serving_pools=serving_pools,
        resolved_models=resolved_models,
    )


def _parse_candidate_mapping(raw: object) -> StageCandidate:
    if not isinstance(raw, Mapping):
        raise ValueError("candidate must be a mapping")
    allowed = {"harness", "model", "pool"}
    if not set(raw.keys()) <= allowed:
        raise ValueError("unknown candidate keys")
    model = raw.get("model")
    if not isinstance(model, str) or not model:
        raise ValueError("model must be a non-empty string")
    harness = raw.get("harness")
    if harness is not None and (not isinstance(harness, str) or not harness):
        raise ValueError("harness must be a non-empty string when present")
    if harness is None:
        raise ValueError("inline table requires harness")
    pool = raw.get("pool")
    if pool is not None and (not isinstance(pool, str) or not pool):
        raise ValueError("pool must be a non-empty string when present")
    return StageCandidate(harness=harness, model=model, pool=pool)


def _provider_for_harness(harness: str | None) -> str | None:
    if harness is None:
        return None
    return PROFILE_TO_PROVIDER.get(harness)


def _resolved_from_candidate(candidate: StageCandidate, catalog: object) -> ResolvedStage:
    pool = candidate.pool or candidate_pool_from_catalog(catalog, harness=candidate.harness, model=candidate.model)
    adapter_name = None
    if candidate.harness is not None:
        adapter_name = bmadloop_adapter_for_preference([candidate.harness])
    return ResolvedStage(
        harness=candidate.harness,
        model=candidate.model,
        pool=pool,
        adapter_name=adapter_name,
    )
