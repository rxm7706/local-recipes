"""Meta-test: ``ci_pause_drift_findings()`` in fleet_picture.py (Story 45.1)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_ci_pause_under_test", FLEET_PICTURE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_ci_pause_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeCompletedProcess:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.returncode = 0


def _fake_run(findings: list[dict]):
    def _run(cmd, **kwargs):
        assert cmd[0] == sys.executable
        assert cmd[1:4] == ["-m", "pyforge.doctor.sources", "ci-pause-drift"]
        assert "--json" in cmd
        return _FakeCompletedProcess(json.dumps(findings))

    return _run


def test_a_real_warn_finding_is_returned(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        _fake_run(
            [
                {
                    "source": "ci-pause-drift",
                    "check": "ci-pause-stuck",
                    "status": "warn",
                    "message": "CI surface 'dashboard.deploy' stuck",
                    "evidence": {},
                },
            ]
        ),
    )
    result = mod.ci_pause_drift_findings()
    assert len(result) == 1
    assert result[0]["status"] == "warn"


def test_ok_findings_are_filtered_out(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        _fake_run(
            [
                {
                    "source": "ci-pause-drift",
                    "check": "ci-pause-drift",
                    "status": "ok",
                    "message": "judged 3 CI surface row(s)",
                    "evidence": {},
                },
            ]
        ),
    )
    assert mod.ci_pause_drift_findings() == []


def test_subprocess_failure_raises(monkeypatch):
    mod = _load_fleet_picture()

    def _boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(2, cmd)

    monkeypatch.setattr(mod.subprocess, "run", _boom)
    with pytest.raises(subprocess.CalledProcessError):
        mod.ci_pause_drift_findings()


def _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path):
    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir()
    monkeypatch.setattr(fleet, "REPO", empty_repo)
    monkeypatch.setattr(fleet, "running_stations", lambda: (set(), {}))
    monkeypatch.setattr(fleet, "loop_home_staleness", lambda: [])
    monkeypatch.setattr(fleet, "bmad_core_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "verification_staleness_findings", lambda: [])
    monkeypatch.setattr(fleet, "dream_chain_gap_findings", lambda: [])
    monkeypatch.setattr(fleet, "sibling_dreams_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "capability_effect_findings", lambda: [])
    monkeypatch.setattr(fleet, "status_body_consistency_findings", lambda: [])
    monkeypatch.setattr(fleet, "baseline_drift_findings", lambda: [])
    monkeypatch.setattr(
        fleet.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )


def test_main_appends_watch_line_for_warn(monkeypatch, capsys, tmp_path):
    mod = _load_fleet_picture()
    _stub_fleet_main_ambient(mod, monkeypatch, tmp_path)
    monkeypatch.setattr(
        mod,
        "ci_pause_drift_findings",
        lambda repo=mod.REPO, timeout=120: [
            {"check": "ci-pause-overdue", "status": "warn", "message": "CI surface overdue line"},
        ],
    )
    mod.main()
    out = capsys.readouterr().out
    assert "ci-pause-overdue: CI surface overdue line" in out


def test_main_degrades_when_probe_raises(monkeypatch, capsys, tmp_path):
    mod = _load_fleet_picture()
    _stub_fleet_main_ambient(mod, monkeypatch, tmp_path)

    def _boom(**kwargs):
        raise RuntimeError("probe failed")

    monkeypatch.setattr(mod, "ci_pause_drift_findings", _boom)
    mod.main()
    out = capsys.readouterr().out
    assert "could not check CI pauses" in out
