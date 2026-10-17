"""Meta-test: ``pages_liveness_findings()`` in fleet_picture.py (doctor Story 48.2, CAP-91)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

# pyforge-ci is stdlib-only (steward Story 103.3; the definition is the comment above `pyforge-ci` in
# pixi.toml), so this file skips there and runs in scripts-lib-test, in pyforge-guild.
pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"

_STALE = {
    "source": "pages-liveness",
    "check": "pages-liveness-stale",
    "status": "warn",
    # The source's own shape (doctor 48.2 review): the lag and both dates first, the URL last.
    "message": (
        "Pages deploy more than 65 hours behind: last-modified 2026-10-06T03:12:00Z, inputs "
        "2026-10-08T15:30:00-05:00 (published-input commit d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708 on "
        "origin/main), https://rxm7706.github.io/local-recipes/"
    ),
    "evidence": {"lag_hours": 65},
}
_UNAVAILABLE = {
    "source": "pages-liveness",
    "check": "pages-liveness-unavailable",
    "status": "warn",
    "message": "Pages liveness could not be read: HEAD https://rxm7706.github.io/local-recipes/: URLError: offline",
    "evidence": {"unevaluable": True},
}
_OK = {
    "source": "pages-liveness",
    "check": "pages-liveness",
    "status": "ok",
    "message": "Pages deploy current",
    "evidence": {},
}


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_pages_liveness_under_test", FLEET_PICTURE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_pages_liveness_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _fake_run(findings: list[dict], seen: dict):
    def _run(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(findings), stderr="")

    return _run


def test_the_probe_runs_the_dispatcher_with_the_ci_pause_discipline(monkeypatch):
    mod = _load_fleet_picture()
    seen: dict = {}
    monkeypatch.setattr(mod.subprocess, "run", _fake_run([_STALE], seen))
    assert mod.pages_liveness_findings() == [_STALE]
    assert seen["cmd"] == [sys.executable, "-m", "pyforge.doctor.sources", "pages-liveness", "--json"]
    assert seen["kwargs"]["timeout"] == 60
    assert seen["kwargs"]["check"] is True
    assert seen["kwargs"]["cwd"] == mod.REPO


def test_ok_findings_are_filtered_out(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(mod.subprocess, "run", _fake_run([_OK], {}))
    assert mod.pages_liveness_findings() == []


def test_subprocess_failure_raises(monkeypatch):
    mod = _load_fleet_picture()

    def _boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(2, cmd)

    monkeypatch.setattr(mod.subprocess, "run", _boom)
    with pytest.raises(subprocess.CalledProcessError):
        mod.pages_liveness_findings()


def _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path):
    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir()
    monkeypatch.setattr(fleet, "REPO", empty_repo)
    monkeypatch.setattr(fleet, "running_stations", lambda: (set(), {}))
    monkeypatch.setattr(fleet, "loop_home_staleness", lambda: [])
    monkeypatch.setattr(fleet, "bmad_core_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "verification_staleness_findings", lambda: [])
    monkeypatch.setattr(fleet, "dream_chain_gap_findings", lambda: [])
    monkeypatch.setattr(fleet, "ci_pause_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "sibling_dreams_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "capability_effect_findings", lambda: [])
    monkeypatch.setattr(fleet, "status_body_consistency_findings", lambda: [])
    monkeypatch.setattr(fleet, "baseline_drift_findings", lambda: [])
    monkeypatch.setattr(
        fleet.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )


def test_main_prints_one_watch_line_per_warn(monkeypatch, capsys, tmp_path):
    mod = _load_fleet_picture()
    _stub_fleet_main_ambient(mod, monkeypatch, tmp_path)
    monkeypatch.setattr(mod, "pages_liveness_findings", lambda: [_STALE, _UNAVAILABLE])
    mod.main()
    out = capsys.readouterr().out
    lines = [line.strip() for line in out.splitlines() if "pages-liveness" in line]
    assert lines == [
        f"- pages-liveness-stale: {_STALE['message'][:110]}",
        f"- pages-liveness-unavailable: {_UNAVAILABLE['message'][:110]}",
    ]
    assert "could not check Pages liveness" not in out
    # The 110-character cut keeps the evidence: the lag and both dates.
    stale_line = lines[0]
    for evidence in ("more than 65 hours", "2026-10-06T03:12:00Z", "2026-10-08T15:30:00-05:00"):
        assert evidence in stale_line


def test_main_prints_no_pages_line_when_the_site_is_current(monkeypatch, capsys, tmp_path):
    mod = _load_fleet_picture()
    _stub_fleet_main_ambient(mod, monkeypatch, tmp_path)
    monkeypatch.setattr(mod, "pages_liveness_findings", lambda: [])
    mod.main()
    out = capsys.readouterr().out
    assert "pages-liveness" not in out
    assert "Pages liveness" not in out


def test_main_degrades_when_the_probe_raises(monkeypatch, capsys, tmp_path):
    mod = _load_fleet_picture()
    _stub_fleet_main_ambient(mod, monkeypatch, tmp_path)

    def _boom(**kwargs):
        raise RuntimeError("probe failed")

    monkeypatch.setattr(mod, "pages_liveness_findings", _boom)
    mod.main()
    out = capsys.readouterr().out
    assert "could not check Pages liveness" in out
