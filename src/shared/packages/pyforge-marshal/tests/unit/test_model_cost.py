"""Story 28.10 (CAP-11) — declared model-cost catalog tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.core import model_cost, policy
from pyforge.marshal.core.model_cost import (
    TokenCounts,
    catalog_declared,
    estimate_spend_usd,
    resolve_cache_read_ratio,
    resolve_model_price,
    weighted_total,
)

_SAMPLE_CATALOG = {
    "providers": {
        "cursor": {
            "subscription_pool": "cursor-ultra",
            "models": {
                "composer-2.5": {
                    "input_per_million": 0.50,
                    "output_per_million": 2.50,
                    "cache_read_per_million": 0.20,
                },
                "composer-2.5-fast": {
                    "input_per_million": 3.00,
                    "output_per_million": 15.00,
                    "cache_read_per_million": 0.50,
                },
            },
        },
        "anthropic": {
            "subscription_pool": "claude-max",
            "models": {
                "sonnet-5": {
                    "input_per_million": 2.00,
                    "output_per_million": 10.00,
                    "cache_read_per_million": 0.20,
                    "cache_write_per_million": 2.50,
                },
            },
        },
    }
}


def test_empty_catalog_is_not_declared_and_policy_default_is_byte_identical():
    assert not catalog_declared({})
    assert not catalog_declared({"providers": {}})
    effective, _ = policy.compose(project_slug="acme", project={}, flags={})
    assert effective.model_cost_catalog.value == {}


def test_per_provider_cache_read_ratio_differs_from_global_default():
    cursor_ratio = resolve_cache_read_ratio(_SAMPLE_CATALOG, provider="cursor", model="composer-2.5")
    anthropic_ratio = resolve_cache_read_ratio(_SAMPLE_CATALOG, provider="anthropic", model="sonnet-5")
    assert cursor_ratio == pytest.approx(0.40)
    assert anthropic_ratio == pytest.approx(0.10)
    assert cursor_ratio != anthropic_ratio


def test_weighted_total_uses_declared_provider_ratio():
    tokens = TokenCounts(
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=1000,
        cache_creation_tokens=0,
    )
    at_global = weighted_total(tokens, model_cost.DEFAULT_CACHE_READ_WEIGHT)
    at_cursor = weighted_total(tokens, 0.40)
    assert at_cursor > at_global
    assert at_global == 1600
    assert at_cursor == 1900


def test_unknown_model_is_not_fabricated():
    assert resolve_model_price(_SAMPLE_CATALOG, provider="cursor", model="missing") is None


def test_estimate_spend_usd_from_declared_prices():
    price = resolve_model_price(_SAMPLE_CATALOG, provider="cursor", model="composer-2.5")
    assert price is not None
    tokens = TokenCounts(
        input_tokens=1_000_000,
        output_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
    )
    assert estimate_spend_usd(tokens, price) == pytest.approx(0.50)


def test_compose_accepts_model_cost_catalog_from_project_layer():
    effective, findings = policy.compose(
        project_slug="pyforge-marshal",
        project={"model_cost_catalog": _SAMPLE_CATALOG},
        flags={},
    )
    assert not findings
    assert catalog_declared(effective.model_cost_catalog.value)
    assert effective.model_cost_catalog.layer == "project"


def test_compose_rejects_malformed_catalog():
    _, findings = policy.compose(
        project_slug="acme",
        project={"model_cost_catalog": {"providers": {"x": {"models": {}}}}},
        flags={},
    )
    assert any(f.code == "MRS-POLICY-002" for f in findings)


def test_model_cost_module_has_no_network_imports():
    source = Path(model_cost.__file__).read_text(encoding="utf-8")
    for token in ("urllib", "requests", "httpx", "aiohttp", "socket"):
        assert token not in source


def test_marshal_policy_toml_seed_catalog_parses():
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    if not policy_path.is_file():
        pytest.skip("marshal-policy.toml not present in this checkout")
    import tomllib

    with open(policy_path, "rb") as handle:
        data = tomllib.load(handle)
    catalog = data.get("model_cost_catalog")
    assert catalog is not None
    assert catalog_declared(catalog)
    effective, findings = policy.compose(
        project_slug="pyforge-marshal",
        project={"model_cost_catalog": catalog},
        flags={},
    )
    assert not findings
    assert catalog_declared(effective.model_cost_catalog.value)
