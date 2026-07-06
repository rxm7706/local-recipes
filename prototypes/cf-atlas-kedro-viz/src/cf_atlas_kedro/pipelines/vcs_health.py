"""VCS & Health pipeline — GitHub/GitLab live queries + upstream tracking.

Spec § 5.2 pipeline 4; Story B1 phases E.5, K, L, N.
"""

from kedro.pipeline import Pipeline, node, pipeline

from cf_atlas_kedro.nodes import stub


def create_pipeline() -> Pipeline:
    return pipeline(
        [
            node(stub("extract_github_graphql"), None, "raw_github_graphql",
                 name="extract_github_graphql", tags=["credentialed"]),
            node(stub("extract_forge_apis"), None, "raw_forge_apis",
                 name="extract_forge_apis"),
            node(stub("extract_extra_registries"), None, "raw_extra_registries",
                 name="extract_extra_registries"),
            node(stub("phase_e5_archived_feedstocks"),
                 ["raw_github_graphql", "packages"], "archived_feedstocks",
                 name="phase_e5_archived_feedstocks", tags=["credentialed"]),
            node(stub("phase_k_vcs_versions"),
                 ["raw_github_graphql", "raw_forge_apis", "cf_graph_enrichment"],
                 "vcs_versions",
                 name="phase_k_vcs_versions", tags=["ttl-gated", "credentialed"]),
            node(stub("phase_l_extra_registries"),
                 ["raw_extra_registries", "cf_graph_enrichment"], "registry_versions",
                 name="phase_l_extra_registries", tags=["ttl-gated"]),
            node(stub("phase_n_github_live"),
                 ["raw_github_graphql", "feedstock_health"], "github_live",
                 name="phase_n_github_live", tags=["credentialed"]),
        ],
        tags=["vcs_health"],
    )
