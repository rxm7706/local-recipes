"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_capability_effect_caller_reach.py``.

The live fleet proof runs ``capability_effect.gather_caller_reach`` over this
repository, so it runs in the station's live-tree half; every other caller-reach
test builds its own tree and stays in
``test_sources_capability_effect_caller_reach.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import capability_effect

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    """This repository's root, found when a test runs (never at import time)."""
    here = Path(__file__).resolve()
    root = next((p for p in here.parents if (p / "pixi.toml").is_file() and (p / "_bmad-output").is_dir()), None)
    assert root is not None, "repo root not found"
    return root


def test_live_fleet_proves_capability_effect_no_caller_finding() -> None:
    """Live fleet proof — Story 21.3 caution: not a single synthetic join value.

    Original target (2026-09-09): ``spec-risk-tiered-review-depth`` symbols
    ``classify_review_tier`` / ``resolve_review_cycles`` with zero callers
    outside ``core/gate.py`` and ``tests/unit/test_gate.py``.

    Marshal Story 33.5 (done) wired ``cli/gate.py`` callers at
    ``cli/gate.py:701`` and ``:705``, so those symbols now have production
    callers outside ``core/gate.py``. This test therefore requires at least
    one other live ``capability-effect-no-caller`` finding on the real fleet.
    """
    root = _repo_root()
    findings = capability_effect.gather_caller_reach(root)

    no_caller = [f for f in findings if f.check == "capability-effect-no-caller"]
    assert no_caller, "expected at least one live capability-effect-no-caller finding on the real fleet"

    risk_findings = [
        f
        for f in no_caller
        if f.evidence.get("spec_slug") == "spec-risk-tiered-review-depth"
        and f.evidence.get("symbol") in {"classify_review_tier", "resolve_review_cycles"}
    ]
    if not risk_findings:
        assert len(no_caller) >= 1
    else:
        for finding in risk_findings:
            assert finding.status is DoctorStatus.WARN
            assert "whole-word textual scan" in finding.message
