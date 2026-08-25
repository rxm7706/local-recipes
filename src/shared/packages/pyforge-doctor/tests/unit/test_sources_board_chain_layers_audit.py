"""Unit tests for ``board.gather_chain_layers_audit`` (Story 17.3 /
FR-150 residual + FR-152).

Seeds layer computation from ``pyforge.doctor.sources.fleet_scan``
(extracted from the retired Guildhall generator). Covers presence /
absence reporting, per-project isolation, and CLI ``--layers --project``.
Distinct from INV-A..D and dreams-hygiene.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import board

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
_HAVE_REAL_SCAN = bool(
    _REPO_ROOT and (_REPO_ROOT / "scripts" / "fleet_scan.py").is_file()
)
_HAVE_REAL_ROSTER = bool(
    _REPO_ROOT
    and (_REPO_ROOT / "docs" / "governance" / "guild-roster.json").is_file()
)

pytestmark = pytest.mark.skipif(
    not (_HAVE_REAL_SCAN and _HAVE_REAL_ROSTER),
    reason="fleet_scan.py + guild-roster.json required",
)


def _install_generate(target: Path) -> None:
    assert _REPO_ROOT is not None
    (target / "scripts").mkdir(parents=True, exist_ok=True)
    (target / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    (target / "docs" / "dreams").mkdir(parents=True, exist_ok=True)
    (target / "pixi.toml").write_text("[workspace]\nname = \"fixture\"\n", encoding="utf-8")
    shutil.copy(
        _REPO_ROOT / "scripts" / "fleet_scan.py",
        target / "scripts" / "fleet_scan.py",
    )
    shutil.copy(
        _REPO_ROOT / "docs" / "governance" / "guild-roster.json",
        target / "docs" / "governance" / "guild-roster.json",
    )


def _write_project_skeleton(
    target: Path,
    project: str,
    *,
    dream: bool = True,
    spec: bool = True,
    brief: bool = False,
    prd: bool = False,
    arch: bool = False,
    epics: bool = False,
) -> None:
    pa = target / "_bmad-output" / "projects" / project / "planning-artifacts"
    pa.mkdir(parents=True, exist_ok=True)
    if dream:
        ddir = target / "docs" / "dreams"
        ddir.mkdir(parents=True, exist_ok=True)
        (ddir / f"{project}.md").write_text(
            "---\nowner: marshal\nstatus: realized\ntitle: T\n---\nbody\n",
            encoding="utf-8",
        )
    if spec:
        sdir = pa / "specs" / f"spec-{project}"
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "SPEC.md").write_text("---\nstatus: ready\n---\n# Spec\n", encoding="utf-8")
        (sdir / ".memlog.md").write_text(
            "---\nupdated: 2026-08-01\n---\n", encoding="utf-8"
        )
    if brief:
        (pa / f"product-brief-{project}.md").write_text("# brief\n", encoding="utf-8")
    if prd:
        (pa / "prd.md").write_text("# prd\n", encoding="utf-8")
    if arch:
        (pa / "architecture.md").write_text("# arch\n", encoding="utf-8")
    if epics:
        (pa / "epics.md").write_text("# epics\n", encoding="utf-8")


def test_reports_present_and_missing_layers(tmp_path: Path) -> None:
    _install_generate(tmp_path)
    _write_project_skeleton(
        tmp_path, "pyforge-marshal", dream=True, spec=True, brief=True
    )
    findings = board.gather_chain_layers_audit(tmp_path, "pyforge-marshal")
    layer_summary = [f for f in findings if f.check == "chain-layers-audit"]
    assert len(layer_summary) == 1
    f = layer_summary[0]
    assert f.source is Source.CHAIN_LAYERS_AUDIT
    assert f.status is DoctorStatus.WARN  # many layers still missing
    assert "dream" in f.evidence["present"]
    assert "spec" in f.evidence["present"]
    assert "brief" in f.evidence["present"]
    assert "prd" in f.evidence["missing"]
    assert "arch" in f.evidence["missing"]
    assert "epics" in f.evidence["missing"]
    assert "chainAudit" in f.evidence
    assert f.evidence["chainAudit"]["verdict"] == "fail"
    # CAP-3 checkpoints emitted (Story 21.1).
    checks = {f.check for f in findings}
    assert "chain-audit-checkpoint-layers" in checks
    assert "chain-audit-verdict" in checks
    layers_cp = next(
        f for f in findings if f.check == "chain-audit-checkpoint-layers"
    )
    assert layers_cp.status is DoctorStatus.FAIL


def test_full_applicable_layers_reports_ok(tmp_path: Path) -> None:
    """When every non-na layer is present, status is OK."""
    _install_generate(tmp_path)
    project = "pyforge-marshal"
    _write_project_skeleton(
        tmp_path,
        project,
        dream=True,
        spec=True,
        brief=True,
        prd=True,
        arch=True,
        epics=True,
    )
    pa = tmp_path / "_bmad-output" / "projects" / project / "planning-artifacts"
    # Satisfy remaining primary-chain globs used by generate.py.
    (pa / "research").mkdir(exist_ok=True)
    (pa / "research" / "domain-pyforge-marshal.md").write_text("x\n", encoding="utf-8")
    (pa / "research" / "market-pyforge-marshal.md").write_text("x\n", encoding="utf-8")
    (pa / "research" / "technical-pyforge-marshal.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "presentations" / project / "project").mkdir(parents=True, exist_ok=True)
    (tmp_path / "presentations" / project / "project" / "x.html").write_text(
        "<html></html>\n", encoding="utf-8"
    )
    (tmp_path / "_bmad-output" / "projects" / project / "project-context.md").write_text(
        "# ctx\n", encoding="utf-8"
    )
    (pa / "sprint-status-ledger.yaml").write_text("development_status:\n", encoding="utf-8")
    pkg = tmp_path / "src" / "shared" / "packages" / project
    (pkg / "tests").mkdir(parents=True, exist_ok=True)
    (pkg / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (pkg / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    (pa / "implementation-readiness-report.md").write_text("# gate\n", encoding="utf-8")
    (pa / "retros").mkdir(exist_ok=True)
    (pa / "retros" / "retro-pyforge-marshal.md").write_text("# retro\n", encoding="utf-8")
    (tmp_path / "pixi.toml").write_text(
        f'[tasks]\n"{project}-test" = "true"\n', encoding="utf-8"
    )

    findings = board.gather_chain_layers_audit(tmp_path, project)
    layer_summary = [f for f in findings if f.check == "chain-layers-audit"]
    assert len(layer_summary) == 1
    ev = layer_summary[0].evidence
    for layer in ("dream", "spec", "brief", "prd", "arch", "epics"):
        assert layer in ev["present"], layer
    assert "prd" not in ev["missing"]
    verdict = next(f for f in findings if f.check == "chain-audit-verdict")
    assert "layers" in verdict.evidence["checkpoints"]
    assert "orphans" in verdict.evidence["checkpoints"]


def test_isolation_does_not_credit_sibling_project_artifacts(
    tmp_path: Path,
) -> None:
    _install_generate(tmp_path)
    _write_project_skeleton(tmp_path, "pyforge-marshal", dream=True, spec=True)
    # Sibling has a full brief/prd — must NOT appear in marshal's report.
    _write_project_skeleton(
        tmp_path,
        "pyforge-doctor",
        dream=True,
        spec=True,
        brief=True,
        prd=True,
        arch=True,
        epics=True,
    )
    findings = board.gather_chain_layers_audit(tmp_path, "pyforge-marshal")
    ev = next(f for f in findings if f.check == "chain-layers-audit").evidence
    assert "brief" in ev["missing"]
    assert "prd" in ev["missing"]
    # Files listed must stay under marshal (or shared dreams/presentations).
    for paths in ev["files"].values():
        for rel in paths:
            assert "pyforge-doctor" not in rel, rel


def test_missing_generate_is_unevaluable(tmp_path: Path) -> None:
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(
        parents=True
    )
    findings = board.gather_chain_layers_audit(tmp_path, "pyforge-marshal")
    assert findings[0].check == "chain-layers-audit-unevaluable"
    assert findings[0].status is DoctorStatus.WARN


def test_unknown_project_is_unevaluable(tmp_path: Path) -> None:
    _install_generate(tmp_path)
    findings = board.gather_chain_layers_audit(tmp_path, "pyforge-no-such-station")
    assert findings[0].check == "chain-layers-audit-unevaluable"


def test_cap3_checkpoint_findings_use_pass_fail(tmp_path: Path) -> None:
    """Story 21.1: each CAP-3 checkpoint is OK or FAIL, not warn-only."""
    _install_generate(tmp_path)
    _write_project_skeleton(
        tmp_path, "pyforge-marshal", dream=True, spec=True, brief=True
    )
    findings = board.gather_chain_layers_audit(tmp_path, "pyforge-marshal")
    checkpoint_checks = {
        "chain-audit-checkpoint-layers",
        "chain-audit-checkpoint-coherence",
        "chain-audit-checkpoint-staleness",
        "chain-audit-checkpoint-orphans",
        "chain-audit-verdict",
    }
    got = {f.check: f.status for f in findings if f.check in checkpoint_checks}
    assert set(got) == checkpoint_checks
    for status in got.values():
        assert status in (DoctorStatus.OK, DoctorStatus.FAIL)


def test_layers_cli_invokes_audit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ok = (
        Finding(
            source=Source.CHAIN_LAYERS_AUDIT,
            check="chain-layers-audit",
            status=DoctorStatus.OK,
            message="clean",
            evidence={"project": "pyforge-marshal", "present": [], "missing": []},
        ),
    )
    monkeypatch.setattr(
        board, "gather_chain_layers_audit", lambda target, project: ok
    )
    monkeypatch.setitem(
        dispatch.DISPATCH,
        "chain-completeness",
        lambda target: (_ for _ in ()).throw(AssertionError("INV gather ran")),
    )
    code = dispatch.main(
        ["chain-completeness", "--layers", "--project", "pyforge-marshal", "--json"]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out) == [f.to_json_dict() for f in ok]


def test_layers_without_project_is_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        dispatch.main(["chain-completeness", "--layers"])
    assert exc.value.code == 2
    assert "--project" in capsys.readouterr().err


def test_layers_on_wrong_source_is_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        dispatch.main(
            ["dream-chain", "--layers", "--project", "pyforge-marshal"]
        )
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--layers" in err
    assert "chain-completeness" in err


def test_default_chain_completeness_unchanged(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inv_ok = (
        Finding(
            source=Source.CHAIN_COMPLETENESS,
            check="chain-completeness",
            status=DoctorStatus.OK,
            message="inv clean",
            evidence={},
        ),
    )
    monkeypatch.setitem(
        dispatch.DISPATCH, "chain-completeness", lambda target: inv_ok
    )
    monkeypatch.setattr(
        board,
        "gather_chain_layers_audit",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("layers ran")),
    )
    assert dispatch.main(["chain-completeness", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [
        f.to_json_dict() for f in inv_ok
    ]
