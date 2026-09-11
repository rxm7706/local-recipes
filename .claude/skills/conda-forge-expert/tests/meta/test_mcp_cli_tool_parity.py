"""Story 16.3 — Mason's MCP tool surface passes the CLI-tool parity gate.

Parity between a station's CLI verbs and its MCP tools was, until this
story, a gated number for marshal only (`pyforge.marshal.mcp.parity`,
`test_cli_tool_parity.py`). This extends that same gate engine over the CFE
server's 46 `@mcp.tool()` registrations via `.claude/tools/mcp_cli_parity.py`
— a CLI wrapper can no longer gain or lose a pixi task with no tool
counterpart (or vice versa) without something going red.

Live inventory must stay clean. Fixture injections prove a deliberate
mismatch actually FAILS the gate — the property this story exists to add,
not merely that the gate runs.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PARITY_MODULE_PATH = Path(__file__).resolve().parents[4] / "tools" / "mcp_cli_parity.py"


def _load_mcp_cli_parity():
    spec = importlib.util.spec_from_file_location("mcp_cli_parity", _PARITY_MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["mcp_cli_parity"] = module
    spec.loader.exec_module(module)
    return module


parity = _load_mcp_cli_parity()

pytestmark = pytest.mark.skipif(
    parity.MARSHAL_IMPORT_ERROR is not None,
    reason=(
        "pyforge.marshal.mcp.parity is unavailable in this checkout "
        f"(monorepo not fully checked out?): {parity.MARSHAL_IMPORT_ERROR}"
    ),
)


def _live_kwargs() -> dict:
    return {
        "tool_specs": parity.build_tool_specs(),
        "cli_verbs": parity.discover_cli_verbs(),
        "cli_only": frozenset(parity.CLI_ONLY_VERBS),
        "tool_only": frozenset(parity.TOOL_ONLY_NAMES),
    }


def test_live_mcp_cli_tool_parity_passes():
    """Production tool/CLI surfaces + the declared allowlists satisfy parity."""
    kwargs = _live_kwargs()
    parity.assert_cli_tool_parity(**kwargs)
    assert parity.parity_findings(**kwargs) == []


def test_build_tool_specs_covers_all_46_tools():
    # NOTE: bump this count alongside adding/removing an @mcp.tool() registration.
    assert len(parity.build_tool_specs()) == 46


def test_tool_only_inventory_matches_declared_allowlist():
    specs = parity.build_tool_specs()
    tool_only_in_specs = {name for name, spec in specs.items() if spec["cli"] is None}
    assert tool_only_in_specs == set(parity.TOOL_ONLY_NAMES)


def test_cli_verbs_anchored_at_pixi_task_name_not_wrapper_stem():
    """Regression: verbs must be pixi task names, never the wrapper file's
    stem — a stem-anchored derivation cannot detect a pixi task being
    renamed, added, or removed independent of its file, which is exactly
    the drift class this story exists to close."""
    verbs = parity.discover_cli_verbs()
    assert "check-deps" in verbs
    assert "dependency-checker" not in verbs
    assert "build-local" in verbs
    assert "local_builder" not in verbs


def test_scan_project_resolves_via_full_pixi_feature_scan():
    """Regression: scanning every pixi feature (not just local-recipes) is
    what lets `scan_project` resolve to the vuln-db-only `scan-project`
    task, instead of misfiling as a tool-only asymmetry it is not."""
    specs = parity.build_tool_specs()
    assert specs["scan_project"]["cli"] == ["scan-project"]
    assert "scan_project" not in parity.TOOL_ONLY_NAMES


def test_prepare_submission_branch_override_resolves_to_prepare_pr():
    """Regression: the one case static script-reference analysis cannot
    disambiguate on its own (see mcp_cli_parity.py's module docstring)."""
    specs = parity.build_tool_specs()
    assert specs["prepare_submission_branch"]["cli"] == ["prepare-pr"]
    assert specs["submit_pr"]["cli"] == ["submit-pr"]


def test_fixture_cli_on_surface_missing_tool_fails():
    """Deliberate miss: an on-surface CLI verb with no tool counterpart."""
    kwargs = _live_kwargs()
    broken_verbs = kwargs["cli_verbs"] | {"totally-fake-verb"}
    findings = parity.parity_findings(**{**kwargs, "cli_verbs": broken_verbs})
    codes = {f.code for f in findings}
    assert "cli_missing_tool" in codes
    with pytest.raises(AssertionError, match="cli_missing_tool|totally-fake-verb"):
        parity.assert_cli_tool_parity(**{**kwargs, "cli_verbs": broken_verbs})


def test_fixture_tool_without_cli_undeclared_fails():
    """Deliberate miss: a tool with no CLI verb and no allowlist entry."""
    kwargs = _live_kwargs()
    broken_specs = {
        **kwargs["tool_specs"],
        "phantom_tool": {"description": "fixture-only", "cli": None},
    }
    findings = parity.parity_findings(**{**kwargs, "tool_specs": broken_specs})
    codes = {f.code for f in findings}
    assert "tool_without_cli" in codes
    with pytest.raises(AssertionError, match="tool_without_cli"):
        parity.assert_cli_tool_parity(**{**kwargs, "tool_specs": broken_specs})
