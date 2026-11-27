"""Unit tests for ``board.gather_chain_layers_audit`` (Story 17.3 /
FR-150 residual + FR-152).

Seeds layer computation from ``scripts/fleet_scan.py`` (extracted from the
retired Guildhall generator). Covers the unevaluable audit and the CLI
``--layers --project`` here. The presence / absence, per-project isolation
and checkout-script loader tests copy or load this repository's own
``scripts/fleet_scan.py`` and roster, so they run in
``test_live_sources_board_chain_layers_audit.py``. Distinct from INV-A..D and
dreams-hygiene.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import board

# Doctor Story 58.1 (spec-pyforge-doctor:CAP-97): no test here reads this repository, so the module runs in the
# package half; the tests that do run in test_live_sources_board_chain_layers_audit.py.


def test_missing_generate_is_unevaluable(tmp_path: Path) -> None:
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(parents=True)
    findings = board.gather_chain_layers_audit(tmp_path, "pyforge-marshal")
    assert findings[0].check == "chain-layers-audit-unevaluable"
    assert findings[0].status is DoctorStatus.WARN


# --- the batch form (doctor Story 69.1) ---------------------------------------------------


def test_batch_without_a_checkout_script_is_unevaluable_per_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _no_checkout(name: str) -> Path:
        raise FileNotFoundError(f"scripts/{name} not found above /nowhere")

    monkeypatch.setattr(board, "locate_checkout_script", _no_checkout)
    batch = board.gather_chain_layers_audits(tmp_path, ("pyforge-marshal", "pyforge-doctor"))
    assert list(batch) == ["pyforge-marshal", "pyforge-doctor"]
    for project, findings in batch.items():
        assert [f.check for f in findings] == ["chain-layers-audit-unevaluable"]
        assert findings[0].status is DoctorStatus.WARN
        assert findings[0].evidence["project"] == project


def test_batch_degrades_a_raising_project_alone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ok = (
        Finding(
            source=Source.CHAIN_LAYERS_AUDIT,
            check="chain-audit-verdict",
            status=DoctorStatus.OK,
            message="ok",
            evidence={},
        ),
    )

    def gather(target: Path, project: str, scan: object) -> tuple[Finding, ...]:
        if project == "pyforge-doctor":
            raise RuntimeError("boom")
        return ok

    monkeypatch.setattr(board, "_gather_chain_layers_audit", gather)
    batch = board.gather_chain_layers_audits(tmp_path, ("pyforge-marshal", "pyforge-doctor", "pyforge-herald"))
    assert batch["pyforge-marshal"] == ok
    assert batch["pyforge-herald"] == ok
    (degraded,) = batch["pyforge-doctor"]
    assert degraded.status is DoctorStatus.WARN
    assert "boom" in degraded.message


def test_fleet_scan_memo_keeps_only_a_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed load is retried by the next project; a successful load and scan run once."""
    loads: list[Path] = []
    scans: list[tuple] = []

    class _Gen:
        def scan_fleet(self, *args: object) -> dict:
            scans.append(args)
            return {"rows": []}

    def load(target: Path) -> _Gen:
        loads.append(target)
        if len(loads) == 1:
            raise FileNotFoundError("first load fails")
        return _Gen()

    monkeypatch.setattr(board, "_load_dashboard_generate", load)
    scan = board._FleetScan(tmp_path)
    with pytest.raises(FileNotFoundError):
        scan.module()
    first = scan.module()
    assert scan.module() is first
    assert scan.fleet() == {"rows": []}
    assert scan.fleet() == {"rows": []}
    assert len(loads) == 2
    assert scans == [({}, None)]


def test_layers_cli_invokes_audit(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    ok = (
        Finding(
            source=Source.CHAIN_LAYERS_AUDIT,
            check="chain-layers-audit",
            status=DoctorStatus.OK,
            message="clean",
            evidence={"project": "pyforge-marshal", "present": [], "missing": []},
        ),
    )
    monkeypatch.setattr(board, "gather_chain_layers_audit", lambda target, project: ok)
    monkeypatch.setitem(
        dispatch.DISPATCH,
        "chain-completeness",
        lambda target: (_ for _ in ()).throw(AssertionError("INV gather ran")),
    )
    code = dispatch.main(["chain-completeness", "--layers", "--project", "pyforge-marshal", "--json"])
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
        dispatch.main(["dream-chain", "--layers", "--project", "pyforge-marshal"])
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
    monkeypatch.setitem(dispatch.DISPATCH, "chain-completeness", lambda target: inv_ok)
    monkeypatch.setattr(
        board,
        "gather_chain_layers_audit",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("layers ran")),
    )
    assert dispatch.main(["chain-completeness", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [f.to_json_dict() for f in inv_ok]
