"""Story 53.2 review (I1): main()'s ATTENTION-block landing-findings rendering.

``execute_dispatch_land``'s envelope findings (MRS-DISP-047 warn / MRS-DISP-048
error) must reach ``fleet-picture``'s ATTENTION block, not just the journal --
same isolation pattern as ``test_fleet_picture_attention_dispatch_refused.py``.
"""

from __future__ import annotations

import importlib.util
import json
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


_DEFAULT_LEDGER = "development_status:\n  epic-53: backlog\n  53-2-x: backlog\n"


def _seed_marshal_ledger(repo: Path, ledger: str = _DEFAULT_LEDGER) -> None:
    ledger_dir = repo / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "sprint-status-ledger.yaml").write_text(ledger, encoding="utf-8")


def _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path: Path, ledger: str = _DEFAULT_LEDGER) -> None:
    """Isolate main() from live ledgers / marshal / doctor / gh probes."""
    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir()
    _seed_marshal_ledger(empty_repo, ledger)
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
        "landing_superseded": False,
        "landing_story": "",
        "awaiting_operator_remedy": None,
        "missing_spec_escalation_glob": None,
        "dispatch_stranded_work": None,
    }
    row.update(overrides)
    return row


def _run_main_with_live(fleet, monkeypatch, tmp_path: Path, live_row: dict, ledger: str = _DEFAULT_LEDGER):
    _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path, ledger)
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


_REFUSED_1597 = [{"code": "MRS-DISP-020", "severity": "error", "message": "merge of PR #1597 failed"}]
_FINALIZE_FAILED = [
    {
        "code": "MRS-DISP-020",
        "severity": "error",
        "message": "dispatch land finalize (promote + ledger) failed for 46.6: exit 1",
    }
]
_LEDGER_46_6_DONE = "development_status:\n  epic-46: in-progress\n  46-6-a-persistence-advisory: done\n"
_LEDGER_46_6_BACKLOG = "development_status:\n  epic-46: in-progress\n  46-6-a-persistence-advisory: backlog\n"


def test_main_lists_a_refusal_landed_since_and_done_as_not_waiting_on_you(fleet, monkeypatch, capsys, tmp_path):
    """Story 56.1 (CAP-266): a refusal whose story is on `main` (marshal
    status's `dispatch_landing_superseded`) AND reads `done` in the tracked
    ledger is history, not a decision owed -- the not-blocking list names
    the dispatch run's own story, and the `>>` block has no line for it."""
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(landing_story="46.6", landing_findings=_REFUSED_1597, landing_superseded=True),
        ledger=_LEDGER_46_6_DONE,
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert ">> marshal: landing refused" not in out
    assert (
        "   - marshal: landing refused (1 finding(s)) -- MRS-DISP-020 -- but 46.6 has since landed on main "
        "and reads done, not waiting on you"
    ) in out


def test_main_keeps_a_post_merge_finalize_failure_in_attention(fleet, monkeypatch, capsys, tmp_path):
    """Review 1 (high): a finalize (promote + ledger) that failed AFTER the
    merge journals the same MRS-DISP-020 and the story is on `main` -- but
    its ledger key is not `done`, so the promotion is still owed."""
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(landing_story="46.6", landing_findings=_FINALIZE_FAILED, landing_superseded=True),
        ledger=_LEDGER_46_6_BACKLOG,
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert (
        "  >> marshal: landing refused (1 finding(s)) -- MRS-DISP-020 -- 46.6 is on main but its ledger key "
        "is not done: finish the promote + ledger"
    ) in out
    assert "not waiting on you" not in out


def test_the_landing_line_names_the_dispatch_story_not_current_story(fleet, monkeypatch, capsys, tmp_path):
    """Review 1 (medium): `current_story` is the loop home's story unless the
    dispatch run is live or a dead tail -- a `completed` run keeps an
    unrelated one. The line names the run's own story (`dispatch_story`)."""
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(
            state="idle",
            story="47.1",
            dispatch_completion_verdict="completed",
            landing_story="46.6",
            landing_findings=_REFUSED_1597,
            landing_superseded=True,
        ),
        ledger=_LEDGER_46_6_DONE,
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "but 46.6 has since landed on main" in out
    assert "47.1 has since landed" not in out


def test_main_keeps_an_unsuperseded_refusal_in_attention(fleet, monkeypatch, capsys, tmp_path):
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(landing_story="46.6", landing_findings=_REFUSED_1597, landing_superseded=False),
        ledger=_LEDGER_46_6_DONE,
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "  >> marshal: landing refused (1 finding(s)) -- MRS-DISP-020\n" in out
    assert "has since landed on main" not in out


def test_running_stations_maps_the_marker_and_the_dispatch_story(fleet, monkeypatch):
    """The live-row mapping trusts only a literal `true` from marshal
    status -- an absent key, or any other value, is not superseded -- and
    takes the landing's story from `dispatch_story`, never `current_story`."""
    rows = [
        {
            "slug": "pyforge-doctor",
            "state": "stopped",
            "current_story": "30.3",
            "dispatch_story": "30.3",
            "dispatch_landing_superseded": True,
        },
        {"slug": "pyforge-marshal", "state": "idle", "current_story": "47.1", "dispatch_story": "46.6"},
        {"slug": "pyforge-herald", "state": "stopped", "dispatch_landing_superseded": "yes"},
    ]
    stdout = json.dumps({"data": {"homes": rows}})
    monkeypatch.setattr(
        fleet.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr=""),
    )
    _running, info = fleet.running_stations()
    assert info["doctor"]["landing_superseded"] is True
    assert info["marshal"]["landing_superseded"] is False
    assert info["herald"]["landing_superseded"] is False
    assert info["marshal"]["landing_story"] == "46.6"
    assert info["herald"]["landing_story"] == ""
