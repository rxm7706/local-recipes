"""A preflight lane is its task and its environment (Story 103.5, spec-pyforge-steward CAP-159).

``pr-preflight-lanes`` may name one task in two environments -- atlas Story 31.1 adds ``mypy`` in
``pyforge-foundry-full`` beside the Guild's. Each test here builds such a lane list and proves the
runner keeps the two lanes apart wherever it selects, runs, orders, journals, logs and budgets them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pyforge.steward import preflight, preflight_budget, preflight_ci, preflight_xdist

INV = "inv"  # the invoking environment every bare depends-on lane runs in
OTHER = "other"
_NOOP_INSTALL = lambda _env: 0  # noqa: E731

TWIN_PIXI = (
    "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
    'depends-on = ["a", { task = "a", environment = "other" }]\n'
    '[feature.guild-tasks.tasks.a]\ncmd = "true"\n'
)


def _repo(tmp_path: Path, pixi: str = TWIN_PIXI) -> Path:
    """A directory that is not a git repository: selection cannot read a diff, so every lane runs."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text(pixi, encoding="utf-8")
    return repo


def _run_record(repo: Path) -> dict:
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    return next(record for record in reversed(records) if "lanes" in record)


def _entries(record: dict) -> list[tuple[str, str, str, int]]:
    return [(e["task"], e["environment"], e["status"], e["exit_code"]) for e in record["lanes"]]


def test_one_task_in_two_environments_is_two_lanes() -> None:
    import tomllib

    lanes = preflight.list_preflight_lanes(tomllib.loads(TWIN_PIXI), invoking_env=INV)
    assert [(lane.task, lane.environment) for lane in lanes] == [("a", INV), ("a", OTHER)]


def test_both_lanes_of_one_task_run_and_journal_their_own_results(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC1, AC2: both lanes run, each with its own context, and each journals its own outcome."""
    repo = _repo(tmp_path)
    contexts: list[preflight.LaneRunContext] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        contexts.append(ctx)
        return 0 if ctx.lane.environment == INV else 3

    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        keep_going=True,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_LANE_RED
    assert [(c.lane.task, c.lane.environment) for c in contexts] == [("a", INV), ("a", OTHER)]
    assert len({c.log_path for c in contexts}) == 2
    assert len({c.scratch_dir for c in contexts}) == 2
    assert len({c.env["TMPDIR"] for c in contexts}) == 2
    record = _run_record(repo)
    assert _entries(record) == [("a", INV, "ok", 0), ("a", OTHER, "red", 3)]
    assert record["verdict"] == "red"
    err = capsys.readouterr().err
    other_log = contexts[1].log_path
    assert f"lane 'a' in environment {OTHER!r} exited 3 (log: {other_log})" in err
    assert f"red lane 'a' in environment {OTHER!r} (log: {other_log})" in err
    assert f"in environment {INV!r} exited" not in err
    assert f"red lane 'a' in environment {INV!r}" not in err


def test_each_lane_of_one_task_writes_its_own_log(tmp_path: Path) -> None:
    """AC3: real subprocesses; each lane's log is ``<task>@<environment>.log`` and holds only its own output."""
    repo = _repo(tmp_path)

    def argv(lane: preflight.Lane) -> list[str]:
        code = 0 if lane.environment == INV else 1
        return [sys.executable, "-c", f"print('output of a in {lane.environment}'); raise SystemExit({code})"]

    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=2,
        keep_going=True,
        install_environment=_NOOP_INSTALL,
        scratch_parent=tmp_path / "scratch",
        subprocess_argv_for_lane=argv,
    )
    assert code == preflight.EXIT_LANE_RED  # a red run keeps its scratch root
    (root,) = (tmp_path / "scratch").glob("pyforge-preflight-*")
    inv_log = root / f"{preflight.lane_label('a', INV)}.log"
    other_log = root / f"{preflight.lane_label('a', OTHER)}.log"
    assert inv_log.name == "a@inv.log"
    assert inv_log.read_text(encoding="utf-8") == f"output of a in {INV}\n"
    assert other_log.read_text(encoding="utf-8") == f"output of a in {OTHER}\n"
    assert not (root / "a.log").exists()
    assert sorted(p.name for p in root.iterdir() if p.is_dir()) == ["a@inv", "a@other"]
    assert _entries(_run_record(repo)) == [("a", INV, "ok", 0), ("a", OTHER, "red", 1)]


