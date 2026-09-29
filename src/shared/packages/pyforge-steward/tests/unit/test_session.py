"""Story 63.4 — ``steward session check``: one verdict for session preconditions."""

from __future__ import annotations

import enum
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.session import (
    SessionDuty,
    SessionFinding,
    _active_project_slug,
    _bmad_method_finding,
    _gh_auth_finding,
    _pixi_guild_finding,
    _scribe_reachability_finding,
    _seed_kit_findings,
    _tier3_feed_finding,
    format_session_report,
    gather_session_findings,
)


@pytest.fixture
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "bmad-loop-worktree").is_file():
            return ancestor
    pytest.fail("could not locate local-recipes repo root from test file location")


# --------------------------------------------------------------------------
# Finding (1): pixi + pyforge-guild materialized
# --------------------------------------------------------------------------


def test_pixi_guild_finding_missing_pixi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: None)
    finding = _pixi_guild_finding(tmp_path)
    assert finding.name == "pixi-guild"
    assert finding.ok is False
    assert finding.remedy is not None
    assert "install-pixi" in finding.remedy


def test_pixi_guild_finding_env_not_materialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda name: f"/usr/bin/{name}")
    finding = _pixi_guild_finding(tmp_path)
    assert finding.ok is False
    assert finding.remedy == "pixi install --frozen -e pyforge-guild"


def test_pixi_guild_finding_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda name: f"/usr/bin/{name}")
    (tmp_path / ".pixi" / "envs" / "pyforge-guild").mkdir(parents=True)
    finding = _pixi_guild_finding(tmp_path)
    assert finding.ok is True
    assert finding.remedy is None


# --------------------------------------------------------------------------
# Finding (2): bmad-method drift verdict
# --------------------------------------------------------------------------


def test_bmad_method_finding_fallback_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``pyforge.doctor`` is not installed in the pyforge-steward test env, so this
    exercises the real AC4 fallback path (``upgrade.run_bmad_drift_integrity``)."""
    calls: dict[str, Path] = {}

    def fake_run_bmad_drift_integrity(repo: Path) -> types.SimpleNamespace:
        calls["repo"] = repo
        return types.SimpleNamespace(ok=True, detail="no HARD findings")

    monkeypatch.setattr("pyforge.steward.upgrade.run_bmad_drift_integrity", fake_run_bmad_drift_integrity)
    finding = _bmad_method_finding(tmp_path)
    assert finding.name == "bmad-method"
    assert finding.ok is True
    assert finding.remedy is None
    assert calls["repo"] == tmp_path


def test_bmad_method_finding_fallback_fail_names_remedy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pyforge.steward.upgrade.run_bmad_drift_integrity",
        lambda repo: types.SimpleNamespace(ok=False, detail="2 HARD finding(s)"),
    )
    finding = _bmad_method_finding(tmp_path)
    assert finding.ok is False
    assert finding.detail == "2 HARD finding(s)"
    assert finding.remedy == "pixi run -e pyforge-guild bmad-drift-check"


def test_bmad_method_finding_uses_doctor_verdict_when_importable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: when ``pyforge.doctor`` IS importable, its own verdict is used verbatim
    -- simulated here by injecting fake ``pyforge.doctor.*`` modules into
    ``sys.modules`` (the real package is not installed in this pixi env)."""

    class FakeDoctorStatus(enum.Enum):
        OK = "ok"
        WARN = "warn"
        FAIL = "fail"

    class FakeRow:
        def __init__(self, status: FakeDoctorStatus, check: str, message: str) -> None:
            self.status = status
            self.check = check
            self.message = message

    models_mod = types.ModuleType("pyforge.doctor.models")
    models_mod.DoctorStatus = FakeDoctorStatus  # type: ignore[attr-defined]
    sources_pkg = types.ModuleType("pyforge.doctor.sources")
    bmad_method_mod = types.ModuleType("pyforge.doctor.sources.bmad_method")
    doctor_pkg = types.ModuleType("pyforge.doctor")

    seen: dict[str, Path] = {}

    def fake_gather(root: Path) -> list[FakeRow]:
        seen["root"] = root
        return [FakeRow(FakeDoctorStatus.OK, "bmad-pin", "on target")]

    bmad_method_mod.gather = fake_gather  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "pyforge.doctor", doctor_pkg)
    monkeypatch.setitem(sys.modules, "pyforge.doctor.models", models_mod)
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources", sources_pkg)
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources.bmad_method", bmad_method_mod)

    finding = _bmad_method_finding(tmp_path)
    assert finding.ok is True
    assert seen["root"] == tmp_path
    assert "no FAIL findings" in finding.detail


