"""Story 25.3 — FR-155 CLI ⇄ tool parity is a gated number, not review.

Live inventory must stay clean. Fixture injections prove a deliberate
mismatch fails the gate (the property the story exists to enforce).
"""

from __future__ import annotations

import pytest

from pyforge.atlas.mcp.audit import registered_surface_tools
from pyforge.atlas.mcp.parity import (
    CLI_ONLY_VERBS,
    TOOL_ONLY_NAMES,
    assert_cli_tool_parity,
    discover_cli_verbs,
    parity_findings,
    tools_by_cli_verb,
)
from pyforge.atlas.mcp.tools import TOOL_SPECS


def test_tool_specs_covers_registered_server_tools():
    assert set(TOOL_SPECS) == registered_surface_tools()


def test_run_tool_cli_pipeline_tokens_match_tool_names():
    """Full argv tail must match the pipeline each run_* tool triggers."""
    for name, spec in TOOL_SPECS.items():
        if not name.startswith("run_") or not name.endswith("_pipeline"):
            continue
        cli = spec.get("cli")
        assert isinstance(cli, list) and len(cli) == 3 and cli[1] == "--pipeline"
        expected = name.removeprefix("run_").removesuffix("_pipeline")
        assert cli[2] == expected, f"{name}: cli pipeline token {cli[2]!r} != {expected!r}"


def test_every_cli_only_verb_has_a_reason_sentence():
    for verb, reason in CLI_ONLY_VERBS.items():
        assert reason.strip(), f"CLI-only verb {verb!r} missing reason sentence"


def test_live_cli_tool_parity_passes():
    """Production TOOL_SPECS + CLI-only allowlist must satisfy FR-155."""
    assert_cli_tool_parity()
    assert parity_findings() == []


def test_discover_cli_verbs_matches_known_surface():
    verbs = discover_cli_verbs()
    assert "run" in verbs
    assert frozenset(CLI_ONLY_VERBS) <= verbs
    for verb in tools_by_cli_verb():
        assert verb in verbs


def test_fixture_cli_on_surface_missing_tool_fails():
    """Deliberate FR-155 miss: on-surface CLI verb with no tool."""
    # Drop every tool that claims ``run``; keep tool-only entries only.
    broken = {name: dict(spec) for name, spec in TOOL_SPECS.items() if spec.get("cli") is None}
    findings = parity_findings(tool_specs=broken)
    codes = {f.code for f in findings}
    assert "cli_missing_tool" in codes
    with pytest.raises(AssertionError, match="cli_missing_tool|run"):
        assert_cli_tool_parity(tool_specs=broken)


def test_fixture_tool_claims_unknown_cli_fails():
    """Deliberate FR-155 miss: tool argv claims a non-existent CLI verb."""
    broken = {
        **{n: dict(s) for n, s in TOOL_SPECS.items()},
        "run_phantom_pipeline": {
            "description": "fixture-only",
            "cli": ["not-a-real-verb", "--pipeline", "core"],
        },
    }
    findings = parity_findings(tool_specs=broken)
    assert any(f.code == "tool_cli_unknown" for f in findings)
    with pytest.raises(AssertionError, match="tool_cli_unknown|not-a-real-verb"):
        assert_cli_tool_parity(tool_specs=broken)


def test_fixture_cli_only_stale_when_tool_exists_fails():
    """Deliberate FR-155 miss: CLI-only allowlist still lists a tooled verb."""
    cli_only = frozenset(CLI_ONLY_VERBS) | frozenset({"run"})
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
    findings = parity_findings(tool_only=TOOL_ONLY_NAMES | frozenset({"run_core_pipeline"}))
    assert any(f.code == "tool_only_has_cli" for f in findings)
    with pytest.raises(AssertionError, match="tool_only_has_cli"):
        assert_cli_tool_parity(tool_only=TOOL_ONLY_NAMES | frozenset({"run_core_pipeline"}))


def test_fixture_tool_cli_malformed_fails():
    """Deliberate FR-155 miss: tool cli is not a usable argv sequence."""
    broken = {
        **{n: dict(s) for n, s in TOOL_SPECS.items()},
        "run_bad_pipeline": {"description": "fixture", "cli": "run --pipeline core"},
    }
    findings = parity_findings(tool_specs=broken)
    assert any(f.code == "tool_cli_malformed" for f in findings)
    with pytest.raises(AssertionError, match="tool_cli_malformed"):
        assert_cli_tool_parity(tool_specs=broken)
