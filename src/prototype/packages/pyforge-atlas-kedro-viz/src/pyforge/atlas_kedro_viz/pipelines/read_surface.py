"""Read surface — BSL semantic layer + Vizro dashboard + kedro-mcp tools.

Spec § 5.5-5.6 + § 6: the 24 legacy read CLIs become BSL measures consumed by
Vizro pages and MCP tools (FR-8 / FR-9 / FR-7).
"""

from kedro.pipeline import Pipeline, node, pipeline

from pyforge.atlas_kedro_viz.nodes import stub


def create_pipeline() -> Pipeline:
    return pipeline(
        [
            node(stub("build_bsl_semantic_model"),
                 ["v_packages_enriched", "v_actionable_packages",
                  "v_pypi_intelligence_valid", "v_current_version_vulns",
                  "dependency_graph"],
                 "bsl_semantic_model",
                 name="build_bsl_semantic_model"),
            node(stub("serve_vizro_dashboard"), "bsl_semantic_model",
                 "vizro_dashboard",
                 name="serve_vizro_dashboard"),
            node(stub("expose_kedro_mcp_tools"),
                 ["bsl_semantic_model", "readiness_scores"], "kedro_mcp_tools",
                 name="expose_kedro_mcp_tools"),
        ],
        tags=["read_surface"],
    )