def test_bmad_method_finding_matches_real_doctor_gather_when_importable(repo_root: Path) -> None:
    """Story 63.4 review finding (Intent Alignment (e)): AC3's other two
    tests inject fake ``pyforge.doctor.*`` modules into ``sys.modules``
    because the real package is absent from the ``pyforge-steward`` pixi
    env -- so the actual import branch (real ``pyforge.doctor`` on
    ``sys.path``) was never proven. Skips there; runs for real under
    ``-e pyforge-guild`` / ``-e local-recipes``, where both packages are
    installed, and asserts ``_bmad_method_finding``'s verdict matches the
    real ``gather`` call verbatim -- not a re-implementation of its logic.
    """
    pytest.importorskip("pyforge.doctor")
    from pyforge.doctor.models import DoctorStatus
    from pyforge.doctor.sources import bmad_method

    finding = _bmad_method_finding(repo_root)
    rows = bmad_method.gather(repo_root)
    fail_rows = [row for row in rows if row.status is DoctorStatus.FAIL]
    if fail_rows:
        assert finding.ok is False
        for row in fail_rows[:5]:
            assert row.check in finding.detail
        assert finding.remedy == "pixi run -e pyforge-guild bmad-drift-check"
    else:
        assert finding.ok is True
        assert "no FAIL findings" in finding.detail
        assert finding.remedy is None


def test_bmad_method_finding_doctor_fail_rows_surface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeDoctorStatus(enum.Enum):
        OK = "ok"
        FAIL = "fail"

    class FakeRow:
        def __init__(self, status: FakeDoctorStatus, check: str, message: str) -> None:
            self.status = status
            self.check = check
            self.message = message

    models_mod = types.ModuleType("pyforge.doctor.models")
    models_mod.DoctorStatus = FakeDoctorStatus  # type: ignore[attr-defined]
    sources_pkg = types.ModuleType("pyforge.doctor.sources")
    bmad_method_mod = types.ModuleType("pyforge.doctor.sources.bmad_method")
    bmad_method_mod.gather = lambda root: [  # type: ignore[attr-defined]
        FakeRow(FakeDoctorStatus.FAIL, "bmad-pin", "core is behind pinned version")
    ]
    doctor_pkg = types.ModuleType("pyforge.doctor")

    monkeypatch.setitem(sys.modules, "pyforge.doctor", doctor_pkg)
    monkeypatch.setitem(sys.modules, "pyforge.doctor.models", models_mod)
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources", sources_pkg)
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources.bmad_method", bmad_method_mod)

    finding = _bmad_method_finding(tmp_path)
    assert finding.ok is False
    assert "bmad-pin" in finding.detail
    assert finding.remedy == "pixi run -e pyforge-guild bmad-drift-check"


# --------------------------------------------------------------------------
# Findings (3) token-kit and (5) codegraph-index -- one `seed check --json` call
# --------------------------------------------------------------------------


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_seed_kit_findings_probe_could_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_oserror(_root: Path) -> subprocess.CompletedProcess[str]:
        raise OSError("no such file")

    monkeypatch.setattr("pyforge.steward.session._run_seed_check", raise_oserror)
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert codegraph_finding.ok is False
    assert "could not run" in kit_finding.detail
    assert kit_finding.remedy == "pixi run -e pyforge-guild marshal seed kit"


