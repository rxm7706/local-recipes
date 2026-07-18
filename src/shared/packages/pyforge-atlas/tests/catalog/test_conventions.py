"""Gate check 4 (AC-1/AC-3): naming / layer / TTL / path conventions
(spine Consistency rows)."""

from __future__ import annotations

import re

from .conftest import (
    EXPECTED_FLIP_MARKERS,
    FLIP_LIST,
    LAYERS,
    OUTPUT_LAYERS,
    parse_markers,
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


def test_a3_flip_markers_match_declared_flip_list(catalog_raw_text):
    """The `# A3: IncrementalParquetDataset` markers in catalog.yml ARE the
    A3 handoff flip list — drift in either direction fails."""
    markers = parse_markers(catalog_raw_text)
    marked = {name for name, m in markers.items() if m == "A3"}
    assert marked == FLIP_LIST, (
        f"marker/FLIP_LIST drift — only-in-yaml: {sorted(marked - FLIP_LIST)}, "
        f"only-in-declared-list: {sorted(FLIP_LIST - marked)}"
    )


def test_flip_story_markers_match_declared_map(catalog_raw_text):
    """Review-pass P2: the GROWN flip list — every `# FLIP(<story>)` marker
    (interim declarations a NAMED story re-declares) is pinned in
    conftest.EXPECTED_FLIP_MARKERS; drift in either direction fails, so the
    one-APIDataset-one-URL contradiction can never go implicit again."""
    markers = parse_markers(catalog_raw_text)
    flip_marked = {name: m for name, m in markers.items() if m != "A3"}
    assert flip_marked == EXPECTED_FLIP_MARKERS, (
        f"FLIP marker drift — in-yaml: {flip_marked}, "
        f"declared: {EXPECTED_FLIP_MARKERS}"
    )


def test_every_ttl_gated_entry_has_a_ttl_parameter(parameters, catalog_config):
    ttls = parameters.get("ttls") or {}
    missing = sorted(n for n in FLIP_LIST if n not in ttls)
    assert not missing, f"TTL-gated entries without a ttls.<name> parameter: {missing}"
    # every ttls key must reference a real catalog entry (no orphan TTLs)
    orphans = sorted(k for k in ttls if k not in catalog_config)
    assert not orphans, f"ttls keys with no catalog entry: {orphans}"
    # positive integer seconds only — bools are ints in Python (P8), so
    # `some_ttl: true` must be rejected explicitly, not coerced to 1s
    bad = {
        k: v
        for k, v in ttls.items()
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0
    }
    assert not bad, f"non-positive/non-integer/boolean TTLs: {bad}"


_NO_TTL_RE = re.compile(r"^#\s*NO-TTL\(([a-z][a-z0-9_]*)\):")


def _no_ttl_markers(parameters_raw_text) -> set[str]:
    return {
        m.group(1)
        for line in parameters_raw_text.splitlines()
        if (m := _NO_TTL_RE.match(line.strip()))
    }


def test_no_ttl_markers_are_valid_and_kev_is_covered(
    parameters, catalog_config, parameters_raw_text
):
    """Review-pass P8: a deliberately TTL-less fetch feed must say so with
    an explicit `# NO-TTL(<entry>): <reason>` marker (the story's
    do-not-guess rule made KEV's omission deliberate — this makes it
    visible and gate-checked instead of indistinguishable from an
    oversight). Markers must name a real catalog entry that has NO ttls
    key (a stale marker on a now-TTL'd entry fails)."""
    ttls = parameters.get("ttls") or {}
    markers = _no_ttl_markers(parameters_raw_text)
    unknown = sorted(m for m in markers if m not in catalog_config)
    assert not unknown, f"NO-TTL markers naming unknown catalog entries: {unknown}"
    stale = sorted(m for m in markers if m in ttls)
    assert not stale, f"NO-TTL markers on entries that DO have a ttls key: {stale}"
    # the three vulnerability side-feeds: each has a TTL or an explicit NO-TTL
    for feed in (
        "vulnerability_cisa_kev_raw",
        "vulnerability_epss_raw",
        "vulnerability_cwe_catalog_raw",
    ):
        assert feed in ttls or feed in markers, (
            f"{feed}: neither a ttls key nor a NO-TTL marker — a TTL-less "
            "fetch feed must be deliberate and documented"
        )
    # G-4(B2): the A2 NO-TTL placeholder for KEV was explicitly deferred to the
    # vulnerability-pipeline port; B2 made the cadence decision (daily re-fetch),
    # so KEV now carries a ttls key instead of a NO-TTL marker. Verify the VALUE
    # (the recorded daily cadence), not just membership.
    assert ttls.get("vulnerability_cisa_kev_raw") == 86400  # G-4 daily re-fetch


def test_orphan_ttls_name_their_future_consumer(parameters, parameters_raw_text):
    """Review-pass P8: ttls keys outside the A3 FLIP_LIST are consumed by
    NO shipped code yet — each must carry a `[future_consumer: B*]`
    annotation naming the owning story, so they are visibly pending work,
    not dead config."""
    ttls = parameters.get("ttls") or {}
    annotated = {
        m.group(1): m.group(2)
        for line in parameters_raw_text.splitlines()
        if (m := re.match(
            r"^([a-z][a-z0-9_]*):.*\[future_consumer:\s*(B\d+)\b", line.strip()
        ))
    }
    missing = sorted(k for k in ttls if k not in FLIP_LIST and k not in annotated)
    assert not missing, (
        f"orphan ttls keys (not in FLIP_LIST) without a [future_consumer: B*] "
        f"annotation: {missing}"
    )
    stray = sorted(k for k in annotated if k in FLIP_LIST)
    assert not stray, f"FLIP_LIST entries carrying a future_consumer annotation: {stray}"


def test_freshness_contract_is_separate_from_fetch_ttls(parameters):
    """AD-15: the consumer-side freshness contract is its own parameter,
    never conflated into the ttls namespace."""
    assert (parameters.get("freshness") or {}).get("stale_after_days") == 14
    assert "stale_after_days" not in (parameters.get("ttls") or {})


def test_no_global_ttl_constant(parameters):
    """AD-5: per-dataset TTLs only — no single global TTL key."""
    for forbidden in ("ttl", "global_ttl", "default_ttl", "ttl_seconds", "ttl_days"):
        assert forbidden not in parameters, f"global TTL constant found: {forbidden}"