@pytest.mark.parametrize(
    ("keep_going", "status", "by_key"),
    [(False, "cancelled", "cancelled_by"), (True, "not-run", "blocked_by")],
)
def test_a_stop_names_the_environment_of_the_lane_that_caused_it(
    tmp_path: Path, keep_going: bool, status: str, by_key: str
) -> None:
    """AC4: a dependent of the red twin is journaled with that twin's task and environment."""
    repo = _repo(
        tmp_path,
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["a", { task = "a", environment = "other" }, "c"]\n'
        '[feature.guild-tasks.tasks.a]\ncmd = "true"\n'
        '[feature.guild-tasks.tasks.c]\ncmd = "true"\n'
        'depends-on = [{ task = "a", environment = "other" }]\n',
    )
    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        keep_going=keep_going,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=lambda ctx: 0 if ctx.lane.environment == INV else 1,
        scratch_parent=tmp_path / "scratch",
    )
    assert code == preflight.EXIT_LANE_RED
    by_lane = {(e["task"], e["environment"]): e for e in _run_record(repo)["lanes"]}
    assert by_lane[("a", INV)]["status"] == "ok"
    assert by_lane[("a", OTHER)]["status"] == "red"
    dependent = by_lane[("c", INV)]
    assert dependent["status"] == status
    assert dependent[by_key] == "a"
    assert dependent[f"{by_key}_environment"] == OTHER


def test_the_journal_record_only_gains_optional_fields() -> None:
    """AC10: a plain lane result keeps its keys; an interrupt names no environment."""
    plain = preflight._lane_result_dict(preflight.LaneResult("a", INV, 1.5, 0, "ok", 0.25))  # noqa: SLF001
    assert set(plain) == {"task", "environment", "seconds", "exit_code", "status", "start_offset"}
    interrupted = preflight._lane_result_dict(  # noqa: SLF001
        preflight.LaneResult("a", INV, 1.0, -15, "cancelled", 0.0, cancelled_by="interrupt")
    )
    assert interrupted["cancelled_by"] == "interrupt"
    assert "cancelled_by_environment" not in interrupted
    blocked = preflight._lane_result_dict(  # noqa: SLF001
        preflight.LaneResult("c", INV, 0.0, 0, "not-run", 0.0, blocked_by="a", blocked_by_environment=OTHER)
    )
    assert (blocked["blocked_by"], blocked["blocked_by_environment"]) == ("a", OTHER)


