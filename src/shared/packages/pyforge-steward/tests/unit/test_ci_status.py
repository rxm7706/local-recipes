"""Story 99.3 — steward ci status/vars (CAP-166 FR-39)."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path
from typing import Any

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
                "id": "pages",
                "workflow": ".github/workflows/pages.yml",
                "kind": "workflow",
                "switch": "PAUSE_PAGES",
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
        "pages.yml",
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
                {"path": ".github/workflows/pages.yml", "state": "active"},
            ]
        },
        "runs": {
            ".github/workflows/pages.yml": [
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
    assert by_id["pages"]["verdict"] == "stuck"
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
        "pages.yml",
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


_MASTER_UPDATED = "2026-10-14T08:00:00Z"
_MASTER_DETAIL = (
    "master switch PAUSE_ALL_CI is true: every job that reads it is skipped, and the registry declares no master pause"
)
_MASTER_PAUSE_DETAIL = "paused by the master switch PAUSE_ALL_CI"


def _minimal_gh_runner(tmp_path: Path, variables: list[dict], fixed_now: datetime) -> Any:
    fx = {
        "rate_limit": {"resources": {"core": {"limit": 5000, "remaining": 4999}}},
        "variables": variables,
        "workflows": {"workflows": []},
        "runs": {},
        "pending": {},
    }

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:2] == ["gh", "api"] and argv[2] == "rate_limit":
            return _FakeProc(argv, stdout=json.dumps(fx["rate_limit"]))
        if argv[:2] == ["gh", "api"] and "actions/workflows" in argv[2]:
            return _FakeProc(argv, stdout=json.dumps(fx["workflows"]))
        if argv[:3] == ["gh", "variable", "list"]:
            return _FakeProc(argv, stdout=json.dumps(fx["variables"]))
        if argv[:3] == ["gh", "run", "list"]:
            return _FakeProc(argv, stdout=json.dumps([]))
        if argv[:2] == ["gh", "api"] and "pending_deployments" in argv[2]:
            return _FakeProc(argv, stdout=json.dumps([]))
        return _FakeProc(argv, returncode=1, stderr=f"unexpected argv: {argv}")

    return runner


def _master_gating_surfaces(*, include_precedence: bool = False, include_retired: bool = False) -> list[dict]:
    surfaces: list[dict] = [
        {
            "id": "wf.all-gated",
            "workflow": ".github/workflows/wf-all-gated.yml",
            "kind": "workflow",
            "switch": "PAUSE_WF_ALL",
            "switch_class": "pause",
            "state": "live",
            "owner": "pyforge-steward",
        },
        {
            "id": "job.gated",
            "workflow": ".github/workflows/job-gated.yml",
            "job": "only",
            "kind": "ci-job",
            "switch": "PAUSE_JOB_GATED",
            "switch_class": "pause",
            "state": "live",
            "owner": "pyforge-steward",
        },
        {
            "id": "step.gated",
            "workflow": ".github/workflows/step-gated.yml",
            "job": "main",
            "step": "gate-step",
            "kind": "ci-step",
            "switch": "PAUSE_STEP_GATED",
            "switch_class": "pause",
            "state": "live",
            "owner": "pyforge-steward",
        },
        {
            "id": "wf.mixed",
            "workflow": ".github/workflows/wf-mixed.yml",
            "kind": "workflow",
            "switch": "PAUSE_WF_MIXED",
            "switch_class": "pause",
            "state": "live",
            "owner": "pyforge-steward",
        },
        {
            "id": "wf.dispatch-only",
            "workflow": ".github/workflows/wf-dispatch-only.yml",
            "kind": "workflow",
            "switch": None,
            "switch_class": "pause",
            "state": "live",
            "owner": "pyforge-steward",
        },
        {
            "id": "row.value",
            "workflow": ".github/workflows/wf-value.yml",
            "job": "j",
            "step": "s",
            "kind": "value",
            "switch": "SOME_VALUE",
            "switch_class": "value",
            "state": "live",
            "owner": "pyforge-steward",
        },
        {
            "id": "row.manual",
            "workflow": ".github/workflows/wf-manual.yml",
            "kind": "workflow",
            "switch": None,
            "switch_class": "pause",
            "state": "paused-manually",
            "owner": "pyforge-steward",
        },
    ]
    if include_retired:
        surfaces.append(
            {
                "id": "row.retired",
                "workflow": ".github/workflows/wf-retired.yml",
                "kind": "workflow",
                "switch": None,
                "switch_class": "pause",
                "state": "retired",
                "owner": "pyforge-steward",
            }
        )
    if include_precedence:
        surfaces.extend(
            [
                {
                    "id": "drift.own-switch",
                    "workflow": ".github/workflows/drift-own.yml",
                    "job": "only",
                    "kind": "ci-job",
                    "switch": "PAUSE_DRIFT_OWN",
                    "switch_class": "pause",
                    "state": "live",
                    "owner": "pyforge-steward",
                },
                {
                    "id": "paused.own-switch",
                    "workflow": ".github/workflows/paused-own.yml",
                    "job": "only",
                    "kind": "ci-job",
                    "switch": "PAUSE_OWN_PAUSED",
                    "switch_class": "pause",
                    "state": "paused",
                    "owner": "pyforge-steward",
                },
            ]
        )
    return surfaces


def _write_master_gating_tree(root: Path, *, include_precedence: bool = False, include_retired: bool = False) -> Path:
    reg = {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
        },
        "surfaces": _master_gating_surfaces(
            include_precedence=include_precedence,
            include_retired=include_retired,
        ),
    }
    reg_path = root / "docs" / "governance" / "ci-surfaces.yaml"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    (wf / "wf-all-gated.yml").write_text(
        """on: push
