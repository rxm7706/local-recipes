"""A touched-scope preflight leaves the other lanes to CI (Story 103.6, spec-pyforge-steward CAP-159).

The scope comes from ``PYFORGE_PREFLIGHT_SCOPE`` or, unset, the flag ``pyforge.steward.preflight_ci_arbitrates``.
In the touched scope a lane runs when the diff changes its station package, a path its command names, or -- for a
lint-and-types lane -- Python under ``src/``; the five fast-core detectors run in place of ``detectors-ci``; every
other lane is deferred and journaled. Every test here runs the real functions on fixture repositories; none runs pixi.
The hook's side (the skip comes first; the variable passes through) is tested beside the hook's other tests, in
``tests/scripts/test_lint_types_gate.py``.
"""

from __future__ import annotations

import json
import os
import signal
import time
import tomllib
from pathlib import Path

import pytest
from pyforge.core.flags import FlagConfigError
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.steward import preflight, preflight_budget, preflight_ci

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

flag_provider = make_flag_provider_fixture()

INV = "pyforge-guild"  # the invoking environment every bare depends-on lane runs in
_NOOP_INSTALL = lambda _env: 0  # noqa: E731

FAST_CORE = [(task, INV) for task in preflight.FAST_CORE_TASKS]

PIXI = """
[feature.guild-tasks.tasks.pr-preflight-lanes]
depends-on = [
  "lint-types",
  "detectors-ci",
  "named",
  "site-check",
  { task = "pyforge-a-test", environment = "pyforge-a" },
  { task = "pyforge-a-gate", environment = "pyforge-a" },
  { task = "pyforge-b-test", environment = "pyforge-b" },
]
[feature.guild-tasks.tasks.lint-types]
depends-on = ["ruff", "mypy"]
[feature.guild-tasks.tasks.ruff]
cmd = "python tools/lint.py ruff"
[feature.guild-tasks.tasks.mypy]
cmd = "python tools/lint.py mypy"
[feature.guild-tasks.tasks.detectors-ci]
cmd = "python tools/detectors.py --scope repo"
[feature.guild-tasks.tasks.named]
cmd = "pytest tests/named/test_named.py::test_one -q"
[feature.guild-tasks.tasks.site-check]
cmd = "python site/check.py"
depends-on = ["site-build"]
[feature.guild-tasks.tasks.site-build]
cmd = "npm ci"
cwd = "site"
[feature.a.tasks.pyforge-a-test]
cmd = "pytest src/shared/packages/pyforge-a/tests -q"
[feature.a.tasks.pyforge-a-gate]
cmd = "python tools/gate.py --base origin/main --suites unit"
[feature.b.tasks.pyforge-b-test]
cmd = "pytest src/shared/packages/pyforge-b/tests -q"
""" + "".join(f'[feature.guild-tasks.tasks.{task}]\ncmd = "true"\n' for task in preflight.FAST_CORE_TASKS)

ALL_LANES = [
    ("ruff", INV),
    ("mypy", INV),
    ("detectors-ci", INV),
    ("named", INV),
    ("site-build", INV),
    ("site-check", INV),
    ("pyforge-a-test", "pyforge-a"),
    ("pyforge-a-gate", "pyforge-a"),
    ("pyforge-b-test", "pyforge-b"),
]


def _repo(tmp_path: Path, pixi: str = PIXI) -> Path:
    repo = tmp_path / "repo"
    for relative in (
        "tools/lint.py",
        "tools/detectors.py",
        "tools/gate.py",
        "tests/named/test_named.py",
        "site/check.py",
        "site/index.html",
        "src/shared/packages/pyforge-a/src/a.py",
        "src/shared/packages/pyforge-a/tests/test_a.py",
        "src/shared/packages/django-a/src/view.py",
        "src/shared/packages/pyforge-b/tests/test_b.py",
        "docs/note.md",
    ):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    (repo / "pixi.toml").write_text(pixi, encoding="utf-8")
    return repo


def _lanes(pixi: str = PIXI) -> list[preflight.Lane]:
    return preflight.list_preflight_lanes(tomllib.loads(pixi), invoking_env=INV)