def test_a_pause_on_one_lane_leaves_its_twin_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC5: only the paused lane is held back and journaled with its pause; its twin still runs."""
    repo = _repo(tmp_path)
    paused = preflight_ci.PausedLane("a", OTHER, "PAUSE_X", "2026-10-04", "2026-11-01")
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _root: True)
    monkeypatch.setattr(
        preflight_ci, "resolve_ci_vars", lambda *a, **k: preflight_ci.CiVarResolution("snapshot 1h", lambda _n: "")
    )
    monkeypatch.setattr(preflight_ci, "list_paused_ci_surfaces", lambda *a, **k: [])
    monkeypatch.setattr(preflight_ci, "discover_paused_lanes", lambda *a, **k: [paused])
    ran: list[preflight.LaneKey] = []

    def run(lane: preflight.Lane) -> int:
        ran.append((lane.task, lane.environment))
        return 0

    code = preflight.run_preflight(repo, invoking_env=INV, jobs=1, install_environment=_NOOP_INSTALL, run_lane=run)
    assert code == preflight.EXIT_OK
    assert ran == [("a", INV)]
    by_lane = {(e["task"], e["environment"]): e for e in _run_record(repo)["lanes"]}
    assert by_lane[("a", INV)]["status"] == "ok"
    assert by_lane[("a", OTHER)]["status"] == "not-run"
    assert by_lane[("a", OTHER)]["verdict"] == paused.journal_verdict()


def test_selection_keeps_each_lane_of_one_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Selection: a verdict per lane decides that lane alone, and the journal names each with its environment."""
    repo = _repo(tmp_path)
    selection = preflight_ci.Selection(
        base_ref=preflight_ci.BASE_REF,
        all_reason=None,
        changed_paths=(),
        dirty_paths=(),
        verdicts=(
            preflight_ci.LaneVerdict("a", INV, True, reason="fires"),
            preflight_ci.LaneVerdict("a", OTHER, False, workflow="w.yml", rule="paths"),
        ),
    )
    monkeypatch.setattr(preflight_ci, "select_lanes", lambda *a, **k: selection)
    ran: list[preflight.LaneKey] = []
    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane=lambda lane: ran.append((lane.task, lane.environment)) or 0,
    )
    assert code == preflight.EXIT_OK
    assert ran == [("a", INV)]
    record = _run_record(repo)
    assert _entries(record) == [("a", INV, "ok", 0)]
    assert [(e["lane"], e["environment"]) for e in record["selection"]["selected"]] == [("a", INV)]
    assert [(e["lane"], e["environment"]) for e in record["selection"]["skipped"]] == [("a", OTHER)]


def _budget_selection(*lanes: tuple[str, str]) -> dict:
    return {"selected": [{"lane": task, "environment": env, "reason": "test"} for task, env in lanes]}


def test_budget_counts_station_lanes_by_task_and_environment() -> None:
    """AC8: one station suite in two environments is two station lanes, not one."""
    one = _budget_selection(("pyforge-atlas-test", "pyforge-atlas"), ("lint-types", "pyforge-guild"))
    two = _budget_selection(("pyforge-atlas-test", "pyforge-atlas"), ("pyforge-atlas-test", "pyforge-foundry-full"))
    assert preflight_budget.is_single_station_budget(one) is True
    assert preflight_budget.is_single_station_budget(two) is False


def test_budget_lines_name_each_lane_with_its_environment() -> None:
    """AC8: the slowest lanes are labelled ``<task>@<environment>``; an entry without one by its task."""
    run = {
        "run_id": "r",
        "total_seconds": 90.0,
        "logical_cores": 16,
        "selection": _budget_selection(("mypy", "pyforge-guild"), ("mypy", "pyforge-foundry-full")),
        "lanes": [
            {"task": "mypy", "environment": "pyforge-guild", "seconds": 10.0, "status": "ok"},
            {"task": "mypy", "environment": "pyforge-foundry-full", "seconds": 70.0, "status": "ok"},
            {"task": "legacy", "seconds": 5.0, "status": "ok"},
        ],
    }
    judgement = preflight_budget.judge_run(run, budget_seconds=60, install_seconds=[])
    assert judgement.exit_code == preflight_budget.EXIT_OVER_BUDGET
    (line,) = judgement.lines
    assert "slowest lanes: mypy@pyforge-foundry-full 70.0s, mypy@pyforge-guild 10.0s, legacy 5.0s" in line


def test_xdist_shares_are_keyed_by_lane() -> None:
    """AC8: two lanes of one ``-n auto`` task each get a share, keyed by ``(task, environment)``."""
    import tomllib

    pixi = tomllib.loads('[feature.x.tasks.suite]\ncmd = "pytest t -q -n auto"\n')
    mapping = preflight_xdist.lane_xdist_worker_map(
        lanes=[("suite", INV), ("suite", OTHER)],
        pixi_data=pixi,
        logical_cores=8,
        pool_jobs=4,
    )
    assert mapping == {("suite", INV): 4, ("suite", OTHER): 4}
