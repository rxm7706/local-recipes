"""Universal SBOM pipeline — CycloneDX suite as downstream nodes of the rebuild.

Spec § 5.2 pipeline 5 + the derived-artifact regeneration cadence rule
(export-purls / universe-sbom re-run after every atlas rebuild).
"""

from kedro.pipeline import Pipeline, node, pipeline

from cf_atlas_kedro.nodes import stub


def create_pipeline() -> Pipeline:
    return pipeline(
        [
            node(stub("extract_project_manifest"), None, "raw_project_manifest",
                 name="extract_project_manifest"),
            node(stub("extract_endoflife_eol"), None, "raw_endoflife_eol",
                 name="extract_endoflife_eol"),
            node(stub("extract_lts_registry"), None, "lts_registry",
                 name="extract_lts_registry"),
            node(stub("export_purls"),
                 ["packages", "pypi_mapping_extended"], "purl_export",
                 name="export_purls"),
            node(stub("universe_sbom"),
                 ["pypi_universe", "packages", "purl_export"], "universe_sbom_bom",
                 name="universe_sbom"),
            node(stub("inventory_match"),
                 ["raw_project_manifest", "universe_sbom_bom",
                  "v_pypi_intelligence_valid", "v_current_version_vulns"],
                 "inventory_report",
                 name="inventory_match"),
            node(stub("library_futures"),
                 ["inventory_report", "v_pypi_intelligence_valid",
                  "v_current_version_vulns", "raw_endoflife_eol", "lts_registry"],
                 "futures_scores",
                 name="library_futures"),
            node(stub("recommend_2027"),
                 ["futures_scores", "inventory_report"], "recommend_2027_bom",
                 name="recommend_2027"),
        ],
        tags=["universal_sbom"],
    )
