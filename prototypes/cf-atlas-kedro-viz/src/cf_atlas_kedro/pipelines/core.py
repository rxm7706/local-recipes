"""Core pipeline — foundational conda-forge enumeration + graph building.

Spec § 5.2 pipeline 1; Story B1 phases B, B.5, B.6, E, F, J, M.
Sources per reference/atlas-phases-overview.md At-a-glance index.
"""

from kedro.pipeline import Pipeline, node, pipeline

from cf_atlas_kedro.nodes import stub


def create_pipeline() -> Pipeline:
    return pipeline(
        [
            # Raw API extractions (zero-input so `kedro run` executes end-to-end)
            node(stub("extract_conda_repodata"), None, "raw_conda_repodata",
                 name="extract_conda_repodata"),
            node(stub("extract_feedstock_outputs"), None, "raw_feedstock_outputs",
                 name="extract_feedstock_outputs"),
            node(stub("extract_cf_graph"), None, "raw_cf_graph",
                 name="extract_cf_graph"),
            node(stub("extract_anaconda_downloads"), None, "raw_anaconda_downloads",
                 name="extract_anaconda_downloads"),
            # Phases
            node(stub("phase_b_conda_enumeration"), "raw_conda_repodata", "packages",
                 name="phase_b_conda_enumeration"),
            node(stub("phase_b5_feedstock_outputs"),
                 ["raw_feedstock_outputs", "packages"], "feedstock_outputs_map",
                 name="phase_b5_feedstock_outputs"),
            node(stub("phase_b6_yanked_detection"),
                 ["packages", "feedstock_outputs_map"], "package_status",
                 name="phase_b6_yanked_detection"),
            node(stub("phase_e_cf_graph_enrichment"),
                 ["raw_cf_graph", "packages"], "cf_graph_enrichment",
                 name="phase_e_cf_graph_enrichment"),
            node(stub("phase_f_download_counts", n_outputs=2),
                 ["raw_anaconda_downloads", "packages"],
                 ["download_counts", "package_version_downloads"],
                 name="phase_f_download_counts", tags=["ttl-gated"]),
            node(stub("phase_j_dependency_graph"),
                 ["raw_cf_graph", "cf_graph_enrichment"], "dependency_graph",
                 name="phase_j_dependency_graph"),
            node(stub("phase_m_feedstock_health"),
                 ["raw_cf_graph", "packages"], "feedstock_health",
                 name="phase_m_feedstock_health"),
            # Views (materialized query surface)
            node(stub("build_enriched_views", n_outputs=2),
                 ["packages", "cf_graph_enrichment", "download_counts", "package_status"],
                 ["v_packages_enriched", "v_actionable_packages"],
                 name="build_enriched_views"),
        ],
        namespace=None,
        tags=["core"],
    )
