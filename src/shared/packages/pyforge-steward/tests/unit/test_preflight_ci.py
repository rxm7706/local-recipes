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


def test_a_row_without_a_local_twin_matches_no_lane() -> None:
    """Most registry rows declare no local twin; the lookup skips them instead of raising IndexError.

    Found 2026-10-15 by a full-scope pr-preflight with CI pauses on: the first paused-only lane reached a
    row with no `local_twin` and `"".split()[0]` crashed the whole run.
    """
    registry = {
        "surfaces": [
            {"id": "no-twin"},
            {"id": "blank-twin", "local_twin": "   "},
            {"id": "null-twin", "local_twin": None},
            {"id": "image", "local_twin": "platform-ci-local --images"},
        ]
    }
    assert preflight_ci._registry_row_for_lane(registry, "test-ci") is None
    assert preflight_ci._registry_row_for_lane(registry, "platform-ci-local") == registry["surfaces"][3]


# ---- Story 99.8: the red-main banner --------------------------------------------------------------

_NOW_998 = datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)


def _write_status(root: Path, rows: list[dict], *, fetched_at: str = "2026-10-25T10:00:00+00:00") -> None:
    path = root / preflight_ci.CI_STATUS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"fetched_at": fetched_at, "repo": "o/r", "rate_limit": {}, "rows": rows}), encoding="utf-8"
    )


def _main_row(row_id: str, conclusion: str, run_id: int | None = 7) -> dict:
    return {
        "id": row_id,
        "latest_main_run": {"conclusion": conclusion, "created_at": "2026-10-25T09:00:00Z", "run_id": run_id},
    }


def test_a_red_main_run_prints_one_line_for_every_surface_it_covers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_status(
        tmp_path,
        [
            _main_row("kedro-viz-publish.publish", "failure"),
            _main_row("kedro-viz-publish.vizro", "failure"),
            _main_row("pages", "success", run_id=8),
            _main_row("detectors.detectors", "timed_out", run_id=9),
            _main_row("lint-types", "cancelled", run_id=10),
            {"id": "never-ran", "latest_main_run": None},
            {"id": "older-envelope"},
        ],
    )
    preflight_ci.print_main_red_banner(tmp_path, now=_NOW_998)
    lines = capsys.readouterr().err.splitlines()
    assert lines == [
        "preflight: main is red on kedro-viz-publish.publish, kedro-viz-publish.vizro: failure, run 7 (2026-10-25T09:00:00Z)",
        "preflight: main is red on detectors.detectors: timed_out, run 9 (2026-10-25T09:00:00Z)",
    ]


def test_a_green_main_prints_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_status(tmp_path, [_main_row("pages", "success"), _main_row("x", "skipped", 2), _main_row("y", "neutral", 3)])
    preflight_ci.print_main_red_banner(tmp_path, now=_NOW_998)
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    ("setup", "needle"),
    [
        ("missing", "no ci status snapshot"),
        ("stale", "is 26h old"),
        ("corrupt", "is unreadable"),
        ("no-rows", "is unreadable"),
        ("no-time", "no readable fetched_at"),
        ("not-utf8", "is unreadable"),
        ("future", "is in the future"),
    ],
)
def test_a_snapshot_that_cannot_answer_says_so_in_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], setup: str, needle: str
) -> None:
    path = tmp_path / preflight_ci.CI_STATUS_REL
    if setup == "stale":
        _write_status(tmp_path, [_main_row("pages", "failure")], fetched_at="2026-10-24T10:00:00+00:00")
    elif setup == "corrupt":
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
    elif setup == "no-rows":
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"fetched_at": "2026-10-25T10:00:00+00:00"}), encoding="utf-8")
    elif setup == "no-time":
        _write_status(tmp_path, [_main_row("pages", "failure")], fetched_at="")
    elif setup == "not-utf8":
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"fetched_at": "2026-10-25T10:00:00+00:00", "rows": ["\xff\xfe"]}')
    elif setup == "future":
        _write_status(tmp_path, [_main_row("pages", "failure")], fetched_at="2026-10-25T13:00:00+00:00")
    preflight_ci.print_main_red_banner(tmp_path, now=_NOW_998)
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("preflight: main CI state unknown: ")
    assert needle in lines[0]
    assert "pyforge steward ci status" in lines[0]


def test_odd_rows_are_judged_without_raising(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_status(
        tmp_path,
        [
            "not a row",
            {"id": ["a", "list"], "latest_main_run": {"conclusion": "failure", "created_at": None, "run_id": None}},
            {"id": {"a": "dict"}, "latest_main_run": {"conclusion": "failure", "run_id": "12"}},
            {"id": "flag", "latest_main_run": {"conclusion": "failure", "run_id": True}},
            {"id": "one", "latest_main_run": {"conclusion": "failure", "run_id": 1}},
            {"id": "bad-run", "latest_main_run": "failure"},
        ],
    )
    preflight_ci.print_main_red_banner(tmp_path, now=_NOW_998)
    lines = capsys.readouterr().err.splitlines()
    assert "preflight: main is red on one: failure, run 1" in lines
    assert "preflight: main is red on flag: failure, run ?" in lines
    assert len(lines) == 4


def test_the_banner_never_raises(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_root: Path, *, now: datetime | None = None) -> tuple[list, str | None]:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(preflight_ci, "red_main_runs", boom)
    preflight_ci.print_main_red_banner(tmp_path, now=_NOW_998)
    assert capsys.readouterr().err == "preflight: main CI state unknown: the ci status snapshot could not be judged (RuntimeError)\n"
