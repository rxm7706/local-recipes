"""Meta-test: ``ci_pause_drift_findings()`` in fleet_picture.py (Story 45.1)."""

from __future__ import annotations

import ast
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
CI_PAUSE_SOURCE = REPO_ROOT / "src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py"


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


def _source_dispatch_timeout() -> float:
    """The source's own dispatch bound, read from its file (no ``pyforge.doctor`` import in this lane)."""
    tree = ast.parse(CI_PAUSE_SOURCE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_DISPATCH_TIMEOUT" for target in node.targets
        ):
            return float(ast.literal_eval(node.value))
    raise AssertionError(f"_DISPATCH_TIMEOUT not found in {CI_PAUSE_SOURCE}")


def test_probe_timeout_outlasts_the_sources_dispatch_bound(monkeypatch):
    """Story 45.4 (DOC-M-D4): the probe main() calls waits longer than the source waits on steward, so a hung
    steward comes back as the source's ci-pause-unobserved WARN instead of the probe timing out first."""
    mod = _load_fleet_picture()
    seen: dict[str, float] = {}

    def _run(cmd, **kwargs):
        seen["timeout"] = kwargs["timeout"]
        return _FakeCompletedProcess("[]")

    monkeypatch.setattr(mod.subprocess, "run", _run)
    assert mod.ci_pause_drift_findings() == []
    assert seen["timeout"] > _source_dispatch_timeout()


def test_main_names_a_hung_steward_as_unobserved(monkeypatch, capsys, tmp_path):
    """Story 45.4 (AC4): the source's timeout WARN reaches ATTENTION as its own watch line."""
    mod = _load_fleet_picture()
    _stub_fleet_main_ambient(mod, monkeypatch, tmp_path)
    message = "could not read steward ci status --json (cause: timed out after 120s)"
    monkeypatch.setattr(
        mod,
        "ci_pause_drift_findings",
        lambda repo=mod.REPO, timeout=150: [{"check": "ci-pause-unobserved", "status": "warn", "message": message}],
    )
    mod.main()
    out = capsys.readouterr().out
    assert f"ci-pause-unobserved: {message}" in out
    assert "could not check CI pauses" not in out
