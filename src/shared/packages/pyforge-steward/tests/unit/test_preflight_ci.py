"""Story 99.5 — preflight honors CI pause switches (CAP-166 FR-39)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.steward import preflight, preflight_ci

flag_provider = make_flag_provider_fixture()

REPO_ROOT = Path(__file__).resolve().parents[6]


def _write_ci_vars(root: Path, variables: dict[str, str], *, fetched_at: datetime) -> None:
    path = root / ".steward" / "ci-vars.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "fetched_at": fetched_at.isoformat(),
                "repo": "rxm7706/local-recipes",
                "variables": variables,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _mini_registry(root: Path) -> None:
    reg = {
        "version": 1,
        "conventions": {"master": "PAUSE_ALL_CI"},
        "surfaces": [
            {
                "id": "station-tests.guild-container",
                "workflow": ".github/workflows/pyforge-station-tests.yml",
                "job": "guild-container",
                "switch": "PAUSE_CONTAINER_BUILDS",
                "switch_class": "pause",
                "state": "live",
                "local_twin": "pyforge-steward-guild-image-build",
                "paused_since": "2026-10-04",
                "review_by": "2026-11-01",
            },
        ],
    }
    path = root / "docs" / "governance" / "ci-surfaces.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(reg, sort_keys=False), encoding="utf-8")


@flag_states("pyforge.steward.ci_pause_control")
def test_snapshot_wins_when_fresh(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    flag_provider["pyforge.steward.ci_pause_control"] = True
    root = tmp_path / "repo"
    root.mkdir()
    _mini_registry(root)
    now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
    _write_ci_vars(
        root,
        {"PAUSE_CONTAINER_BUILDS": "true"},
        fetched_at=now - timedelta(hours=1),
    )
    resolution = preflight_ci.resolve_ci_vars(root, flag_on=True, now=now)
    assert resolution.source == "snapshot 1h"
    assert resolution.lookup("PAUSE_CONTAINER_BUILDS") == "true"


@flag_states("pyforge.steward.ci_pause_control")
def test_stale_snapshot_falls_back_to_declared(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    flag_provider["pyforge.steward.ci_pause_control"] = True
    root = tmp_path / "repo"
    root.mkdir()
    _mini_registry(root)
    now = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
    _write_ci_vars(
        root,
        {"PAUSE_CONTAINER_BUILDS": "false"},
        fetched_at=now - timedelta(hours=25),
    )
    resolution = preflight_ci.resolve_ci_vars(root, flag_on=True, now=now)
    assert resolution.source == "declared"
    assert resolution.lookup("PAUSE_CONTAINER_BUILDS") == ""


@flag_states("pyforge.steward.ci_pause_control")
def test_unreadable_snapshot_uses_declared(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    flag_provider["pyforge.steward.ci_pause_control"] = True
    root = tmp_path / "repo"
    root.mkdir()
    _mini_registry(root)
    (root / ".steward").mkdir(parents=True)
    (root / ".steward" / "ci-vars.json").write_text("{not json", encoding="utf-8")
    resolution = preflight_ci.resolve_ci_vars(root, flag_on=True)
    assert resolution.source == "declared"
    assert resolution.note == "snapshot unreadable"


@flag_states("pyforge.steward.ci_pause_control")
def test_flag_off_uses_declared_only(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    flag_provider["pyforge.steward.ci_pause_control"] = False
    root = tmp_path / "repo"
    root.mkdir()
    _mini_registry(root)
    _write_ci_vars(root, {"PAUSE_CONTAINER_BUILDS": "true"}, fetched_at=datetime.now(tz=UTC))
    resolution = preflight_ci.resolve_ci_vars(root, flag_on=False)
    assert resolution.source == "declared"


def test_emit_twin_banner_prints_paused_surface(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _mini_registry(root)
    _write_ci_vars(
        root,
        {"PAUSE_CONTAINER_BUILDS": "true"},
        fetched_at=datetime.now(tz=UTC),
    )

    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _root: True)
    preflight_ci.emit_twin_banner(root, "guild_image_ci")
    err = capsys.readouterr().err
    assert "paused in CI: pyforge-steward-guild-image-build" in err
    assert "PAUSE_CONTAINER_BUILDS" in err


@flag_states("pyforge.steward.ci_pause_control")
def test_run_preflight_journals_paused_skip(
    tmp_path: Path, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    flag_provider["pyforge.steward.ci_pause_control"] = True
    from test_preflight_selection import INVOKING_ENV, STEWARD_PLACEHOLDER, lanes_and_pixi, make_repo

    repo = make_repo(tmp_path, {STEWARD_PLACEHOLDER: "touch\n"})
    _mini_registry(repo)
    _write_ci_vars(
        repo,
        {"PAUSE_CONTAINER_BUILDS": "true"},
        fetched_at=datetime.now(tz=UTC),
    )
    lanes, _pixi = lanes_and_pixi(repo)
    target = lanes[0]
    paused = preflight_ci.PausedLane(
        target.task,
        target.environment,
        "PAUSE_CONTAINER_BUILDS",
        "2026-10-04",
        "2026-11-01",
    )
    monkeypatch.setattr(
        preflight_ci,
        "discover_paused_lanes",
        lambda *a, **k: [paused],
    )
    monkeypatch.setattr(
        preflight_ci, "resolve_ci_vars", lambda *a, **k: preflight_ci.CiVarResolution("snapshot 1h", lambda n: "true")
    )
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _r: True)
    ran: list[tuple[str, str]] = []
    code = preflight.run_preflight(
        repo,
        invoking_env=INVOKING_ENV,  # the lanes' own environment, as the paused lane names it
        jobs=1,
        install_environment=lambda _e: 0,
        run_lane=lambda lane: ran.append((lane.task, lane.environment)) or 0,
    )
    assert code == 0
    assert (target.task, target.environment) not in ran
    journal = repo / preflight.JOURNAL_RELATIVE
    text = journal.read_text(encoding="utf-8")
    assert "skipped: paused in CI (PAUSE_CONTAINER_BUILDS since 2026-10-04, review_by 2026-11-01)" in text


@flag_states("pyforge.steward.ci_pause_control")
def test_ignore_ci_pauses_journals_override(
    tmp_path: Path, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    flag_provider["pyforge.steward.ci_pause_control"] = True
    from test_preflight_selection import INVOKING_ENV, STEWARD_PLACEHOLDER, lanes_and_pixi, make_repo

    repo = make_repo(tmp_path, {STEWARD_PLACEHOLDER: "touch\n"})
    lanes, _pixi = lanes_and_pixi(repo)
    target = lanes[0]
    paused = preflight_ci.PausedLane(
        target.task,
        target.environment,
        "PAUSE_X",
        "2026-10-04",
        "2026-11-01",
    )
    monkeypatch.setattr(preflight_ci, "discover_paused_lanes", lambda *a, **k: [paused])
    monkeypatch.setattr(
        preflight_ci,
        "resolve_ci_vars",
        lambda *a, **k: preflight_ci.CiVarResolution("snapshot 1h", lambda n: "true"),
    )
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _r: True)
    ran: list[tuple[str, str]] = []

    def _run(lane: preflight.Lane) -> int:
        ran.append((lane.task, lane.environment))
        return 0

    code = preflight.run_preflight(
        repo,
        invoking_env=INVOKING_ENV,  # the lanes' own environment, as the paused lane names it
        jobs=1,
        ignore_ci_pauses=True,
        install_environment=lambda _e: 0,
        run_lane=_run,
    )
    assert code == 0
    assert (target.task, target.environment) in ran
    journal = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8")
    assert "ci_pause_override" in journal
    assert "--ignore-ci-pauses" in journal
