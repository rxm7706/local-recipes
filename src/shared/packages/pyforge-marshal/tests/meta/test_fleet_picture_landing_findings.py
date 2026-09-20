"""Story 53.2 review (I1): main()'s ATTENTION-block landing-findings rendering.

``execute_dispatch_land``'s envelope findings (MRS-DISP-047 warn / MRS-DISP-048
error) must reach ``fleet-picture``'s ATTENTION block, not just the journal --
same isolation pattern as ``test_fleet_picture_attention_dispatch_refused.py``.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"

_STORY = "53-2-landing-findings-coverage"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_landing_findings_test", FLEET_PICTURE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_landing_findings_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _seed_marshal_ledger(repo: Path) -> None:
    ledger_dir = repo / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "sprint-status-ledger.yaml").write_text(
        "development_status:\n  epic-53: backlog\n  53-2-x: backlog\n",
        encoding="utf-8",
    )


def _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path: Path) -> None:
    """Isolate main() from live ledgers / marshal / doctor / gh probes."""
    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir()
    _seed_marshal_ledger(empty_repo)
    monkeypatch.setattr(fleet, "REPO", empty_repo)
    monkeypatch.setattr(fleet, "loop_home_staleness", lambda: [])
    monkeypatch.setattr(fleet, "bmad_core_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "verification_staleness_findings", lambda: [])
    monkeypatch.setattr(fleet, "dream_chain_gap_findings", lambda: [])
    monkeypatch.setattr(fleet, "sibling_dreams_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "capability_effect_findings", lambda: [])
    monkeypatch.setattr(fleet, "baseline_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "_open_prs_by_head_ref", lambda: {})
    monkeypatch.setattr(
        fleet.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )


def _marshal_live_row(**overrides) -> dict:
    row = {
        "state": "running",
        "story": _STORY,
        "dispatch_phase": "building",
        "dispatch_completion_verdict": None,
        "dispatch_verification_verdict": None,
        "dispatch_verification_failed_gate": None,
        "escalation_reason": None,
        "escalation_artifact": None,
        "scope_advisories": [],
        "landing_findings": [],
        "awaiting_operator_remedy": None,
        "missing_spec_escalation_glob": None,
        "dispatch_stranded_work": None,
    }
    row.update(overrides)
    return row


def _run_main_with_live(fleet, monkeypatch, tmp_path: Path, live_row: dict):
    _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path)
    monkeypatch.setattr(
        fleet,
        "running_stations",
        lambda: ({"marshal"}, {"marshal": live_row}),
    )
    return fleet.main()


@pytest.fixture
def fleet():
    return _load_fleet_picture()


def test_main_needs_names_a_refused_landing_error_finding(fleet, monkeypatch, capsys, tmp_path):
    """MRS-DISP-048 (error) means the landing was refused -- a `needs` line."""
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(landing_findings=[{"code": "MRS-DISP-048", "severity": "error", "message": "refused"}]),
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "ATTENTION:" in out
    assert "landing refused" in out
    assert "MRS-DISP-048" in out


def test_main_watch_names_a_non_blocking_landing_warn_finding(fleet, monkeypatch, capsys, tmp_path):
    """MRS-DISP-047 (warn) is FYI -- a `watch` line, never `needs`."""
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(landing_findings=[{"code": "MRS-DISP-047", "severity": "warn", "message": "reconciled"}]),
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "landing refused" not in out
    assert "landing finding(s) (not blocking)" in out
    assert "MRS-DISP-047" in out


def test_main_silent_when_no_landing_findings(fleet, monkeypatch, capsys, tmp_path):
    rc = _run_main_with_live(fleet, monkeypatch, tmp_path, _marshal_live_row(landing_findings=[]))
    out = capsys.readouterr().out

    assert rc == 0
    assert "landing refused" not in out
    assert "landing finding(s)" not in out
