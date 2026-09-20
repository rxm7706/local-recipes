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

REPO_ROOT = Path(__file__).resolve().parents[6]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"

AWAITING_LABEL = "awaiting-operator (run bmad-loop confirm)"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_missing_spec_test", FLEET_PICTURE)
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
