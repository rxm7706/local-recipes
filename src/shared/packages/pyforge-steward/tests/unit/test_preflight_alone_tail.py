"""Story 117.30 (spec-pyforge-steward CAP-175, a fix under CAP-159): an alone-tail lane runs its last segment alone.

Doctor's five-second budget test, the last ``&&`` segment of ``pyforge-doctor-live-test``, spends more CPU when other
lanes share the cores, and went red inside a full preflight while passing alone. A lane whose task is in
``ALONE_TAIL_TASKS`` runs its earlier segments beside the other lanes and its last segment once no other lane is in
flight or ready, and no lane starts while it runs.

Every scheduling test runs the real ``run_preflight`` over a fixture ``pixi.toml`` with an injected lane runner that
records each part's start and end; none runs pixi. The fixtures are not git repositories, so selection runs every
lane. A hang guard dumps every thread's stack and ends the process rather than hang the steward lane (as in
``test_preflight_docs_site_mutex.py``).
"""

from __future__ import annotations

import faulthandler
import json
import threading
import time
import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from pyforge.steward import preflight

INV = "pyforge-guild"
TIMED = "timed-live-test"
HANG_SECONDS = 120
# A part that must overlap another is given this long, so a loaded host's thread start-up cannot hide the overlap.
OVERLAP_SECONDS = 0.6
TAIL_CMD = "pytest tests/test_budget.py -q"
HEAD_CMD = 'pytest tests -q -m \\"live_tree and not slow\\" -n auto --ignore=tests/test_budget.py'


@pytest.fixture(autouse=True)
def _hang_guard(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    dump = tmp_path_factory.getbasetemp() / f"hang-guard-{request.node.name}.txt"
    with dump.open("w", encoding="utf-8") as handle:
        faulthandler.dump_traceback_later(HANG_SECONDS, exit=True, file=handle)
        try:
            yield
        finally:
            faulthandler.cancel_dump_traceback_later()


def _pixi(
    lanes: list[str],
    *,
    cmds: dict[str, str] | None = None,
    deps: dict[str, list[str]] | None = None,
    env: dict[str, dict[str, str]] | None = None,
) -> str:
    """A lane list of bare tasks in the invoking environment: ``cmd = "true"`` unless ``cmds`` names one."""
    cmds, deps, env = cmds or {}, deps or {}, env or {}
    body = "[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [" + ", ".join(f'"{n}"' for n in lanes)
    body += "]\n"
    for name in dict.fromkeys([*lanes, *(d for ds in deps.values() for d in ds)]):
        body += f'[feature.guild-tasks.tasks.{name}]\ncmd = "{cmds.get(name, "true")}"\n'
        if name in deps:
            body += "depends-on = [" + ", ".join(f'"{d}"' for d in deps[name]) + "]\n"
        if name in env:
            body += "env = { " + ", ".join(f'{k} = "{v}"' for k, v in env[name].items()) + " }\n"
    return body


def _write_pixi(repo: Path, text: str) -> None:
    (repo / "pixi.toml").write_text(text, encoding="utf-8")


class _Parts:
    """Each lane part's start and end, recorded by an injected runner; ``codes`` and ``seconds`` set a part's exit
    code and length (default 0 and 0.3 s). A part is ``(task, part)``; a lane with no tail runs as ``whole``."""

    def __init__(
        self,
        seconds: dict[tuple[str, str], float] | None = None,
        codes: dict[tuple[str, str], int] | None = None,
    ) -> None:
        self.seconds = seconds or {}
        self.codes = codes or {}
        self.rows: dict[tuple[str, str], tuple[float, float]] = {}
        self._lock = threading.Lock()

    def __call__(self, ctx: preflight.LaneRunContext) -> int:
        key = (ctx.lane.task, ctx.part)
        start = time.monotonic()
        time.sleep(self.seconds.get(key, 0.3))
        end = time.monotonic()
        with self._lock:
            self.rows[key] = (start, end)
        return self.codes.get(key, 0)

    def overlap(self, a: tuple[str, str], b: tuple[str, str]) -> bool:
        (a0, a1), (b0, b1) = self.rows[a], self.rows[b]
        return a0 < b1 and b0 < a1


def _run(
    repo: Path,
    runner: Callable[[preflight.LaneRunContext], int],
    *,
    jobs: int = 8,
    keep_going: bool = False,
    install_environment: Callable[[str], int] = lambda _env: 0,
    tasks: frozenset[str] = frozenset({TIMED}),
    critical_path: bool = False,
    logical_cores: int | None = None,
    expected_seconds: dict[tuple[str, str], float] | None = None,
) -> int:
    return preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=jobs,
        keep_going=keep_going,
        install_environment=install_environment,
        run_lane_ctx=runner,
        alone_tail_tasks=tasks,
        critical_path=critical_path,
        logical_cores=logical_cores,
        expected_seconds=expected_seconds,
    )


