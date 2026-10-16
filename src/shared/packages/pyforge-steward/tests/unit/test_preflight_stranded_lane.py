"""Story 107.1 (fix under spec-pyforge-steward CAP-159): a stranded preflight lane is refused, never pulled in.

A lane starts only after every lane it ``depends-on`` is green. Before this story a lane whose dependency was not in
the run (CI's selection, a CI pause on the dependency alone, or the touched cut's fast core left it out) was never
ready and never blocked, and with nothing in flight ``run_preflight``'s loop spun (``DW-steward-103-6-1``,
``DW-steward-103-6-2``). Now such a run refuses with ``EXIT_CONFIG`` before any install or lane starts
(:func:`preflight.stranded_dependencies`), naming each lane, why it runs, each missing dependency, what CI does with
it, and the fixes (:func:`preflight.stranded_lane_message`). It never pulls the dependency in: CI's selection leaves
one out only when nothing in CI runs it with the lane, so running it here could turn CI's red into a local green
(the review's ruling, recorded in the story spec).

Every test runs the real functions over a fixture ``pixi.toml`` with an injected lane runner and, where the run needs
one, a monkeypatched selection; none runs pixi. A refused run's install and lane runner raise if reached, so a run
that got past the refusal fails at once instead of hanging. Every test also runs under Story 105.1's hang guard: a
regression into the spin dumps every thread's stack to ``<pytest basetemp>/hang-guard-<test>.txt`` and ends the
process with exit 1 instead of hanging the steward lane (``tests/unit/test_preflight_docs_site_mutex.py`` says why it
works that way).
"""

from __future__ import annotations

import faulthandler
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from pyforge.steward import preflight, preflight_ci

INV = "pyforge-guild"
OTHER = "pyforge-other"
# The longest any test here may take before the hang guard ends the process. The slowest takes well under 1 s.
HANG_SECONDS = 120
_NOOP_INSTALL = lambda _env: 0  # noqa: E731
REFUSED = "preflight: refusing the run before any install or lane starts"
CMD_MATCH = "coverage-gates.yml job 'named-module-gates' fires"  # how a command-line-matched lane's verdict reads


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


