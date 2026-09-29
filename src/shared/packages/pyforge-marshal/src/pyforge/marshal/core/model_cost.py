"""Declared model-cost catalog helpers (Story 28.10, CAP-11).

Pure functions over policy-declared price tables — never network I/O.
Dollar figures are advisory estimates from declared prices × observed token
counts; they never feed verdicts or exit codes.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

DEFAULT_CACHE_READ_WEIGHT = 0.1
_MILLION = 1_000_000.0

# Harness adapter name -> catalog provider key (Story 28.10).
ADAPTER_TO_PROVIDER: dict[str, str] = {
    "cursor": "cursor",
    "claude": "anthropic",
    "copilot": "openai",
    "gemini": "google",
}

PriceField = Literal[
    "input_per_million",
    "output_per_million",
    "cache_read_per_million",
    "cache_write_per_million",
]


@dataclass(frozen=True)
class TokenCounts:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float
    cache_read_per_million: float | None = None
    cache_write_per_million: float | None = None
    subscription_pool: str | None = None


def catalog_declared(catalog: object) -> bool:
    """True when the policy carries a non-empty declared catalog."""
    if not isinstance(catalog, Mapping):
        return False
    providers = catalog.get("providers")
    return isinstance(providers, Mapping) and bool(providers)


def adapter_provider(adapter_name: str | None) -> str | None:
    if adapter_name is None:
        return None
    return ADAPTER_TO_PROVIDER.get(adapter_name)


def resolve_model_price(
    catalog: Mapping[str, object],
    *,
    provider: str,
    model: str | None = None,
) -> ModelPrice | None:
    """Look up a declared price entry; absent models are not fabricated."""
    providers = catalog.get("providers")
    if not isinstance(providers, Mapping):
        return None
    provider_block = providers.get(provider)
    if not isinstance(provider_block, Mapping):
        return None
    models = provider_block.get("models")
    if not isinstance(models, Mapping):
        return None
    if model is not None:
        entry = models.get(model)
        if isinstance(entry, Mapping):
            return _price_from_entry(entry, provider_block)
        return None
    # Provider-level default: first declared model with input pricing.
    for entry in models.values():
        if isinstance(entry, Mapping):
            parsed = _price_from_entry(entry, provider_block)
            if parsed is not None:
                return parsed
    return None


def provider_declaring_model(catalog: object, model: str) -> str | None:
    """Which declared catalog provider (if any) names this exact model --
    the reverse of ``resolve_model_price`` (that looks up a KNOWN provider's
    price; this finds which provider, if any, claims a given model at all).

    Used to catch a ``model_tier_map`` stage entry whose model plainly
    belongs to a DIFFERENT provider than the adapter that will actually
    launch it -- e.g. a Cursor model (``composer-2.5-fast``) landing on the
    ``claude`` adapter because its tier-map entry carried no explicit
    ``harness`` key and the operator's own ``harness_preference`` (`cursor`)
    has no bmad-loop counterpart, so the render silently falls back to the
    template's baseline adapter while the model override still applies
    unchanged (2026-09-12, dispatch-tier-routing-fails-safe). Absence from
    the catalog is not itself suspicious: most legitimate default-adapter
    models (``sonnet``, ``opus``, ``haiku`` -- see
    ``HARNESS_DEFAULT_MODEL_IDS``) are never catalogued at all, since the
    catalog is a declared PRICE snapshot, not a model registry."""
    if not catalog_declared(catalog) or not isinstance(catalog, Mapping):
        return None
    providers = catalog.get("providers")
    if not isinstance(providers, Mapping):
        return None
    for provider_name, provider_block in providers.items():
        if not isinstance(provider_block, Mapping):
            continue
        models = provider_block.get("models")
        if isinstance(models, Mapping) and model in models:
            return provider_name
    return None


#: Marshal's own model-tier vocabulary (Story 22.8's harness-profile TOMLs
#: under ``data/harness_profiles/``: every profile either maps these three
#: names to its own CLI spelling (``[model_map]``, e.g. ``gemini.toml``) or
#: passes them through verbatim as its default ids (``model_passthrough``,
#: e.g. ``claude.toml``'s own comment: "Marshal's model tiers
#: (opus/sonnet/haiku)"). These are exactly the "default-adapter models"
#: ``provider_declaring_model``'s docstring says are legitimately never
#: catalogued (Story 51.5, CAP-253).
HARNESS_DEFAULT_MODEL_IDS: frozenset[str] = frozenset({"sonnet", "opus", "haiku"})


def is_harness_default_model(model: str) -> bool:
    """True when ``model`` is one of marshal's own tier-vocabulary ids --
    a harness's own default/alias id, not a genuinely foreign or mistyped
    model. Used alongside ``provider_declaring_model`` to tell "uncatalogued
    because it's the harness's own default" apart from "uncatalogued
    because no provider claims it at all" (Story 51.5, CAP-253)."""
    return model in HARNESS_DEFAULT_MODEL_IDS


