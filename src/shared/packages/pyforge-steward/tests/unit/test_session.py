"""Story 63.4 — ``steward session check``: one verdict for session preconditions."""

from __future__ import annotations

import enum
import json
import shutil
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


def _hide_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``pyforge.doctor`` unimportable for one test, whatever env runs it. The
    fallback tests assumed the ``pyforge-steward`` env (no doctor) and failed under
    ``-e pyforge-guild``, where doctor is installed (found by Story 79.1). Every
    submodule is masked too: a cached ``pyforge.doctor.models`` would import without
    its parent."""
    for name in (
        "pyforge.doctor",
        "pyforge.doctor.models",
        "pyforge.doctor.sources",
        "pyforge.doctor.sources.bmad_method",
    ):
        monkeypatch.setitem(sys.modules, name, None)


def test_bmad_method_finding_fallback_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With ``pyforge.doctor`` unimportable, the real AC4 fallback path
    (``upgrade.run_bmad_drift_integrity``) runs."""
    _hide_doctor(monkeypatch)
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
    _hide_doctor(monkeypatch)
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


def _seed_envelope(kit: list[dict[str, str]]) -> str:
    """``marshal seed check --json``'s real stdout: the schema-stable ``{verb, ok, result}``
    envelope every seed verb shares (marshal ``cli/seed.py::_json_ok_envelope``, Story 12.5),
    with ``kit`` under ``result``. Story 73.1 (CAP-162): these fakes used a bare ``{"kit": ...}``
    that marshal never emits, so the tests passed while every real run read as unparseable."""
    return json.dumps({"verb": "check", "ok": True, "result": {"strict": False, "findings": [], "kit": kit}})


#: One ``marshal seed check --json`` document recorded from the live CLI (Story 73.1): exit 1
#: (its own report is failing), the kit under ``result``, no absolute paths.
_RECORDED_ENVELOPE = Path(__file__).resolve().parent.parent / "fixtures" / "marshal_seed_check_envelope.json"


def test_seed_kit_findings_read_the_recorded_live_document(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """73.1 AC1: the recorded document, returned with exit 1, names every non-ok kit item
    with its status; nothing reads "unparseable"."""
    text = _RECORDED_ENVELOPE.read_text(encoding="utf-8")
    kit = json.loads(text)["result"]["kit"]
    non_ok = [f"{entry['item']}: {entry['status']}" for entry in kit if entry["status"] != "ok"]
    codegraph = next(entry for entry in kit if entry["item"] == "codegraph-index")
    assert non_ok, "the recorded document must carry a non-ok kit to prove this path"
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=text, returncode=1))
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert kit_finding.detail == "; ".join(non_ok)
    assert codegraph_finding.ok is (codegraph["status"] == "ok")
    assert codegraph["status"] in codegraph_finding.detail
    assert "unparseable" not in kit_finding.detail + codegraph_finding.detail


@pytest.mark.parametrize("returncode", [0, 1])
def test_seed_kit_findings_an_all_ok_kit_is_ok_whatever_the_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, returncode: int
) -> None:
    """73.1 AC2: the seed check exits 1 whenever its own report fails; the exit code is
    never the kit's verdict."""
    document = json.loads(_RECORDED_ENVELOPE.read_text(encoding="utf-8"))
    for entry in document["result"]["kit"]:
        entry["status"] = "ok"
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check",
        lambda _root: _completed(stdout=json.dumps(document), returncode=returncode),
    )
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is True
    assert codegraph_finding.ok is True


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
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=_seed_envelope(payload["kit"]))
    )
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
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=_seed_envelope(payload["kit"]))
    )
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert "caveman-skill: missing" in kit_finding.detail
    assert kit_finding.remedy == "pixi run -e pyforge-guild marshal seed kit"
    # codegraph-index item itself is ok -- independent of the other kit items
    assert codegraph_finding.ok is True


def test_seed_kit_findings_missing_codegraph_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"kit": [{"item": "caveman-skill", "layer": "output", "status": "ok"}]}
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=_seed_envelope(payload["kit"]))
    )
    _kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert codegraph_finding.ok is False
    assert "no codegraph-index entry" in codegraph_finding.detail


def test_seed_kit_findings_codegraph_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "kit": [
            {"item": "codegraph-index", "layer": "structure-graph", "status": "stale", "detail": "6 days old"},
        ]
    }
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=_seed_envelope(payload["kit"]))
    )
    _kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert codegraph_finding.ok is False
    assert "stale" in codegraph_finding.detail
    assert codegraph_finding.remedy == "pixi run -e pyforge-guild marshal seed kit"


