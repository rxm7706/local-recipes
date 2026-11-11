"""Meta-test: Story 28.19 missing-spec escalation naming in fleet_picture.py.

``MRS-DISP-005`` refuse with remaining backlog must surface the expected
tracked spec glob in the state column (and not the generic bmad-loop confirm
remedy). Same importlib harness as conda-forge-expert's
``test_fleet_picture_awaiting_operator.py`` — lives here so marshal changes
do not touch ``conda-forge-expert`` (``test_skf_domain_skill`` guard).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Story 116.2 (spec-pyforge-marshal:CAP-305): this module reads the repository outside this package, so it runs in
# the live-tree half; it finds the repository root when a test runs, never at import, so the module imports off
# the tree (the package half collects it before the marker deselects it).
pytestmark = pytest.mark.live_tree


def _fleet_picture_path() -> Path:
    # tests/meta -> tests -> pyforge-marshal -> packages -> shared -> src -> repo root
    return Path(__file__).resolve().parents[6] / "scripts" / "fleet_picture.py"


AWAITING_LABEL = "awaiting-operator (run bmad-loop confirm)"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_missing_spec_test", _fleet_picture_path())
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_missing_spec_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_missing_spec_awaiting_operator_uses_the_spec_path_remedy():
    """Story 28.19: MRS-DISP-005 refuse names the expected spec glob."""
    mod = _load_fleet_picture()
    remedy = (
        "missing tracked spec: author _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-39-4-*.md"
    )
    cell = mod.station_state(
        running=False,
        story="39.4",
        hstate="awaiting-operator",
        done=10,
        total=11,
        backlog=1,
        awaiting_operator_remedy=remedy,
    )
    assert cell == f"awaiting-operator ({remedy})"
    assert "spec-39-4-*.md" in cell
    assert AWAITING_LABEL not in cell
