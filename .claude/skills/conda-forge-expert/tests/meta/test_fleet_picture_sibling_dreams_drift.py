"""Meta-test: `sibling_dreams_drift_findings()` in fleet_picture.py (Story 16.1)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_sibling_under_test", FLEET_PICTURE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_sibling_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeCompletedProcess:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.returncode = 0


def _fake_run(findings: list[dict]):
    def _run(cmd, **kwargs):
        assert cmd[0] == sys.executable
        assert cmd[1:4] == ["-m", "pyforge.doctor.sources", "sibling-dreams-drift"]
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
                    "source": "sibling-dreams-drift",
                    "check": "sibling-dreams-drift",
                    "status": "warn",
                    "message": "sibling dream 'X' diverges on owner",
                    "evidence": {},
                },
            ]
        ),
    )
    result = mod.sibling_dreams_drift_findings()
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
                    "source": "sibling-dreams-drift",
                    "check": "sibling-dreams-drift",
                    "status": "ok",
                    "message": "quiet",
                    "evidence": {},
                },
            ]
        ),
    )
    assert mod.sibling_dreams_drift_findings() == []


def test_subprocess_failure_raises(monkeypatch):
    mod = _load_fleet_picture()

    def _boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(2, cmd)

    monkeypatch.setattr(mod.subprocess, "run", _boom)
    with pytest.raises(subprocess.CalledProcessError):
        mod.sibling_dreams_drift_findings()
