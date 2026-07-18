"""AC-4 — the 23-atlas-tool audit mapping is complete, honest, and pinned.

- keys == exactly the 23 atlas-relevant legacy tools;
- every ``read_dataset:<name>`` target is a DECLARED catalog dataset
  (conf/base/catalog.yml keys are the source of truth);
- ``library-futures`` / ``add-handoff`` / the 4 seed-gap suggesters stay
  CLI-only and never appear in the audit;
- the 4 pipeline-trigger tools match ``tools.PIPELINE_NAMES``, and that
  static mirror matches the REAL registry (the 4 create_pipeline modules).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import yaml

from pyforge.atlas.mcp import audit, tools

MEMBER_DIR = Path(__file__).resolve().parents[2]
CATALOG_YML = MEMBER_DIR / "conf" / "base" / "catalog.yml"

# The 23 atlas-relevant legacy tools (reference: cf-atlas-legacy
# references/mcp-tools.md + the read-only conda_forge_server.py).
THE_23 = {
    "staleness_report",
    "platform_breakdown",
    "pyver_breakdown",
    "channel_split",
    "feedstock_health",
    "whodepends",
    "behind_upstream",
    "cve_watcher",
    "version_downloads",
    "release_cadence",
    "find_alternative",
    "adoption_stage",
    "pypi_only_candidates",
    "export_purls",
    "universe_sbom",
    "inventory_match",
    "recommend_2027",
    "pypi_intelligence",
    "package_health",
    "query_atlas",
    "my_feedstocks",
    "env_inspect",
    "scan_project",
}

VALID_VERDICT_PREFIXES = ("read_dataset:", "pipeline-trigger", "deferred-to-BSL(D1)")


def _declared_catalog_names() -> set[str]:
    return set(yaml.safe_load(CATALOG_YML.read_text(encoding="utf-8")))


def test_audit_covers_exactly_the_23_atlas_tools():
    assert len(THE_23) == 23
    assert set(audit.ATLAS_TOOL_AUDIT) == THE_23


def test_every_verdict_uses_the_declared_vocabulary():
    for tool, verdict in audit.ATLAS_TOOL_AUDIT.items():
        assert verdict.startswith(VALID_VERDICT_PREFIXES), (
            f"{tool}: unknown verdict {verdict!r}"
        )


def test_every_read_dataset_target_is_a_declared_catalog_dataset():
    declared = _declared_catalog_names()
    targets = audit.read_dataset_targets()
    assert targets, "audit must serve at least some tools via read_dataset"
    missing = targets - declared
    assert not missing, (
        f"read_dataset verdicts point at undeclared catalog datasets: {missing}"
    )


def test_cli_only_tools_stay_cli_only():
    assert "library-futures" in audit.CLI_ONLY_TOOLS
    assert "add-handoff" in audit.CLI_ONLY_TOOLS
    for suggester in (
        "cwe-seed-gap",
        "spdx-schema-gap",
        "license-map-gap",
        "lts-registry-gap",
    ):
        assert suggester in audit.CLI_ONLY_TOOLS
    assert len(audit.CLI_ONLY_TOOLS) == 6
    # none of them is (re-)exposed via the audit / the new MCP surface
    assert not set(audit.CLI_ONLY_TOOLS) & set(audit.ATLAS_TOOL_AUDIT)
    normalized = {name.replace("-", "_") for name in audit.CLI_ONLY_TOOLS}
    assert not normalized & set(audit.ATLAS_TOOL_AUDIT)


def test_pipeline_trigger_tools_match_the_registered_pipelines():
    assert audit.PIPELINE_TRIGGER_TOOLS == (
        "run_core_pipeline",
        "run_vcs_health_pipeline",
        "run_pypi_intelligence_pipeline",
        "run_vulnerability_pipeline",
        "run_seed_gaps_pipeline",  # B6: the seed_gaps pipeline trigger
        "run_universal_sbom_pipeline",  # B7: the universal_sbom pipeline trigger
        "run_derived_artifacts_pipeline",  # B7: the derived_artifacts pipeline trigger
    )
    stems = tuple(
        name.removeprefix("run_").removesuffix("_pipeline")
        for name in audit.PIPELINE_TRIGGER_TOOLS
    )
    assert stems == tools.PIPELINE_NAMES


def test_pipeline_names_mirror_the_real_registry():
    """Pins the static PIPELINE_NAMES mirror (list_pipelines' source)
    against the real find_pipelines() discovery surface: the pipelines/
    subpackages that expose create_pipeline()."""
    for name in tools.PIPELINE_NAMES:
        mod = importlib.import_module(f"pyforge.atlas.pipelines.{name}.pipeline")
        assert callable(mod.create_pipeline), name

    pipelines_dir = (
        MEMBER_DIR / "src" / "pyforge" / "atlas" / "pipelines"
    )
    discovered = {
        p.parent.name for p in pipelines_dir.glob("*/pipeline.py")
    }
    assert discovered == set(tools.PIPELINE_NAMES)
