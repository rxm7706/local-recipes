"""Story 107.1 (fix under spec-pyforge-steward CAP-159): a preflight lane runs with its dependencies.

A lane starts only after every lane it ``depends-on`` is green. Before this story a lane whose dependency was not in
the run (the selection, a CI pause on the dependency alone, or the touched cut's fast core left it out) was never
ready and never blocked, and with nothing in flight ``run_preflight``'s loop spun (``DW-steward-103-6-1``,
``DW-steward-103-6-2``). Now the chosen lanes bring the lanes they depend on, as ``pixi run`` does
(:func:`preflight.close_over_dependencies`), and a lane still stranded after the cut refuses the run with
``EXIT_CONFIG`` before any install (:func:`preflight.stranded_dependencies`).

Every test runs the real functions over a fixture ``pixi.toml`` with an injected lane runner and, where the run needs
one, a monkeypatched selection; none runs pixi. Every test runs under Story 105.1's hang guard: a regression into the
spin dumps every thread's stack to ``<pytest basetemp>/hang-guard-<test>.txt`` and ends the process with exit 1
instead of hanging the steward lane (``tests/unit/test_preflight_docs_site_mutex.py`` says why it works that way).
"""

from __future__ import annotations

import faulthandler
import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from pyforge.steward import preflight, preflight_ci

INV = "pyforge-guild"
OTHER = "pyforge-other"
# The longest any test here may take before the hang guard ends the process. The slowest takes well under 2 s.
HANG_SECONDS = 120
_NOOP_INSTALL = lambda _env: 0  # noqa: E731


@pytest.fixture(autouse=True)
def _hang_guard(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    dump = tmp_path_factory.getbasetemp() / f"hang-guard-{request.node.name}.txt"
    with dump.open("w", encoding="utf-8") as handle:
        faulthandler.dump_traceback_later(HANG_SECONDS, exit=True, file=handle)
        try:
            yield
        finally:
            faulthandler.cancel_dump_traceback_later()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _pixi(lanes: list[str], deps: dict[str, list[str]] | None = None, cmds: dict[str, str] | None = None) -> str:
    """A lane list of bare tasks in the invoking environment, each ``cmd = "true"`` unless ``cmds`` names one, with
    ``deps`` as their depends-on."""
    deps = deps or {}
    cmds = cmds or {}
    body = "[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [" + ", ".join(f'"{n}"' for n in lanes)
    body += "]\n"
    for name in dict.fromkeys([*lanes, *deps, *(d for ds in deps.values() for d in ds)]):
        body += f'[feature.guild-tasks.tasks.{name}]\ncmd = "{cmds.get(name, "true")}"\n'
        if name in deps:
            body += "depends-on = [" + ", ".join(f'"{d}"' for d in deps[name]) + "]\n"
    return body


def _selection(selected: set[str], every: list[str], *changed: str) -> preflight_ci.Selection:
    """What CI's rules chose: a verdict per lane, ``selected`` the tasks that fire."""
    return preflight_ci.Selection(
        base_ref=preflight_ci.BASE_REF,
        all_reason=None,
        changed_paths=tuple(changed),
        dirty_paths=(),
        verdicts=tuple(
            preflight_ci.LaneVerdict(task, INV, True, reason="fires")
            if task in selected
            else preflight_ci.LaneVerdict(task, INV, False, workflow="w.yml", rule="paths")
            for task in every
        ),
    )


def _quiet_ci(monkeypatch: pytest.MonkeyPatch, selection: preflight_ci.Selection) -> None:
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _root: False)
    monkeypatch.setattr(preflight_ci, "select_lanes", lambda *a, **k: selection)


def _records(repo: Path) -> list[dict[str, Any]]:
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _run_record(repo: Path) -> dict[str, Any]:
    return next(record for record in reversed(_records(repo)) if "lanes" in record)


class _Intervals:
    """Each lane's start and end, recorded by an injected runner that sleeps ``seconds``; ``red`` lanes exit 1."""

    def __init__(self, seconds: float = 0.05, red: frozenset[str] = frozenset()) -> None:
        self.seconds = seconds
        self.red = red
        self.rows: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def __call__(self, ctx: preflight.LaneRunContext) -> int:
        start = time.monotonic()
        time.sleep(self.seconds)
        end = time.monotonic()
        with self._lock:
            self.rows[ctx.lane.task] = (start, end)
        return 1 if ctx.lane.task in self.red else 0

    def before(self, first: str, then: str) -> bool:
        return self.rows[first][1] <= self.rows[then][0]


def _refuse(what: str) -> Any:
    def refuse(*_args: object) -> int:
        raise AssertionError(f"{what} was reached")

    return refuse


# ---- the closure itself ------------------------------------------------------------------------------------------