def test_seed_kit_findings_layer_off_and_stale_name_the_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 73.1: the kit this repo's primary checkout reports today -- the wire layer
    declared off, the codegraph index stale -- surfaces both as non-ok, named (AC5)."""
    kit = [
        {"item": "caveman-skill", "layer": "output", "status": "ok"},
        {"item": "ccr-store", "layer": "wire", "status": "layer-off"},
        {"item": "codegraph-index", "layer": "structure-graph", "status": "stale", "detail": "predates HEAD"},
    ]
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=_seed_envelope(kit), returncode=1)
    )
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert "ccr-store: layer-off" in kit_finding.detail
    assert "codegraph-index: stale" in kit_finding.detail
    assert "caveman-skill" not in kit_finding.detail
    assert codegraph_finding.ok is False
    assert codegraph_finding.detail == "codegraph-index: stale -- predates HEAD"


def test_seed_kit_findings_error_envelope_reports_its_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """73.1 AC3: an ``ok: false`` envelope names the seed error's type and message."""
    payload = {
        "verb": "check",
        "ok": False,
        "error": {"type": "ManifestError", "message": "bad manifest", "remedy": "reinstall marshal"},
    }
    monkeypatch.setattr(
        "pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=json.dumps(payload), returncode=1)
    )
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert codegraph_finding.ok is False
    assert "reported a seed error: ManifestError: bad manifest" in kit_finding.detail
    assert kit_finding.detail == codegraph_finding.detail
    assert kit_finding.remedy == "pixi run -e pyforge-guild marshal seed kit"


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        (json.dumps({"kit": [{"item": "codegraph-index", "status": "ok"}]}), "no kit report (keys found: kit)"),
        (
            json.dumps({"verb": "check", "ok": True, "result": {}}),
            "no kit report (keys found: ok, result, verb; result keys: none)",
        ),
        (json.dumps({"verb": "check", "ok": True, "result": {"kit": "not a list"}}), "no kit report"),
        (json.dumps(["not", "an", "object"]), "no kit report: the document is a JSON list"),
        (json.dumps({"verb": "check", "ok": False}), "reported a seed error with no detail"),
        (json.dumps({"verb": "check", "ok": True, "result": {"kit": ["x"]}}), "returned a malformed kit entry"),
    ],
)
def test_seed_kit_findings_payload_without_an_envelope_kit_is_non_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdout: str, expected: str
) -> None:
    """73.1 AC5: a JSON document with no ``result.kit`` reads "no kit report", naming the
    keys it found -- never "unparseable". A bare top-level ``kit`` (the shape the pre-73.1
    fakes used) is not marshal's output and is not read as if it were."""
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: _completed(stdout=stdout))
    kit_finding, codegraph_finding = _seed_kit_findings(tmp_path)
    assert kit_finding.ok is False
    assert codegraph_finding.ok is False
    assert expected in kit_finding.detail
    assert "unparseable" not in kit_finding.detail


def test_seed_kit_findings_parse_the_real_marshal_seed_check(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stories 73.1 / 79.1: the halves of CAP-5 drifted because each side's tests faked
    the other's output. Where the ``marshal`` CLI is installed (``-e pyforge-guild``), run
    the real ``marshal seed check --json`` against this repo and parse its stdout;
    skips in ``-e pyforge-steward``, which has no marshal. Calls the CLI, never
    imports ``pyforge.marshal``."""
    marshal = shutil.which("marshal")
    if marshal is None:
        pytest.skip("the marshal CLI is not installed in this environment")
    real = subprocess.run(
        [marshal, "seed", "check", "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    monkeypatch.setattr("pyforge.steward.session._run_seed_check", lambda _root: real)
    kit_finding, codegraph_finding = _seed_kit_findings(repo_root)
    for finding in (kit_finding, codegraph_finding):
        assert "unparseable" not in finding.detail, finding.detail
        assert "no kit report" not in finding.detail, finding.detail
        assert "seed error" not in finding.detail, finding.detail
    assert "no codegraph-index entry" not in codegraph_finding.detail
    # the detail names real kit items, whichever of them are ok today
    assert any(item in kit_finding.detail for item in ("caveman-skill", "ccr-store", "codegraph-index"))


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


def test_cli_session_check_json_failure_report_goes_to_stderr(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 79.1: pins the stream marshal's dispatch preamble reads. A failed duty's
    report goes to stderr (``cli.py::main``), so a non-ok ``--json`` verdict is a JSON
    object on stderr with nothing on stdout."""
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "pyforge.steward.session.gather_session_findings",
        lambda *, root, project=None: (SessionFinding(name="gh-auth", ok=False, detail="0 calls left", remedy="wait"),),
    )
    assert main(["session", "check", "--json"]) == EXIT_FAILED
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["ok"] is False
    assert [f["name"] for f in payload["findings"] if not f["ok"]] == ["gh-auth"]