def test_seed_kit_findings_unparseable_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout="not json"))
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert codegraph_finding.ok is False
    assert "unparseable output" in kit_finding.detail


def test_seed_kit_findings_all_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "kit": [
            {"item": "caveman-skill", "layer": "output", "status": "ok"},
            {"item": "ccr-store", "layer": "wire", "status": "ok"},
            {"item": "codegraph-index", "layer": "structure-graph", "status": "ok", "detail": "fresh"},
        ]
    }
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=json.dumps(payload)))
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is True
    assert kit_finding.remedy is None
    assert codegraph_finding.ok is True
    assert codegraph_finding.detail == "fresh"


def test_seed_kit_findings_non_ok_item_fails_kit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "kit": [
            {"item": "caveman-skill", "layer": "output", "status": "missing"},
            {"item": "ccr-store", "layer": "wire", "status": "ok"},
            {"item": "codegraph-index", "layer": "structure-graph", "status": "ok"},
        ]
    }
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=json.dumps(payload)))
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert "caveman-skill: missing" in kit_finding.detail
    assert kit_finding.remedy == "pixi run -e pyforge-guild marshal seed kit"
    # codegraph-index item itself is ok -- independent of the other kit items
    assert codegraph_finding.ok is True


def test_seed_kit_findings_missing_codegraph_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"kit": [{"item": "caveman-skill", "layer": "output", "status": "ok"}]}
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=json.dumps(payload)))
    _kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert codegraph_finding.ok is False
    assert "no codegraph-index entry" in codegraph_finding.detail


def test_seed_kit_findings_codegraph_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "kit": [
            {"item": "codegraph-index", "layer": "structure-graph", "status": "stale", "detail": "6 days old"},
        ]
    }
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=json.dumps(payload)))
    _kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert codegraph_finding.ok is False
    assert "stale" in codegraph_finding.detail
    assert codegraph_finding.remedy == "pixi run -e pyforge-guild marshal seed kit"


# --------------------------------------------------------------------------
# Finding (4): gh auth + rate limit -- must NEVER fail open
# --------------------------------------------------------------------------


def test_gh_auth_finding_gh_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: None)
    finding = _gh_auth_finding()
    assert finding.ok is False
    assert finding.remedy is not None


def test_gh_auth_finding_launch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: "/usr/bin/gh")

    def raise_oserror(*_args: object, **_kwargs: object) -> None:
        raise OSError("boom")

    monkeypatch.setattr("pyforge.steward.session.subprocess.run", raise_oserror)
    finding = _gh_auth_finding()
    assert finding.ok is False
    assert finding.remedy == "gh auth login"


def test_gh_auth_finding_unauthenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: "/usr/bin/gh")
    monkeypatch.setattr(
        "pyforge.steward.session.subprocess.run",
        lambda argv, **_kw: _completed(returncode=1, stderr="not logged in"),
    )
    finding = _gh_auth_finding()
    assert finding.ok is False
    assert finding.remedy == "gh auth login"


def test_gh_auth_finding_rate_limit_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: "/usr/bin/gh")

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        if "auth" in argv:
            return _completed(returncode=0)
        return _completed(returncode=1, stderr="network error")

    monkeypatch.setattr("pyforge.steward.session.subprocess.run", fake_run)
    finding = _gh_auth_finding()
    assert finding.ok is False


def test_gh_auth_finding_rate_limit_unparseable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: "/usr/bin/gh")

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        if "auth" in argv:
            return _completed(returncode=0)
        return _completed(returncode=0, stdout="not json")

    monkeypatch.setattr("pyforge.steward.session.subprocess.run", fake_run)
    finding = _gh_auth_finding()
    assert finding.ok is False
    assert "unparseable" in finding.detail


