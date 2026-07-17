"""Gate check 4 (AC-1/AC-3): naming / layer / TTL / path conventions
(spine Consistency rows)."""

from __future__ import annotations

import re

from .conftest import (
    FLIP_LIST,
    LAYERS,
    OUTPUT_LAYERS,
    parse_flip_markers,
    pipeline_for,
)

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def test_names_are_snake_case_with_declared_domain_prefix(catalog_config):
    bad = {}
    for name in catalog_config:
        if not _NAME_RE.match(name):
            bad[name] = "not snake_case"
        elif pipeline_for(name) is None:
            bad[name] = "no declared domain prefix"
    assert not bad, f"naming violations: {bad}"


def test_every_entry_carries_a_layer_tag(catalog_config):
    bad = {}
    for name, spec in catalog_config.items():
        layer = (spec.get("metadata") or {}).get("layer")
        if layer not in LAYERS:
            bad[name] = layer
    assert not bad, f"missing/invalid metadata.layer: {bad}"


def test_output_filepaths_follow_data_layer_name_convention(catalog_config):
    """Persisted outputs live under data/<layer>/<dataset_name>/ — nodes
    never choose physical layout (spine Parquet-layout row). External raw
    inputs (legacy stores / seeds / API feeds) are exempt unless they
    already point under data/ (then the same rule applies)."""
    bad = {}
    for name, spec in catalog_config.items():
        layer = (spec.get("metadata") or {}).get("layer")
        path = spec.get("filepath") or spec.get("path")
        if path is None:
            if layer in OUTPUT_LAYERS:
                bad[name] = "output entry with no filepath/path"
            continue
        path = str(path)
        is_local_data = path.startswith("data/")
        if layer in OUTPUT_LAYERS or is_local_data:
            prefix = f"data/{layer}/{name}"
            if not (path == prefix or path.startswith(prefix + "/")):
                bad[name] = path
    assert not bad, f"filepath convention violations: {bad}"


def test_flip_markers_match_declared_flip_list(catalog_raw_text):
    """The `# A3: IncrementalParquetDataset` markers in catalog.yml ARE the
    A3 handoff flip list — drift in either direction fails."""
    marked = parse_flip_markers(catalog_raw_text)
    assert marked == FLIP_LIST, (
        f"marker/FLIP_LIST drift — only-in-yaml: {sorted(marked - FLIP_LIST)}, "
        f"only-in-declared-list: {sorted(FLIP_LIST - marked)}"
    )


def test_every_ttl_gated_entry_has_a_ttl_parameter(parameters, catalog_config):
    ttls = parameters.get("ttls") or {}
    missing = sorted(n for n in FLIP_LIST if n not in ttls)
    assert not missing, f"TTL-gated entries without a ttls.<name> parameter: {missing}"
    # every ttls key must reference a real catalog entry (no orphan TTLs)
    orphans = sorted(k for k in ttls if k not in catalog_config)
    assert not orphans, f"ttls keys with no catalog entry: {orphans}"
    # positive integer seconds only
    bad = {k: v for k, v in ttls.items() if not isinstance(v, int) or v <= 0}
    assert not bad, f"non-positive/non-integer TTLs: {bad}"


def test_freshness_contract_is_separate_from_fetch_ttls(parameters):
    """AD-15: the consumer-side freshness contract is its own parameter,
    never conflated into the ttls namespace."""
    assert (parameters.get("freshness") or {}).get("stale_after_days") == 14
    assert "stale_after_days" not in (parameters.get("ttls") or {})


def test_no_global_ttl_constant(parameters):
    """AD-5: per-dataset TTLs only — no single global TTL key."""
    for forbidden in ("ttl", "global_ttl", "default_ttl", "ttl_seconds", "ttl_days"):
        assert forbidden not in parameters, f"global TTL constant found: {forbidden}"