def _journal_lanes(repo: Path) -> dict[str, dict]:
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").splitlines()
    record = next(row for row in map(json.loads, reversed(lines)) if "lanes" in row)
    return {lane["task"]: lane for lane in record["lanes"]}


# --- alone_tail_plan ---------------------------------------------------------------------------------------------


def test_plan_splits_the_command_at_its_last_and_and_keeps_the_task_env() -> None:
    data = tomllib.loads(_pixi([TIMED], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}, env={TIMED: {"PYTHONPATH": "src"}}))
    plan = preflight.alone_tail_plan(data, TIMED)
    assert plan is not None
    assert plan.head == (
        ("pytest", "tests", "-q", "-m", "live_tree and not slow", "-n", "auto", "--ignore=tests/test_budget.py"),
    )
    assert plan.tail == ("pytest", "tests/test_budget.py", "-q")
    assert dict(plan.env) == {"PYTHONPATH": "src"}


def test_plan_keeps_every_segment_before_the_last_as_the_head() -> None:
    data = tomllib.loads(_pixi([TIMED], cmds={TIMED: "a 1 && b 2 && c 3"}))
    plan = preflight.alone_tail_plan(data, TIMED)
    assert plan is not None
    assert plan.head == (("a", "1"), ("b", "2"))
    assert plan.tail == ("c", "3")


@pytest.mark.parametrize(
    "cmd",
    [
        "pytest tests -q",  # no tail
        "pytest tests && ",  # an empty tail
        "pytest tests | tee log && pytest b",  # a pipe needs a shell
        "pytest tests && pytest b > out.txt",  # so does a redirect
        "pytest $TESTS && pytest b",  # and an expansion
        "pytest 'unclosed && pytest b",  # an argv that does not parse
    ],
)
def test_plan_refuses_a_command_with_no_tail_it_can_run_as_argv(cmd: str) -> None:
    data = tomllib.loads(_pixi([TIMED], cmds={TIMED: cmd.replace('"', '\\"')}))
    assert preflight.alone_tail_plan(data, TIMED) is None


def test_plan_refuses_a_missing_task_and_an_env_that_expands() -> None:
    data = tomllib.loads(_pixi([TIMED], cmds={TIMED: "a && b"}, env={TIMED: {"PYTHONPATH": "$PIXI_PROJECT_ROOT"}}))
    assert preflight.alone_tail_plan(data, "no-such-task") is None
    assert preflight.alone_tail_plan(data, TIMED) is None


# --- scheduling ------------------------------------------------------------------------------------------------------


def test_the_tail_runs_after_every_other_lane_and_no_lane_overlaps_it(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi(["lane-a", "lane-b", TIMED, "lane-c"], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}))
    runs = _Parts(seconds={(TIMED, "head"): 0.1, ("lane-c", "whole"): OVERLAP_SECONDS})
    assert _run(tmp_path, runs) == preflight.EXIT_OK
    others = [("lane-a", "whole"), ("lane-b", "whole"), ("lane-c", "whole")]
    assert set(runs.rows) == {*others, (TIMED, "head"), (TIMED, "tail")}
    tail_start = runs.rows[(TIMED, "tail")][0]
    for other in others:
        assert runs.rows[other][1] <= tail_start, (other, runs.rows)
        assert not runs.overlap(other, (TIMED, "tail"))
    # The head still runs beside the other lanes, as the whole lane did.
    assert runs.overlap((TIMED, "head"), ("lane-c", "whole"))
    assert runs.rows[(TIMED, "head")][1] <= tail_start


def test_a_lane_that_depends_on_the_alone_lane_starts_after_its_tail(tmp_path: Path) -> None:
    _write_pixi(
        tmp_path,
        _pixi(["gate", "lane-a"], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}, deps={"gate": [TIMED]}),
    )
    runs = _Parts(seconds={(TIMED, "head"): 0.1})
    assert _run(tmp_path, runs) == preflight.EXIT_OK
    assert runs.rows[(TIMED, "tail")][1] <= runs.rows[("gate", "whole")][0]
    assert runs.rows[("lane-a", "whole")][1] <= runs.rows[(TIMED, "tail")][0]


