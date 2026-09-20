"""Story 17-1 — detector incident log companion and bmad-drift blind-spot pins.

The four ``bmad-drift`` finding kinds named in FR-145 are pinned by dedicated
fixtures in ``test_sources_factory.py`` (Story 6.8). This module guards the
tracked incident log and documents those cross-references so a future detector
fix cannot land without its mandatory log entry.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_FACTORY_TESTS = Path(__file__).resolve().parent / "test_sources_factory.py"

_LOG = Path(__file__).resolve().parents[2] / "docs" / "detector-incident-log.md"

_REQUIRED_SECTIONS = (
    "## Mandatory-entry rule",
    "## Schema",
    "## Entries",
)

_ENTRY_HEADER = re.compile(r"^### \d{4}-\d{2}-\d{2} — ", re.MULTILINE)

_ENTRY_FIELDS = (
    "date",
    "detector",
    "wrong claim",
    "true value",
    "root cause",
    "fixing commit",
    "pinning fixture",
)

_BMAD_DRIFT_PIN_TESTS = (
    "test_pin_missing_reports_fail",
    "test_archive_misplaced_and_stray_file_are_flagged",
    "test_spec_status_stale_reports_warn_when_a_matching_retro_exists",
)


def _factory_test_names() -> set[str]:
    tree = ast.parse(_FACTORY_TESTS.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}


def test_detector_incident_log_exists_with_mandatory_entry_rule() -> None:
    text = _LOG.read_text(encoding="utf-8")
    for section in _REQUIRED_SECTIONS:
        assert section in text, f"missing section: {section}"
    assert "same commit" in text.lower()


def test_detector_incident_log_has_seed_entries_with_full_schema() -> None:
    text = _LOG.read_text(encoding="utf-8")
    headers = _ENTRY_HEADER.findall(text)
    assert len(headers) >= 3, f"expected at least three seed entries, got {len(headers)}"
    for field in _ENTRY_FIELDS:
        assert field in text, f"schema field never used in log: {field}"


def test_bmad_drift_blind_spot_fixtures_exist_in_factory_suite() -> None:
    names = _factory_test_names()
    missing = [name for name in _BMAD_DRIFT_PIN_TESTS if name not in names]
    assert not missing, f"FR-145 pin tests missing from test_sources_factory.py: {missing}"
