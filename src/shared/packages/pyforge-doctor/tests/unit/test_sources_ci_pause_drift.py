"""Story 45.1 — ci-pause-drift source (CAP-89 / FR-22)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("jsonschema")

from jsonschema import Draft202012Validator

from pyforge.doctor import cli_bridge
from pyforge.doctor.cli_bridge import CliBridgeError
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import ci_pause_drift

REPO_ROOT = Path(__file__).resolve().parents[6]
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ci_pause_drift"
SCHEMA_PATH = REPO_ROOT / "src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(SCHEMA)
_ALL_FIXTURES = sorted(FIXTURES.glob("*.json"))


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _fake_bridge(exit_code: int, payload: dict | None, *, on_stderr: bool = False):
    text = json.dumps(payload) if payload is not None else "not json"

    def _run(argv, *, cwd, timeout=120.0):
        assert argv[-3:] == ["ci", "status", "--json"]
        if exit_code == -1:
            raise CliBridgeError("launch failed")
        if exit_code == -2:
            raise CliBridgeError("timed out after 120s")
        stdout = text if not on_stderr and exit_code == 0 else ""
        stderr = text if on_stderr or exit_code != 0 else ""
        if exit_code == -2:
            pass
        return exit_code if exit_code >= 0 else 0, stdout, stderr

    return _run


def _checks(findings: tuple) -> list[str]:
    return [f.check for f in findings]


def _warn_checks(findings: tuple) -> list[str]:
    return [f.check for f in findings if f.status == DoctorStatus.WARN]


@pytest.mark.parametrize("fixture_path", _ALL_FIXTURES, ids=lambda p: p.name)
def test_fixture_matches_ci_status_schema(fixture_path: Path) -> None:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    errors = sorted(_VALIDATOR.iter_errors(payload), key=lambda e: e.json_path)
    assert not errors, f"{fixture_path.name}: {[e.message for e in errors]}"


def test_row_drift_yields_one_ci_pause_drift_warn(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_drift.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert _warn_checks(findings) == ["ci-pause-drift"]
    assert findings[0].message.startswith("CI surface 'drift-live'")


def test_row_overdue_yields_one_ci_pause_overdue_warn(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_overdue.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert _warn_checks(findings) == ["ci-pause-overdue"]


def test_dashboard_deploy_waiting_replay_is_stuck(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_stuck_dashboard_deploy.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert _warn_checks(findings) == ["ci-pause-stuck"]
    assert "dashboard.deploy" in findings[0].message


def test_cancel_streak_is_stuck(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_stuck_cancel_streak.json")))
    assert _warn_checks(ci_pause_drift.gather(tmp_path)) == ["ci-pause-stuck"]


def test_stale_canary_on_paused_high_cost_is_stuck(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_stuck_canary_stale.json")))
    assert _warn_checks(ci_pause_drift.gather(tmp_path)) == ["ci-pause-stuck"]


def test_drift_with_review_days_left_minus_three_yields_two_warns(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_drift_and_overdue.json")))
    assert set(_warn_checks(ci_pause_drift.gather(tmp_path))) == {"ci-pause-drift", "ci-pause-overdue"}


def test_review_days_left_zero_is_not_overdue(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("rows_quiet_ok.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert "ci-pause-overdue" not in _checks(findings)


def test_quiet_rows_yield_one_ok_naming_count(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("rows_quiet_ok.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert "6 CI surface row(s)" in findings[0].message


def test_empty_rows_ok_count_zero(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("rows_empty.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert findings[0].status == DoctorStatus.OK
    assert "0 CI surface row(s)" in findings[0].message


def test_unregistered_drift_owner_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_unregistered_drift.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert "owner (none)" in findings[0].message


@pytest.mark.parametrize(
    ("exit_code", "stderr_line"),
    [
        (3, "ci: refused — flag pyforge.steward.ci_pause_control is off"),
        (127, "pyforge.core.dispatch: no steward distribution installed"),
        (2, "unexpected failure"),
    ],
)
def test_refusal_or_unknown_exit_yields_unobserved(
    monkeypatch, tmp_path: Path, exit_code: int, stderr_line: str
) -> None:

    def _run(argv, *, cwd, timeout=120.0):
        return exit_code, "", stderr_line

    monkeypatch.setattr(cli_bridge, "run_argv", _run)
    findings = ci_pause_drift.gather(tmp_path)
    assert _warn_checks(findings) == ["ci-pause-unobserved"]
    assert f"exit {exit_code}" in findings[0].message
    assert stderr_line.splitlines()[0] in findings[0].message
    assert not any(f.status == DoctorStatus.OK for f in findings)


def test_bridge_timeout_yields_unobserved(monkeypatch, tmp_path: Path) -> None:
    def _timeout(argv, *, cwd, timeout=120.0):
        raise CliBridgeError("timed out after 120s")

    monkeypatch.setattr(cli_bridge, "run_argv", _timeout)
    findings = ci_pause_drift.gather(tmp_path)
    assert _warn_checks(findings) == ["ci-pause-unobserved"]
    assert "timed out" in findings[0].message.lower()


def test_launch_failure_yields_unobserved(monkeypatch, tmp_path: Path) -> None:
    def _boom(argv, *, cwd, timeout=120.0):
        raise CliBridgeError("failed to launch: OSError(2)")

    monkeypatch.setattr(cli_bridge, "run_argv", _boom)
    findings = ci_pause_drift.gather(tmp_path)
    assert _warn_checks(findings) == ["ci-pause-unobserved"]


def test_non_json_stdout_yields_unobserved(monkeypatch, tmp_path: Path) -> None:
    def _run(argv, *, cwd, timeout=120.0):
        return 0, "not json", ""

    monkeypatch.setattr(cli_bridge, "run_argv", _run)
    findings = ci_pause_drift.gather(tmp_path)
    assert _warn_checks(findings) == ["ci-pause-unobserved"]


def test_payload_without_rows_yields_unobserved(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, {"rows": "x"}))
    assert _warn_checks(ci_pause_drift.gather(tmp_path)) == ["ci-pause-unobserved"]


def test_row_without_verdict_yields_unobserved(monkeypatch, tmp_path: Path) -> None:
    payload = _load_fixture("row_drift.json")
    del payload["rows"][0]["verdict"]
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, payload))
    assert _warn_checks(ci_pause_drift.gather(tmp_path)) == ["ci-pause-unobserved"]


def test_partial_read_on_stderr(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        cli_bridge,
        "run_argv",
        _fake_bridge(1, _load_fixture("partial_with_drift.json"), on_stderr=True),
    )
    findings = ci_pause_drift.gather(tmp_path)
    assert "ci-pause-drift" in _warn_checks(findings)
    assert "ci-pause-partial" in _warn_checks(findings)


def test_gather_warn_fixtures_never_emit_fail(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_drift.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert all(f.status in (DoctorStatus.WARN, DoctorStatus.OK) for f in findings)


# --- AC10 guard tests (each names the mutation it catches) -------------------


def test_mutation_fail_status_breaks_warn_only_contract(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_drift.json")))
    findings = ci_pause_drift.gather(tmp_path)
    assert all(f.status != DoctorStatus.FAIL for f in findings)


def test_mutation_overdue_from_verdict_instead_of_days_left_would_miss_combo(monkeypatch, tmp_path: Path) -> None:
    """Drift row with review_days_left < 0 must emit ci-pause-overdue even when verdict is drift."""
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, _load_fixture("row_drift_and_overdue.json")))
    assert "ci-pause-overdue" in _warn_checks(ci_pause_drift.gather(tmp_path))


def test_mutation_ok_on_unparseable_would_false_clean(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(0, {"rows": "x"}))
    assert not any(f.status == DoctorStatus.OK for f in ci_pause_drift.gather(tmp_path))


def test_mutation_partial_as_unobserved_would_drop_row_findings(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        cli_bridge,
        "run_argv",
        _fake_bridge(1, _load_fixture("partial_with_drift.json"), on_stderr=True),
    )
    findings = ci_pause_drift.gather(tmp_path)
    assert "ci-pause-drift" in _warn_checks(findings)
    assert "ci-pause-partial" in _warn_checks(findings)


def test_source_is_ci_pause_drift() -> None:
    assert Source.CI_PAUSE_DRIFT.value == "ci-pause-drift"


def test_partial_read_on_stdout(monkeypatch, tmp_path: Path) -> None:
    """Steward Story 103.7: a partial read prints its report, with partial and run_list_errors, on stdout."""
    payload = {
        **_load_fixture("partial_with_drift.json"),
        "partial": True,
        "run_list_errors": [".github/workflows/platform-ci.yml: HTTP 404"],
    }
    assert not list(_VALIDATOR.iter_errors(payload))
    text = json.dumps(payload)

    def _run(argv, *, cwd, timeout=120.0):
        assert argv[-3:] == ["ci", "status", "--json"]
        return 1, text, ""

    monkeypatch.setattr(cli_bridge, "run_argv", _run)
    findings = ci_pause_drift.gather(tmp_path)
    assert "ci-pause-drift" in _warn_checks(findings)
    assert "ci-pause-partial" in _warn_checks(findings)
    assert "ci-pause-unobserved" not in _checks(findings)