def resolve_cache_read_ratio(
    catalog: Mapping[str, object] | None,
    *,
    provider: str | None,
    model: str | None = None,
    default: float = DEFAULT_CACHE_READ_WEIGHT,
) -> float:
    """Derive cache-read weight from declared ratios; global default fallback."""
    if catalog is None or provider is None:
        return default
    price = resolve_model_price(catalog, provider=provider, model=model)
    if price is None or price.input_per_million <= 0:
        return default
    if price.cache_read_per_million is None:
        return default
    ratio = price.cache_read_per_million / price.input_per_million
    if not math.isfinite(ratio) or ratio < 0:
        return default
    return ratio


def weighted_total(tokens: TokenCounts, cache_read_weight: float) -> int:
    """bmad-loop-compatible weighted token tally."""
    if not math.isfinite(cache_read_weight):
        return tokens.input_tokens + tokens.output_tokens
    return tokens.input_tokens + tokens.output_tokens + round(tokens.cache_read_tokens * cache_read_weight)


def estimate_spend_usd(
    tokens: TokenCounts,
    price: ModelPrice,
) -> float | None:
    """Estimated USD spend from declared per-1M prices × token counts."""
    if price.input_per_million < 0 or price.output_per_million < 0:
        return None
    total = (tokens.input_tokens * price.input_per_million + tokens.output_tokens * price.output_per_million) / _MILLION
    if price.cache_read_per_million is not None and tokens.cache_read_tokens:
        total += (tokens.cache_read_tokens * price.cache_read_per_million) / _MILLION
    if price.cache_write_per_million is not None and tokens.cache_creation_tokens:
        total += (tokens.cache_creation_tokens * price.cache_write_per_million) / _MILLION
    if not math.isfinite(total):
        return None
    return round(total, 6)


def estimate_layer_savings_usd(
    layer_savings: Mapping[str, object],
    price: ModelPrice,
) -> dict[str, float]:
    """Advisory dollar estimates for per-layer savings fields when priced."""
    result: dict[str, float] = {}
    planning_saved = layer_savings.get("planning_graph_tokens_saved")
    if isinstance(planning_saved, (int, float)) and not isinstance(planning_saved, bool):
        token_counts = TokenCounts(
            input_tokens=0,
            output_tokens=int(planning_saved),
            cache_read_tokens=0,
            cache_creation_tokens=0,
        )
        usd = estimate_spend_usd(token_counts, price)
        if usd is not None:
            result["planning_graph_tokens_saved"] = usd
    return result


def _price_from_entry(
    entry: Mapping[str, object],
    provider_block: Mapping[str, object],
) -> ModelPrice | None:
    input_rate = _positive_number(entry.get("input_per_million"))
    output_rate = _positive_number(entry.get("output_per_million"))
    if input_rate is None or output_rate is None:
        return None
    cache_read = _optional_number(entry.get("cache_read_per_million"))
    cache_write = _optional_number(entry.get("cache_write_per_million"))
    pool = entry.get("subscription_pool")
    if pool is None:
        pool = provider_block.get("subscription_pool")
    subscription_pool = pool if isinstance(pool, str) and pool else None
    return ModelPrice(
        input_per_million=input_rate,
        output_per_million=output_rate,
        cache_read_per_million=cache_read,
        cache_write_per_million=cache_write,
        subscription_pool=subscription_pool,
    )


def _positive_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number < 0 or not math.isfinite(number):
        return None
    return number


def _optional_number(value: object) -> float | None:
    if value is None:
        return None
    return _positive_number(value)
