"""Story 105.1 (fix under spec-pyforge-steward CAP-159): the preflight never runs two docs-site lanes at once.

Every test runs the real ``run_preflight`` (or the real pool function) over a fixture ``pixi.toml`` with an injected
lane runner; none runs pixi. The fixtures are not git repositories, so selection runs every lane (no
``refs/remotes/origin/main``), and the service keys come from the fixture workflows alone
(``preflight_ci.static_service_mutex_keys``).

Every test runs under a hang guard: a scheduler or lock regression into a spin or a deadlock dumps every thread's
stack to ``<pytest basetemp>/hang-guard-<test>.txt`` and ends the process with exit 1
(``faulthandler.dump_traceback_later(..., exit=True)``) instead of hanging the steward lane. pytest captures stderr,
so the stacks go to that file, which a red preflight lane keeps in its scratch. ``run_preflight`` installs a SIGINT
handler, so it has to stay on the main thread; faulthandler's watchdog is a thread of its own and needs no signal.
"""

from __future__ import annotations

import faulthandler
import json
import threading
import time
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest

from pyforge.steward import preflight, preflight_ci

_NOOP_INSTALL = lambda _env: 0  # noqa: E731
INV = "pyforge-guild"
POSTGRES = "services:postgres"
DOCS = preflight.DOCS_SITE_MUTEX_KEY
# A test that asserts two lanes DO overlap gives each this long, so a loaded host's thread start-up cannot hide it.
OVERLAP_SECONDS = 0.6
# The longest any test here may take before the hang guard ends the process. The slowest takes about 2 s.
HANG_SECONDS = 120


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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pixi(lanes: list[str], deps: dict[str, list[str]] | None = None) -> str:
    """A lane list of bare tasks, each ``cmd = "true"`` in the invoking environment, with ``deps`` as depends-on."""
    deps = deps or {}
    body = "[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [" + ", ".join(f'"{n}"' for n in lanes)
    body += "]\n"
    for name in dict.fromkeys([*lanes, *(d for ds in deps.values() for d in ds)]):
        body += f'[feature.guild-tasks.tasks.{name}]\ncmd = "true"\n'
        if name in deps:
            body += "depends-on = [" + ", ".join(f'"{d}"' for d in deps[name]) + "]\n"
    return body


class _Intervals:
    """Each lane's start and end, recorded by an injected runner that sleeps ``seconds``."""

    def __init__(self, seconds: float = 0.3) -> None:
        self.seconds = seconds
        self.rows: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def __call__(self, ctx: preflight.LaneRunContext) -> int:
        start = time.monotonic()
        time.sleep(self.seconds)
        end = time.monotonic()
        with self._lock:
            self.rows[ctx.lane.task] = (start, end)
        return 0

    def overlap(self, a: str, b: str) -> bool:
        (a0, a1), (b0, b1) = self.rows[a], self.rows[b]
        return a0 < b1 and b0 < a1


def _journal(repo: Path) -> dict:
    lines = (repo / preflight.JOURNAL_RELATIVE).read_text(encoding="utf-8").splitlines()
    return next(record for record in map(json.loads, reversed(lines)) if "lanes" in record)


def test_lane_mutex_keys_compose_the_service_key_and_the_docs_site_key_in_sorted_order() -> None:
    lanes = [
        preflight.Lane("pyforge-herald-test", "pyforge-herald"),
        preflight.Lane("docs-site-install", "site"),
        preflight.Lane("scribe-db", INV),
        preflight.Lane("lint-types", INV),
    ]
    service = {("pyforge-herald-test", "pyforge-herald"): POSTGRES, ("scribe-db", INV): POSTGRES}
    keys = preflight.lane_mutex_keys(lanes, service)
    assert keys == {
        ("pyforge-herald-test", "pyforge-herald"): (POSTGRES, DOCS),
        ("docs-site-install", "site"): (DOCS,),
        ("scribe-db", INV): (POSTGRES,),
        ("lint-types", INV): (),
    }
    assert POSTGRES < DOCS  # the one order: a lane holding both takes the service first