jobs:
  j1:
    if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_WF_ALL != 'true') }}
    runs-on: ubuntu-latest
    steps: []
  j2:
    if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_WF_ALL != 'true') }}
    runs-on: ubuntu-latest
    steps: []
""",
        encoding="utf-8",
    )
    (wf / "job-gated.yml").write_text(
        """on: push
jobs:
  only:
    if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_JOB_GATED != 'true') }}
    runs-on: ubuntu-latest
    steps: []
""",
        encoding="utf-8",
    )
    (wf / "step-gated.yml").write_text(
        """on: push
jobs:
  main:
    runs-on: ubuntu-latest
    steps:
      - name: gate-step
        if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_STEP_GATED != 'true') }}
        run: echo ok
""",
        encoding="utf-8",
    )
    (wf / "wf-mixed.yml").write_text(
        """on: push
jobs:
  gated:
    if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_WF_MIXED != 'true') }}
    runs-on: ubuntu-latest
    steps: []
  not-gated:
    if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_WF_MIXED_ONLY != 'true') }}
    runs-on: ubuntu-latest
    steps: []
""",
        encoding="utf-8",
    )
    (wf / "wf-dispatch-only.yml").write_text(
        """on:
  workflow_dispatch:
jobs:
  manual:
    runs-on: ubuntu-latest
    steps: []
""",
        encoding="utf-8",
    )
    for name in ("wf-value.yml", "wf-manual.yml"):
        (wf / name).write_text("on: push\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n", encoding="utf-8")
    if include_retired:
        (wf / "wf-retired.yml").write_text(
            "on: push\njobs:\n  j:\n    runs-on: ubuntu-latest\n    steps: []\n", encoding="utf-8"
        )
    if not include_precedence:
        return reg_path
    (wf / "drift-own.yml").write_text(
        """on: push
jobs:
  only:
    if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_DRIFT_OWN != 'true') }}
    runs-on: ubuntu-latest
    steps: []
""",
        encoding="utf-8",
    )
    (wf / "paused-own.yml").write_text(
        """on: push
jobs:
  only:
    if: ${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_OWN_PAUSED != 'true') }}
    runs-on: ubuntu-latest
    steps: []