def _lane(task: str, *deps: str, env: str = INV) -> preflight.Lane:
    return preflight.Lane(task, env, tuple((dep, env) for dep in deps))


def test_nothing_to_pull_in_returns_the_chosen_lanes_as_they_were() -> None:
    every = [_lane("c"), _lane("b", "c"), _lane("a", "b"), _lane("x")]
    chosen = [every[3], every[0], every[1]]  # out of declaration order, as --ignore-ci-pauses can leave it
    closure = preflight.close_over_dependencies(chosen, every)
    assert closure.lanes == tuple(chosen)
    assert closure.pulled_in == ()


def test_a_missing_dependency_is_pulled_in_transitively_in_declaration_order() -> None:
    every = [_lane("c"), _lane("b", "c"), _lane("a", "b"), _lane("x")]
    closure = preflight.close_over_dependencies([every[2], every[3]], every)
    assert [lane.task for lane in closure.lanes] == ["c", "b", "a", "x"]
    assert [(lane.task, needed_by) for lane, needed_by in closure.pulled_in] == [("c", ("b", INV)), ("b", ("a", INV))]


def test_a_pulled_in_lane_names_the_first_lane_in_run_order_that_needs_it() -> None:
    every = [_lane("c"), _lane("d1", "c"), _lane("d2", "c")]
    closure = preflight.close_over_dependencies([every[2], every[1]], every)
    assert [(lane.task, needed_by) for lane, needed_by in closure.pulled_in] == [("c", ("d2", INV))]
    assert [lane.task for lane in closure.lanes] == ["c", "d1", "d2"]


def test_a_dependency_is_a_task_in_its_own_environment() -> None:
    """Story 103.5: a lane is its task and its environment, so the same task chosen in another environment does not
    stand in for the dependency."""
    dep_other = preflight.Lane("t", OTHER)
    dep_inv = preflight.Lane("t", INV)
    needs = preflight.Lane("a", INV, (("t", OTHER),))
    closure = preflight.close_over_dependencies([dep_inv, needs], [dep_other, dep_inv, needs])
    assert closure.pulled_in == ((dep_other, ("a", INV)),)
    assert closure.lanes == (dep_other, dep_inv, needs)


def test_a_dependency_outside_the_lane_list_stays_out_for_the_refusal() -> None:
    every = [_lane("a", "ghost")]
    closure = preflight.close_over_dependencies(every, every)
    assert closure == preflight.DependencyClosure(lanes=tuple(every))
    assert preflight.stranded_dependencies(closure.lanes) == ((every[0], (("ghost", INV),)),)


def test_stranded_dependencies_names_each_lane_and_each_missing_dependency() -> None:
    lanes = [_lane("b"), _lane("a", "b", "c", "d"), _lane("e", "f")]
    assert preflight.stranded_dependencies(lanes) == (
        (lanes[1], (("c", INV), ("d", INV))),
        (lanes[2], (("f", INV),)),
    )
    assert preflight.stranded_dependencies(lanes[:1]) == ()


# ---- run_preflight -----------------------------------------------------------------------------------------------

# lint, install, build, app: app depends on build, build on install (list_preflight_lanes' declaration order).
CHAIN = _pixi(["lint", "app"], {"app": ["build"], "build": ["install"]})
CHAIN_LANES = ["lint", "install", "build", "app"]


def test_a_full_run_brings_the_dependencies_the_selection_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """DW-steward-103-6-1: the selection keeps ``app`` and drops what it depends on. Both run first, in order, the
    run exits 0, and the journal names each lane it pulled in and the lane that needs it."""
    _write(tmp_path / "pixi.toml", CHAIN)
    _quiet_ci(monkeypatch, _selection({"lint", "app"}, CHAIN_LANES))
    runs = _Intervals()
    code = preflight.run_preflight(
        tmp_path, invoking_env=INV, jobs=4, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
    )
    assert code == preflight.EXIT_OK
    assert set(runs.rows) == set(CHAIN_LANES)
    assert runs.before("install", "build") and runs.before("build", "app"), runs.rows
    record = _run_record(tmp_path)
    assert [(entry["task"], entry["status"]) for entry in record["lanes"]] == [(task, "ok") for task in CHAIN_LANES]
    assert record["selection"]["pulled_in"] == [
        {"lane": "install", "environment": INV, "reason": "build@pyforge-guild depends on it"},
        {"lane": "build", "environment": INV, "reason": "app@pyforge-guild depends on it"},
    ]
    # CI's own selection is journaled as it was: the pulled-in lanes are still what its rules skipped.
    assert [entry["lane"] for entry in record["selection"]["skipped"]] == ["install", "build"]
    err = capsys.readouterr().err
    assert "preflight: pulled in install@pyforge-guild: build@pyforge-guild depends on it\n" in err
    assert "preflight: pulled in build@pyforge-guild: app@pyforge-guild depends on it\n" in err
    assert "preflight: running 4 of 4 lanes, 0 skipped by their workflow's own rules\n" in err