def test_gh_auth_finding_exhausted_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: "/usr/bin/gh")

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        if "auth" in argv:
            return _completed(returncode=0)
        return _completed(returncode=0, stdout=json.dumps({"resources": {"core": {"remaining": 0}}}))

    monkeypatch.setattr("pyforge.steward.session.subprocess.run", fake_run)
    finding = _gh_auth_finding()
    assert finding.ok is False
    assert "exhausted" in finding.detail


def test_gh_auth_finding_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: "/usr/bin/gh")

    def fake_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        if "auth" in argv:
            return _completed(returncode=0)
        return _completed(returncode=0, stdout=json.dumps({"resources": {"core": {"remaining": 4999}}}))

    monkeypatch.setattr("pyforge.steward.session.subprocess.run", fake_run)
    finding = _gh_auth_finding()
    assert finding.ok is True
    assert finding.remedy is None
    assert "4999" in finding.detail


# --------------------------------------------------------------------------
# Finding (6): Tier-3 sprint-status feed for the active project
# --------------------------------------------------------------------------


def test_active_project_slug_prefers_flag_over_env_and_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "env-slug")
    marker = tmp_path / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True)
    marker.write_text("marker-slug\n", encoding="utf-8")
    assert _active_project_slug(project="flag-slug", root=tmp_path) == "flag-slug"


def test_active_project_slug_env_beats_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "env-slug")
    marker = tmp_path / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True)
    marker.write_text("marker-slug\n", encoding="utf-8")
    assert _active_project_slug(project=None, root=tmp_path) == "env-slug"


def test_active_project_slug_falls_back_to_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    marker = tmp_path / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True)
    marker.write_text("marker-slug\n", encoding="utf-8")
    assert _active_project_slug(project=None, root=tmp_path) == "marker-slug"


def test_active_project_slug_none_when_nothing_resolves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    assert _active_project_slug(project=None, root=tmp_path) is None


def test_tier3_feed_finding_no_active_project_is_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    finding = _tier3_feed_finding(root=tmp_path, project=None)
    assert finding.ok is True
    assert finding.remedy is None


def test_tier3_feed_finding_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    feed = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-steward" / "implementation-artifacts" / "sprint-status.yaml"
    )
    feed.parent.mkdir(parents=True)
    feed.write_text("stories: []\n", encoding="utf-8")
    finding = _tier3_feed_finding(root=tmp_path, project="pyforge-steward")
    assert finding.ok is True


def test_tier3_feed_finding_absent_names_exact_remedy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    finding = _tier3_feed_finding(root=tmp_path, project="pyforge-steward")
    assert finding.ok is False
    assert finding.remedy == (
        "cp planning-artifacts/sprint-status-ledger.yaml implementation-artifacts/sprint-status.yaml"
    )


# --------------------------------------------------------------------------
# Finding (7): scribe recall reachability -- report-only, never gates the exit code
# --------------------------------------------------------------------------


def test_scribe_reachability_finding_always_ok_on_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: "/usr/bin/scribe")
    finding = _scribe_reachability_finding(tmp_path)
    assert finding.ok is True


def test_scribe_reachability_finding_always_ok_via_guild_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: None)
    (tmp_path / ".pixi" / "envs" / "pyforge-guild").mkdir(parents=True)
    finding = _scribe_reachability_finding(tmp_path)
    assert finding.ok is True


