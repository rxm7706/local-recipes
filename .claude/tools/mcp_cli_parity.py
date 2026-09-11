#!/usr/bin/env python3
"""CLI <-> MCP-tool parity derivation for the conda-forge-expert (CFE) server.

Story 16.3: extends marshal's ``pyforge.marshal.mcp.parity`` generic gate
engine (``assert_cli_tool_parity`` / ``parity_findings``) over Mason's 46
``@mcp.tool()`` registrations in ``conda_forge_server.py``, rather than
forking a second independent copy of the gate — the CFE skill records that a
second independent copy of a gate is exactly how the ``_http.py`` credential
leak survived a "durable fix."

Marshal's own ``TOOL_SPECS`` declares each tool's CLI argv template by hand
(``{"cli": ["status", "--format", "json"]}``); the CFE server has no such
declared mapping, so this module DERIVES both surfaces instead of hand
listing them:

* **CLI surface** — every pixi task, across every ``[feature.*.tasks.*]``
  table (not just ``local-recipes``: ``[feature.vuln-db.tasks.*]`` also
  invokes ``.claude/scripts/conda-forge-expert/`` wrappers, e.g.
  ``scan-project`` -> ``scan_project.py``, the identical script the
  ``scan_project`` MCP tool references), whose ``cmd`` invokes a script
  under ``.claude/scripts/conda-forge-expert/``. The CLI **verb** is the
  pixi **task name** (what a person or agent actually types after
  ``pixi run -e <env>``), never the wrapper file's stem — a wrapper can be
  renamed, added, or removed independent of its underlying script, which is
  exactly the drift class this gate exists to close.
* **Tool surface** — every ``@mcp.tool()``-decorated function in
  ``conda_forge_server.py``, resolved to a CLI verb by finding which
  ``SCRIPTS_DIR / "<script>.py"`` constant its body references. The server
  module is parsed via ``ast``, never imported/executed, so this carries
  none of the MCP server's own runtime dependencies (``mcp``/FastMCP).

One case static script-reference analysis cannot disambiguate on its own:
``prepare_submission_branch`` and ``submit_pr`` both invoke the identical
canonical ``submit_pr.py`` script (via the ``SUBMIT_PR_SCRIPT`` constant) —
but ``prepare_submission_branch`` passes ``--prepare-only``, which is what
the *separate* ``prepare-pr`` pixi task (a different wrapper file,
delegating to that same canonical script) also does. ``_VERB_OVERRIDE``
records that one hand-verified mapping explicitly.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS_FILE = _REPO_ROOT / ".claude" / "tools" / "conda_forge_server.py"
_PIXI_TOML = _REPO_ROOT / "pixi.toml"

# Extend marshal's primitive rather than forking it — never a mason-local
# independent copy of the gate.
_MARSHAL_SRC = _REPO_ROOT / "src" / "shared" / "packages" / "pyforge-marshal" / "src"
if str(_MARSHAL_SRC) not in sys.path:
    sys.path.insert(0, str(_MARSHAL_SRC))

MARSHAL_IMPORT_ERROR: ImportError | None
try:
    from pyforge.marshal.mcp.parity import (  # noqa: E402
        ParityFinding,
        assert_cli_tool_parity,
        parity_findings,
    )

    MARSHAL_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - partial/monorepo-less checkout
    ParityFinding = None  # type: ignore[assignment,misc]
    assert_cli_tool_parity = None  # type: ignore[assignment]
    parity_findings = None  # type: ignore[assignment]
    MARSHAL_IMPORT_ERROR = exc


# The one case static analysis cannot disambiguate on its own: both
# `submit-pr` and `prepare-pr` pixi tasks delegate to the identical
# canonical `submit_pr.py` script (two different wrapper files, one target).
# `prepare_submission_branch`'s body references the same SUBMIT_PR_SCRIPT
# constant the `submit_pr` tool references, so without this override both
# tools would resolve to `submit-pr` and `prepare-pr` would misread as an
# undeclared CLI-only verb.
_VERB_OVERRIDE: dict[str, str] = {
    "prepare_submission_branch": "prepare-pr",
}

# Deliberate CLI-only verbs: a real pixi task invoking a
# `.claude/scripts/conda-forge-expert/` wrapper with no MCP tool claiming it.
# Every entry carries a one-line reason — never a silent skip; a missing or
# stale entry is itself a parity-gate finding.
CLI_ONLY_VERBS: dict[str, str] = {
    "recipe-build": "trigger_build (tool-only) drives rattler-build directly; native-build.sh has no MCP binding",
    "recipe-build-cross": "trigger_build (tool-only) drives rattler-build directly; cross-build.sh has no MCP binding",
    "build-local": "local_builder.py's Docker-less build path predates trigger_build's native rattler-build integration; no tool wraps it",
    "build-local-all": "local_builder.py --all-platforms; see build-local",
    "build-local-check": "local_builder.py --check; see build-local",
    "build-local-setup-sdk": "local_builder.py --setup-osx-sdk; see build-local",
    "migrate": "feedstock-migrator.py is a separate, older meta.yaml->v1 converter; migrate_to_v1 (tool-only) uses feedrattler instead",
    "generate-recipe": "recipe-generator.py's own PyPI/GitHub/template generator has no MCP tool; generate_recipe_from_pypi (tool-only) shells to grayskull instead",
    "generate-cran": "recipe-generator.py cran; see generate-recipe",
    "generate-cpan": "recipe-generator.py cpan; see generate-recipe",
    "generate-luarocks": "recipe-generator.py luarocks; see generate-recipe",
    "generate-npm": "recipe-generator.py npm; see generate-recipe",
    "query-cf-atlas": "conda_forge_atlas.py's legacy name-lookup query; query_atlas (tool-only) runs validated raw SQL instead",
    "build-cf-atlas": "conda_forge_atlas.py's legacy full-rebuild entrypoint; no MCP tool triggers a full atlas rebuild",
    "stats-cf-atlas": "conda_forge_atlas.py's legacy summary-stats subcommand; no MCP tool wraps it",
    "bootstrap-data": "bootstrap_data.py's full data-refresh orchestrator is an operational rebuild step; no MCP tool wraps it",
    "atlas-phase": "atlas_phase.py runs one cf_atlas phase against the live DB, an operational rebuild step; no MCP tool wraps it",
    "mapping-gap": "mapping_gap.py is an offline read-only suggester; no MCP tool wraps it",
    "library-futures": "library_futures.py's S7 scorer; recommend_2027 (the MCP tool) runs it internally as a step but library-futures has no separate tool binding",
    "add-handoff": "add_handoff.py is an offline read-only suggester; no MCP tool wraps it",
    "gen-yml-reference": "gen_yml_reference.py regenerates doc reference files; no MCP tool wraps it",
    "fetch-cisa-kev": "cisa_kev_fetcher.py is a data refresher; no MCP tool wraps it",
    "fetch-epss": "epss_fetcher.py is a data refresher; no MCP tool wraps it",
    "lts-registry-gap": "lts_registry_gap.py is an offline read-only suggester; no MCP tool wraps it",
    "fetch-cwe-catalog": "cwe_catalog_fetcher.py is a data refresher; no MCP tool wraps it",
    "cwe-seed-gap": "cwe_seed_gap.py is an offline read-only suggester; no MCP tool wraps it",
    "generate-failure-catalog": "failure_catalog_generator.py regenerates a derived doc; no MCP tool wraps it",
    "spdx-schema-gap": "spdx_schema_gap.py is an offline read-only suggester; no MCP tool wraps it",
    "license-map-gap": "license_map_gap.py is an offline read-only suggester; no MCP tool wraps it",
    "license-check": "license-checker.py has no MCP tool; optimize_recipe's ABT-001 check covers license_file presence inline",
    "autotick-npm": "npm_updater.py has no MCP tool; update_recipe/update_recipe_from_github cover PyPI/GitHub autotick only",
    "generate-bmad-suite": "bmad_suite_metapackage.py is bmad-suite metapackage maintenance, unrelated to the per-recipe MCP tool surface",
    "build-bmad-suite": "build_bmad_suite.py is bmad-suite metapackage maintenance, unrelated to the per-recipe MCP tool surface",
    "detail-cf-atlas-vdb": "detail_cf_atlas.py --vdb --vdb-all; package_health (the detail-cf-atlas tool) never passes --vdb-all",
    "inventory-channel": "inventory_channel.py scans a channel/mirror; scan_project (the MCP tool) covers project/image/SBOM inputs only",
}

# Deliberate tool-only names: an MCP tool with no CLI-wrapper pixi task.
TOOL_ONLY_NAMES: dict[str, str] = {
    "generate_recipe_from_pypi": "invokes `pixi run -e grayskull pypi` directly; no pixi task matches this behavior",
    "trigger_build": "drives rattler-build / build-locally.py directly (recipe-build / recipe-build-cross / recipe-build-docker equivalents); no single wrapper script backs it",
    "get_build_summary": "reads the local build_summary.json trigger_build writes; no standalone CLI verb for 'read the last build result'",
    "lookup_feedstock": "feedstock_lookup.py deliberately has no pixi task (MCP-only inventory helper, per test_skill_md_consistency.py's no_task_allowlist)",
    "enrich_from_feedstock": "feedstock_enrich.py deliberately has no pixi task (MCP-only inventory helper, per test_skill_md_consistency.py's no_task_allowlist)",
    "get_feedstock_context": "feedstock_context.py deliberately has no pixi task (MCP-only inventory helper, per test_skill_md_consistency.py's no_task_allowlist)",
    "edit_recipe": "recipe_editor.py deliberately has no pixi task -- JSON action-list args don't fit the task metaphor (pixi.toml comment + test_skill_md_consistency.py's no_task_allowlist)",
    "migrate_to_v1": "uses feedrattler directly; feedstock-migrator.py's separate converter (pixi task `migrate`) has no tool binding",
    "query_atlas": "runs a validated raw SQL query against cf_atlas.db directly; distinct from conda_forge_atlas.py's `query` subcommand (pixi task query-cf-atlas)",
}


def _is_mcp_tool(dec: ast.expr) -> bool:
    """True for a call-form ``@mcp.tool()`` decorator only (not a bare
    ``@mcp.tool`` attribute, and not an unrelated object's ``.tool()``)."""
    return (
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and dec.func.attr == "tool"
        and isinstance(dec.func.value, ast.Name)
        and dec.func.value.id == "mcp"
    )


def _script_stem_constants(tree: ast.Module) -> dict[str, str]:
    """``{CONSTANT_NAME: script_stem}`` for every ``NAME = SCRIPTS_DIR /
    "x.py"``-shaped module-level assignment in ``conda_forge_server.py``."""
    stems: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        if not isinstance(value, ast.BinOp):
            continue
        right = value.right
        if not (isinstance(right, ast.Constant) and isinstance(right.value, str)):
            continue
        if not right.value.endswith((".py", ".sh")):
            continue
        stems[target.id] = right.value.rsplit(".", 1)[0]
    return stems


_WRAPPER_CMD_RE = re.compile(r"\.claude/scripts/conda-forge-expert/([^\s/]+)\.(?:py|sh)")


def _cfe_pixi_tasks() -> dict[str, str]:
    """``{pixi_task_name: wrapper_script_stem}`` for every task, scanned
    across every ``[feature.*.tasks.*]`` table, whose ``cmd`` invokes a
    script under ``.claude/scripts/conda-forge-expert/``. Scanning every
    feature (not just ``local-recipes``) matters: ``vuln-db`` invokes
    wrapper scripts some local-recipes MCP tools also reference."""
    data = tomllib.loads(_PIXI_TOML.read_text())
    tasks: dict[str, str] = {}
    for feature in data.get("feature", {}).values():
        for task_name, task in feature.get("tasks", {}).items():
            cmd = task.get("cmd")
            if not isinstance(cmd, str):
                continue
            match = _WRAPPER_CMD_RE.search(cmd)
            if match:
                tasks[task_name] = match.group(1)
    return tasks


def discover_cli_verbs() -> frozenset[str]:
    """Every pixi task name that invokes a CFE wrapper script — the CLI
    surface a person or agent actually types after ``pixi run -e <env>``."""
    return frozenset(_cfe_pixi_tasks())


def _verb_by_stem(tasks: dict[str, str]) -> dict[str, str]:
    """``stem -> task name`` reverse lookup. When 2+ tasks share a stem
    (e.g. ``local_builder.py``'s four ``build-local*`` tasks), the
    alphabetically-first task name wins; no live tool reference triggers
    this ambiguity today (verified directly against the current tree)."""
    by_stem: dict[str, list[str]] = {}
    for task_name, stem in tasks.items():
        by_stem.setdefault(stem, []).append(task_name)
    return {stem: sorted(names)[0] for stem, names in by_stem.items()}


def build_tool_specs() -> dict[str, dict[str, Any]]:
    """``{tool_name: {"description": ..., "cli": [verb] | None}}`` for every
    ``@mcp.tool()`` registration in ``conda_forge_server.py`` — the same
    shape marshal's ``TOOL_SPECS`` uses, so ``parity_findings`` needs no
    changes to consume it. The server module is parsed via ``ast``, never
    imported, so this needs none of the MCP server's own dependencies."""
    tree = ast.parse(_TOOLS_FILE.read_text(), filename=str(_TOOLS_FILE))
    stem_by_const = _script_stem_constants(tree)
    verb_by_stem = _verb_by_stem(_cfe_pixi_tasks())

    specs: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_mcp_tool(dec) for dec in node.decorator_list):
            continue

        name = node.name
        doc = ast.get_docstring(node) or name
        description = doc.strip().splitlines()[0]

        if name in _VERB_OVERRIDE:
            specs[name] = {"description": description, "cli": [_VERB_OVERRIDE[name]]}
            continue

        referenced_stems = sorted(
            {
                stem_by_const[ref.id]
                for ref in ast.walk(node)
                if isinstance(ref, ast.Name) and ref.id in stem_by_const
            }
        )
        if not referenced_stems:
            specs[name] = {"description": description, "cli": None}
            continue

        verb = verb_by_stem.get(referenced_stems[0])
        specs[name] = {"description": description, "cli": [verb] if verb else None}

    return specs
