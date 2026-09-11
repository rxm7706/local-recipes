"""FR-155 MCP tool inventory for ``conda_forge_server.py`` (Story 16.3).

One entry per ``@mcp.tool`` on the CFE MCP server. ``cli`` is the pixi task
name (``pixi run -e local-recipes <cli> …``); ``None`` marks a deliberate
tool-only surface with no CLI counterpart.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CFE_SERVER = _REPO_ROOT / ".claude" / "tools" / "conda_forge_server.py"

TOOL_SPECS: dict[str, dict[str, Any]] = {
    "validate_recipe": {
        "description": "Validate a conda-forge recipe against best practices.",
        "cli": ["validate"],
    },
    "check_dependencies": {
        "description": "Check recipe dependencies resolve on conda-forge.",
        "cli": ["check-deps"],
    },
    "generate_recipe_from_pypi": {
        "description": "Generate a recipe from PyPI via grayskull + post-processors.",
        "cli": ["generate-recipe"],
    },
    "run_system_health_check": {
        "description": "Comprehensive local development environment health check.",
        "cli": ["health-check"],
    },
    "update_cve_database": {
        "description": "Download/update the local OSV CVE database.",
        "cli": ["update-cve-db"],
    },
    "scan_for_vulnerabilities": {
        "description": "Scan recipe dependencies for known vulnerabilities.",
        "cli": ["scan-vulnerabilities"],
    },
    "trigger_build": {
        "description": "Trigger a native or Docker local recipe build asynchronously.",
        "cli": ["recipe-build"],
    },
    "get_build_summary": {
        "description": "Read the last build summary or in-flight build PID state.",
        "cli": None,
    },
    "lookup_feedstock": {
        "description": "Look up an existing conda-forge feedstock recipe.",
        "cli": None,
    },
    "enrich_from_feedstock": {
        "description": "Merge feedstock metadata into a freshly generated recipe.",
        "cli": None,
    },
    "get_feedstock_context": {
        "description": "Fetch open/recent feedstock GitHub issues as planning context.",
        "cli": None,
    },
    "edit_recipe": {
        "description": "Apply structured edit actions to a recipe file.",
        "cli": None,
    },
    "update_mapping_cache": {
        "description": "Refresh the PyPI-to-conda name mapping cache.",
        "cli": ["update-mapping-cache"],
    },
    "get_conda_name": {
        "description": "Resolve a PyPI package name to its conda-forge equivalent.",
        "cli": ["resolve-name"],
    },
    "analyze_build_failure": {
        "description": "Analyze a build log against known failure patterns.",
        "cli": ["analyze-failure"],
    },
    "optimize_recipe": {
        "description": "Lint a recipe for conda-forge optimizations.",
        "cli": ["lint-optimize"],
    },
    "update_recipe": {
        "description": "Autotick a recipe to the latest PyPI version.",
        "cli": ["autotick"],
    },
    "prepare_submission_branch": {
        "description": "Stage a recipe branch on the staged-recipes fork without opening a PR.",
        "cli": ["prepare-pr"],
    },
    "submit_pr": {
        "description": "Submit a recipe PR to conda-forge/staged-recipes.",
        "cli": ["submit-pr"],
    },
    "update_recipe_from_github": {
        "description": "Autotick a GitHub-sourced recipe to the latest release.",
        "cli": ["autotick-github"],
    },
    "check_github_version": {
        "description": "Check the latest GitHub release for a recipe or repo.",
        "cli": ["version-check"],
    },
    "migrate_to_v1": {
        "description": "Convert meta.yaml to recipe.yaml via feedrattler.",
        "cli": ["migrate"],
    },
    "staleness_report": {
        "description": "List feedstocks ordered by oldest conda upload.",
        "cli": ["staleness-report"],
    },
    "platform_breakdown": {
        "description": "Per-platform download breakdown from cf_atlas.",
        "cli": ["platform-breakdown"],
    },
    "pyver_breakdown": {
        "description": "Per-Python download breakdown and python_min policy check.",
        "cli": ["pyver-breakdown"],
    },
    "channel_split": {
        "description": "Per-channel download breakdown from cf_atlas.",
        "cli": ["channel-split"],
    },
    "download_pr_artifacts": {
        "description": "Download CI-published .conda artifacts from a feedstock PR.",
        "cli": ["pr-artifacts"],
    },
    "feedstock_health": {
        "description": "Surface feedstocks with bot/CI/GitHub health issues.",
        "cli": ["feedstock-health"],
    },
    "whodepends": {
        "description": "cf_atlas dependency graph forward/reverse query.",
        "cli": ["whodepends"],
    },
    "behind_upstream": {
        "description": "List feedstocks behind their upstream-of-record version.",
        "cli": ["behind-upstream"],
    },
    "cve_watcher": {
        "description": "Diff cf_atlas vuln_history snapshots over time.",
        "cli": ["cve-watcher"],
    },
    "version_downloads": {
        "description": "Per-version download breakdown for one package.",
        "cli": ["version-downloads"],
    },
    "release_cadence": {
        "description": "Release cadence trend classifier from cf_atlas Phase I.",
        "cli": ["release-cadence"],
    },
    "find_alternative": {
        "description": "Suggest healthier alternatives for archived packages.",
        "cli": ["find-alternative"],
    },
    "adoption_stage": {
        "description": "Lifecycle stage classifier for packages or maintainers.",
        "cli": ["adoption-stage"],
    },
    "pypi_only_candidates": {
        "description": "List PyPI projects with no conda-forge equivalent.",
        "cli": ["pypi-only-candidates"],
    },
    "export_purls": {
        "description": "Export purl + mapping artifacts from cf_atlas.db.",
        "cli": ["export-purls"],
    },
    "universe_sbom": {
        "description": "Emit the full conda-forge + PyPI universe as an SBOM.",
        "cli": ["universe-sbom"],
    },
    "inventory_match": {
        "description": "Match a user inventory against cf_atlas.db.",
        "cli": ["inventory-match"],
    },
    "recommend_2027": {
        "description": "2027–2030 window scorecard for a user inventory.",
        "cli": ["recommend-2027"],
    },
    "pypi_intelligence": {
        "description": "Surface enriched PyPI candidates from cf_atlas.",
        "cli": ["pypi-intelligence"],
    },
    "package_health": {
        "description": "Full health card for one package via detail_cf_atlas.",
        "cli": ["detail-cf-atlas"],
    },
    "query_atlas": {
        "description": "Ad-hoc read-only SQL against cf_atlas packages table.",
        "cli": None,
    },
    "my_feedstocks": {
        "description": "Per-maintainer feedstock portfolio and triage view.",
        "cli": ["my-feedstocks"],
    },
    "env_inspect": {
        "description": "Inspect a pixi/conda environment from multiple angles.",
        "cli": ["env-inspect"],
    },
    "scan_project": {
        "description": "Vulnerability/license/atlas scan of a project or container input.",
        "cli": ["scan-project"],
    },
}


def registered_mcp_tools(server_path: Path | None = None) -> frozenset[str]:
    """Return ``@mcp.tool`` function names registered on the live CFE server."""
    path = _CFE_SERVER if server_path is None else server_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            is_tool = (
                isinstance(dec, ast.Attribute)
                and dec.attr == "tool"
                and isinstance(dec.value, ast.Name)
                and dec.value.id == "mcp"
            ) or (
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "tool"
            )
            if is_tool:
                names.add(node.name)
    return frozenset(names)


def assert_tool_specs_covers_server(
    tool_specs: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    server_path: Path | None = None,
) -> None:
    """Raise when ``TOOL_SPECS`` drifts from live ``@mcp.tool`` registrations."""
    specs = TOOL_SPECS if tool_specs is None else tool_specs
    registered = registered_mcp_tools(server_path)
    spec_names = frozenset(specs)
    missing = registered - spec_names
    extra = spec_names - registered
    problems: list[str] = []
    if missing:
        problems.append(f"registered tools missing from TOOL_SPECS: {sorted(missing)}")
    if extra:
        problems.append(f"TOOL_SPECS entries with no @mcp.tool: {sorted(extra)}")
    if problems:
        raise AssertionError("; ".join(problems))