""",
        encoding="utf-8",
    )
    return reg_path


def _run_master_fixture(
    tmp_path: Path,
    *,
    master_value: str | None,
    extra_variables: list[dict] | None = None,
    precedence_variables: bool = False,
) -> dict:
    reg_path = _write_master_gating_tree(
        tmp_path,
        include_precedence=precedence_variables,
        include_retired=precedence_variables,
    )
    variables: list[dict] = list(extra_variables or [])
    if master_value is not None:
        variables.append(
            {"name": "PAUSE_ALL_CI", "value": master_value, "updatedAt": _MASTER_UPDATED},
        )
    if precedence_variables:
        variables.extend(
            [
                {"name": "PAUSE_DRIFT_OWN", "value": "true", "updatedAt": "2026-10-01T00:00:00Z"},
                {"name": "PAUSE_OWN_PAUSED", "value": "true", "updatedAt": "2026-10-02T00:00:00Z"},
            ]
        )
    fixed_now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_minimal_gh_runner(tmp_path, variables, fixed_now),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    assert result.ok is True
    payload = result.details["payload"]
    assert isinstance(payload, dict)
    return payload


def test_master_row_ac1_unset_false_true(tmp_path: Path) -> None:
    for master_value, live_val, verdict, paused_since in (
        (None, None, "live", None),
        ("false", "false", "live", None),
        ("true", "true", "drift", _MASTER_UPDATED),
    ):
        payload = _run_master_fixture(tmp_path, master_value=master_value)
        master_rows = [r for r in payload["rows"] if r["id"] == "master:PAUSE_ALL_CI"]
        assert len(master_rows) == 1
        row = master_rows[0]
        assert row["switch"] == "PAUSE_ALL_CI"
        assert row["declared_state"] == "live"
        assert row["live_switch_value"] == live_val
        assert row["verdict"] == verdict
        assert row["paused_since"] == paused_since
        assert row["paused_by_master"] is False
        if verdict == "drift":
            assert row["detail"] == _MASTER_DETAIL
        assert not any(r["id"] == "unregistered:PAUSE_ALL_CI" for r in payload["rows"])


def test_gated_rows_ac2_master_on(tmp_path: Path) -> None:
    payload = _run_master_fixture(tmp_path, master_value="true")
    by_id = {r["id"]: r for r in payload["rows"]}

    for rid in ("wf.all-gated", "job.gated", "step.gated"):
        row = by_id[rid]
        assert row["verdict"] == "paused"
        assert row["paused_by_master"] is True
        assert row["detail"] == _MASTER_PAUSE_DETAIL
        assert row["paused_since"] == _MASTER_UPDATED

    assert by_id["wf.mixed"]["verdict"] == "live"
    assert by_id["wf.mixed"]["paused_by_master"] is False
    assert by_id["wf.dispatch-only"]["verdict"] == "live"
    assert by_id["wf.dispatch-only"]["paused_by_master"] is False
    assert by_id["row.value"]["paused_by_master"] is False
    assert by_id["row.manual"]["paused_by_master"] is False


def test_precedence_ac3_master_on(tmp_path: Path) -> None:
    payload = _run_master_fixture(tmp_path, master_value="true", precedence_variables=True)
    by_id = {r["id"]: r for r in payload["rows"]}
    drift = by_id["drift.own-switch"]
    assert drift["verdict"] == "drift"
    assert drift["paused_by_master"] is True
    assert "master switch" not in str(drift.get("detail", ""))
    paused = by_id["paused.own-switch"]
    assert paused["verdict"] == "paused"
    assert paused["paused_by_master"] is True
    assert paused.get("detail") != _MASTER_PAUSE_DETAIL
    assert paused["paused_since"] == "2026-10-02T00:00:00Z"


def test_master_off_adds_only_master_row_and_flag(tmp_path: Path) -> None:
    reg_path = _write_fixture_tree(tmp_path)
    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    payload = run_status(deps, json_out=True).details["payload"]
    by_id = {r["id"]: r for r in payload["rows"]}
    assert "master:PAUSE_ALL_CI" in by_id
    for rid, row in by_id.items():
        if rid == "master:PAUSE_ALL_CI":
            continue
        assert row["paused_by_master"] is False


def test_ci_status_master_on_fixture_checked_in(tmp_path: Path) -> None:
    payload = _run_master_fixture(tmp_path, master_value="true")
    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "ci_status_master_on.json"
    canonical = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if fixture_path.is_file():
        assert canonical == fixture_path.read_text(encoding="utf-8")
    else:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(canonical, encoding="utf-8")


def test_ac6_consumers_read_master_fixture() -> None:
    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "ci_status_master_on.json"
    assert fixture_path.is_file(), "run test_ci_status_master_on_fixture_checked_in first"
    repo_root = Path(__file__).resolve().parents[6]
    fixture_s = str(fixture_path)

    doctor_snippet = f"""
