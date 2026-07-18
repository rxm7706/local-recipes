"""PyPI Intelligence pipeline — mapping, skew detection, and scoring.

Spec § 5.2 pipeline 2; Story B2 phases C, C.5, D, H, O-S plus the
`add-handoff` single-write-path (shared `phase_r_upsert_one` /
`apply_readiness_scores` helpers — spec § 3.3 write paths).
"""

from kedro.pipeline import Pipeline, node, pipeline

from pyforge.atlas_kedro_viz.nodes import stub


def create_pipeline() -> Pipeline:
    return pipeline(
        [
            node(stub("extract_parselmouth_map"), None, "raw_parselmouth_map",
                 name="extract_parselmouth_map"),
            node(stub("extract_pypi_simple_index"), None, "raw_pypi_simple_index",
                 name="extract_pypi_simple_index"),
            node(stub("extract_pypi_project_json"), None, "raw_pypi_project_json",
                 name="extract_pypi_project_json"),
            node(stub("extract_bigquery_downloads"), None, "raw_bigquery_downloads",
                 name="extract_bigquery_downloads", tags=["credentialed"]),
            node(stub("extract_cross_channel_repodata"), None,
                 "raw_cross_channel_repodata",
                 name="extract_cross_channel_repodata"),
            node(stub("intake_handoff_request"), None, "handoff_request",
                 name="intake_handoff_request"),
            # Mapping (Phases C / C.5)
            node(stub("phase_c_parselmouth_join"),
                 ["raw_parselmouth_map", "packages"], "pypi_mapping",
                 name="phase_c_parselmouth_join"),
            node(stub("phase_c5_source_url_match"),
                 ["cf_graph_enrichment", "pypi_mapping"], "pypi_mapping_extended",
                 name="phase_c5_source_url_match"),
            # Universe + skew (Phases D / H)
            node(stub("phase_d_pypi_enumeration"),
                 ["raw_pypi_simple_index", "pypi_mapping_extended"], "pypi_universe",
                 name="phase_d_pypi_enumeration"),
            node(stub("phase_h_skew_detection"),
                 ["raw_pypi_project_json", "pypi_mapping_extended"],
                 "pypi_current_versions",
                 name="phase_h_skew_detection", tags=["ttl-gated"]),
            # Scoring chain (Phases O -> P -> Q -> R -> S)
            node(stub("phase_o_serial_snapshots"), "pypi_universe",
                 "activity_snapshots", name="phase_o_serial_snapshots"),
            node(stub("phase_p_pypi_downloads"),
                 ["raw_bigquery_downloads", "pypi_universe"], "pypi_downloads",
                 name="phase_p_pypi_downloads", tags=["credentialed"]),
            node(stub("phase_q_cross_channel"),
                 ["raw_cross_channel_repodata", "pypi_universe"],
                 "cross_channel_presence",
                 name="phase_q_cross_channel"),
            node(stub("phase_r_pypi_json_enrich"),
                 ["raw_pypi_project_json", "pypi_universe", "activity_snapshots",
                  "pypi_downloads", "cross_channel_presence"],
                 "pypi_intelligence",
                 name="phase_r_pypi_json_enrich"),
            node(stub("add_handoff_upsert"),
                 ["handoff_request", "pypi_universe"], "handoff_rows",
                 name="add_handoff_upsert"),
            node(stub("phase_s_computed_scores"),
                 ["pypi_intelligence", "handoff_rows"], "readiness_scores",
                 name="phase_s_computed_scores"),
            # Views
            node(stub("build_pypi_views", n_outputs=2),
                 ["pypi_intelligence", "readiness_scores"],
                 ["v_pypi_intelligence_valid", "v_pypi_candidates"],
                 name="build_pypi_views"),
        ],
        tags=["pypi_intelligence"],
    )
