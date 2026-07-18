"""Pipeline shape + boundary invariants (Story B6, AC-1 / AC-3 / AC-4).

- AC-1: the four outputs are the pre-declared ``seed_gaps_*_report`` datasets.
- AC-3: every report catalog entry carries ``metadata.layer: derived`` and
  every pipeline input is a curated seed OR a rebuild-produced dataset (no
  external mutable state), so the runner re-materializes the reports after every
  rebuild alongside the other derived artifacts.
- AC-4: the node-name set is EXACTLY the four read-only suggesters — ``mapping-gap``
  / ``g10_spelling`` writeback machinery is absent — and the ``pypi_intelligence``
  mapping stage's ``g10_spelling`` no-clobber surface (``_PROTECTED_MATCH_SOURCES``)
  is untouched by B6.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from pyforge.atlas.pipelines.seed_gaps import create_pipeline

_MEMBER_DIR = Path(__file__).resolve().parents[3]
_CATALOG_YML = _MEMBER_DIR / "conf" / "base" / "catalog.yml"

_EXPECTED_NODES = {
    "report_lts_registry_gap",
    "report_cwe_seed_gap",
    "report_spdx_schema_gap",
    "report_license_map_gap",
}
_EXPECTED_REPORTS = {
    "seed_gaps_lts_registry_report",
    "seed_gaps_cwe_report",
    "seed_gaps_spdx_report",
    "seed_gaps_license_map_report",
}
_SEED_INPUTS = {
    "seed_lts_registry",
    "seed_cwe_categories",
    "seed_spdx_schema",
    "seed_spdx_upstream_list_raw",
}
# Rebuild-produced (cross-pipeline, AD-3) inputs the suggesters diff against.
_REBUILD_INPUTS = {
    "pypi_endoflife_raw",
    "core_packages_enumerated",
    "pypi_conda_mapping",
    "vulnerability_cwe_categories",
    "pypi_intelligence_enriched",
}


def test_node_names_are_exactly_the_four_suggesters_no_mapping_gap():
    pipeline = create_pipeline()
    names = {n.name for n in pipeline.nodes}
    assert names == _EXPECTED_NODES  # AC-4: exact set
    assert "mapping-gap" not in names
    assert "mapping_gap" not in names
    assert not any("g10" in n for n in names)  # no g10_spelling writeback node


def test_outputs_are_the_seed_gaps_report_datasets():
    pipeline = create_pipeline()
    assert pipeline.outputs() == _EXPECTED_REPORTS  # AC-1


def test_inputs_are_only_seeds_or_rebuild_produced():
    """AC-3: no external mutable state — every input is a curated seed dataset
    or a rebuild-produced (cross-pipeline) dataset."""
    pipeline = create_pipeline()
    assert pipeline.inputs() <= (_SEED_INPUTS | _REBUILD_INPUTS)


def test_report_catalog_entries_carry_derived_layer():
    """AC-3: the four reports are ``metadata.layer: derived`` — the runner
    re-materializes them per rebuild alongside the other derived artifacts."""
    catalog = yaml.safe_load(_CATALOG_YML.read_text(encoding="utf-8"))
    for name in _EXPECTED_REPORTS:
        assert name in catalog, name
        assert catalog[name]["metadata"]["layer"] == "derived", name


def test_g10_spelling_no_clobber_surface_untouched_in_pypi_intelligence():
    """AC-4: B6 leaves the ``mapping-gap`` no-clobber surface intact — the
    ``_PROTECTED_MATCH_SOURCES`` tuple in pypi_intelligence still carries
    ``g10_spelling`` (its writeback lives in pipeline 2, never in seed_gaps)."""
    from pyforge.atlas.pipelines.pypi_intelligence import nodes as pypi_nodes

    assert "g10_spelling" in pypi_nodes._PROTECTED_MATCH_SOURCES