import json
from pathlib import Path
from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources.ci_pause_drift import _findings_for_rows, _parse_payload
payload = json.loads(Path({fixture_s!r}).read_text(encoding="utf-8"))
parsed = _parse_payload(json.dumps(payload))
assert parsed is not None
findings = _findings_for_rows(parsed["rows"])
warns = [f for f in findings if f.status == DoctorStatus.WARN and f.check == "ci-pause-drift"]
assert len(warns) == 1
assert "master:PAUSE_ALL_CI" in warns[0].message
assert not any("wf.all-gated" in f.message for f in warns)
"""
    subprocess.run(
        ["pixi", "run", "--frozen", "-e", "pyforge-doctor", "python", "-c", doctor_snippet],
        cwd=repo_root,
        check=True,
    )

    # Herald's tile and guild status page read the snapshot through docs-site/src/lib/status.ts since herald Story 43.7
    # (node builtins only, run with node's type stripping in herald's env).
    status_ts = (repo_root / "docs-site" / "src" / "lib" / "status.ts").as_uri()
    herald_snippet = f"""
import fs from 'node:fs';
import {{ orderRows, tileLine, validateCiStatus }} from {json.dumps(status_ts)};
const payload = JSON.parse(fs.readFileSync({json.dumps(fixture_s)}, 'utf8'));
validateCiStatus(payload, {json.dumps(fixture_s)});
const notLive = orderRows(payload.rows, false);
if (notLive[0].id !== 'master:PAUSE_ALL_CI') throw new Error(`first non-live row is ${{notLive[0].id}}`);
for (const row of notLive) {{
  if (row.detail && !tileLine(row).includes(String(row.detail))) throw new Error(`detail missing for ${{row.id}}`);
}}
"""
    subprocess.run(
        [
            "pixi",
            "run",
            "--frozen",
            "-e",
            "pyforge-herald",
            "node",
            "--experimental-strip-types",
            "--no-warnings",
            "--input-type=module",
            "-e",
            herald_snippet,
        ],
        cwd=repo_root,
        check=True,
    )

    marshal_snippet = f"""