def _selection(selected: set[str], every: list[str], *changed: str, reason: str = "fires") -> preflight_ci.Selection:
    """What CI's rules chose: a verdict per lane, ``selected`` the tasks that fire, each with ``reason``."""
    return preflight_ci.Selection(
        base_ref=preflight_ci.BASE_REF,
        all_reason=None,
        changed_paths=tuple(changed),
        dirty_paths=(),
        verdicts=tuple(
            preflight_ci.LaneVerdict(task, INV, True, reason=reason)
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


def _refuse(what: str) -> Any:
    def refuse(*_args: object) -> int:
        raise AssertionError(f"{what} was reached")

    return refuse


def _refused_run(repo: Path, **kwargs: Any) -> int:
    """``run_preflight`` with an install and a lane runner that fail the test if the run reaches either."""
    return preflight.run_preflight(
        repo, invoking_env=INV, install_environment=_refuse("pixi install"), run_lane=_refuse("a lane"), **kwargs
    )


def _refusal(err: str) -> list[str]:
    """The refusal block: every stderr line from the first stranded lane's to the refusal line."""
    lines = err.splitlines()
    start = next(index for index, line in enumerate(lines) if " runs (" in line)
    return lines[start:]


# ---- the check itself --------------------------------------------------------------------------------------------


def _lane(task: str, *deps: str, env: str = INV) -> preflight.Lane:
    return preflight.Lane(task, env, tuple((dep, env) for dep in deps))


def test_stranded_dependencies_names_each_lane_and_each_missing_dependency() -> None:
    lanes = [_lane("b"), _lane("a", "b", "c", "d"), _lane("e", "f")]
    assert preflight.stranded_dependencies(lanes) == (
        (lanes[1], (("c", INV), ("d", INV))),
        (lanes[2], (("f", INV),)),
    )


def test_a_run_that_holds_every_dependency_strands_nothing() -> None:
    assert preflight.stranded_dependencies([_lane("c"), _lane("b", "c"), _lane("a", "b")]) == ()
    assert preflight.stranded_dependencies([]) == ()


def test_a_dependency_is_a_task_in_its_own_environment() -> None:
    """Story 103.5: a lane is its task and its environment, so the same task in another environment does not stand
    in for the dependency."""
    needs = preflight.Lane("a", INV, (("t", OTHER),))
    assert preflight.stranded_dependencies([preflight.Lane("t", INV), needs]) == ((needs, (("t", OTHER),)),)


def test_the_no_counterpart_reason_is_the_one_the_selection_gives() -> None:
    """The message tells a lane no CI step runs by its verdict's reason; pin the prefix to the reader's own text."""
    selected, reason, _sites = preflight_ci._outcome([])  # noqa: SLF001 -- the reader's verdict for a lane no step runs
    assert selected
    assert reason.startswith(preflight.NO_CI_COUNTERPART)


# ---- run_preflight refuses ---------------------------------------------------------------------------------------

# lint, install, build, app: app depends on build, build on install (list_preflight_lanes' declaration order).
CHAIN = _pixi(["lint", "app"], {"app": ["build"], "build": ["install"]})
CHAIN_LANES = ["lint", "install", "build", "app"]


def test_a_full_run_whose_selection_drops_a_dependency_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """DW-steward-103-6-1: CI's reader selects ``app`` by its command line and drops ``build``, which ``app`` depends
    on. The run refuses with exit 2; no environment is installed, no lane starts, nothing is journaled."""
    _write(tmp_path / "pixi.toml", CHAIN)
    _quiet_ci(monkeypatch, _selection({"lint", "app"}, CHAIN_LANES, reason=CMD_MATCH))
    assert _refused_run(tmp_path) == preflight.EXIT_CONFIG
    assert _refusal(capsys.readouterr().err) == [
        f"preflight: app@pyforge-guild runs ({CMD_MATCH}) but depends on build@pyforge-guild, which this run does "
        "not run",
        "preflight:   CI runs app's command without build@pyforge-guild: the step that selects it runs the command, "
        "not `pixi run app`, which is what runs a task's dependencies",
        "preflight:   fix: make the CI step run `pixi run app`, or drop app's depends-on",
        REFUSED,
    ]
    assert not (tmp_path / preflight.JOURNAL_RELATIVE).exists()


def test_a_dependency_paused_in_ci_strands_its_dependent_and_the_run_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 99.5's pause holds back ``install``, which ``app`` (selected by its command line) depends on: refused,
    after the pause banner, before any install."""
    _write(tmp_path / "pixi.toml", _pixi(["install", "app"], {"app": ["install"]}))
    paused = preflight_ci.PausedLane("install", INV, "PAUSE_X", "2026-10-04", "2026-11-01")
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _root: True)
    monkeypatch.setattr(
        preflight_ci, "resolve_ci_vars", lambda *a, **k: preflight_ci.CiVarResolution("snapshot 1h", lambda _n: "true")
    )
    monkeypatch.setattr(preflight_ci, "list_paused_ci_surfaces", lambda *a, **k: [])
    monkeypatch.setattr(preflight_ci, "discover_paused_lanes", lambda *a, **k: [paused])
    monkeypatch.setattr(
        preflight_ci, "select_lanes", lambda *a, **k: _selection({"app"}, ["install", "app"], reason=CMD_MATCH)
    )
    assert _refused_run(tmp_path) == preflight.EXIT_CONFIG
    err = capsys.readouterr().err
    assert "preflight: paused in CI: install (PAUSE_X since 2026-10-04, review_by 2026-11-01)" in err
    assert _refusal(err)[0] == (
        f"preflight: app@pyforge-guild runs ({CMD_MATCH}) but depends on install@pyforge-guild, which this run does "
        "not run"
    )
    assert _refusal(err)[-1] == REFUSED
    assert not (tmp_path / preflight.JOURNAL_RELATIVE).exists()


def test_a_lane_no_ci_step_runs_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A lane with no CI counterpart always runs here; CI runs it neither with its dependency nor without."""
    _write(tmp_path / "pixi.toml", CHAIN)
    reason = "no CI counterpart in .github/workflows (always runs)"
    _quiet_ci(monkeypatch, _selection({"lint", "app"}, CHAIN_LANES, reason=reason))
    assert _refused_run(tmp_path) == preflight.EXIT_CONFIG
    assert _refusal(capsys.readouterr().err)[1:] == [
        "preflight:   no CI step runs app, so CI never runs it, with build@pyforge-guild or without",
        "preflight:   fix: make the CI step run `pixi run app`, or drop app's depends-on",
        REFUSED,
    ]


def _touched_repo(tmp_path: Path, *, fast_core_dep: str | None = None) -> Path:
    """``app``'s command names ``tools/app.py``; it depends on ``build``, whose command names ``tools/build.py``.
    ``detectors-ci`` gives its place to the fast core in a touched run; ``fast_core_dep`` gives ``flag-gate-check`` a
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


def test_a_touched_run_whose_kept_lane_lost_its_dependency_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Touched scope: the diff touches ``app``, which the cut keeps; CI's selection dropped ``build``, which ``app``
    depends on. The cut keeps a kept lane's dependencies only from the selected lanes, so ``app`` is stranded."""
    repo = _touched_repo(tmp_path)
    selection = _selection({"detectors-ci", "app"}, ["detectors-ci", "build", "app"], "tools/app.py", reason=CMD_MATCH)
    _quiet_ci(monkeypatch, selection)
    assert _refused_run(repo, scope=preflight.SCOPE_TOUCHED) == preflight.EXIT_CONFIG
    assert _refusal(capsys.readouterr().err) == [
        f"preflight: app@pyforge-guild runs ({CMD_MATCH}) but depends on build@pyforge-guild, which this run does "
        "not run",
        "preflight:   CI runs app's command without build@pyforge-guild: the step that selects it runs the command, "
        "not `pixi run app`, which is what runs a task's dependencies",
        "preflight:   fix: make the CI step run `pixi run app`, or drop app's depends-on",
        REFUSED,
    ]
    assert not (repo / preflight.JOURNAL_RELATIVE).exists()


def test_a_fast_core_task_whose_dependency_the_cut_deferred_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """DW-steward-103-6-2: a fast-core task that depends on a lane the touched cut deferred. Refused, naming the
    fast-core reason and the fast core's own fixes."""
    repo = _touched_repo(tmp_path, fast_core_dep="build")
    every = ["detectors-ci", "build", "app"]
    _quiet_ci(monkeypatch, _selection(set(every), every, "docs/note.md"))
    assert _refused_run(repo, scope=preflight.SCOPE_TOUCHED) == preflight.EXIT_CONFIG
    assert _refusal(capsys.readouterr().err) == [
        "preflight: flag-gate-check@pyforge-guild runs (fast core, in place of detectors-ci@pyforge-guild) but "
        "depends on build@pyforge-guild, which this run does not run",
        "preflight:   CI runs flag-gate-check inside detectors-ci (scripts/detectors.py), never as "
        "`pixi run flag-gate-check`, so never with build@pyforge-guild",
        "preflight:   fix: drop flag-gate-check's depends-on, or take flag-gate-check out of FAST_CORE_TASKS",
        REFUSED,
    ]
    assert not (repo / preflight.JOURNAL_RELATIVE).exists()


# The run record of a run that strands nothing, as run_preflight wrote it at 2ca62dbca0 (the story's base): Story
# 107.1 must leave it as it was, key for key. Only the run's identity, the checkout's head (a git hook's GIT_DIR can
# reach it from a temp dir), the clocks and the host move between runs.
_VOLATILE = ("run_id", "started_at", "head_sha", "branch", "total_seconds", "logical_cores", "seconds")
NOTHING_STRANDED_RECORD = {
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
NOTHING_STRANDED_INSTALL = {"environments": [INV], "phase": "install", "verdict": "ok"}


def _normalized(record: dict[str, Any]) -> dict[str, Any]:
    out = {key: value for key, value in record.items() if key not in _VOLATILE}
    if "lanes" in out:
        out["lanes"] = [
            {key: ("*" if key == "start_offset" else value) for key, value in lane.items() if key not in _VOLATILE}
            for lane in out["lanes"]
        ]
    return out


def test_a_run_that_strands_nothing_is_todays_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every dependency selected (``lint``, skipped, has no dependent): the run set, its order, its stderr and both
    journal records are what they were before Story 107.1."""
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
    assert _normalized(install) == NOTHING_STRANDED_INSTALL
    assert _normalized(run) == NOTHING_STRANDED_RECORD
    assert set(install) == {*NOTHING_STRANDED_INSTALL, "run_id", "started_at", "seconds"}
    assert set(run) == {
        *NOTHING_STRANDED_RECORD,
        "run_id",
        "started_at",
        "head_sha",
        "branch",
        "total_seconds",
        "logical_cores",
    }
    assert capsys.readouterr().err == "preflight: running 2 of 3 lanes, 1 skipped by their workflow's own rules\n"
