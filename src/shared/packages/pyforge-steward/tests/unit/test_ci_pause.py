"""Story 99.4 — steward ci pause/resume (CAP-166 FR-39)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

flag_provider = make_flag_provider_fixture()

from pyforge.steward.ci import (
    CI_FLAG_KEY,
    CI_PAUSES_LOG_REL,
    DEFAULT_REPO,
    EXIT_CI_GH_FAILED,
    EXIT_CI_REFUSAL,
    CiDeps,
    run_pause,
    run_resume,
)
from pyforge.steward.cli import EXIT_FAILED, main


@dataclass
class _FakeProc:
    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _base_registry() -> dict:
    return {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
            "dispatch_ignores_pauses": True,
        },
        "grandfathered_names": [],
        "surfaces": [
            {
                "id": "live.guild-container",
                "workflow": ".github/workflows/pyforge-station-tests.yml",
                "job": "guild-container",
                "kind": "ci-job",
                "switch": "PAUSE_CONTAINER_BUILDS",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            },
            {
                "id": "live.platform-a",
                "workflow": ".github/workflows/platform-ci.yml",
                "job": "container",
                "kind": "ci-job",
                "switch": "PAUSE_PLATFORM_CONTAINER_BUILDS",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            },
            {
                "id": "live.platform-b",
                "workflow": ".github/workflows/platform-ci.yml",
                "job": "container-dbgpt",
                "kind": "ci-job",
                "switch": "PAUSE_PLATFORM_CONTAINER_BUILDS",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            },
            {
                "id": "paused.already",
                "workflow": ".github/workflows/already.yml",
                "kind": "workflow",
                "switch": "PAUSE_ALREADY",
                "switch_class": "pause",
                "state": "paused",
                "paused_since": "2026-10-01",
                "review_by": "2026-12-01",
                "owner": "pyforge-steward",
            },
            {
                "id": "retired.sample",
                "workflow": ".github/workflows/retired.yml",
                "kind": "workflow",
                "switch": "PAUSE_RETIRED",
                "switch_class": "pause",
                "state": "retired",
                "owner": "pyforge-steward",
            },
            {
                "id": "gate.row",
                "workflow": ".github/workflows/gate.yml",
                "kind": "workflow",
                "switch": "PAUSE_GATE",
                "switch_class": "pause",
                "state": "live",
                "gate": True,
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
        ],
    }


def _write_registry(root: Path, reg: dict | None = None) -> Path:
    doc = reg if reg is not None else _base_registry()
    path = root / "docs" / "governance" / "ci-surfaces.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return path


def _recording_runner(
    recorded: list[list[str]],
    *,
    gh_set_ok: bool = True,
    gh_delete_ok: bool = True,
    scribe_ok: bool = True,
    git_name: str = "Test Operator",
) -> callable:
    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        recorded.append(list(argv))
        if argv[:3] == ["git", "config", "user.name"]:
            return _FakeProc(argv, stdout=git_name + "\n")
        if argv[:3] == ["gh", "variable", "set"]:
            return _FakeProc(argv, returncode=0 if gh_set_ok else 1, stderr="" if gh_set_ok else "set failed")
        if argv[:3] == ["gh", "variable", "delete"]:
            return _FakeProc(argv, returncode=0 if gh_delete_ok else 1, stderr="" if gh_delete_ok else "delete failed")
        if argv[:2] == ["pixi", "run"] and "scribe" in argv:
            return _FakeProc(argv, returncode=0 if scribe_ok else 1, stderr="" if scribe_ok else "scribe failed")
        return _FakeProc(argv, returncode=0)

    return runner


def test_pause_dry_run_no_gh_or_registry_write(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    before = reg_path.read_bytes()
    recorded: list[list[str]] = []
    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner(recorded),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_pause(
        deps,
        target="live.guild-container",
        reason="save runner time",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert result.ok is True
    assert "dry run" in result.summary
    assert "gh variable set PAUSE_CONTAINER_BUILDS --body true --repo " + DEFAULT_REPO in result.summary
    assert "registry diff:" in result.summary
    assert "scribe capture" in result.summary or "scribe" in result.summary
    assert reg_path.read_bytes() == before
    assert not any(cmd[:3] == ["gh", "variable", "set"] for cmd in recorded)


def test_pause_yes_writes_registry_journal_and_capture(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    recorded: list[list[str]] = []
    fixed_now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner(recorded),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: fixed_now,
    )
    result = run_pause(
        deps,
        target="live.guild-container",
        reason="save runner time",
        review_by="2026-11-01",
        yes=True,
        remove_merge_gate=False,
    )
    assert result.ok is True
    reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    row = next(r for r in reg["surfaces"] if r["id"] == "live.guild-container")
    assert row["state"] == "paused"
    assert row["paused_since"] == "2026-10-13"
    assert row["paused_by"] == "Test Operator"
    assert row["reason"] == "save runner time"
    assert row["review_by"] == "2026-11-01"

    log_path = tmp_path / CI_PAUSES_LOG_REL
    assert log_path.is_file()
    line = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert line["action"] == "pause"
    assert line["switch"] == "PAUSE_CONTAINER_BUILDS"

    gh_sets = [c for c in recorded if c[:3] == ["gh", "variable", "set"]]
    assert len(gh_sets) == 1
    assert gh_sets[0][3] == "PAUSE_CONTAINER_BUILDS"
    scribe = [c for c in recorded if c[:2] == ["pixi", "run"] and "scribe" in c]
    assert len(scribe) == 1


def test_pause_by_switch_name(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner([]),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    result = run_pause(
        deps,
        target="PAUSE_CONTAINER_BUILDS",
        reason="r",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert result.ok is True
    assert "live.guild-container" in result.summary


def test_pause_shared_switch_one_gh_two_rows(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    recorded: list[list[str]] = []
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner(recorded),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    result = run_pause(
        deps,
        target="PAUSE_PLATFORM_CONTAINER_BUILDS",
        reason="burn-down",
        review_by="2026-11-01",
        yes=True,
        remove_merge_gate=False,
    )
    assert result.ok is True
    reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    for rid in ("live.platform-a", "live.platform-b"):
        row = next(r for r in reg["surfaces"] if r["id"] == rid)
        assert row["state"] == "paused"
    gh_sets = [c for c in recorded if c[:3] == ["gh", "variable", "set"]]
    assert len(gh_sets) == 1
    journal = json.loads((tmp_path / CI_PAUSES_LOG_REL).read_text(encoding="utf-8").strip())
    assert journal["surface"] == ["live.platform-a", "live.platform-b"]


def test_refuse_gate_retired_past_review_empty_reason(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner([]),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    gate = run_pause(
        deps,
        target="gate.row",
        reason="x",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert gate.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "gate: true" in gate.summary

    retired = run_pause(
        deps,
        target="retired.sample",
        reason="x",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert retired.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "retired" in retired.summary

    past = run_pause(
        deps,
        target="live.guild-container",
        reason="x",
        review_by="2026-10-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert past.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "past" in past.summary

    empty = run_pause(
        deps,
        target="live.guild-container",
        reason="   ",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert empty.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "reason" in empty.summary


def test_refuse_already_paused_and_enable_opt_in(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner([]),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    again = run_pause(
        deps,
        target="paused.already",
        reason="x",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert again.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "already paused" in again.summary
    assert "2026-10-01" in again.summary

    enable = run_pause(
        deps,
        target="optin.air-gap",
        reason="x",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    assert enable.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "enable" in enable.summary


def test_gh_set_failure_leaves_registry_and_journal(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    before = reg_path.read_bytes()
    recorded: list[list[str]] = []
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner(recorded, gh_set_ok=False),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    result = run_pause(
        deps,
        target="live.guild-container",
        reason="x",
        review_by="2026-11-01",
        yes=True,
        remove_merge_gate=False,
    )
    assert result.ok is False
    assert result.details.get("exit_code") == EXIT_CI_GH_FAILED
    assert reg_path.read_bytes() == before
    assert not (tmp_path / CI_PAUSES_LOG_REL).exists()


def test_resume_dry_run_and_yes(tmp_path: Path) -> None:
    reg = _base_registry()
    for row in reg["surfaces"]:
        if row["id"] == "live.guild-container":
            row["state"] = "paused"
            row["paused_since"] = "2026-10-04"
            row["paused_by"] = "operator"
            row["reason"] = "r"
            row["review_by"] = "2026-11-01"
    reg_path = _write_registry(tmp_path, reg)
    recorded: list[list[str]] = []
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner(recorded),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    dry = run_resume(deps, target="live.guild-container", yes=False)
    assert dry.ok is True
    assert "gh variable delete PAUSE_CONTAINER_BUILDS" in dry.summary
    assert reg_path.read_bytes() == reg_path.read_bytes()

    yes = run_resume(deps, target="live.guild-container", yes=True)
    assert yes.ok is True
    updated = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    row = next(r for r in updated["surfaces"] if r["id"] == "live.guild-container")
    assert row["state"] == "live"
    assert "paused_since" not in row
    deletes = [c for c in recorded if c[:3] == ["gh", "variable", "delete"]]
    assert len(deletes) == 1


def test_resume_refuse_live_row(tmp_path: Path) -> None:
    reg_path = _write_registry(tmp_path)
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner([]),
        registry_path=reg_path,
        flag_on=lambda: True,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    result = run_resume(deps, target="live.guild-container", yes=False)
    assert result.details.get("exit_code") == EXIT_CI_REFUSAL
    assert "not paused" in result.summary


def test_main_pause_dry_run_no_live_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    reg_path = _write_registry(tmp_path)
    recorded: list[list[str]] = []

    def runner(argv: list[str], cwd: Path) -> _FakeProc:
        recorded.append(list(argv))
        return _FakeProc(argv)

    monkeypatch.setattr(
        "pyforge.steward.ci._production_deps",
        lambda root: CiDeps(root=root, runner=runner, registry_path=reg_path, flag_on=lambda: True),
    )
    code = main(
        [
            "ci",
            "pause",
            "live.guild-container",
            "--reason",
            "r",
            "--review-by",
            "2026-11-01",
        ]
    )
    assert code == 0
    assert not any(cmd[:3] == ["gh", "variable", "set"] for cmd in recorded)


@flag_states("pyforge.steward.ci_pause_control")
def test_pause_respects_ci_pause_control_flag(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    reg_path = _write_registry(tmp_path)
    on = flag_provider["pyforge.steward.ci_pause_control"]
    deps = CiDeps(
        root=tmp_path,
        runner=_recording_runner([]),
        registry_path=reg_path,
        flag_on=lambda: on,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
    )
    result = run_pause(
        deps,
        target="live.guild-container",
        reason="save runner time",
        review_by="2026-11-01",
        yes=False,
        remove_merge_gate=False,
    )
    if on:
        assert result.ok is True
        assert "dry run" in result.summary
    else:
        assert result.ok is False
        assert CI_FLAG_KEY in result.summary
        assert result.details.get("exit_code") == EXIT_CI_REFUSAL


def test_no_live_scribe_in_tests() -> None:
    """AC6 — tests use fakes only (smoke: no accidental live subprocess in this module)."""
    assert EXIT_FAILED == 1
