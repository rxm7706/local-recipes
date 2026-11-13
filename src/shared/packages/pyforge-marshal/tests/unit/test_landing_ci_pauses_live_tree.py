"""Story 101.1 AC5: steward 103.1's checked-in ``paused_by_master`` payload, read against marshal's rule.

Story 116.2 (spec-pyforge-marshal:CAP-305): the one ``test_landing_ci_pauses.py`` test that reads a file outside
this package (pyforge-steward's ``tests/fixtures/ci_status_master_on.json``) moved here, marked ``live_tree``; it
fails, never skips, when the fixture is absent. Every other CI-pause landing test stays in
``test_landing_ci_pauses.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pyforge.marshal.core.landing_ci_pauses import (
    envelope_is_valid,
    row_counts_as_paused_at_merge,
    surfaces_from_envelope,
)

pytestmark = pytest.mark.live_tree


def _steward_master_on_fixture() -> Path:
    # tests/unit -> tests -> pyforge-marshal -> packages: steward 103.1's AC6 fixture, read as a file, never imported.
    return Path(__file__).resolve().parents[3] / "pyforge-steward" / "tests" / "fixtures" / "ci_status_master_on.json"


def _listed_by_story_100_1(row: dict[str, Any]) -> bool:
    """Story 100.1's rule alone: the row as a steward before 103.1 would send it."""
    return row_counts_as_paused_at_merge({k: v for k, v in row.items() if k != "paused_by_master"})


def test_101_1_ac5_steward_master_on_fixture() -> None:
    """AC5: steward 103.1's checked-in payload, read as a file; a missing file fails, never skips."""
    fixture = _steward_master_on_fixture()
    assert fixture.is_file(), f"steward 103.1's fixture is missing: {fixture}"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert envelope_is_valid(payload) is True
    rows = [row for row in payload["rows"] if isinstance(row, dict)]
    surfaces = surfaces_from_envelope(payload)
    assert surfaces == sorted(set(surfaces))
    assert "master:PAUSE_ALL_CI" in surfaces
    gated_paused = [row["id"] for row in rows if row.get("verdict") == "paused" and row.get("paused_by_master") is True]
    assert gated_paused, "the fixture holds no gated paused row; the check below would be vacuous"
    for row_id in gated_paused:
        assert row_id in surfaces, row_id
    ungated = [row for row in rows if row.get("paused_by_master") is False]
    assert ungated, "the fixture holds no ungated row; the check below would be vacuous"
    for row in ungated:
        assert (row["id"] in surfaces) is _listed_by_story_100_1(row), row