def _selection(*changed: str, dirty: tuple[str, ...] = (), all_reason: str | None = None) -> preflight_ci.Selection:
    return preflight_ci.Selection(
        base_ref=preflight_ci.BASE_REF,
        all_reason=all_reason,
        changed_paths=tuple(changed),
        dirty_paths=dirty,
        verdicts=tuple(preflight_ci.LaneVerdict(task, env, True, reason="fires") for task, env in ALL_LANES),
    )


def _cut(repo: Path, *changed: str, **kwargs: object) -> preflight.TouchedCut:
    return preflight.touched_cut(repo, _lanes(), tomllib.loads(PIXI), _selection(*changed, **kwargs))  # type: ignore[arg-type]


def _keys(lanes: tuple[preflight.Lane, ...] | list[preflight.Lane]) -> list[tuple[str, str]]:
    return [(lane.task, lane.environment) for lane in lanes]


def _run_record(repo: Path) -> dict:
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    return next(record for record in reversed(records) if "lanes" in record)


# ---- AC1: the scope ------------------------------------------------------------------------------


@flag_states(preflight.SCOPE_FLAG_KEY)
def test_unset_variable_follows_the_flag(flag_provider: dict[str, bool]) -> None:
    on = flag_provider[preflight.SCOPE_FLAG_KEY]
    choice = preflight.resolve_scope({}, flag_on=lambda: on)
    assert choice.scope == (preflight.SCOPE_TOUCHED if on else preflight.SCOPE_FULL)
    assert choice.source == f"flag {preflight.SCOPE_FLAG_KEY} {'on' if on else 'off'}"


@flag_states(preflight.SCOPE_FLAG_KEY)
@pytest.mark.parametrize("value", [preflight.SCOPE_FULL, preflight.SCOPE_TOUCHED])
def test_the_variable_wins_and_the_flag_is_not_read(flag_provider: dict[str, bool], value: str) -> None:
    def flag_on() -> bool:
        raise AssertionError("the flag must not be read when PYFORGE_PREFLIGHT_SCOPE is set")

    assert flag_provider[preflight.SCOPE_FLAG_KEY] in (True, False)
    choice = preflight.resolve_scope({preflight.SCOPE_ENV: value}, flag_on=flag_on)
    assert choice == preflight.ScopeChoice(value, f"{preflight.SCOPE_ENV}={value}")


@pytest.mark.parametrize("value", ["bogus", "Touched", "", " full"])
def test_an_unknown_scope_refuses(value: str) -> None:
    with pytest.raises(preflight.PreflightScopeError) as excinfo:
        preflight.resolve_scope({preflight.SCOPE_ENV: value}, flag_on=lambda: True)
    message = str(excinfo.value)
    assert preflight.SCOPE_FULL in message and preflight.SCOPE_TOUCHED in message


@pytest.mark.parametrize(
    ("environment", "scope"),
    [("dev", preflight.SCOPE_TOUCHED), ("staging", preflight.SCOPE_FULL), ("production", preflight.SCOPE_FULL)],
)
def test_the_shipped_flag_reads_from_the_tree(monkeypatch: pytest.MonkeyPatch, environment: str, scope: str) -> None:
    """The default reader is the one flag tree, as each environment renders it: on in dev, off elsewhere."""
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
    choice = preflight.resolve_scope({})
    assert choice.scope == scope
    assert choice.source == f"flag {preflight.SCOPE_FLAG_KEY} {'on' if scope == preflight.SCOPE_TOUCHED else 'off'}"