def test_two_alone_tails_run_one_at_a_time(tmp_path: Path) -> None:
    other = "other-timed-test"
    _write_pixi(
        tmp_path,
        _pixi(["lane-a", TIMED, other], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}", other: f"{HEAD_CMD} && {TAIL_CMD}"}),
    )
    runs = _Parts()
    assert _run(tmp_path, runs, tasks=frozenset({TIMED, other})) == preflight.EXIT_OK
    assert not runs.overlap((TIMED, "tail"), (other, "tail"))
    for tail in ((TIMED, "tail"), (other, "tail")):
        assert runs.rows[("lane-a", "whole")][1] <= runs.rows[tail][0]
        assert runs.rows[(TIMED, "head")][1] <= runs.rows[tail][0]
        assert runs.rows[(other, "head")][1] <= runs.rows[tail][0]


def test_the_journal_keeps_one_row_with_the_tail_named(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi(["lane-a", TIMED], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}))
    runs = _Parts(seconds={(TIMED, "head"): 0.1, (TIMED, "tail"): 0.2})
    assert _run(tmp_path, runs) == preflight.EXIT_OK
    row = _journal_lanes(tmp_path)[TIMED]
    assert row["status"] == "ok"
    assert row["exit_code"] == 0
    tail = row["alone_tail"]
    assert tail["status"] == "ok"
    assert tail["exit_code"] == 0
    assert tail["seconds"] >= 0.2
    assert row["seconds"] >= tail["seconds"] + 0.1
    assert tail["start_offset"] > row["start_offset"]


def test_a_red_head_never_runs_the_tail(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi(["lane-a", TIMED], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}))
    runs = _Parts(codes={(TIMED, "head"): 1})
    assert _run(tmp_path, runs, keep_going=True) == preflight.EXIT_LANE_RED
    assert (TIMED, "tail") not in runs.rows
    assert ("lane-a", "whole") in runs.rows
    row = _journal_lanes(tmp_path)[TIMED]
    assert row["status"] == "red"
    assert "alone_tail" not in row


def test_a_red_tail_reds_the_lane_and_the_run(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi(["lane-a", TIMED], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}))
    runs = _Parts(codes={(TIMED, "tail"): 1})
    assert _run(tmp_path, runs) == preflight.EXIT_LANE_RED
    row = _journal_lanes(tmp_path)[TIMED]
    assert row["status"] == "red"
    assert row["exit_code"] == 1
    assert row["alone_tail"]["exit_code"] == 1


def test_a_red_lane_that_stops_the_run_cancels_a_waiting_tail(tmp_path: Path) -> None:
    """Without --keep-going a red lane stops the run: a head that already passed leaves its tail unrun, and the lane
    is journaled cancelled by the red lane, as a lane the stop kept from starting is."""
    _write_pixi(tmp_path, _pixi(["bad", TIMED], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}))
    runs = _Parts(seconds={(TIMED, "head"): 0.05, ("bad", "whole"): OVERLAP_SECONDS}, codes={("bad", "whole"): 1})
    assert _run(tmp_path, runs) == preflight.EXIT_LANE_RED
    assert (TIMED, "tail") not in runs.rows
    row = _journal_lanes(tmp_path)[TIMED]
    assert row["status"] == "cancelled"
    assert row["cancelled_by"] == "bad"


def test_with_keep_going_a_red_lane_still_leaves_the_tail_to_run(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi(["bad", TIMED], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}))
    runs = _Parts(seconds={(TIMED, "head"): 0.05}, codes={("bad", "whole"): 1})
    assert _run(tmp_path, runs, keep_going=True) == preflight.EXIT_LANE_RED
    assert runs.rows[("bad", "whole")][1] <= runs.rows[(TIMED, "tail")][0]
    assert _journal_lanes(tmp_path)[TIMED]["status"] == "ok"


def test_the_critical_path_scheduler_also_runs_the_tail_last_and_alone(tmp_path: Path) -> None:
    """Story 117.3's admission (longest first, by the cores a lane takes) on a two-core machine: the xdist head is
    admitted by its share, the tail still waits for every other lane and none overlaps it."""
    _write_pixi(
        tmp_path,
        _pixi(["lane-a", TIMED, "lane-b", "lane-c"], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}", "lane-c": "x -n auto"}),
    )
    runs = _Parts(seconds={(TIMED, "head"): 0.1})
    expected = {(TIMED, INV): 50.0, ("lane-a", INV): 10.0, ("lane-b", INV): 5.0, ("lane-c", INV): 20.0}
    code = _run(tmp_path, runs, critical_path=True, logical_cores=2, expected_seconds=expected)
    assert code == preflight.EXIT_OK
    others = [("lane-a", "whole"), ("lane-b", "whole"), ("lane-c", "whole")]
    for other in others:
        assert runs.rows[other][1] <= runs.rows[(TIMED, "tail")][0], (other, runs.rows)


