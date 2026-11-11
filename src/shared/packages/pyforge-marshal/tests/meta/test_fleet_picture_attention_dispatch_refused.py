"""Story 34.4: main()'s ATTENTION-block refused-verdict scoping.

Mirrors ``test_not_stuck_when_refused_verdict_is_stale_and_a_different_engine_is_running``
in ``test_fleet_picture_dispatch_phase.py`` (the ``station_state()`` sibling) but drives
``main()``'s ATTENTION ``needs.append`` branch via a mocked ``running_stations()`` —
same isolation pattern as ``tests/scripts/test_fleet_picture_baseline_drift_attention.py``.
"""

from __future__ import annotations

import importlib.util
import subprocess
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


_STORY = "34-4-attention-dispatch-refused-coverage"
_GATE = "MRS-GATE-007"
_REFUSED_LINE = "dispatch verify REFUSED"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_attention_dispatch_refused_test", _fleet_picture_path()
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_attention_dispatch_refused_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _seed_marshal_ledger(repo: Path) -> None:
    ledger_dir = repo / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "sprint-status-ledger.yaml").write_text(
        "development_status:\n  epic-34: backlog\n  34-4-x: backlog\n",
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
        "dispatch_verification_verdict": "refused",
        "dispatch_verification_failed_gate": _GATE,
        "escalation_reason": None,
        "escalation_artifact": None,
        "scope_advisories": [],
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


def test_main_attention_names_genuine_dispatch_refused(fleet, monkeypatch, capsys, tmp_path):
    """Live dispatch run with ``dispatch_phase`` set → ATTENTION ``needs`` line."""
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(dispatch_phase="building"),
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "ATTENTION:" in out
    assert _REFUSED_LINE in out
    assert _GATE in out
    assert _STORY in out
    assert f">> marshal: {_REFUSED_LINE} ({_GATE}) on {_STORY}" in out


def test_main_attention_silent_when_refused_verdict_is_stale(fleet, monkeypatch, capsys, tmp_path):
    """Spin session live (``dispatch_phase=None``) must not ATTENTION off stale refused."""
    rc = _run_main_with_live(
        fleet,
        monkeypatch,
        tmp_path,
        _marshal_live_row(dispatch_phase=None),
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "ATTENTION:" in out
    assert _REFUSED_LINE not in out
    assert "none of the stations is waiting on you" in out