def test_main_refuses_an_unknown_scope_and_starts_no_lane(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(preflight, "run_preflight", lambda *a, **k: calls.append(k) or 0)
    monkeypatch.setenv(preflight.SCOPE_ENV, "bogus")
    assert preflight.main([]) == preflight.EXIT_CONFIG
    assert calls == []
    err = capsys.readouterr().err
    assert "'bogus' is not a scope" in err and "full" in err and "touched" in err


def test_main_refuses_when_the_flag_tree_cannot_be_read(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken() -> bool:
        raise FlagConfigError("PYFORGE_ENVIRONMENT='nowhere' is not an environment")

    calls: list[dict] = []
    monkeypatch.delenv(preflight.SCOPE_ENV, raising=False)
    monkeypatch.setattr(preflight, "_scope_flag_on", broken)
    monkeypatch.setattr(preflight, "run_preflight", lambda *a, **k: calls.append(k) or 0)
    assert preflight.main([]) == preflight.EXIT_CONFIG
    assert calls == []
    assert f"cannot read the flag {preflight.SCOPE_FLAG_KEY}" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("environ", "flag", "scope", "source"),
    [
        ({preflight.SCOPE_ENV: "touched"}, False, "touched", "PYFORGE_PREFLIGHT_SCOPE=touched"),
        ({preflight.SCOPE_ENV: "full"}, True, "full", "PYFORGE_PREFLIGHT_SCOPE=full"),
        ({}, True, "touched", f"flag {preflight.SCOPE_FLAG_KEY} on"),
        ({}, False, "full", f"flag {preflight.SCOPE_FLAG_KEY} off"),
    ],
)
def test_main_passes_the_resolved_scope_to_the_run(
    monkeypatch: pytest.MonkeyPatch, environ: dict, flag: bool, scope: str, source: str
) -> None:
    calls: list[dict] = []
    monkeypatch.delenv(preflight.SCOPE_ENV, raising=False)
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(preflight, "_scope_flag_on", lambda: flag)
    monkeypatch.setattr(preflight, "run_preflight", lambda *a, **k: calls.append(k) or 0)
    assert preflight.main(["--jobs", "2"]) == 0
    (kwargs,) = calls
    assert (kwargs["scope"], kwargs["scope_source"], kwargs["jobs"]) == (scope, source, 2)


def test_run_preflight_refuses_a_scope_it_does_not_know(tmp_path: Path) -> None:
    assert preflight.run_preflight(_repo(tmp_path), scope="most") == preflight.EXIT_CONFIG


# ---- AC3: the cut --------------------------------------------------------------------------------


def test_a_station_package_change_keeps_that_stations_lanes(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), "src/shared/packages/pyforge-a/src/a.py")
    assert _keys(cut.lanes) == [
        ("ruff", INV),
        ("mypy", INV),
        *FAST_CORE,
        ("pyforge-a-test", "pyforge-a"),
        ("pyforge-a-gate", "pyforge-a"),
    ]
    assert _keys(cut.deferred) == [
        ("detectors-ci", INV),
        ("named", INV),
        ("site-build", INV),
        ("site-check", INV),
        ("pyforge-b-test", "pyforge-b"),
    ]
    reasons = dict(cut.reasons)
    assert reasons[("pyforge-a-gate", "pyforge-a")].startswith("its station package src/shared/packages/pyforge-a/")
    assert reasons[("ruff", INV)].startswith("lint and types: Python under src/ changed")


DOCS_PIXI = """
[feature.guild-tasks.tasks.pr-preflight-lanes]
depends-on = [
  "detectors-ci",
  { task = "docs-site-install", environment = "site" },
  { task = "pyforge-herald-test", environment = "pyforge-herald" },
  { task = "pyforge-b-test", environment = "pyforge-b" },
]
[feature.guild-tasks.tasks.detectors-ci]
cmd = "python tools/detectors.py --scope repo"
[feature.site.tasks.docs-site-install]
cmd = "npm ci"
cwd = "docs-site"
[feature.herald.tasks.pyforge-herald-test]
cmd = "pytest src/shared/packages/pyforge-herald/tests -q"
[feature.b.tasks.pyforge-b-test]
cmd = "pytest src/shared/packages/pyforge-b/tests -q"
""" + "".join(f'[feature.guild-tasks.tasks.{task}]\ncmd = "true"\n' for task in preflight.FAST_CORE_TASKS)


def _docs_cut(tmp_path: Path, *changed: str, install_selected: bool = True) -> preflight.TouchedCut:
    repo = _repo(tmp_path, DOCS_PIXI)
    herald_test = repo / "src/shared/packages/pyforge-herald/tests/test_h.py"
    herald_test.parent.mkdir(parents=True, exist_ok=True)
    herald_test.write_text("", encoding="utf-8")
    pixi = tomllib.loads(DOCS_PIXI)
    lanes = [
        lane
        for lane in preflight.list_preflight_lanes(pixi, invoking_env=INV)
        if install_selected or lane.task != preflight.DOCS_SITE_INSTALL_TASK
    ]
    verdicts = tuple(preflight_ci.LaneVerdict(lane.task, lane.environment, True, reason="fires") for lane in lanes)
    selection = preflight_ci.Selection(preflight_ci.BASE_REF, None, tuple(changed), (), verdicts)
    return preflight.touched_cut(repo, lanes, pixi, selection)


