"""Story 16.3 — FR-155 CLI ⇄ tool parity is a gated number, not review.

Live inventory must stay clean. Fixture injections prove a deliberate
mismatch fails the gate (the property the story exists to enforce).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from mcp_parity import (  # noqa: E402
    CLI_ONLY_VERBS,
    TOOL_ONLY_NAMES,
    assert_cli_tool_parity,
    discover_cli_verbs,
    parity_findings,
    tools_by_cli_verb,
)
from mcp_tools import TOOL_SPECS, assert_tool_specs_covers_server  # noqa: E402


def test_tool_specs_covers_registered_server_tools():
    assert_tool_specs_covers_server()


def test_every_cli_only_verb_has_a_reason_sentence():
    for verb, reason in CLI_ONLY_VERBS.items():
        assert reason.strip(), f"CLI-only verb {verb!r} missing reason sentence"


def test_tool_only_inventory_helpers_are_declared():
    for name in TOOL_ONLY_NAMES:
        assert TOOL_SPECS[name].get("cli") is None


def test_live_cli_tool_parity_passes():
    """Production TOOL_SPECS + allowlists must satisfy FR-155."""
    assert_cli_tool_parity()
    assert parity_findings() == []


def test_discover_cli_verbs_matches_known_surface():
    verbs = discover_cli_verbs()
    assert "validate" in verbs and "check-deps" in verbs
    assert frozenset(CLI_ONLY_VERBS) <= verbs
    for verb in tools_by_cli_verb():
        assert verb in verbs


def test_fixture_cli_on_surface_missing_tool_fails():
    """Deliberate FR-155 miss: on-surface CLI verb with no tool."""
    broken = {
        name: dict(spec)
        for name, spec in TOOL_SPECS.items()
        if name != "validate_recipe"
    }
    findings = parity_findings(tool_specs=broken)
    codes = {f.code for f in findings}
    assert "cli_missing_tool" in codes
    with pytest.raises(AssertionError, match="cli_missing_tool|validate"):
        assert_cli_tool_parity(tool_specs=broken)


def test_fixture_tool_claims_unknown_cli_fails():
    """Deliberate FR-155 miss: tool argv claims a non-existent CLI verb."""
    broken = {
        **{n: dict(s) for n, s in TOOL_SPECS.items()},
        "cfe_phantom": {
            "description": "fixture-only",
            "cli": ["not-a-real-verb"],
        },
    }
    findings = parity_findings(tool_specs=broken)
    assert any(f.code == "tool_cli_unknown" for f in findings)
    with pytest.raises(AssertionError, match="tool_cli_unknown|not-a-real-verb"):
        assert_cli_tool_parity(tool_specs=broken)


def test_fixture_cli_only_stale_when_tool_exists_fails():
    """Deliberate FR-155 miss: CLI-only allowlist still lists a tooled verb."""
    cli_only = frozenset(CLI_ONLY_VERBS) | frozenset({"validate"})
    findings = parity_findings(cli_only=cli_only)
    assert any(f.code == "cli_only_has_tool" for f in findings)
    with pytest.raises(AssertionError, match="cli_only_has_tool"):
        assert_cli_tool_parity(cli_only=cli_only)


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
    findings = parity_findings(
        tool_only=TOOL_ONLY_NAMES | frozenset({"validate_recipe"})
    )
    assert any(f.code == "tool_only_has_cli" for f in findings)
    with pytest.raises(AssertionError, match="tool_only_has_cli"):
        assert_cli_tool_parity(
            tool_only=TOOL_ONLY_NAMES | frozenset({"validate_recipe"})
        )


def test_fixture_tool_cli_malformed_fails():
    """Deliberate FR-155 miss: tool cli is not a usable argv sequence."""
    broken = {
        **{n: dict(s) for n, s in TOOL_SPECS.items()},
        "cfe_bad": {"description": "fixture", "cli": "validate"},
    }
    findings = parity_findings(tool_specs=broken)
    assert any(f.code == "tool_cli_malformed" for f in findings)
    with pytest.raises(AssertionError, match="tool_cli_malformed"):
        assert_cli_tool_parity(tool_specs=broken)
