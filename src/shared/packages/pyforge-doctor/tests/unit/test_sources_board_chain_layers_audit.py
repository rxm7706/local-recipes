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