def test_a_kept_docs_site_lane_brings_the_selected_install(tmp_path: Path) -> None:
    """Herald Story 45.1: pyforge-herald-test declares no dependency on docs-site-install (the SBOM laptop gate runs it
    and stays npm-free), so the cut keeps a selected install beside a kept docs-site lane, which reads it; the install
    is declared first, so it takes the docs-site lanes' first turn."""
    cut = _docs_cut(tmp_path, "src/shared/packages/pyforge-herald/tests/test_h.py")
    assert _keys(cut.lanes) == [
        *FAST_CORE,
        ("docs-site-install", "site"),
        ("pyforge-herald-test", "pyforge-herald"),
    ]
    assert dict(cut.reasons)[("docs-site-install", "site")] == "pyforge-herald-test@pyforge-herald reads its install"
    assert ("pyforge-b-test", "pyforge-b") in _keys(cut.deferred)


def test_the_install_stays_deferred_when_no_docs_site_lane_is_kept(tmp_path: Path) -> None:
    cut = _docs_cut(tmp_path, "src/shared/packages/pyforge-b/tests/test_b.py")
    assert _keys(cut.lanes) == [*FAST_CORE, ("pyforge-b-test", "pyforge-b")]
    assert ("docs-site-install", "site") in _keys(cut.deferred)


def test_an_install_the_selection_did_not_select_is_never_added(tmp_path: Path) -> None:
    cut = _docs_cut(tmp_path, "src/shared/packages/pyforge-herald/tests/test_h.py", install_selected=False)
    assert _keys(cut.lanes) == [*FAST_CORE, ("pyforge-herald-test", "pyforge-herald")]


def test_the_portal_package_is_the_stations_too(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), "src/shared/packages/django-a/templates/a.html")
    assert _keys(cut.lanes) == [*FAST_CORE, ("pyforge-a-test", "pyforge-a"), ("pyforge-a-gate", "pyforge-a")]


def test_a_path_the_command_names_keeps_the_lane_and_what_it_needs(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), dirty=("site/check.py",))
    assert _keys(cut.lanes) == [*FAST_CORE, ("site-build", INV), ("site-check", INV)]
    assert dict(cut.reasons)[("site-build", INV)] == "site-check@pyforge-guild depends on it"


def test_a_pytest_node_id_names_its_file(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), "tests/named/test_named.py")
    assert _keys(cut.lanes) == [*FAST_CORE, ("named", INV)]


def test_the_cwd_is_not_a_path_the_command_names(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), "site/index.html")
    assert _keys(cut.lanes) == FAST_CORE


@pytest.mark.parametrize(
    ("changed", "lint"),
    [("src/shared/packages/pyforge-b/README.md", False), ("src/platform/app.py", True), ("scripts/x.py", False)],
)
def test_lint_and_types_run_when_python_under_src_changed(tmp_path: Path, changed: str, lint: bool) -> None:
    kept = _keys(_cut(_repo(tmp_path), changed).lanes)
    assert (("ruff", INV) in kept and ("mypy", INV) in kept) is lint


def test_a_change_to_the_lint_script_keeps_the_lint_lanes(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), "tools/lint.py")
    assert _keys(cut.lanes) == [("ruff", INV), ("mypy", INV), *FAST_CORE]


def test_a_diff_that_touches_nothing_keeps_only_the_fast_core(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), "docs/note.md", "pixi.toml")
    assert _keys(cut.lanes) == FAST_CORE
    assert _keys(cut.deferred) == ALL_LANES
    assert _keys(cut.fast_core) == FAST_CORE


def test_detectors_ci_kept_itself_needs_no_fast_core(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), "tools/detectors.py")
    assert _keys(cut.lanes) == [("detectors-ci", INV)]
    assert cut.fast_core == ()