def test_a_red_pulled_in_dependency_cancels_its_dependents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A pulled-in lane is a lane like any other: when it goes red, what depends on it never starts."""
    _write(tmp_path / "pixi.toml", CHAIN)
    _quiet_ci(monkeypatch, _selection({"lint", "app"}, CHAIN_LANES))
    runs = _Intervals(red=frozenset({"install"}))
    code = preflight.run_preflight(
        tmp_path, invoking_env=INV, jobs=1, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
    )
    assert code == preflight.EXIT_LANE_RED
    by_task = {entry["task"]: entry for entry in _run_record(tmp_path)["lanes"]}
    assert by_task["install"]["status"] == "red"
    assert by_task["build"]["status"] == by_task["app"]["status"] == "cancelled"
    assert "build" not in runs.rows and "app" not in runs.rows


def test_a_paused_dependency_runs_and_loses_its_paused_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 99.5's pause holds back a lane CI would not run. A dependency paused alone is still run by its
    dependent's CI job (``pixi run`` runs a task's dependencies), so the preflight runs it too, and the journal has
    its run, not a paused ``not-run`` row."""
    _write(tmp_path / "pixi.toml", _pixi(["install", "app"], {"app": ["install"]}))
    paused = preflight_ci.PausedLane("install", INV, "PAUSE_X", "2026-10-04", "2026-11-01")
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _root: True)
    monkeypatch.setattr(
        preflight_ci, "resolve_ci_vars", lambda *a, **k: preflight_ci.CiVarResolution("snapshot 1h", lambda _n: "true")
    )
    monkeypatch.setattr(preflight_ci, "list_paused_ci_surfaces", lambda *a, **k: [])
    monkeypatch.setattr(preflight_ci, "discover_paused_lanes", lambda *a, **k: [paused])
    monkeypatch.setattr(preflight_ci, "select_lanes", lambda *a, **k: _selection({"app"}, ["install", "app"]))
    runs = _Intervals()
    code = preflight.run_preflight(
        tmp_path, invoking_env=INV, jobs=2, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
    )
    assert code == preflight.EXIT_OK
    assert runs.before("install", "app"), runs.rows
    record = _run_record(tmp_path)
    assert [(entry["task"], entry["status"]) for entry in record["lanes"]] == [("install", "ok"), ("app", "ok")]
    assert all("verdict" not in entry for entry in record["lanes"])
    reason = "app@pyforge-guild depends on it, paused in CI, where its dependent's job runs it through pixi run"
    assert record["selection"]["pulled_in"] == [{"lane": "install", "environment": INV, "reason": reason}]
    err = capsys.readouterr().err
    assert "preflight: paused in CI: install (PAUSE_X since 2026-10-04, review_by 2026-11-01)" in err
    assert f"preflight: pulled in install@pyforge-guild: {reason}\n" in err


def _touched_repo(tmp_path: Path, *, fast_core_dep: str | None = None) -> Path:
    """``app``'s command names ``tools/app.py``; it depends on ``build``, whose command names ``tools/build.py``.
    ``detectors-ci`` gives its place to the fast core in a touched run; ``fast_core_dep`` gives one fast-core task a
    dependency."""
    repo = tmp_path / "repo"
    for relative in ("tools/app.py", "tools/build.py", "docs/note.md"):
        _write(repo / relative, "")
    deps = {"app": ["build"]}
    if fast_core_dep is not None:
        deps["flag-gate-check"] = [fast_core_dep]
    pixi = _pixi(
        ["detectors-ci", "app"],
        deps,
        {"app": "python tools/app.py", "build": "python tools/build.py"},
    )
    pixi += "".join(
        f'[feature.guild-tasks.tasks.{task}]\ncmd = "true"\n'
        for task in preflight.FAST_CORE_TASKS
        if task != "flag-gate-check" or fast_core_dep is None
    )
    _write(repo / "pixi.toml", pixi)
    return repo


