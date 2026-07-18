"""Single-writer proof for the three § 3.4 external-refresh stores (Story B5 — AC-2).

The `add-handoff` single-write-path invariant, applied to the external stores: each of
`vulnerability_vdb_store`, `vulnerability_osv_offline_store`, `pypi_conda_map_store` is
produced by EXACTLY ONE node (its refresh asset) across the whole pipeline set, and
consumed read-only everywhere else. Phases G / G' and `scan-project` offline mode never
write them — the pipeline writes them only via the refresh assets.
"""

from __future__ import annotations

from pyforge.atlas.pipelines.core import create_pipeline as core_create
from pyforge.atlas.pipelines.pypi_intelligence import create_pipeline as pypi_create
from pyforge.atlas.pipelines.vcs_health import create_pipeline as vcs_create
from pyforge.atlas.pipelines.vulnerability import create_pipeline as vuln_create

# store -> the ONE node allowed to write it (its § 3.4 refresh asset).
_STORE_TO_REFRESH_ASSET = {
    "vulnerability_vdb_store": "refresh_vdb_store",
    "vulnerability_osv_offline_store": "refresh_osv_offline_store",
    "pypi_conda_map_store": "export_pypi_conda_map",
}


def _all_nodes():
    combined = core_create() + vcs_create() + pypi_create() + vuln_create()
    return list(combined.nodes)


def test_each_store_written_by_exactly_one_refresh_asset():
    nodes = _all_nodes()
    for store, expected_writer in _STORE_TO_REFRESH_ASSET.items():
        producers = [n.name for n in nodes if store in n.outputs]
        assert producers == [expected_writer], (store, producers)


def test_stores_are_consumed_read_only_never_a_non_refresh_output():
    """No node other than the store's own refresh asset may output it — so every
    consumer (G / G', scan-project offline) references it as an INPUT only."""
    nodes = _all_nodes()
    for store, expected_writer in _STORE_TO_REFRESH_ASSET.items():
        offenders = [n.name for n in nodes if store in n.outputs and n.name != expected_writer]
        assert not offenders, (store, offenders)


def test_vdb_store_feeds_g_and_gprime_as_inputs():
    """The vdb store is consumed by the Phase G / G' nodes (summarize_vdb_vulns /
    per_version_vulns) as inputs — the refresh -> consume edge, unchanged in behavior."""
    vuln = vuln_create()
    consumers = {n.name for n in vuln.nodes if "vulnerability_vdb_store" in n.inputs}
    assert {"summarize_vdb_vulns", "per_version_vulns"} <= consumers
    # and the refresh asset does NOT read the store (it writes it).
    refresh = next(n for n in vuln.nodes if n.name == "refresh_vdb_store")
    assert "vulnerability_vdb_store" not in refresh.inputs