def test_the_fast_core_runs_in_the_environment_detectors_ci_ran_in(tmp_path: Path) -> None:
    lanes = preflight.list_preflight_lanes(tomllib.loads(PIXI), invoking_env="local-recipes")
    cut = preflight.touched_cut(_repo(tmp_path), lanes, tomllib.loads(PIXI), _selection("docs/note.md"))
    assert _keys(cut.fast_core) == [(task, "local-recipes") for task in preflight.FAST_CORE_TASKS]


def test_an_unreadable_diff_keeps_every_lane_and_says_so(tmp_path: Path) -> None:
    cut = _cut(_repo(tmp_path), all_reason="refs/remotes/origin/main does not exist")
    assert _keys(cut.lanes) == ALL_LANES
    assert cut.deferred == ()
    assert cut.note is not None and "refs/remotes/origin/main does not exist" in cut.note


def test_a_missing_fast_core_task_is_a_config_error(tmp_path: Path) -> None:
    pixi = PIXI.replace('[feature.guild-tasks.tasks.chain-completeness-check]\ncmd = "true"\n', "")
    with pytest.raises(preflight.PreflightConfigError, match="chain-completeness-check"):
        preflight.touched_cut(_repo(tmp_path, pixi), _lanes(pixi), tomllib.loads(pixi), _selection("docs/note.md"))


def test_command_paths_reads_only_existing_repository_paths(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    data = tomllib.loads(PIXI)
    assert preflight_ci.command_paths(repo, data, "pyforge-a-gate") == ("tools/gate.py",)
    assert preflight_ci.command_paths(repo, data, "named") == ("tests/named/test_named.py",)
    assert preflight_ci.command_paths(repo, data, "site-build") == ()
    assert preflight_ci.command_paths(repo, data, "lint-types") == ()
    assert preflight_ci.command_paths(repo, data, "no-such-task") == ()
    assert preflight_ci.command_paths(
        repo, {"feature": {"f": {"tasks": {"t": {"cmd": ["python", "tools/lint.py"]}}}}}, "t"
    ) == ("tools/lint.py",)
    escaping = {"feature": {"f": {"tasks": {"t": {"cmd": "cat ../outside . $HOME/x 'unclosed"}}}}}
    assert preflight_ci.command_paths(repo, escaping, "t") == ()


def test_station_package_dirs_come_from_the_environment_name(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert preflight_ci.station_package_dirs(repo, "pyforge-a") == (
        "src/shared/packages/pyforge-a",
        "src/shared/packages/django-a",
    )
    assert preflight_ci.station_package_dirs(repo, "pyforge-b") == ("src/shared/packages/pyforge-b",)
    assert preflight_ci.station_package_dirs(repo, "pyforge-guild") == ()
    assert preflight_ci.station_package_dirs(repo, "pyforge-") == ()
    assert preflight_ci.station_package_dirs(repo, "site") == ()


def test_the_lint_lanes_are_the_lint_types_closure() -> None:
    assert preflight_ci.lint_types_tasks(tomllib.loads(PIXI)) == frozenset({"ruff", "mypy"})
    assert preflight_ci.lint_types_tasks({}) == frozenset()


# ---- AC4: the run and the journal ----------------------------------------------------------------


def _quiet_ci(monkeypatch: pytest.MonkeyPatch, selection: preflight_ci.Selection) -> None:
    monkeypatch.setattr(preflight_ci, "_flag_on", lambda _root: False)
    monkeypatch.setattr(preflight_ci, "select_lanes", lambda *a, **k: selection)


def test_a_touched_run_runs_the_cut_and_journals_what_it_deferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _quiet_ci(monkeypatch, _selection("src/shared/packages/pyforge-a/README.md"))
    ran: list[tuple[str, str]] = []
    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane=lambda lane: ran.append((lane.task, lane.environment)) or 0,
        scope=preflight.SCOPE_TOUCHED,
        scope_source="PYFORGE_PREFLIGHT_SCOPE=touched",
    )
    assert code == preflight.EXIT_OK
    assert ran == [*FAST_CORE, ("pyforge-a-test", "pyforge-a"), ("pyforge-a-gate", "pyforge-a")]
    record = _run_record(repo)
    assert record["mode"] == "touched"
    assert record["deferred"] == [
        {"lane": task, "environment": env, "reason": "CI arbitrates"}
        for task, env in ALL_LANES
        if (task, env) not in {("pyforge-a-test", "pyforge-a"), ("pyforge-a-gate", "pyforge-a")}
    ]
    assert [(e["task"], e["environment"]) for e in record["lanes"]] == ran
    assert len(record["selection"]["selected"]) == len(ALL_LANES)  # the CI selection is journaled as before
    captured = capsys.readouterr()
    assert (
        "preflight: scope touched (PYFORGE_PREFLIGHT_SCOPE=touched): 7 lanes run, 7 deferred -- CI arbitrates"
        in captured.out
    )
    assert (
        "preflight: fast core, in place of detectors-ci@pyforge-guild: spec-surface-check, flag-gate-check"
        in captured.out
    )
    for entry in record["deferred"]:
        assert f"preflight: deferred (CI arbitrates): {entry['lane']}@{entry['environment']}\n" in captured.out
    assert (
        "running 7 lanes (2 of 9 and 5 fast-core detectors), 0 skipped by their workflow's own rules, 7 deferred to CI"
        in captured.err
    )


def test_a_full_run_is_todays_run_and_journals_nothing_deferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _quiet_ci(monkeypatch, _selection("src/shared/packages/pyforge-a/tests/test_a.py"))
    ran: list[tuple[str, str]] = []
    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane=lambda lane: ran.append((lane.task, lane.environment)) or 0,
    )
    assert code == preflight.EXIT_OK
    assert ran == ALL_LANES
    record = _run_record(repo)
    assert (record["mode"], record["deferred"]) == ("full", [])
    assert {
        "run_id",
        "started_at",
        "head_sha",
        "branch",
        "logical_cores",
        "jobs",
        "keep_going",
        "total_seconds",
        "verdict",
        "invoking_environment",
        "selection",
        "lanes",
    } <= set(record)
    captured = capsys.readouterr()
    assert "preflight: scope full\n" in captured.out
    assert "deferred" not in captured.out
    assert "running 9 of 9 lanes, 0 skipped by their workflow's own rules\n" in captured.err