def test_a_touched_run_keeps_the_dependency_the_selection_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Touched scope: the diff touches ``app``; the selection dropped ``build``, which ``app`` depends on. The closure
    brings ``build`` before the cut, and the cut keeps it because ``app`` depends on it."""
    repo = _touched_repo(tmp_path)
    _quiet_ci(monkeypatch, _selection({"detectors-ci", "app"}, ["detectors-ci", "build", "app"], "tools/app.py"))
    ran: list[str] = []
    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane=lambda lane: ran.append(lane.task) or 0,
        scope=preflight.SCOPE_TOUCHED,
    )
    assert code == preflight.EXIT_OK
    assert ran.index("build") < ran.index("app")
    record = _run_record(repo)
    assert record["selection"]["pulled_in"] == [
        {"lane": "build", "environment": INV, "reason": "app@pyforge-guild depends on it"}
    ]
    assert record["deferred"] == [{"lane": "detectors-ci", "environment": INV, "reason": preflight.DEFERRED_REASON}]


def test_a_lane_stranded_after_the_cut_refuses_before_any_install_or_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """DW-steward-103-6-2: a fast-core task that depends on a lane the touched cut deferred. The run refuses with
    EXIT_CONFIG, naming the lane and its dependency; no environment is installed, no lane starts, nothing is
    journaled."""
    repo = _touched_repo(tmp_path, fast_core_dep="build")
    _quiet_ci(
        monkeypatch, _selection({"detectors-ci", "build", "app"}, ["detectors-ci", "build", "app"], "docs/note.md")
    )
    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        install_environment=_refuse("pixi install"),
        run_lane=_refuse("a lane"),
        scope=preflight.SCOPE_TOUCHED,
    )
    assert code == preflight.EXIT_CONFIG
    err = capsys.readouterr().err
    assert (
        "preflight: flag-gate-check@pyforge-guild depends on build@pyforge-guild, which this run does not run\n" in err
    )
    assert err.rstrip().endswith("preflight: refusing the run before any install or lane starts")
    assert not (repo / preflight.JOURNAL_RELATIVE).exists()


# The run record of a run that pulls nothing in, as run_preflight wrote it at 2ca62dbca0 (the story's base): Story
# 107.1 must leave it as it was, key for key. Only the run's identity, the checkout's head (a git hook's GIT_DIR can
# reach it from a temp dir), the clocks and the host move between runs.
_VOLATILE = ("run_id", "started_at", "head_sha", "branch", "total_seconds", "logical_cores", "seconds")
NOTHING_PULLED_IN_RECORD = {
    "deferred": [],
    "invoking_environment": INV,
    "jobs": 1,
    "keep_going": False,
    "lanes": [
        {"environment": INV, "exit_code": 0, "start_offset": "*", "status": "ok", "task": "install"},
        {"environment": INV, "exit_code": 0, "start_offset": "*", "status": "ok", "task": "app"},
    ],
    "mode": "full",
    "selection": {
        "all_reason": None,
        "base_ref": preflight_ci.BASE_REF,
        "changed_paths": 1,
        "dirty_paths": 0,
        "mode": "diff",
        "selected": [
            {"environment": INV, "lane": "install", "reason": "fires"},
            {"environment": INV, "lane": "app", "reason": "fires"},
        ],
        "skipped": [{"environment": INV, "lane": "lint", "rule": "paths", "workflow": "w.yml"}],
    },
    "verdict": "ok",
}
NOTHING_PULLED_IN_INSTALL = {"environments": [INV], "phase": "install", "verdict": "ok"}


def _normalized(record: dict[str, Any]) -> dict[str, Any]:
    out = {key: value for key, value in record.items() if key not in _VOLATILE}
    if "lanes" in out:
        out["lanes"] = [
            {key: ("*" if key == "start_offset" else value) for key, value in lane.items() if key not in _VOLATILE}
            for lane in out["lanes"]
        ]
    return out


def test_a_run_that_pulls_nothing_in_is_todays_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every dependency already selected (``lint``, skipped, has no dependent): the run set, its order, its stderr
    and both journal records are what they were before Story 107.1, with no ``pulled_in`` key."""
    _write(tmp_path / "pixi.toml", _pixi(["install", "app", "lint"], {"app": ["install"]}))
    _quiet_ci(monkeypatch, _selection({"install", "app"}, ["install", "app", "lint"], "x/y.md"))
    ran: list[str] = []
    code = preflight.run_preflight(
        tmp_path,
        invoking_env=INV,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane=lambda lane: ran.append(lane.task) or 0,
    )
    assert code == preflight.EXIT_OK
    assert ran == ["install", "app"]
    install, run = _records(tmp_path)
    assert _normalized(install) == NOTHING_PULLED_IN_INSTALL
    assert _normalized(run) == NOTHING_PULLED_IN_RECORD
    assert set(install) == {*NOTHING_PULLED_IN_INSTALL, "run_id", "started_at", "seconds"}
    assert set(run) == {
        *NOTHING_PULLED_IN_RECORD,
        "run_id",
        "started_at",
        "head_sha",
        "branch",
        "total_seconds",
        "logical_cores",
    }
    assert capsys.readouterr().err == "preflight: running 2 of 3 lanes, 1 skipped by their workflow's own rules\n"
