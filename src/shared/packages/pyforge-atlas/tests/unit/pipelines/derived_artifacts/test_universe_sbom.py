"""Story B7 — build_universe_sbom (AC-3): the full-universe CycloneDX BOM under
the 14-day freshness contract. One conda component per package, cfe:atlas_built_at
stamped, ?channel qualifier on every conda purl, cfe:pypi_name on mapped rows."""

from __future__ import annotations

import time

import pandas as pd

from pyforge.atlas.pipelines.derived_artifacts.nodes import build_universe_sbom
from pyforge.atlas.pipelines.universal_sbom.nodes import check_universe_freshness


def _core():
    return pd.DataFrame(
        [
            {"conda_name": "numpy", "latest_version": "1.26.0"},
            {"conda_name": "pillow", "latest_version": "10.3.0"},
            {"conda_name": "noversion", "latest_version": None},
        ]
    )


def _mapping():
    return pd.DataFrame([{"pypi_name": "pillow", "conda_name": "pillow"}])


def test_universe_bom_shape_and_channel_qualifiers():
    bom = build_universe_sbom(_core(), _mapping(), {})
    assert bom["bomFormat"] == "CycloneDX"
    by_name = {c["name"]: c for c in bom["components"]}
    assert by_name["numpy"]["purl"] == "pkg:conda/numpy@1.26.0?channel=conda-forge"
    assert by_name["noversion"]["purl"] == "pkg:conda/noversion?channel=conda-forge"  # no version -> bare
    # every conda purl carries the qualifier
    assert all("?channel=conda-forge" in c["purl"] for c in bom["components"])


def test_mapped_row_carries_cfe_pypi_name_for_membership():
    bom = build_universe_sbom(_core(), _mapping(), {})
    by_name = {c["name"]: c for c in bom["components"]}
    props = {p["name"]: p["value"] for p in by_name["pillow"].get("properties", [])}
    assert props["cfe:pypi_name"] == "pillow"
    # unmapped row has no pypi property
    assert "properties" not in by_name["numpy"]


def test_atlas_built_at_stamp_enables_the_freshness_gate():
    now = time.time()
    bom = build_universe_sbom(_core(), _mapping(), {"universe_sbom": {"now": now}})
    props = {p["name"]: p["value"] for p in bom["metadata"]["properties"]}
    assert props["cfe:atlas_built_at"] == str(int(now))
    # the produced BOM passes its own freshness gate (fresh)
    assert check_universe_freshness(bom, 14, now=now + 3600) is not None


def test_built_at_defaults_to_now_when_no_param():
    before = int(time.time())
    bom = build_universe_sbom(_core(), _mapping(), {})
    stamp = int(next(p["value"] for p in bom["metadata"]["properties"] if p["name"] == "cfe:atlas_built_at"))
    assert stamp >= before