import json
from pathlib import Path
from pyforge.marshal.core.landing_ci_pauses import envelope_is_valid, surfaces_from_envelope
payload = json.loads(Path({fixture_s!r}).read_text(encoding="utf-8"))
assert envelope_is_valid(payload) is True
assert "master:PAUSE_ALL_CI" in surfaces_from_envelope(payload)
"""
    subprocess.run(
        ["pixi", "run", "--frozen", "-e", "pyforge-marshal", "python", "-c", marshal_snippet],
        cwd=repo_root,
        check=True,
    )


# --- Story 103.7: a retired row reads no runs, and a partial read keeps stdout ---------------------------------------

_RETIRED_GONE_WF = ".github/workflows/retired-gone.yml"


def _registry_with_retired_gone(root: Path) -> Path:
    """The fixture registry plus a retired row whose workflow file is not in the tree (Story 99.7's deleted files)."""
    _write_fixture_tree(root)
    reg = _fixture_registry()
    reg["surfaces"].append(
        {
            "id": "retired.gone",
            "workflow": _RETIRED_GONE_WF,
            "kind": "workflow",
            "switch": None,
            "switch_class": "pause",
            "state": "retired",
            "owner": "pyforge-steward",
        }
    )
    reg_path = root / "docs" / "governance" / "ci-surfaces.yaml"
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    return reg_path


def _run_list_workflows(recorded: list[list[str]]) -> list[str]:
    return [argv[argv.index("--workflow") + 1] for argv in recorded if argv[:3] == ["gh", "run", "list"]]


def test_retired_row_reads_no_runs_and_the_read_is_complete(tmp_path: Path) -> None:
    """AC1: GitHub 404s a deleted workflow that never ran on its own; a retired row never asks for its runs."""
    reg_path = _registry_with_retired_gone(tmp_path)
    recorded: list[list[str]] = []
    fixed_now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, recorded, fixed_now, fail_run_for=_RETIRED_GONE_WF),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    assert result.ok is True
    assert result.details["partial"] is False
    payload = result.details["payload"]
    assert "partial" not in payload and "run_list_errors" not in payload
    by_id = {r["id"]: r for r in payload["rows"]}
    assert by_id["retired.gone"]["verdict"] == "retired"
    assert by_id["retired.gone"]["last_green_run"] is None
    assert by_id["retired.sample"]["last_green_run"] is None
    fetched = _run_list_workflows(recorded)
    assert _RETIRED_GONE_WF not in fetched
    assert ".github/workflows/retired-sample.yml" not in fetched
    assert ".github/workflows/pages.yml" in fetched