def test_two_docs_site_lanes_never_overlap_and_dependencies_keep_their_order(tmp_path: Path) -> None:
    """The measured collision: npm ci (docs-site-install) beside herald's Astro builds (pyforge-herald-test), and the
    Pages chain behind the install. No two of them overlap, and each still starts after its dependency."""
    _write(
        tmp_path / "pixi.toml",
        _pixi(
            ["pyforge-herald-test", "pages-check", "docs-site-validate-sidebar"],
            {
                "pages-check": ["pages-build"],
                "pages-build": ["docs-site-install"],
                "docs-site-validate-sidebar": ["docs-site-install"],
            },
        ),
    )
    runs = _Intervals()
    code = preflight.run_preflight(
        tmp_path, invoking_env=INV, jobs=8, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
    )
    assert code == preflight.EXIT_OK
    docs = ["pyforge-herald-test", "docs-site-install", "pages-build", "pages-check", "docs-site-validate-sidebar"]
    assert set(runs.rows) == set(docs)
    for i, a in enumerate(docs):
        for b in docs[i + 1 :]:
            assert not runs.overlap(a, b), (a, b, runs.rows)
    assert runs.rows["docs-site-install"][1] <= runs.rows["pages-build"][0]
    assert runs.rows["pages-build"][1] <= runs.rows["pages-check"][0]
    assert runs.rows["docs-site-install"][1] <= runs.rows["docs-site-validate-sidebar"][0]
    assert {entry["status"] for entry in _journal(tmp_path)["lanes"]} == {"ok"}


def test_a_docs_site_lane_and_an_unrelated_lane_still_overlap(tmp_path: Path) -> None:
    _write(tmp_path / "pixi.toml", _pixi(["docs-site-install", "lint-types"]))
    runs = _Intervals(seconds=OVERLAP_SECONDS)
    assert (
        preflight.run_preflight(
            tmp_path, invoking_env=INV, jobs=4, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
        )
        == preflight.EXIT_OK
    )
    assert runs.overlap("docs-site-install", "lint-types"), runs.rows


def test_the_pool_gives_the_slot_to_a_lane_that_can_run(tmp_path: Path) -> None:
    """Two slots, two docs-site lanes declared first: the second docs-site lane waits pending, not in a slot, so the
    unrelated lane runs beside the first instead of behind both."""
    _write(tmp_path / "pixi.toml", _pixi(["docs-site-install", "pyforge-herald-test", "lint-types"]))
    runs = _Intervals(seconds=OVERLAP_SECONDS)
    assert (
        preflight.run_preflight(
            tmp_path, invoking_env=INV, jobs=2, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
        )
        == preflight.EXIT_OK
    )
    assert not runs.overlap("docs-site-install", "pyforge-herald-test"), runs.rows
    assert runs.overlap("docs-site-install", "lint-types"), runs.rows


def test_a_lane_with_a_service_key_and_the_docs_site_key_takes_both_without_deadlock(tmp_path: Path) -> None:
    """herald's suite holds the Postgres service key and the docs-site key; it overlaps neither the docs-site lane nor
    the other Postgres lane, those two (which share nothing) still overlap each other, a lane sharing no key overlaps
    a key holder, and the run finishes. Since steward Story 117.2 the install takes the first docs-site turn, so herald
    runs after it and the unrelated lane overlaps the install. (``run_preflight`` installs a SIGINT handler, so it runs
    on this main thread; the lock order itself is proven without the scheduler by the opposite-orders test below.)"""
    _write(
        tmp_path / ".github" / "workflows" / "w.yml",
        "on:\n  pull_request:\n    paths: ['**']\n"
        "jobs:\n"
        "  herald:\n    services:\n      postgres:\n        image: pgvector/pgvector:pg17\n"
        f"    steps:\n      - run: pixi run --frozen -e {INV} pyforge-herald-test\n"
        "  db:\n    services:\n      postgres:\n        image: pgvector/pgvector:pg17\n"
        f"    steps:\n      - run: pixi run --frozen -e {INV} scribe-db\n",
    )
    _write(tmp_path / "pixi.toml", _pixi(["pyforge-herald-test", "docs-site-install", "scribe-db", "lint-types"]))
    lanes = [preflight.Lane(task, INV) for task in ("pyforge-herald-test", "docs-site-install", "scribe-db")]
    service = preflight_ci.static_service_mutex_keys(tmp_path, lanes, tomllib.loads(_read(tmp_path / "pixi.toml")))
    assert preflight.lane_mutex_keys(lanes, service) == {
        ("pyforge-herald-test", INV): (POSTGRES, DOCS),
        ("docs-site-install", INV): (DOCS,),
        ("scribe-db", INV): (POSTGRES,),
    }
    runs = _Intervals(seconds=OVERLAP_SECONDS)
    assert (
        preflight.run_preflight(
            tmp_path, invoking_env=INV, jobs=4, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
        )
        == preflight.EXIT_OK
    )
    assert not runs.overlap("pyforge-herald-test", "docs-site-install"), runs.rows
    assert not runs.overlap("pyforge-herald-test", "scribe-db"), runs.rows
    assert runs.overlap("docs-site-install", "scribe-db"), runs.rows
    assert runs.overlap("docs-site-install", "lint-types"), runs.rows


