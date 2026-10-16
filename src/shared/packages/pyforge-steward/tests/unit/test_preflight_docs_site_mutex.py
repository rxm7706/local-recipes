"""Story 105.1 (fix under spec-pyforge-steward CAP-159): the preflight never runs two docs-site lanes at once.

Every test runs the real ``run_preflight`` (or the real pool function) over a fixture ``pixi.toml`` with an injected
lane runner; none runs pixi. The fixtures are not git repositories, so selection runs every lane (no
``refs/remotes/origin/main``), and the service keys come from the fixture workflows alone
(``preflight_ci.static_service_mutex_keys``).
"""

from __future__ import annotations

import json
import threading
import time
import tomllib
from pathlib import Path

import pytest

from pyforge.steward import preflight, preflight_ci

_NOOP_INSTALL = lambda _env: 0  # noqa: E731
INV = "pyforge-guild"
POSTGRES = "services:postgres"
DOCS = preflight.DOCS_SITE_MUTEX_KEY
# A test that asserts two lanes DO overlap gives each this long, so a loaded host's thread start-up cannot hide it.
OVERLAP_SECONDS = 0.6


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
    the other Postgres lane, those two (which share nothing) still overlap each other, and the run finishes.
    (``run_preflight`` installs a SIGINT handler, so it runs on this main thread; the lock order itself is proven
    without the scheduler by the opposite-orders test below.)"""
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
    assert runs.overlap("pyforge-herald-test", "lint-types"), runs.rows


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
                    coord, preflight.Lane(task, INV), tmp_path / "scratch", keys, runs, False, {}
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
            coord, preflight.Lane("pyforge-herald-test", INV), tmp_path / "scratch", (POSTGRES, DOCS), boom, False, {}
        )
    for key in (POSTGRES, DOCS):
        lock = coord.mutex_lock(key)
        assert lock.acquire(blocking=False), key
        lock.release()


def test_every_thread_gets_the_one_lock_of_a_key() -> None:
    coord = preflight._RunCoordinator(  # noqa: SLF001
        repo_root=Path("."), run_id="t", run_start=0.0, jobs=16, keep_going=False
    )
    start = threading.Barrier(16)
    got: list[threading.Lock] = []
    guard = threading.Lock()

    def take() -> None:
        start.wait()
        lock = coord.mutex_lock(DOCS)
        with guard:
            got.append(lock)

    threads = [threading.Thread(target=take) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(got) == 16
    assert len({id(lock) for lock in got}) == 1
