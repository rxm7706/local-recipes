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

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

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
        # Story 45.4 (DOC-D-C5): pyforge.core.dispatch exits 127 (EXIT_NOT_FOUND) when the mapped console script
        # fails to launch, and 2 (EXIT_USAGE) when it finds no steward distribution to map.
        (127, "executable not found: 'steward' ([Errno 2] No such file or directory: 'steward')"),
        (
            2,
            "station 'steward' is not installed in this environment; it runs in -e pyforge-steward: "
            "pixi run -e pyforge-steward pyforge steward <noun> <verb>",
        ),
    ],
    ids=["steward-refused", "console-script-failed-to-launch", "no-steward-distribution"],
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


# --- Story 45.4 (CAP-89; DOC-M-Z3, DOC-D-C5): steward's reason on every rule, inside fleet-picture's cut ---------

# scripts/fleet_picture.py keeps the first 110 characters of each ATTENTION message (never widened for this).
_FLEET_PICTURE_CUT = 110
_REASON_STARTS_WITHIN = 50
_ABSENT = object()


def _gather_fixture(monkeypatch, tmp_path: Path, payload: dict, *, exit_code: int = 0) -> tuple:
    monkeypatch.setattr(cli_bridge, "run_argv", _fake_bridge(exit_code, payload))
    return ci_pause_drift.gather(tmp_path)


@pytest.mark.parametrize(
    ("fixture", "exit_code", "check"),
    [
        ("row_drift.json", 0, "ci-pause-drift"),
        ("partial_with_drift.json", 1, "ci-pause-drift"),
        ("row_drift_and_overdue.json", 0, "ci-pause-drift"),
        ("row_drift_and_overdue.json", 0, "ci-pause-overdue"),
        ("row_unregistered_drift.json", 0, "ci-pause-drift"),
    ],
    ids=["drift", "partial-drift", "drift-and-overdue:drift", "drift-and-overdue:overdue", "unregistered-drift"],
)
def test_the_rows_detail_follows_the_rule_before_switch_and_owner(
    monkeypatch, tmp_path: Path, fixture: str, exit_code: int, check: str
) -> None:
    """AC1/AC2: the reason sits right after the surface and the rule, starting within the first 50 characters.

    Fails when the detail is dropped from the drift or the overdue branch, or moved back after the owner.
    """
    payload = _load_fixture(fixture)
    detail = payload["rows"][0]["detail"]
    findings = _gather_fixture(monkeypatch, tmp_path, payload, exit_code=exit_code)
    [finding] = [f for f in findings if f.check == check]
    assert finding.status == DoctorStatus.WARN
    at = finding.message.find(detail)
    assert 0 <= at < _REASON_STARTS_WITHIN, finding.message
    assert finding.message[at - 2 : at] == ": ", finding.message
    assert at < finding.message.index("(switch "), finding.message
    assert at < finding.message.index(", owner "), finding.message


def test_row_drift_keeps_its_whole_reason_inside_the_cut(monkeypatch, tmp_path: Path) -> None:
    """AC2: on row_drift.json the whole detail survives fleet-picture's 110-character ATTENTION cut."""
    payload = _load_fixture("row_drift.json")
    detail = payload["rows"][0]["detail"]
    [finding] = _gather_fixture(monkeypatch, tmp_path, payload)
    assert detail in finding.message[:_FLEET_PICTURE_CUT]
    assert finding.message == (
        "CI surface 'drift-live' drifted: live switch PAUSE_DRIFT_LIVE is true but registry declares live "
        "(switch 'PAUSE_DRIFT_LIVE', owner pyforge-steward)"
    )


def test_drift_past_review_by_names_the_reason_on_both_findings(monkeypatch, tmp_path: Path) -> None:
    """AC1: the overdue finding of a drifted row carries the row's detail too, and keeps its own fields after it."""
    findings = _gather_fixture(monkeypatch, tmp_path, _load_fixture("row_drift_and_overdue.json"))
    by_check = {f.check: f.message for f in findings}
    assert by_check == {
        "ci-pause-drift": (
            "CI surface 'drift-live' drifted: registry/live mismatch (switch 'PAUSE_DRIFT_LIVE', owner pyforge-steward)"
        ),
        "ci-pause-overdue": (
            "CI surface 'drift-live' past review date: registry/live mismatch (switch 'PAUSE_DRIFT_LIVE', "
            "owner pyforge-steward, review_by '2026-10-10', 3 day(s) overdue)"
        ),
    }


def test_a_stuck_row_with_a_detail_names_it(monkeypatch, tmp_path: Path) -> None:
    """AC1: steward sends no detail on stuck rows today; when it does, the stuck finding carries it."""
    payload = _load_fixture("row_stuck_cancel_streak.json")
    payload["rows"][0]["detail"] = "five cancelled runs since the last green one"
    [finding] = _gather_fixture(monkeypatch, tmp_path, payload)
    assert finding.check == "ci-pause-stuck"
    assert finding.message == (
        "CI surface 'cancel-streak' stuck: five cancelled runs since the last green one "
        "(switch 'PAUSE_CANCEL_STREAK', owner pyforge-steward, last_green_run '2026-10-05T00:00:00Z')"
    )


@pytest.mark.parametrize(
    "detail",
    [_ABSENT, "", None, 42, ["registry/live mismatch"]],
    ids=["absent", "empty", "null", "int", "list"],
)
def test_a_row_without_a_string_detail_reads_as_before(monkeypatch, tmp_path: Path, detail: object) -> None:
    """AC1: no detail, or an empty or non-string one, leaves every rule's message exactly as before Story 45.4."""
    payload = _load_fixture("row_drift_and_overdue.json")
    if detail is _ABSENT:
        del payload["rows"][0]["detail"]
    else:
        payload["rows"][0]["detail"] = detail
    by_check = {f.check: f.message for f in _gather_fixture(monkeypatch, tmp_path, payload)}
    assert by_check == {
        "ci-pause-drift": "CI surface 'drift-live' drifted (switch 'PAUSE_DRIFT_LIVE', owner pyforge-steward)",
        "ci-pause-overdue": (
            "CI surface 'drift-live' past review date (switch 'PAUSE_DRIFT_LIVE', owner pyforge-steward, "
            "review_by '2026-10-10', 3 day(s) overdue)"
        ),
    }


@pytest.mark.parametrize(
    ("fixture", "message"),
    [
        (
            "row_overdue.json",
            "CI surface 'overdue.pause' past review date (switch 'PAUSE_OVERDUE', owner pyforge-steward, "
            "review_by '2026-10-01', 5 day(s) overdue)",
        ),
        (
            "row_stuck_dashboard_deploy.json",
            "CI surface 'dashboard.deploy' stuck (switch None, owner pyforge-steward, "
            "last_green_run '2026-10-01T00:00:00Z')",
        ),
    ],
    ids=["overdue", "stuck"],
)
def test_recorded_rows_without_a_detail_are_unchanged(monkeypatch, tmp_path: Path, fixture: str, message: str) -> None:
    """AC1/AC7: the recorded rows that carry no detail keep today's message, still one WARN each."""
    [finding] = _gather_fixture(monkeypatch, tmp_path, _load_fixture(fixture))
    assert finding.status == DoctorStatus.WARN
    assert finding.message == message