class _SlowLock:
    """A real lock that, once taken, pauses, so a second thread takes its own first lock before this one goes on:
    two lanes that took their keys in opposite orders would then wait for each other forever."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        taken = self._lock.acquire()
        time.sleep(0.2)
        return taken

    def release(self) -> None:
        self._lock.release()


def test_two_lanes_given_their_keys_in_opposite_orders_take_them_in_one_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coord = preflight._RunCoordinator(  # noqa: SLF001
        repo_root=tmp_path, run_id="t", run_start=time.monotonic(), jobs=2, keep_going=False
    )
    locks = {POSTGRES: _SlowLock(), DOCS: _SlowLock()}
    monkeypatch.setattr(coord, "mutex_lock", lambda key: locks[key])
    runs = _Intervals(seconds=0.1)
    results: list[preflight.LaneResult] = []

    def lane(task: str, keys: tuple[str, ...]) -> threading.Thread:
        def run() -> None:
            results.append(
                preflight._run_lane_in_pool(  # noqa: SLF001
                    coord, preflight.Lane(task, INV), tmp_path / "scratch", keys, runs, False
                )
            )

        return threading.Thread(target=run, daemon=True)

    first = lane("pyforge-herald-test", (POSTGRES, DOCS))
    second = lane("docs-site-install", (DOCS, POSTGRES))
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)
    assert not first.is_alive() and not second.is_alive(), "two lanes waited for each other's key"
    assert sorted(result.status for result in results) == ["ok", "ok"]
    assert not runs.overlap("pyforge-herald-test", "docs-site-install"), runs.rows


def test_a_lane_releases_every_mutex_it_took_when_it_fails(tmp_path: Path) -> None:
    coord = preflight._RunCoordinator(  # noqa: SLF001
        repo_root=tmp_path, run_id="t", run_start=time.monotonic(), jobs=1, keep_going=True
    )

    def boom(_ctx: preflight.LaneRunContext) -> int:
        raise RuntimeError("lane crashed")

    with pytest.raises(RuntimeError, match="lane crashed"):
        preflight._run_lane_in_pool(  # noqa: SLF001
            coord, preflight.Lane("pyforge-herald-test", INV), tmp_path / "scratch", (POSTGRES, DOCS), boom, False
        )
    for key in (POSTGRES, DOCS):
        lock = coord.mutex_lock(key)
        assert lock.acquire(blocking=False), key
        lock.release()


class _RacyLocks(dict[str, threading.Lock]):
    """A lock map that holds the race window open: a membership check, and a ``setdefault``, each pause between the
    check and the store. Two threads then both find the key missing and both store a lock, unless a guard keeps the
    second out: any guarded form (``setdefault`` or check-then-set) stores one lock, and any unguarded form stores two.
    The test pins AC4's property, not the shipped implementation (re-review nit)."""

    def __init__(self) -> None:
        super().__init__()
        self.stored: list[threading.Lock] = []

    def __contains__(self, key: object) -> bool:
        found = super().__contains__(key)
        time.sleep(0.1)  # a second thread checks inside this window unless a guard keeps it out
        return found

    def __setitem__(self, key: str, value: threading.Lock) -> None:
        self.stored.append(value)
        super().__setitem__(key, value)

    def setdefault(self, key: str, default: threading.Lock) -> threading.Lock:  # type: ignore[override]
        if not super().__contains__(key):
            time.sleep(0.1)
            self.stored.append(default)
            super().__setitem__(key, default)
        return super().__getitem__(key)