def test_an_unreadable_diff_runs_everything_and_says_so_on_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    _quiet_ci(monkeypatch, _selection(all_reason="refs/remotes/origin/main does not exist"))
    ran: list[tuple[str, str]] = []
    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane=lambda lane: ran.append((lane.task, lane.environment)) or 0,
        scope=preflight.SCOPE_TOUCHED,
    )
    assert code == preflight.EXIT_OK
    assert ran == ALL_LANES
    assert _run_record(repo)["deferred"] == []
    assert (
        "the diff cannot be read (refs/remotes/origin/main does not exist), so every selected lane runs"
        in capsys.readouterr().out
    )


def test_a_touched_run_with_a_missing_fast_core_task_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pixi = PIXI.replace('[feature.guild-tasks.tasks.flag-gate-check]\ncmd = "true"\n', "")
    repo = _repo(tmp_path, pixi)
    _quiet_ci(monkeypatch, _selection("docs/note.md"))
    code = preflight.run_preflight(
        repo, invoking_env=INV, install_environment=_NOOP_INSTALL, run_lane=lambda _l: 0, scope=preflight.SCOPE_TOUCHED
    )
    assert code == preflight.EXIT_CONFIG
    assert not (repo / preflight.JOURNAL_RELATIVE).exists()


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_an_interrupted_touched_run_journals_its_scope_and_what_it_deferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _quiet_ci(monkeypatch, _selection("tests/named/test_named.py"))

    def interrupt(_lane: preflight.Lane) -> int:
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(0.2)
        return 0

    code = preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane=interrupt,
        scope=preflight.SCOPE_TOUCHED,
    )
    assert code == preflight.EXIT_INTERRUPT
    record = _run_record(repo)
    assert record["verdict"] == "interrupted"
    assert record["mode"] == "touched"
    assert ("named", INV) not in {(d["lane"], d["environment"]) for d in record["deferred"]}
    assert ("pyforge-b-test", "pyforge-b") in {(d["lane"], d["environment"]) for d in record["deferred"]}


