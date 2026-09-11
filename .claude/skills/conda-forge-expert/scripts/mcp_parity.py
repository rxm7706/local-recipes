"""CLI ⇄ MCP-tool parity for the CFE server (Story 16.3, FR-155).

Extends marshal's ``pyforge.marshal.mcp.parity`` primitive — no forked gate
logic. CLI verbs are pixi task names whose ``cmd`` invokes the CFE script
surface; tool inventory is ``mcp_tools.TOOL_SPECS``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_MARSHAL_SRC = _REPO_ROOT / "src" / "shared" / "packages" / "pyforge-marshal" / "src"
if str(_MARSHAL_SRC) not in sys.path:
    sys.path.insert(0, str(_MARSHAL_SRC))

from mcp_tools import TOOL_SPECS
from pyforge.marshal.mcp import parity as _marshal_parity

_PIXI_TOML = _REPO_ROOT / "pixi.toml"
_CFE_SCRIPT_MARKER = ".claude/scripts/conda-forge-expert/"
_CFE_CMD_MARKERS = (_CFE_SCRIPT_MARKER, "build-locally.py", "test-recipes.py")

# Pixi tasks that deliberately have no MCP tool yet. Each entry carries a
# reason sentence — an allowlist is a declaration with a reason, never a way
# to reach green.
CLI_ONLY_VERBS: dict[str, str] = {
    "add-handoff": (
        "Inventory-match ADD-bucket handoff writer — batch operator surface, "
        "not an MCP read/trigger."
    ),
    "atlas-phase": (
        "Single cf_atlas phase runner — long-running operator rebuild, not an "
        "MCP tool surface."
    ),
    "autotick-npm": (
        "npm-registry autotick — separate ecosystem entrypoint, no MCP wrapper."
    ),
    "bootstrap-data": (
        "Full data refresh orchestrator — attended operator bootstrap, not MCP."
    ),
    "build-bmad-suite": (
        "BMAD suite member build lane — factory operator surface, not MCP."
    ),
    "build-cf-atlas": (
        "cf_atlas full rebuild — attended operator job, not an MCP read/trigger."
    ),
    "build-linux": (
        "Docker linux matrix build via build-locally.py — CI operator surface."
    ),
    "build-local": (
        "Native local_builder entry — mason/CFE build lane, not MCP trigger_build."
    ),
    "build-local-all": (
        "Multi-platform local_builder sweep — operator surface, not MCP."
    ),
    "build-local-check": (
        "Local cross-build diagnostics — operator surface, not MCP."
    ),
    "build-local-setup-sdk": (
        "MacOS SDK bootstrap for cross-builds — one-time operator setup."
    ),
    "build-osx": (
        "Native osx build-locally.py entry — platform operator surface."
    ),
    "build-win": (
        "Native win build-locally.py entry — platform operator surface."
    ),
    "cwe-seed-gap": (
        "CWE seed suggester — read-only gap report, no MCP inventory helper."
    ),
    "detail-cf-atlas-vdb": (
        "Verbose detail_cf_atlas --vdb-all preset — vuln-db operator CLI, "
        "not the MCP package_health card."
    ),
    "fetch-cisa-kev": (
        "CISA KEV ingest — data refresh operator task, not MCP."
    ),
    "fetch-cwe-catalog": (
        "CWE catalog fetch — data refresh operator task, not MCP."
    ),
    "fetch-epss": (
        "EPSS ingest — data refresh operator task, not MCP."
    ),
    "gen-yml-reference": (
        "Reference doc regeneration from upstream schemas — maintenance surface."
    ),
    "generate-bmad-suite": (
        "BMAD suite recipe pin regeneration — maintenance operator surface."
    ),
    "generate-cpan": (
        "CPAN scaffold variant of recipe-generator — ecosystem-specific CLI only."
    ),
    "generate-cran": (
        "CRAN scaffold variant of recipe-generator — ecosystem-specific CLI only."
    ),
    "generate-failure-catalog": (
        "Failure pattern catalog regeneration — maintenance operator surface."
    ),
    "generate-luarocks": (
        "LuaRocks scaffold variant of recipe-generator — ecosystem CLI only."
    ),
    "generate-npm": (
        "npm scaffold variant of recipe-generator — ecosystem-specific CLI only."
    ),
    "inventory-channel": (
        "Inventory channel classifier CLI — vuln-db operator surface, not MCP."
    ),
    "library-futures": (
        "2027–2030 futures scorer CLI — consumed via recommend-2027 on MCP."
    ),
    "license-check": (
        "SPDX/license_file linter — standalone validate lane, not MCP."
    ),
    "license-map-gap": (
        "License map gap suggester — read-only maintenance surface."
    ),
    "lts-registry-gap": (
        "LTS registry gap suggester — read-only maintenance surface."
    ),
    "mapping-gap": (
        "conda↔PyPI mapping gap recoverer — offline operator surface."
    ),
    "query-cf-atlas": (
        "conda_forge_atlas.py query CLI — structured lookup, not ad-hoc SQL MCP."
    ),
    "recipe-build-cross": (
        "Cross-target rattler-build wrapper — artifact producer, not MCP trigger."
    ),
    "recipe-build-docker": (
        "Docker CI-parity build via build-locally.py — opt-in operator surface."
    ),
    "spdx-schema-gap": (
        "SPDX schema gap suggester — read-only maintenance surface."
    ),
    "stats-cf-atlas": (
        "Atlas summary statistics CLI — operator read, not MCP tool."
    ),
    "test-recipes": (
        "Random/targeted recipe smoke harness — CI operator surface."
    ),
}

# Named MCP tools that intentionally have no pixi-task counterpart.
TOOL_ONLY_NAMES: frozenset[str] = frozenset(
    {
        "get_build_summary",
        "lookup_feedstock",
        "enrich_from_feedstock",
        "get_feedstock_context",
        "edit_recipe",
        "query_atlas",
    }
)

_TASK_BLOCK_RE = re.compile(
    r"\[feature\.([^.]+)\.tasks\.([^\]]+)\](.*?)(?=\n\[|\Z)",
    re.DOTALL,
)
_CMD_LINE_RE = re.compile(r'^cmd = "([^"]+)"', re.MULTILINE)


def discover_cli_verbs(*, pixi_toml: Path | None = None) -> frozenset[str]:
    """Return pixi task names whose cmd invokes the CFE script surface."""
    path = _PIXI_TOML if pixi_toml is None else pixi_toml
    text = path.read_text(encoding="utf-8")
    verbs: set[str] = set()
    for _feature, task_name, body in _TASK_BLOCK_RE.findall(text):
        cmd_match = _CMD_LINE_RE.search(body)
        if cmd_match is None:
            continue
        cmd = cmd_match.group(1)
        if any(marker in cmd for marker in _CFE_CMD_MARKERS):
            verbs.add(task_name)
    if not verbs:
        raise RuntimeError(f"no CFE pixi tasks discovered in {path}")
    return frozenset(verbs)


def tools_by_cli_verb(
    tool_specs: dict[str, dict[str, object]] | None = None,
) -> dict[str, list[str]]:
    return _marshal_parity.tools_by_cli_verb(
        TOOL_SPECS if tool_specs is None else tool_specs
    )


def parity_findings(
    *,
    tool_specs: dict[str, dict[str, object]] | None = None,
    cli_verbs: frozenset[str] | None = None,
    cli_only: frozenset[str] | None = None,
    tool_only: frozenset[str] | None = None,
) -> list[_marshal_parity.ParityFinding]:
    return _marshal_parity.parity_findings(
        tool_specs=TOOL_SPECS if tool_specs is None else tool_specs,
        cli_verbs=discover_cli_verbs() if cli_verbs is None else cli_verbs,
        cli_only=frozenset(CLI_ONLY_VERBS) if cli_only is None else cli_only,
        tool_only=TOOL_ONLY_NAMES if tool_only is None else tool_only,
    )


def assert_cli_tool_parity(
    *,
    tool_specs: dict[str, dict[str, object]] | None = None,
    cli_verbs: frozenset[str] | None = None,
    cli_only: frozenset[str] | None = None,
    tool_only: frozenset[str] | None = None,
) -> None:
    findings = parity_findings(
        tool_specs=tool_specs,
        cli_verbs=cli_verbs,
        cli_only=cli_only,
        tool_only=tool_only,
    )
    if not findings:
        return
    lines = [f"{f.code}: {f.detail}" for f in findings]
    raise AssertionError(
        "CLI ⇄ tool parity gate failed (FR-155 / CFE):\n  - " + "\n  - ".join(lines)
    )