def test_one_job_still_runs_the_tail_last(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi([TIMED, "lane-a", "lane-b"], cmds={TIMED: f"{HEAD_CMD} && {TAIL_CMD}"}))
    runs = _Parts(seconds={key: 0.05 for key in ((TIMED, "head"), (TIMED, "tail"), ("lane-a", "whole"))})
    assert _run(tmp_path, runs, jobs=1) == preflight.EXIT_OK
    assert max(end for key, (_s, end) in runs.rows.items() if key[0] != TIMED) <= runs.rows[(TIMED, "tail")][0]


def test_a_declared_task_with_no_tail_is_refused_before_any_install(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi(["lane-a", TIMED]))  # TIMED's cmd is "true": no tail
    installs: list[str] = []
    runs = _Parts()

    def install(environment: str) -> int:
        installs.append(environment)
        return 0

    assert _run(tmp_path, runs, install_environment=install) == preflight.EXIT_CONFIG
    assert installs == []
    assert runs.rows == {}


def test_a_lane_outside_the_set_runs_whole(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _pixi(["lane-a", "two-step"], cmds={"two-step": "a && b"}))
    runs = _Parts()
    assert _run(tmp_path, runs) == preflight.EXIT_OK
    assert set(runs.rows) == {("lane-a", "whole"), ("two-step", "whole")}


# --- the subprocess parts --------------------------------------------------------------------------------------------


def _coord(tmp_path: Path, plan: preflight.AloneTail) -> preflight._RunCoordinator:  # noqa: SLF001
    return preflight._RunCoordinator(  # noqa: SLF001
        repo_root=tmp_path,
        run_id="t",
        run_start=time.monotonic(),
        jobs=1,
        keep_going=False,
        alone_tails={TIMED: plan},
    )


def _ctx(tmp_path: Path, part: str) -> preflight.LaneRunContext:
    return preflight.LaneRunContext(
        lane=preflight.Lane(TIMED, "pyforge-doctor"),
        scratch_dir=tmp_path / "scratch",
        log_path=tmp_path / "lane.log",
        env={"PYTHONPATH": "inherited", "KEEP": "1"},
        part=part,
    )


def test_the_head_runs_each_segment_through_pixi_with_the_task_env_and_stops_at_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = preflight.AloneTail(head=(("a", "1"), ("b", "2"), ("c", "3")), tail=("t",), env={"PYTHONPATH": "src"})
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(_coord: object, ctx: preflight.LaneRunContext, argv: list[str], log_handle: object) -> int:
        calls.append((argv, dict(ctx.env)))
        return 2 if argv[-2:] == ["b", "2"] else 0

    monkeypatch.setattr(preflight, "_run_pixi_argv", fake_run)
    code = preflight._subprocess_lane(_coord(tmp_path, plan), _ctx(tmp_path, preflight.PART_HEAD))  # noqa: SLF001
    assert code == 2
    assert [argv for argv, _env in calls] == [
        ["pixi", "run", "--frozen", "-e", "pyforge-doctor", "--", "a", "1"],
        ["pixi", "run", "--frozen", "-e", "pyforge-doctor", "--", "b", "2"],
    ]
    assert all(env["PYTHONPATH"] == "src" and env["KEEP"] == "1" for _argv, env in calls)


def test_the_tail_runs_only_the_last_segment_and_appends_to_the_lane_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = preflight.AloneTail(head=(("a",),), tail=("pytest", "budget.py"), env={})
    calls: list[list[str]] = []

    def fake_run(_coord: object, _ctx: object, argv: list[str], log_handle: object) -> int:
        calls.append(argv)
        log_handle.write(b"tail output\n")  # type: ignore[attr-defined]
        return 0

    monkeypatch.setattr(preflight, "_run_pixi_argv", fake_run)
    (tmp_path / "lane.log").write_bytes(b"head output\n")
    code = preflight._subprocess_lane(_coord(tmp_path, plan), _ctx(tmp_path, preflight.PART_TAIL))  # noqa: SLF001
    assert code == 0
    assert calls == [["pixi", "run", "--frozen", "-e", "pyforge-doctor", "--", "pytest", "budget.py"]]
    assert (tmp_path / "lane.log").read_bytes() == b"head output\ntail output\n"


def test_the_lane_log_prints_from_an_offset(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "lane.log"
    log.write_bytes(b"head output\r\ntail output\n")
    preflight._print_lane_log(log, len(b"head output\r\n"))  # noqa: SLF001
    assert capsys.readouterr().out == "tail output\n"
    preflight._print_lane_log(log)  # noqa: SLF001
    assert capsys.readouterr().out == "head output\ntail output\n"
