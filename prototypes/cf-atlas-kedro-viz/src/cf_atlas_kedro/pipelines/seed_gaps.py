"""Seed-gap suggesters — read-only 'seed freshness' report nodes.

Spec § 3.4 (seed-freshness report nodes): every curated seed / in-code map has
a read-only `*-gap` suggester that diffs the seed against live ground truth and
PROPOSES additions for git review — the maintenance loop that keeps a hand-owned
input from silently drifting. Modeled here as terminal report nodes fanned out
from the external seed datasets: report-only (they never mutate the atlas —
unlike `mapping-gap`'s g10_spelling writeback), downstream of the atlas rebuild
(they read its views), on the `export-purls` / `universe-sbom` regen cadence.

Suggesters: lts-registry-gap (v8.74.0), cwe-seed-gap + spdx-schema-gap
(v8.75.0), license-map-gap (v8.76.0).
"""

from kedro.pipeline import Pipeline, node, pipeline

from cf_atlas_kedro.nodes import stub


def create_pipeline() -> Pipeline:
    return pipeline(
        [
            # Curated external seed inputs (read-only; the pipeline never writes
            # them — git review owns them). lts_registry + raw_endoflife_eol are
            # already produced in the universal_sbom pipeline and reused here.
            node(stub("extract_cwe_categories_seed"), None, "cwe_categories_seed",
                 name="extract_cwe_categories_seed"),
            node(stub("extract_spdx_schema"), None, "spdx_schema",
                 name="extract_spdx_schema"),
            node(stub("extract_license_to_spdx_map"), None, "license_to_spdx_map",
                 name="extract_license_to_spdx_map"),
            # Terminal report nodes — derived-layer artifacts, no writeback.
            node(stub("lts_registry_gap"),
                 ["raw_endoflife_eol", "lts_registry", "v_actionable_packages"],
                 "lts_registry_gap_report", name="lts_registry_gap"),
            node(stub("cwe_seed_gap"),
                 ["cwe_categories", "cwe_categories_seed"],
                 "cwe_seed_gap_report", name="cwe_seed_gap"),
            node(stub("spdx_schema_gap"),
                 ["spdx_schema", "v_actionable_packages"],
                 "spdx_schema_gap_report", name="spdx_schema_gap"),
            node(stub("license_map_gap"),
                 ["license_to_spdx_map", "v_pypi_intelligence_valid"],
                 "license_map_gap_report", name="license_map_gap"),
        ],
        tags=["seed_gaps"],
    )
