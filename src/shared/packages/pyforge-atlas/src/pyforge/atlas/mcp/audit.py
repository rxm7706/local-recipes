"""The 23-atlas-tool audit as PURE DATA (Story B3, Task 3 / AC-4, AD-7).

Maps each of the 23 atlas-relevant legacy MCP tools (reference:
``.claude/skills/cf-atlas-legacy/active/cf-atlas-legacy/references/mcp-tools.md``
+ the live, READ-ONLY ``.claude/tools/conda_forge_server.py``) to its B3
re-exposure verdict. The legacy tools each COMPUTE a metric/health-card
from cf_atlas.db; under AD-7 the migrated surface must not re-host that
logic in a tool body, so the re-exposure is structural, not a 23-function
re-port. Verdict vocabulary:

- ``"read_dataset:<catalog-name>"`` — the migrated data the tool read is a
  declared catalog dataset; the generic ``read_dataset`` surface serves it
  (the load is still a passthrough, wrapped since Story I4 in an AD-17
  build-provenance envelope under ``value``).
- ``"pipeline-trigger"`` — served by the NEW B3 capability (the
  ``run_<pipeline>_pipeline`` triggers): refresh the data, then read it.
- ``"deferred-to-BSL(D1)"`` — metric/composite/free-SELECT semantics that
  are not yet a plain dataset. RECORDED here, NOT re-implemented; the
  logic lands in nodes/views (legacy CLIs/views until D1, BSL after).

This module carries NO metric logic — it is a frozen dict plus trivial
helpers, so the audit is queryable + tested (test_audit_mapping) without
any business logic entering the package.
"""

from __future__ import annotations

ATLAS_TOOL_AUDIT: dict[str, str] = {
    # -- plain dataset reads (served by read_dataset today) --
    "staleness_report": "read_dataset:core_feedstock_health",
    "feedstock_health": "read_dataset:core_feedstock_health",
    "version_downloads": "read_dataset:core_version_download_history",
    "platform_breakdown": "read_dataset:core_downloads_platform_breakdown",
    "pyver_breakdown": "read_dataset:core_downloads_pyver_breakdown",
    "channel_split": "read_dataset:core_downloads_channel_breakdown",
    "whodepends": "read_dataset:core_dependencies",
    "behind_upstream": "read_dataset:vcs_upstream_versions",
    "cve_watcher": "read_dataset:vulnerability_package_version_vulns",
    "pypi_intelligence": "read_dataset:pypi_intelligence_scored",
    "pypi_only_candidates": "read_dataset:pypi_universe",
    # -- composite / free-SELECT / user-input surfaces: recorded, deferred --
    "release_cadence": "deferred-to-BSL(D1)",
    "adoption_stage": "deferred-to-BSL(D1)",
    "find_alternative": "deferred-to-BSL(D1)",
    "export_purls": "deferred-to-BSL(D1)",
    "universe_sbom": "deferred-to-BSL(D1)",
    "inventory_match": "deferred-to-BSL(D1)",
    "recommend_2027": "deferred-to-BSL(D1)",
    "package_health": "deferred-to-BSL(D1)",
    "query_atlas": "deferred-to-BSL(D1)",
    "my_feedstocks": "deferred-to-BSL(D1)",
    "env_inspect": "deferred-to-BSL(D1)",
    "scan_project": "deferred-to-BSL(D1)",
}

# Spec § 5.5 / § 9 AC-4: these stay CLI-only — NO MCP tool wraps them in
# the new surface (the legacy 23-tool reference already excludes them).
CLI_ONLY_TOOLS = (
    "library-futures",
    "add-handoff",
    "cwe-seed-gap",
    "spdx-schema-gap",
    "license-map-gap",
    "lts-registry-gap",
)

# The NEW capability B3 adds (no legacy equivalent): named-pipeline
# triggers riding the one Kedro execution plane (AD-23).
PIPELINE_TRIGGER_TOOLS = (
    "run_core_pipeline",
    "run_vcs_health_pipeline",
    "run_pypi_intelligence_pipeline",
    "run_vulnerability_pipeline",
    "run_seed_gaps_pipeline",
    "run_universal_sbom_pipeline",  # B7: SBOM intake -> match pipeline trigger
    "run_derived_artifacts_pipeline",  # B7: universe-BOM pipeline trigger
)

# The NL capability D3 adds (no legacy equivalent): the Vizro-AI natural-language interface
# over the BSL knowledge graph (FR-9). Its LLM backend routes through repo model-backend
# config (Q3 §11) and the live NL->chart call is the attended Q3 event (DW-D3); the tool body
# stays AD-7-thin, delegating to the pyforge.atlas.nl seam.
NL_INTERFACE_TOOLS = ("query_vizro_ai",)


def read_dataset_targets() -> set[str]:
    """The catalog dataset names referenced by ``read_dataset:`` verdicts."""
    prefix = "read_dataset:"
    return {
        verdict[len(prefix):]
        for verdict in ATLAS_TOOL_AUDIT.values()
        if verdict.startswith(prefix)
    }


def deferred_tools() -> set[str]:
    """The legacy tools recorded as deferred-to-BSL(D1)."""
    return {
        tool
        for tool, verdict in ATLAS_TOOL_AUDIT.items()
        if verdict == "deferred-to-BSL(D1)"
    }