# ---- AC5: old records still parse ----------------------------------------------------------------


def test_the_budget_reads_records_with_and_without_the_scope(tmp_path: Path) -> None:
    def record(run_id: str, **extra: object) -> dict:
        return {
            "run_id": run_id,
            "total_seconds": 30.0,
            "logical_cores": 4,
            "selection": {"selected": [{"lane": "pyforge-a-test", "environment": "pyforge-a", "reason": "x"}]},
            "lanes": [{"task": "pyforge-a-test", "environment": "pyforge-a", "status": "ok", "seconds": 30.0}],
            **extra,
        }

    journal = tmp_path / "runs.jsonl"
    old, new = (
        record("old"),
        record("new", mode="touched", deferred=[{"lane": "x", "environment": "e", "reason": "CI arbitrates"}]),
    )
    journal.write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n", encoding="utf-8")
    judged = [preflight_budget.evaluate_budget(tmp_path, run_id=rid, journal_path=journal) for rid in ("old", "new")]
    assert [j.exit_code for j in judged] == [preflight_budget.EXIT_OK, preflight_budget.EXIT_OK]
    assert [j.lines[0].replace("run new", "run old") for j in judged] == [judged[0].lines[0]] * 2


# ---- Story 71.14: the dependency-completeness lane -------------------------------------------------

DEPS_PIXI = """
[feature.pyforge-ci.tasks.pyforge-deps-test]
cmd = "python -m pytest tests/packaging -q"
"""
DEPS_LANE = preflight.Lane("pyforge-deps-test", "pyforge-ci")


@pytest.mark.parametrize(
    "changed",
    [
        "src/shared/packages/pyforge-atlas/pyproject.toml",
        "src/shared/packages/pyforge-atlas/pixi.toml",
        "src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/tier3_sources.py",
        "src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py",
        "pixi.toml",
        "Containerfile",
        "Containerfile.platform",
    ],
)
def test_the_dependency_lane_runs_when_a_package_manifest_or_its_source_changed(tmp_path: Path, changed: str) -> None:
    verdict = preflight_ci.touch_verdict(
        _repo(tmp_path), DEPS_LANE, tomllib.loads(DEPS_PIXI), [changed], lint_tasks=frozenset()
    )
    assert verdict.touched
    assert changed in verdict.reason


@pytest.mark.parametrize(
    "changed",
    [
        "docs/note.md",
        "src/shared/packages/pyforge-atlas/README.md",
        "src/shared/packages/pyforge-atlas/tests/unit/test_x.py",
        "src/shared/packages/pyforge-atlas/src/pyforge/atlas/conf/base/catalog.yml",
        "src/shared/packages/django-atlas/pyproject.toml",
        "src/platform/app.py",
        "src/shared/packages/pyforge-atlas/pixi.lock",
        "docker/Containerfile",
    ],
)
def test_the_dependency_lane_is_deferred_when_nothing_it_reads_changed(tmp_path: Path, changed: str) -> None:
    verdict = preflight_ci.touch_verdict(
        _repo(tmp_path), DEPS_LANE, tomllib.loads(DEPS_PIXI), [changed], lint_tasks=frozenset()
    )
    assert not verdict.touched


def test_the_package_rule_belongs_to_the_dependency_lane_alone(tmp_path: Path) -> None:
    other = preflight.Lane("pyforge-b-test", "pyforge-b")
    changed = ["src/shared/packages/pyforge-a/pyproject.toml"]
    verdict = preflight_ci.touch_verdict(_repo(tmp_path), other, tomllib.loads(PIXI), changed, lint_tasks=frozenset())
    assert not verdict.touched


def test_the_shipped_lane_list_carries_the_dependency_lane() -> None:
    """AC1: the repository's own ``pr-preflight-lanes`` lists the task in ``pyforge-ci``."""
    root = Path(__file__).resolve().parents[6]
    lanes = preflight.list_preflight_lanes(
        tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8")), invoking_env=INV
    )
    assert (preflight_ci.PACKAGING_TESTS_TASK, "pyforge-ci") in _keys(lanes)