def test_live_row_failed_fetch_is_partial_and_the_envelope_names_it(tmp_path: Path) -> None:
    """AC2 and AC4: a live row's failed run list still makes the read partial, and the envelope says so."""
    import jsonschema

    reg_path = _registry_with_retired_gone(tmp_path)
    fixed_now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now, fail_run_for=".github/workflows/platform-ci.yml"),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    assert result.ok is False
    assert result.details["summary_stream"] == "stdout"
    payload = json.loads(result.summary)
    assert payload["partial"] is True
    assert payload["run_list_errors"] == [".github/workflows/platform-ci.yml: run list failed"]
    by_id = {r["id"]: r for r in payload["rows"]}
    assert by_id["pause.platform-container"]["last_green_run"] == "unknown"
    assert by_id["optin.air-gap"]["last_green_run"] == "unknown"
    assert by_id["pause.guild-container"]["last_green_run"] == "2026-10-01T00:00:00Z"
    assert by_id["retired.gone"]["last_green_run"] is None
    schema_text = (
        resources.files("pyforge.steward").joinpath("data", "ci-status-schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, json.loads(schema_text))

    table = run_status(deps, json_out=False)
    assert table.ok is False
    assert "summary_stream" not in table.details


def _patch_production_deps(monkeypatch: pytest.MonkeyPatch, deps: CiDeps) -> None:
    import pyforge.steward.ci as ci_mod

    monkeypatch.setattr(ci_mod, "_production_deps", lambda _root: deps)


def test_main_complete_read_exits_zero_with_the_envelope_on_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC1 through the CLI: the retired rows that 404'd every live read on 2026-10-15 leave exit 0 and stdout."""
    reg_path = _registry_with_retired_gone(tmp_path)
    fixed_now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now, fail_run_for=_RETIRED_GONE_WF),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    _patch_production_deps(monkeypatch, deps)
    assert main(["ci", "status", "--json"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert "partial" not in json.loads(out)


def test_main_partial_read_prints_the_envelope_on_stdout_and_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3: exit 1 says partial; the --json envelope stays on stdout, and the table keeps stderr."""
    reg_path = _registry_with_retired_gone(tmp_path)
    fixed_now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_make_runner(tmp_path, [], fixed_now, fail_run_for=".github/workflows/platform-ci.yml"),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    _patch_production_deps(monkeypatch, deps)
    assert main(["ci", "status", "--json"]) == 1
    out, err = capsys.readouterr()
    assert err == ""
    envelope = json.loads(out)
    assert envelope["partial"] is True
    assert envelope["rows"]

    assert main(["ci", "status"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("id\tverdict")


_MASTER_GATE_IF = "${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true') }}"


def _retired_master_tree(root: Path, kind: str) -> Path:
    """A retired row and a live control row of one kind, each workflow present and its job reading the master."""
    surfaces: list[dict] = []
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    for state in ("retired", "live"):
        row: dict[str, Any] = {
            "id": f"{state}.{kind}",
            "workflow": f".github/workflows/{state}-{kind}.yml",
            "kind": kind,
            "switch": None,
            "switch_class": "pause",
            "state": state,
            "owner": "pyforge-steward",
        }
        if kind in ("ci-job", "ci-step"):
            row["job"] = "only"
        if kind == "ci-step":
            row["step"] = "the-step"
        surfaces.append(row)
        (wf_dir / f"{state}-{kind}.yml").write_text(
            f"on: push\njobs:\n  only:\n    if: {_MASTER_GATE_IF}\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - name: the-step\n        run: echo ok\n",
            encoding="utf-8",
        )
    reg = {
        "version": 1,
        "conventions": {"pause_prefix": "PAUSE_", "enable_prefix": "ENABLE_", "master": "PAUSE_ALL_CI"},
        "surfaces": surfaces,
    }
    reg_path = root / "docs" / "governance" / "ci-surfaces.yaml"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    return reg_path


@pytest.mark.parametrize("kind", ["workflow", "ci-job", "ci-step"])
def test_108_1_ac7_a_retired_row_that_reads_the_master_is_never_paused_by_it(tmp_path: Path, kind: str) -> None:
    """Story 103.1's contract: a retired row carries ``paused_by_master: false``, read from ``state`` (Story 108.1)."""
    reg_path = _retired_master_tree(tmp_path, kind)
    fixed_now = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)
    variables = [{"name": "PAUSE_ALL_CI", "value": "true", "updatedAt": _MASTER_UPDATED}]
    deps = CiDeps(
        root=tmp_path,
        runner=_minimal_gh_runner(tmp_path, variables, fixed_now),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_status(deps, json_out=True)
    assert result.ok is True
    by_id = {r["id"]: r for r in result.details["payload"]["rows"]}

    retired = by_id[f"retired.{kind}"]
    assert retired["paused_by_master"] is False
    assert retired["verdict"] == "drift"
    assert (
        retired["detail"]
        == f"registry row retired.{kind} is retired but .github/workflows/retired-{kind}.yml still exists"
    )

    # The control: the same row declared live is gated, so the fixture does read the master.
    control = by_id[f"live.{kind}"]
    assert control["paused_by_master"] is True
    assert control["verdict"] == "paused"
    assert control["detail"] == _MASTER_PAUSE_DETAIL


# ---- Story 99.8: each surface's latest main run, and the saved envelope ------------------------------

from pyforge.steward import preflight_ci as _preflight_ci  # noqa: E402
from pyforge.steward.ci import CI_STATUS_REL, _latest_main_run  # noqa: E402


def _run(
    run_id: int,
    *,
    branch: str = "main",
    status: str = "completed",
    conclusion: str | None = "success",
    event: str = "push",
) -> dict[str, object]:
    return {
        "databaseId": run_id,
        "conclusion": conclusion,
        "status": status,
        "createdAt": f"2026-10-2{run_id % 10}T00:00:00Z",
        "event": event,
        "headBranch": branch,
    }


def test_latest_main_run_is_the_newest_completed_main_run() -> None:
    runs = [
        _run(9, status="in_progress", conclusion=None),
        _run(8, branch="feature"),
        _run(7, event="pull_request", conclusion="failure"),
        _run(17, event="pull_request_target", conclusion="failure"),
        _run(6, conclusion="failure"),
        _run(5),
    ]
    assert _latest_main_run(runs) == {"conclusion": "failure", "created_at": "2026-10-26T00:00:00Z", "run_id": 6}


def test_latest_main_run_is_null_when_no_listed_run_qualifies() -> None:
    assert _latest_main_run([]) is None
    assert _latest_main_run([_run(1, branch="feature"), _run(2, status="queued", conclusion=None)]) is None
    assert _latest_main_run([{"databaseId": 3, "status": "completed", "conclusion": "failure"}]) is None
    flagged = _latest_main_run([{**_run(4), "databaseId": True}])
    assert flagged is not None and flagged["run_id"] is None


def _runner_with_main_runs(tmp_path: Path, fixed_now: datetime, runs_by_workflow: dict[str, list[dict]]):
    base = _make_runner(tmp_path, [], fixed_now)

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        if argv[:3] == ["gh", "run", "list"]:
            assert "headBranch" in argv[argv.index("--json") + 1].split(",")
            wf = argv[argv.index("--workflow") + 1]
            if wf in runs_by_workflow:
                return _FakeProc(argv, stdout=json.dumps(runs_by_workflow[wf]))
        return base(argv, cwd)

    return runner


def _status_with_main_runs(tmp_path: Path, runs_by_workflow: dict[str, list[dict]]):
    reg_path = _write_fixture_tree(tmp_path)
    fixed_now = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_runner_with_main_runs(tmp_path, fixed_now, runs_by_workflow),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    return run_status(deps, json_out=True), fixed_now


def test_each_row_reports_its_workflows_latest_main_run(tmp_path: Path) -> None:
    import jsonschema

    result, _now = _status_with_main_runs(
        tmp_path, {".github/workflows/pyforge-station-tests.yml": [_run(4, conclusion="failure"), _run(3)]}
    )
    rows = {r["id"]: r for r in result.details["payload"]["rows"]}
    assert rows["pause.guild-container"]["latest_main_run"] == {
        "conclusion": "failure",
        "created_at": "2026-10-24T00:00:00Z",
        "run_id": 4,
    }
    assert rows["pages"]["latest_main_run"] is None
    assert rows["retired.sample"]["latest_main_run"] is None
    schema = json.loads(
        resources.files("pyforge.steward").joinpath("data", "ci-status-schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(json.loads(result.summary), schema)


def test_an_envelope_without_the_field_still_validates() -> None:
    import jsonschema

    schema = json.loads(
        resources.files("pyforge.steward").joinpath("data", "ci-status-schema.json").read_text(encoding="utf-8")
    )
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "ci_status_master_on.json"
    doc = json.loads(fixture.read_text(encoding="utf-8"))
    for row in doc["rows"]:
        row.pop("latest_main_run", None)
    jsonschema.validate(doc, schema)


def test_status_saves_its_envelope_complete_or_partial(tmp_path: Path) -> None:
    result, _now = _status_with_main_runs(tmp_path, {})
    saved = json.loads((tmp_path / CI_STATUS_REL).read_text(encoding="utf-8"))
    assert saved == result.details["payload"]

    partial_root = tmp_path / "partial"
    partial_root.mkdir()
    reg_path = _write_fixture_tree(partial_root)
    fixed_now = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=partial_root,
        runner=_make_runner(partial_root, [], fixed_now, fail_run_for=".github/workflows/platform-ci.yml"),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    partial = run_status(deps, json_out=True)
    assert partial.ok is False
    assert json.loads((partial_root / CI_STATUS_REL).read_text(encoding="utf-8"))["partial"] is True


def test_the_preflight_reads_the_path_status_writes() -> None:
    assert _preflight_ci.CI_STATUS_REL == CI_STATUS_REL


def test_an_unwritable_snapshot_never_costs_the_envelope(tmp_path: Path) -> None:
    (tmp_path / ".steward").write_text("a file, not a directory", encoding="utf-8")
    result, _now = _status_with_main_runs(tmp_path, {})
    assert result.ok is True
    assert json.loads(result.summary)["rows"]
    assert str(CI_STATUS_REL) in str(result.details["status_snapshot_error"])
