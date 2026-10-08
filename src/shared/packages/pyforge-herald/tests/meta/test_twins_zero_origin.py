"""Live-tree zero-origin scan for HTML twins (Story 30.1 AC)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.herald import twins

REPO_ROOT = Path(__file__).resolve().parents[6]


def test_standalone_twins_have_zero_external_origins():
    findings: list[twins.OriginFinding] = []
    for path in twins.iter_standalone_twin_files(REPO_ROOT):
        findings.extend(twins.scan_file(path))
    assert not findings, _format_findings(findings)


def test_react_deck_index_html_has_zero_external_origins():
    findings: list[twins.OriginFinding] = []
    for path in twins.iter_react_deck_index_files(REPO_ROOT):
        findings.extend(twins.scan_file(path))
    assert not findings, _format_findings(findings)


def _format_findings(findings: list[twins.OriginFinding]) -> str:
    lines = [f"{f.path}: {f.origin} ({f.reference[:80]})" for f in findings[:20]]
    if len(findings) > 20:
        lines.append(f"... and {len(findings) - 20} more")
    return "\n".join(lines)