def test_every_thread_gets_the_one_lock_of_a_key() -> None:
    """Review nit: the map holds the check-to-store window open, so the test fails against the old unguarded
    check-then-set (and against a ``setdefault`` without the guard), which hand two threads two locks."""
    coord = preflight._RunCoordinator(  # noqa: SLF001
        repo_root=Path("."), run_id="t", run_start=0.0, jobs=2, keep_going=False
    )
    racy = _RacyLocks()
    coord.mutex_locks = racy
    start = threading.Barrier(2)
    got: list[threading.Lock] = []
    guard = threading.Lock()

    def take() -> None:
        start.wait()
        lock = coord.mutex_lock(DOCS)
        with guard:
            got.append(lock)

    threads = [threading.Thread(target=take, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(got) == 2
    assert len(racy.stored) == 1, f"{len(racy.stored)} locks stored for one key"
    assert got[0] is got[1] is racy.stored[0]


def test_the_install_starts_before_herald_s_suite(tmp_path: Path) -> None:
    """Review should-fix 2: a lane that pending lanes depend on starts first, so docs-site-install runs before
    pyforge-herald-test even though herald is declared first, and herald's built-site tests read this run's install
    (on a fresh worktree, an install at all)."""
    _write(
        tmp_path / "pixi.toml",
        _pixi(
            ["pyforge-herald-test", "pages-check"],
            {"pages-check": ["pages-build"], "pages-build": ["docs-site-install"]},
        ),
    )
    for jobs in (1, 8):
        runs = _Intervals(seconds=0.1)
        assert (
            preflight.run_preflight(
                tmp_path, invoking_env=INV, jobs=jobs, install_environment=_NOOP_INSTALL, run_lane_ctx=runs
            )
            == preflight.EXIT_OK
        ), jobs
        assert runs.rows["docs-site-install"][1] <= runs.rows["pyforge-herald-test"][0], (jobs, runs.rows)
        assert runs.rows["pages-build"][1] <= runs.rows["pyforge-herald-test"][0], (jobs, runs.rows)


def test_the_docs_site_lanes_trade_turns_and_every_other_lane_keeps_its_position(tmp_path: Path) -> None:
    """Re-review should-fix: with one slot, a keyless lane that a pending lane waits on keeps its declared place
    (``a``, ``b``, ``c``), and the docs-site lanes trade turns only among themselves. ``docs-site-install`` takes the
    turn of ``pyforge-herald-test`` (declared before it), ``pages-build`` the next docs-site turn, and herald the one
    after; ``a`` and ``b``, outside the set, start at their declared positions 0 and 2."""
    started: list[str] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        started.append(ctx.lane.task)
        return 0

    _write(tmp_path / "pixi.toml", _pixi(["a", "c"], {"c": ["b"]}))
    assert (
        preflight.run_preflight(
            tmp_path, invoking_env=INV, jobs=1, install_environment=_NOOP_INSTALL, run_lane_ctx=run_ctx
        )
        == preflight.EXIT_OK
    )
    assert started == ["a", "b", "c"]
    started.clear()
    _write(
        tmp_path / "pixi.toml",
        _pixi(
            ["a", "pyforge-herald-test", "b", "pages-check"],
            {"pages-check": ["pages-build"], "pages-build": ["docs-site-install"]},
        ),
    )
    lanes = preflight.list_preflight_lanes(tomllib.loads(_read(tmp_path / "pixi.toml")), invoking_env=INV)
    declared = [lane.task for lane in lanes]
    assert declared == ["a", "pyforge-herald-test", "b", "docs-site-install", "pages-build", "pages-check"]
    assert (
        preflight.run_preflight(
            tmp_path, invoking_env=INV, jobs=1, install_environment=_NOOP_INSTALL, run_lane_ctx=run_ctx
        )
        == preflight.EXIT_OK
    )
    assert started == ["a", "docs-site-install", "b", "pages-build", "pyforge-herald-test", "pages-check"]
    assert [started.index(task) for task in ("a", "b")] == [declared.index("a"), declared.index("b")]


def test_after_a_red_stop_no_lane_starts_even_one_pending_lanes_depend_on(tmp_path: Path) -> None:
    """Review nit: herald (holding the docs-site key) goes red; the stop ends the run, so nothing that would only feed
    cancelled dependents starts: after-herald and pages-build are journaled as lanes that never started (Story 71.10),
    naming the red lane (Story 71.12). Since steward Story 117.2 the install takes the first docs-site turn whenever it
    is ready (herald Story 45.1), so here it runs green before herald's suite takes the key; its dependent pages-build
    is still cancelled by the stop."""
    _write(
        tmp_path / "pixi.toml",
        _pixi(
            ["pyforge-herald-test", "after-herald", "pages-build"],
            {"after-herald": ["pyforge-herald-test"], "pages-build": ["docs-site-install"]},
        ),
    )
    started: list[str] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        started.append(ctx.lane.task)
        return 1 if ctx.lane.task == "pyforge-herald-test" else 0

    assert (
        preflight.run_preflight(
            tmp_path, invoking_env=INV, jobs=4, install_environment=_NOOP_INSTALL, run_lane_ctx=run_ctx
        )
        == preflight.EXIT_LANE_RED
    )
    assert started == ["docs-site-install", "pyforge-herald-test"]
    by_task = {entry["task"]: entry for entry in _journal(tmp_path)["lanes"]}
    assert by_task["pyforge-herald-test"]["status"] == "red"
    assert (by_task["after-herald"]["status"], by_task["after-herald"]["cancelled_by"]) == (
        "cancelled",
        "pyforge-herald-test",
    )
    assert by_task["docs-site-install"]["status"] == "ok"
    build = by_task["pages-build"]
    assert (build["status"], build["exit_code"], build["seconds"]) == ("cancelled", 0, 0.0)
    assert (build["cancelled_by"], build["cancelled_by_environment"]) == (
        "pyforge-herald-test",
        by_task["pyforge-herald-test"]["environment"],
    )
