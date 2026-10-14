"""Story 99.3 — steward ci status/vars (CAP-166 FR-39)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

flag_provider = make_flag_provider_fixture()

pytest.importorskip("jsonschema")

from pyforge.steward.ci import (
    CANARY_STALE_DAYS,
    CI_FLAG_KEY,
    CI_VARS_REL,
    DEFAULT_REPO,
    EXIT_CI_REFUSAL,
    SCHEMA_ID,
    CiDeps,
    CiDuty,
    _canary_job_name,
    _canary_stale,
    _canary_surface_id,
    _collect_canary_last_green,
    _fetch_run_jobs,
    _parse_utc_timestamp,
    run_status,
    run_vars,
)
from pyforge.steward.cli import main


@dataclass
class _FakeProc:
    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _fixture_registry() -> dict:
    return {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
            "dispatch_ignores_pauses": True,
        },
        "grandfathered_names": ["PAUSE_CONTAINER_BUILDS"],
        "surfaces": [
            {
                "id": "pause.guild-container",
                "workflow": ".github/workflows/pyforge-station-tests.yml",
                "job": "guild-container",
                "kind": "ci-job",
                "switch": "PAUSE_CONTAINER_BUILDS",
                "switch_class": "pause",
                "state": "paused",
                "review_by": "2026-11-01",
                "owner": "pyforge-steward",
            },
            {
                "id": "pause.platform-container",
                "workflow": ".github/workflows/platform-ci.yml",
                "job": "container",
                "kind": "ci-job",
                "switch": "PAUSE_PLATFORM_CONTAINER_BUILDS",
                "switch_class": "pause",
                "state": "paused",
                "review_by": "2026-11-01",
                "owner": "pyforge-steward",
            },
            {
                "id": "optin.air-gap",
                "workflow": ".github/workflows/platform-ci.yml",
                "job": "build-platform-image",
                "kind": "ci-job",
                "switch": "PLATFORM_CI_AIR_GAP_PARITY",
                "switch_class": "enable",
                "state": "opt-in-off",
                "owner": "pyforge-steward",
            },
            {
                "id": "optin.gke",
                "workflow": ".github/workflows/platform-ci.yml",
                "job": "gke-portability-smoke",
                "kind": "ci-job",
                "switch": "PLATFORM_CI_GKE_PORTABILITY_SMOKE",
                "switch_class": "enable",
                "state": "opt-in-off",
                "owner": "pyforge-steward",
            },
            {
                "id": "optin.ocp",
                "workflow": ".github/workflows/platform-ci.yml",
                "job": "ocp-portability-smoke",
                "kind": "ci-job",
                "switch": "PLATFORM_CI_OCP_PORTABILITY_SMOKE",
                "switch_class": "enable",
                "state": "opt-in-off",
                "owner": "pyforge-steward",
            },
            {
                "id": "optin.registry",
                "workflow": ".github/workflows/platform-ci.yml",
                "job": "push-registry-smoke",
                "kind": "ci-job",
                "switch": "PLATFORM_CI_PUSH_REGISTRY",
                "switch_class": "enable",
                "state": "opt-in-off",
                "owner": "pyforge-steward",
            },
            {
                "id": "dashboard",
                "workflow": ".github/workflows/dashboard.yml",
                "kind": "workflow",
                "switch": "PAUSE_DASHBOARD",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
                "stuck_rules": {"deploy_waiting_hours": 24, "consecutive_cancelled_runs": 5},
            },
            {
                "id": "cancel-streak",
                "workflow": ".github/workflows/cancel-streak.yml",
                "kind": "workflow",
                "switch": "PAUSE_CANCEL_STREAK",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
                "stuck_rules": {"consecutive_cancelled_runs": 5},
            },
            {
                "id": "drift-live",
                "workflow": ".github/workflows/drift-live.yml",
                "kind": "workflow",
                "switch": "PAUSE_DRIFT_LIVE",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            },
            {
                "id": "manual.kedro",
                "workflow": ".github/workflows/kedro-viz-publish.yml",
                "kind": "workflow",
                "switch": None,
                "switch_class": "pause",
                "state": "paused-manually",
                "owner": "pyforge-steward",
            },
            {
                "id": "overdue.pause",
                "workflow": ".github/workflows/overdue.yml",
                "kind": "workflow",
                "switch": "PAUSE_OVERDUE",
                "switch_class": "pause",
                "state": "paused",
                "review_by": "2026-09-01",
                "owner": "pyforge-steward",
            },
            {
                "id": "review-today",
                "workflow": ".github/workflows/review-today.yml",
                "kind": "workflow",
                "switch": "PAUSE_REVIEW_TODAY",
                "switch_class": "pause",
                "state": "paused",
                "review_by": "2026-10-13",
                "owner": "pyforge-steward",
            },
            {
                "id": "retired.sample",
                "workflow": ".github/workflows/retired-sample.yml",
                "kind": "workflow",
                "switch": None,
                "switch_class": "pause",
                "state": "retired",
                "owner": "pyforge-steward",
            },
        ],
    }


def _write_fixture_tree(root: Path) -> Path:
    reg = _fixture_registry()
    reg_path = root / "docs" / "governance" / "ci-surfaces.yaml"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "pyforge-station-tests.yml",
        "platform-ci.yml",
        "dashboard.yml",
        "cancel-streak.yml",
        "drift-live.yml",
        "kedro-viz-publish.yml",
        "overdue.yml",
        "review-today.yml",
        "retired-sample.yml",
        "orphan-disabled.yml",
    ):
        (wf_dir / name).write_text("jobs: {}\n", encoding="utf-8")
    return reg_path


def _gh_fixture_responses(now: datetime) -> dict[str, object]:
    _ = now
    waiting_iso = "2026-10-06T12:00:00Z"
    cancelled = [
        {
            "conclusion": "cancelled",
            "status": "completed",
            "createdAt": "2026-10-01T00:00:00Z",
            "event": "push",
            "databaseId": i,
        }
        for i in range(5)
    ]  # noqa: E501
    return {
        "rate_limit": {"resources": {"core": {"limit": 5000, "remaining": 4999}}},
        "variables": [
            {"name": "PAUSE_CONTAINER_BUILDS", "value": "true", "updatedAt": "2026-10-04T00:00:00Z"},
            {"name": "PAUSE_PLATFORM_CONTAINER_BUILDS", "value": "true", "updatedAt": "2026-10-09T00:00:00Z"},
            {"name": "PAUSE_DRIFT_LIVE", "value": "true", "updatedAt": "2026-10-10T00:00:00Z"},
            {"name": "PAUSE_OVERDUE", "value": "true", "updatedAt": "2026-10-01T00:00:00Z"},
            {"name": "PAUSE_REVIEW_TODAY", "value": "true", "updatedAt": "2026-10-13T00:00:00Z"},
            {"name": "PAUSE_UNREGISTERED", "value": "true", "updatedAt": "2026-10-12T00:00:00Z"},
        ],
        "workflows": {
            "workflows": [
                {"path": ".github/workflows/kedro-viz-publish.yml", "state": "disabled_manually"},
                {"path": ".github/workflows/orphan-disabled.yml", "state": "disabled_manually"},
                {"path": ".github/workflows/dashboard.yml", "state": "active"},
            ]
        },
        "runs": {
            ".github/workflows/dashboard.yml": [
                {
                    "databaseId": 37447093993,
                    "conclusion": None,
                    "status": "waiting",
                    "createdAt": waiting_iso,
                    "event": "push",
                }
            ],
            ".github/workflows/cancel-streak.yml": cancelled,
            ".github/workflows/drift-live.yml": [],
            ".github/workflows/pyforge-station-tests.yml": [
                {
                    "databaseId": 1,
                    "conclusion": "success",
                    "status": "completed",
                    "createdAt": "2026-10-01T00:00:00Z",
                    "event": "push",
                }
            ],
        },
        "pending": {37447093993: [{"environment": "github-pages"}]},
    }


def _make_runner(root: Path, recorded: list[list[str]], now: datetime, *, fail_run_for: str | None = None):
    fx = _gh_fixture_responses(now)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        recorded.append(list(argv))
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(argv, stdout=json.dumps(fx["rate_limit"]))
        if argv[:2] == ["gh", "api"] and "actions/workflows" in argv[2]:
            return _FakeProc(argv, stdout=json.dumps(fx["workflows"]))
        if argv[:2] == ["gh", "api"] and "pending_deployments" in argv[2]:
            run_id = int(argv[2].split("/")[-2])
            pending = fx["pending"].get(run_id, [])  # type: ignore[index]
            return _FakeProc(argv, stdout=json.dumps(pending))
        if argv[:3] == ["gh", "variable", "list"]:
            return _FakeProc(argv, stdout=json.dumps(fx["variables"]))
        if argv[:3] == ["gh", "run", "list"]:
            wf = argv[argv.index("--workflow") + 1]
            if fail_run_for and wf == fail_run_for:
                return _FakeProc(argv, returncode=1, stderr="run list failed")
            runs = fx["runs"].get(wf, [])  # type: ignore[union-attr]
            return _FakeProc(argv, stdout=json.dumps(runs))
        return _FakeProc(argv, returncode=1, stderr=f"unexpected argv: {argv}")

    return runner


def test_ci_status_schema_id_pinned() -> None:
    schema_text = (
        resources.files("pyforge.steward").joinpath("data", "ci-status-schema.json").read_text(encoding="utf-8")
    )
    schema = json.loads(schema_text)
    assert schema["$id"] == SCHEMA_ID


def test_fixture_verdicts_ac1(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)
    recorded: list[list[str]] = []
    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, recorded, fixed_now),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    assert result.ok is True
    payload = result.details["payload"]
    assert isinstance(payload, dict)
    by_id = {r["id"]: r for r in payload["rows"]}

    assert by_id["pause.guild-container"]["verdict"] == "paused"
    assert by_id["pause.guild-container"]["review_by"] == "2026-11-01"
    assert by_id["pause.platform-container"]["verdict"] == "paused"
    for oid in ("optin.air-gap", "optin.gke", "optin.ocp", "optin.registry"):
        assert by_id[oid]["verdict"] == "opt-in-off"
    assert by_id["dashboard"]["verdict"] == "stuck"
    assert by_id["cancel-streak"]["verdict"] == "stuck"
    assert by_id["drift-live"]["verdict"] == "drift"
    assert by_id["overdue.pause"]["verdict"] == "overdue"
    assert by_id["review-today"]["verdict"] == "paused"
    assert by_id["review-today"]["review_days_left"] == 0
    assert by_id["retired.sample"]["verdict"] == "drift"
    drift_ids = [r["id"] for r in payload["rows"] if r["verdict"] == "drift"]
    assert any(r.startswith("unregistered-workflow:") for r in drift_ids)
    assert any(r == "unregistered:PAUSE_UNREGISTERED" for r in drift_ids)
    assert all(cmd[0] == "gh" for cmd in recorded)


def test_rate_limit_zero_refuses(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(
                argv,
                stdout=json.dumps({"resources": {"core": {"limit": 5000, "remaining": 0}}}),
            )
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=tmp_path, runner=runner, registry_path=reg_path, flag_on=lambda: True)
    result = run_status(deps, json_out=False)
    assert result.ok is False
    assert result.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "rate_limit" in result.summary
    assert "id\tverdict" not in result.summary


def test_unauthenticated_rate_limit_refuses(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(
                argv,
                stdout=json.dumps({"resources": {"core": {"limit": 60, "remaining": 60}}}),
            )
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=tmp_path, runner=runner, registry_path=reg_path, flag_on=lambda: True)
    result = run_status(deps, json_out=False)
    assert result.ok is False
    assert result.details.get("exit_code") == EXIT_CI_REFUSAL


@flag_states("pyforge.steward.ci_pause_control")
def test_flag_off_refuses_both_verbs(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    reg_path = _write_fixture_tree(tmp_path)
    on = flag_provider["pyforge.steward.ci_pause_control"]
    if not on:
        deps = CiDeps(
            root=tmp_path,
            runner=lambda a, c: _FakeProc(a),
            registry_path=reg_path,
            flag_on=lambda: False,
        )
        for fn, kwargs in ((run_status, {"json_out": False}), (run_vars, {"refresh": False})):
            result = fn(deps, **kwargs)
            assert result.ok is False
            assert CI_FLAG_KEY in result.summary
            assert result.details.get("exit_code") == EXIT_CI_REFUSAL
        return
    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    assert result.ok is True


def test_json_validates_against_schema(tmp_path: Path) -> None:
    import jsonschema

    reg_path = _write_fixture_tree(tmp_path)
    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    payload = json.loads(result.summary)
    schema_text = (
        resources.files("pyforge.steward").joinpath("data", "ci-status-schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, json.loads(schema_text))


def test_vars_refresh_and_age(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)
    fixed_now = datetime(2026, 10, 13, 15, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    refresh = run_vars(deps, refresh=True)
    assert refresh.ok is True
    snap_path = tmp_path / CI_VARS_REL
    assert snap_path.is_file()
    doc = json.loads(snap_path.read_text(encoding="utf-8"))
    assert doc["repo"] == DEFAULT_REPO
    assert "PAUSE_CONTAINER_BUILDS" in doc["variables"]
    assert doc["fetched_at"]

    read = run_vars(deps, refresh=False)
    assert read.ok is True
    assert "age" in read.summary


def test_run_list_partial_failure_still_prints(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)
    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now, fail_run_for=".github/workflows/platform-ci.yml"),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=False)
    assert result.ok is False
    assert "pause.guild-container" in result.summary
    payload = result.details["payload"]
    row = next(r for r in payload["rows"] if r["id"] == "pause.guild-container")
    assert row["last_green_run"] is not None


def test_main_json_flag_off_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_fixture_tree(tmp_path)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tmp_path / "flags.json"))
    (tmp_path / "flags.json").write_text(
        json.dumps(
            {
                "flags": {
                    CI_FLAG_KEY: {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": "off",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    code = main(["ci", "status", "--json"])
    assert code == EXIT_CI_REFUSAL


def test_rate_limit_gh_api_failure_refuses(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(argv, returncode=1, stdout="rate limit denied")
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=tmp_path, runner=runner, registry_path=reg_path, flag_on=lambda: True)
    result = run_status(deps, json_out=False)
    assert result.ok is False
    assert "rate limit denied" in result.summary


def test_rate_limit_invalid_json_refuses(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(argv, stdout="not-json")
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=tmp_path, runner=runner, registry_path=reg_path, flag_on=lambda: True)
    result = run_status(deps, json_out=False)
    assert result.ok is False
    assert "invalid JSON" in result.summary


def test_variable_list_failure_refuses(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(
                argv,
                stdout=json.dumps({"resources": {"core": {"limit": 5000, "remaining": 1}}}),
            )
        if argv[:3] == ["gh", "variable", "list"]:
            return _FakeProc(argv, returncode=1, stderr="variables unavailable")
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=tmp_path, runner=runner, registry_path=reg_path, flag_on=lambda: True)
    result = run_status(deps, json_out=False)
    assert result.ok is False
    assert "variables unavailable" in result.summary


def test_workflows_response_invalid_refuses(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(
                argv,
                stdout=json.dumps({"resources": {"core": {"limit": 5000, "remaining": 1}}}),
            )
        if argv[:3] == ["gh", "variable", "list"]:
            return _FakeProc(argv, stdout=json.dumps([]))
        if argv[:2] == ["gh", "api"] and "actions/workflows" in argv[2]:
            return _FakeProc(argv, stdout=json.dumps({"workflows": "bad"}))
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=tmp_path, runner=runner, registry_path=reg_path, flag_on=lambda: True)
    result = run_status(deps, json_out=False)
    assert result.ok is False
    assert "workflows array" in result.summary


def test_vars_missing_snapshot(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)
    deps = CiDeps(root=tmp_path, runner=lambda a, c: _FakeProc(a), registry_path=reg_path, flag_on=lambda: True)
    result = run_vars(deps, refresh=False)
    assert result.ok is False
    assert "no snapshot yet" in result.summary


def test_vars_corrupt_snapshot(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)
    snap = tmp_path / CI_VARS_REL
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text("{not json", encoding="utf-8")
    deps = CiDeps(root=tmp_path, runner=lambda a, c: _FakeProc(a), registry_path=reg_path, flag_on=lambda: True)
    result = run_vars(deps, refresh=False)
    assert result.ok is False
    assert "corrupt JSON" in result.summary


def test_vars_refresh_rate_limit_refuses(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(
                argv,
                stdout=json.dumps({"resources": {"core": {"limit": 60, "remaining": 60}}}),
            )
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=tmp_path, runner=runner, registry_path=reg_path, flag_on=lambda: True)
    result = run_vars(deps, refresh=True)
    assert result.ok is False
    assert result.details.get("exit_code") == EXIT_CI_REFUSAL


def test_ci_duty_unknown_verb() -> None:
    deps = CiDeps(root=Path("/tmp"), runner=lambda a, c: _FakeProc(a), flag_on=lambda: True)
    ns = argparse.Namespace(_ci_deps=deps, ci_verb="nope", json=False, refresh=False)
    result = CiDuty().run(ns)
    assert result.ok is False
    assert "pause" in result.summary


def test_paused_high_cost_canary_stale_and_fresh() -> None:
    """Story 99.6 AC3: canary_last_green older than 15 days => stuck; recent => not stuck."""
    row = {
        "id": "station-tests.guild-container",
        "state": "paused",
        "cost": "high",
        "canary": "ci-canary.station-tests.guild-container",
    }
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    stale_at = (now - timedelta(days=CANARY_STALE_DAYS)).isoformat().replace("+00:00", "Z")
    fresh_at = (now - timedelta(days=3)).isoformat().replace("+00:00", "Z")
    assert _canary_stale(row, {"station-tests.guild-container": stale_at}, now=now)
    assert _canary_stale(row, {}, now=now)
    assert not _canary_stale(row, {"station-tests.guild-container": fresh_at}, now=now)
    assert _canary_stale(row, {"station-tests.guild-container": "not-a-timestamp"}, now=now)
    assert not _canary_stale({**row, "state": "live"}, {}, now=now)
    assert not _canary_stale({**row, "cost": "low"}, {}, now=now)


def test_canary_surface_id_and_parse_timestamp() -> None:
    assert _canary_surface_id({"canary": "ci-canary.guild-container"}) == "guild-container"
    assert _canary_surface_id({"id": "fallback-id", "canary": "other-prefix"}) == "fallback-id"
    assert _canary_surface_id({"canary": None}) is None
    assert _canary_surface_id({}) is None
    assert _canary_job_name("surf") == "canary (surf)"

    assert _parse_utc_timestamp(None) is None
    assert _parse_utc_timestamp("") is None
    assert _parse_utc_timestamp("  ") is None
    assert _parse_utc_timestamp("not-a-date") is None
    zulu = _parse_utc_timestamp("2026-01-01T00:00:00Z")
    assert zulu is not None and zulu.tzinfo is not None
    naive = _parse_utc_timestamp("2026-01-01T00:00:00")
    assert naive is not None and naive.tzinfo == timezone.utc


def test_fetch_run_jobs_and_collect_canary_last_green() -> None:
    jobs_payload: dict[int, object] = {
        99: {
            "jobs": [
                {"name": "canary (surf-a)", "conclusion": "success", "completedAt": "2026-10-01T00:00:00Z"},
                {"name": "canary (surf-a)", "conclusion": "success", "startedAt": "2026-10-05T00:00:00Z"},
                {"name": "canary (surf-b)", "conclusion": "failure"},
                {"name": "not-canary", "conclusion": "success"},
            ]
        },
        100: {"jobs": [{"name": "canary (surf-a)", "conclusion": "success", "completedAt": "2026-10-10T00:00:00Z"}]},
        101: {"jobs": "not-a-list"},
    }

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2].endswith("/jobs"):
            run_id = int(argv[2].split("/")[-2])
            payload = jobs_payload.get(run_id)
            if payload is None:
                return _FakeProc(argv, returncode=1, stderr="missing run")
            return _FakeProc(argv, stdout=json.dumps(payload))
        return _FakeProc(argv, returncode=1)

    deps = CiDeps(root=Path("/tmp"), runner=runner)
    jobs = _fetch_run_jobs(deps, 99)
    assert jobs is not None and len(jobs) == 4
    assert _fetch_run_jobs(deps, 101) is None
    assert _fetch_run_jobs(deps, 404) is None

    runs = [
        {"conclusion": "success", "databaseId": 99, "createdAt": "2026-09-01T00:00:00Z"},
        {"conclusion": "success", "databaseId": 100, "createdAt": "2026-10-09T00:00:00Z"},
        {"conclusion": "failure", "databaseId": 102},
        {"conclusion": "success", "databaseId": "not-int"},
        {"conclusion": "success", "databaseId": 101},
    ]
    assert _collect_canary_last_green(deps, runs) == {"surf-a": "2026-10-10T00:00:00Z"}


def test_run_status_high_cost_canary_stale_is_stuck(tmp_path: Path) -> None:
    reg = _fixture_registry()
    reg["surfaces"].append(
        {
            "id": "canary-stale.guild-container",
            "workflow": ".github/workflows/pyforge-station-tests.yml",
            "job": "guild-container",
            "kind": "ci-job",
            "switch": "PAUSE_CANARY_STALE",
            "switch_class": "pause",
            "state": "paused",
            "cost": "high",
            "canary": "ci-canary.station-tests.guild-container",
            "review_by": "2026-12-01",
            "owner": "pyforge-steward",
        }
    )
    reg_path = tmp_path / "docs" / "governance" / "ci-surfaces.yaml"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "pyforge-station-tests.yml",
        "platform-ci.yml",
        "dashboard.yml",
        "cancel-streak.yml",
        "drift-live.yml",
        "kedro-viz-publish.yml",
        "overdue.yml",
        "review-today.yml",
        "retired-sample.yml",
        "orphan-disabled.yml",
        "ci-canary.yml",
    ):
        (wf_dir / name).write_text("jobs: {}\n", encoding="utf-8")

    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    fx = _gh_fixture_responses(fixed_now)
    fx["variables"].append({"name": "PAUSE_CANARY_STALE", "value": "true", "updatedAt": "2026-10-01T00:00:00Z"})
    stale_iso = (fixed_now - timedelta(days=CANARY_STALE_DAYS + 1)).isoformat().replace("+00:00", "Z")
    fx["runs"][".github/workflows/ci-canary.yml"] = [
        {"databaseId": 9001, "conclusion": "success", "status": "completed", "createdAt": stale_iso, "event": "push"}
    ]
    canary_jobs = {
        "jobs": [
            {
                "name": "canary (station-tests.guild-container)",
                "conclusion": "success",
                "completedAt": stale_iso,
            }
        ]
    }

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(argv, stdout=json.dumps(fx["rate_limit"]))
        if argv[:2] == ["gh", "api"] and "actions/workflows" in argv[2]:
            return _FakeProc(argv, stdout=json.dumps(fx["workflows"]))
        if argv[:3] == ["gh", "variable", "list"]:
            return _FakeProc(argv, stdout=json.dumps(fx["variables"]))
        if argv[:3] == ["gh", "run", "list"]:
            wf = argv[argv.index("--workflow") + 1]
            return _FakeProc(argv, stdout=json.dumps(fx["runs"].get(wf, [])))
        if argv[:2] == ["gh", "api"] and argv[2].endswith("/jobs"):
            return _FakeProc(argv, stdout=json.dumps(canary_jobs))
        if argv[:2] == ["gh", "api"] and "pending_deployments" in argv[2]:
            return _FakeProc(argv, stdout=json.dumps([]))
        return _FakeProc(argv, returncode=1, stderr=f"unexpected argv: {argv}")

    deps = CiDeps(
        root=tmp_path,
        runner=runner,
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    assert result.ok is True
    payload = result.details["payload"]
    by_id = {r["id"]: r for r in payload["rows"]}
    assert by_id["canary-stale.guild-container"]["verdict"] == "stuck"