def test_scribe_reachability_finding_always_ok_even_when_unreachable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC8: this finding NEVER flips the exit code -- ``ok`` stays True in every branch."""
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: None)
    finding = _scribe_reachability_finding(tmp_path)
    assert finding.ok is True
    assert finding.remedy is not None


# --------------------------------------------------------------------------
# Composition + report formatting
# --------------------------------------------------------------------------


def test_gather_session_findings_returns_all_seven_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.session.shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check",
        lambda _root: (_ for _ in ()).throw(OSError("no seed check")),
    )
    monkeypatch.setattr(
        "pyforge.steward.upgrade.run_bmad_drift_integrity",
        lambda repo: types.SimpleNamespace(ok=True, detail="ok"),
    )
    findings = gather_session_findings(root=tmp_path)
    assert [f.name for f in findings] == [
        "pixi-guild",
        "bmad-method",
        "token-kit",
        "gh-auth",
        "codegraph-index",
        "tier3-feed",
        "scribe-recall",
    ]


def test_format_session_report_text_includes_remedy_for_failures() -> None:
    findings = (
        SessionFinding(name="a", ok=True, detail="fine"),
        SessionFinding(name="b", ok=False, detail="broken", remedy="fix it"),
    )
    text = format_session_report(findings, as_json=False)
    assert "steward session check: FAIL" in text
    assert "FAIL b: broken" in text
    assert "remedy: fix it" in text


def test_format_session_report_text_all_ok() -> None:
    findings = (SessionFinding(name="a", ok=True, detail="fine"),)
    text = format_session_report(findings, as_json=False)
    assert "steward session check: PASS" in text


def test_format_session_report_json_shape() -> None:
    findings = (
        SessionFinding(name="a", ok=True, detail="fine"),
        SessionFinding(name="b", ok=False, detail="broken", remedy="fix it"),
    )
    payload = json.loads(format_session_report(findings, as_json=True))
    assert payload["ok"] is False
    assert len(payload["findings"]) == 2
    assert payload["findings"][1] == {"name": "b", "ok": False, "detail": "broken", "remedy": "fix it"}


# --------------------------------------------------------------------------
# SessionDuty + CLI exit codes
# --------------------------------------------------------------------------


def test_session_duty_rejects_missing_verb() -> None:
    import argparse

    duty = SessionDuty()
    result = duty.run(argparse.Namespace(session_verb=None))
    assert result.ok is False
    assert "check" in result.summary


def test_session_duty_check_all_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import argparse

    monkeypatch.setattr(
        "pyforge.steward.session.gather_session_findings",
        lambda *, root, project=None: (SessionFinding(name="a", ok=True, detail="fine"),),
    )
    duty = SessionDuty()
    ns = argparse.Namespace(session_verb="check", repo=str(tmp_path), project=None, json=False)
    result = duty.run(ns)
    assert result.ok is True
    assert result.details["findings"] == [{"name": "a", "ok": True, "detail": "fine", "remedy": None}]


def test_session_duty_check_reports_not_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import argparse

    monkeypatch.setattr(
        "pyforge.steward.session.gather_session_findings",
        lambda *, root, project=None: (SessionFinding(name="a", ok=False, detail="broken", remedy="fix"),),
    )
    duty = SessionDuty()
    ns = argparse.Namespace(session_verb="check", repo=str(tmp_path), project=None, json=True)
    result = duty.run(ns)
    assert result.ok is False
    payload = json.loads(result.summary)
    assert payload["ok"] is False


def test_cli_session_check_exit_ok(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "pyforge.steward.session.gather_session_findings",
        lambda *, root, project=None: (SessionFinding(name="a", ok=True, detail="fine"),),
    )
    assert main(["session", "check"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "steward session check: PASS" in out


def test_cli_session_check_exit_failed(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "pyforge.steward.session.gather_session_findings",
        lambda *, root, project=None: (SessionFinding(name="a", ok=False, detail="broken", remedy="fix"),),
    )
    assert main(["session", "check"]) == EXIT_FAILED
    err = capsys.readouterr().err
    assert "steward session check: FAIL" in err


def test_cli_session_check_accepts_project_and_json_flags(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(repo_root)
    seen: dict[str, object] = {}

    def fake_gather(*, root: Path, project: str | None = None) -> tuple[SessionFinding, ...]:
        seen["root"] = root
        seen["project"] = project
        return (SessionFinding(name="a", ok=True, detail="fine"),)

    monkeypatch.setattr("pyforge.steward.session.gather_session_findings", fake_gather)
    assert main(["session", "check", "--project", "pyforge-steward", "--json"]) == EXIT_OK
    assert seen["project"] == "pyforge-steward"
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["ok"] is True
