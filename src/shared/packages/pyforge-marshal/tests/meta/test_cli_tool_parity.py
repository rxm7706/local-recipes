"""Story 18.2 — FR-155 CLI ⇄ tool parity is a gated number, not review.

Live inventory must stay clean. Fixture injections prove a deliberate
mismatch fails the gate (the property the story exists to enforce).
"""

from __future__ import annotations

import pytest

from pyforge.marshal.mcp.parity import (
    CLI_ONLY_VERBS,
    TOOL_ONLY_NAMES,
    assert_cli_tool_parity,
    discover_cli_verbs,
    parity_findings,
    tools_by_cli_verb,
)
from pyforge.marshal.mcp.tools import TOOL_SPECS


def test_live_cli_tool_parity_passes():
    """Production TOOL_SPECS + CLI-only allowlist must satisfy FR-155."""
    assert_cli_tool_parity()
    findings = parity_findings()
    assert findings == []


def test_discover_cli_verbs_matches_known_surface():
    verbs = discover_cli_verbs()
    assert "status" in verbs and "check" in verbs
    assert verbs >= CLI_ONLY_VERBS
    # Every tool-claimed verb is a real CLI verb (live inventory).
    for verb in tools_by_cli_verb():
        assert verb in verbs


def test_tool_only_inventory_helper_is_declared():
    assert "list_marshal_tools" in TOOL_ONLY_NAMES
    assert TOOL_SPECS["list_marshal_tools"].get("cli") is None


def test_fixture_cli_on_surface_missing_tool_fails():
    """Deliberate FR-155 miss: on-surface CLI verb with no tool."""
    # Drop status from tools; keep it off the CLI-only allowlist.
    broken = {name: dict(spec) for name, spec in TOOL_SPECS.items() if name != "marshal_status"}
    findings = parity_findings(tool_specs=broken)
    codes = {f.code for f in findings}
    assert "cli_missing_tool" in codes
    with pytest.raises(AssertionError, match="cli_missing_tool|status"):
        assert_cli_tool_parity(tool_specs=broken)


def test_fixture_tool_claims_unknown_cli_fails():
    """Deliberate FR-155 miss: tool argv claims a non-existent CLI verb."""
    broken = {
        **{n: dict(s) for n, s in TOOL_SPECS.items()},
        "marshal_phantom": {
            "description": "fixture-only",
            "cli": ["not-a-real-verb", "--format", "json"],
        },
    }
    findings = parity_findings(tool_specs=broken)
    assert any(f.code == "tool_cli_unknown" for f in findings)
    with pytest.raises(AssertionError, match="tool_cli_unknown|not-a-real-verb"):
        assert_cli_tool_parity(tool_specs=broken)


def test_fixture_cli_only_stale_when_tool_exists_fails():
    """Deliberate FR-155 miss: CLI-only allowlist still lists a tooled verb."""
    findings = parity_findings(cli_only=CLI_ONLY_VERBS | frozenset({"status"}))
    assert any(f.code == "cli_only_has_tool" for f in findings)
    with pytest.raises(AssertionError, match="cli_only_has_tool"):
        assert_cli_tool_parity(cli_only=CLI_ONLY_VERBS | frozenset({"status"}))


def test_fixture_tool_without_cli_undeclared_fails():
    """Deliberate FR-155 miss: cli=None tool not in TOOL_ONLY_NAMES."""
    broken = {
        **{n: dict(s) for n, s in TOOL_SPECS.items()},
        "secret_helper": {"description": "fixture", "cli": None},
    }
    findings = parity_findings(tool_specs=broken)
    assert any(f.code == "tool_without_cli" for f in findings)
    with pytest.raises(AssertionError, match="tool_without_cli"):
        assert_cli_tool_parity(tool_specs=broken)


def test_fixture_tool_only_missing_fails():
    """Deliberate FR-155 miss: TOOL_ONLY_NAMES names a tool absent from specs."""
    findings = parity_findings(tool_only=TOOL_ONLY_NAMES | frozenset({"ghost"}))
    assert any(f.code == "tool_only_missing" for f in findings)
    with pytest.raises(AssertionError, match="tool_only_missing"):
        assert_cli_tool_parity(tool_only=TOOL_ONLY_NAMES | frozenset({"ghost"}))


def test_fixture_tool_only_has_cli_fails():
    """Deliberate FR-155 miss: tool-only allowlist entry that also claims a CLI."""
    findings = parity_findings(tool_only=TOOL_ONLY_NAMES | frozenset({"marshal_status"}))
    assert any(f.code == "tool_only_has_cli" for f in findings)
    with pytest.raises(AssertionError, match="tool_only_has_cli"):
        assert_cli_tool_parity(tool_only=TOOL_ONLY_NAMES | frozenset({"marshal_status"}))


def test_fixture_tool_cli_malformed_fails():
    """Deliberate FR-155 miss: tool cli is not a usable argv sequence."""
    broken = {
        **{n: dict(s) for n, s in TOOL_SPECS.items()},
        "marshal_bad": {"description": "fixture", "cli": "status --format json"},
    }
    findings = parity_findings(tool_specs=broken)
    assert any(f.code == "tool_cli_malformed" for f in findings)
    with pytest.raises(AssertionError, match="tool_cli_malformed"):
        assert_cli_tool_parity(tool_specs=broken)
