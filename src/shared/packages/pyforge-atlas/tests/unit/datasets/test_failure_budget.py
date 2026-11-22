"""Story 50.1 (spec-pyforge-atlas CAP-64, CAP-65; AD-13): a host that keeps failing costs a run a bounded time.

The weekly public data build ran into its 240-minute limit on five runs (2026-11-02 to 2026-11-16), each time
silent inside ``vcs_gitlab_api_raw``'s refresh: a host that fails every request for a transient cause cost
``2 URLs x (retries + 1) x (timeout or Retry-After)`` per project, with no limit and no line logged. A refresh now
carries a failure budget per host and per run; when it is used up the host is not asked again, the rows it never
reached keep their last-good values, the store is marked stale with the reason, and the log says so. No network:
an injected fetcher, sleep and clock.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from kedro.io import DatasetError

from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets import vcs_sources as V
from pyforge.atlas.datasets.rate_limit import (
    DEFAULT_FAILURE_BUDGET_SECONDS,
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DEFAULT_RUN_DEADLINE_SECONDS,
    FailureBudget,
    HostUnavailable,
    RateLimitedScheduler,
)
from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.datasets.vcs_sources import RegistryUpstreamDataset, VcsHostSeedDataset

GITLAB = "https://gitlab.com/api/v4"


class _Clock:
    """A clock the injected sleep advances, so waits cost time and nothing really sleeps."""

    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def _http_error(status: int, retry_after: str | None = None) -> Exception:
    headers = {"Retry-After": retry_after} if retry_after else {}
    response = SimpleNamespace(status_code=status, headers=headers)
    return DatasetError("Failed to fetch data", SimpleNamespace(response=response))


def _timeout() -> Exception:
    try:
        raise TimeoutError("timed out")
    except TimeoutError as cause:
        try:
            raise DatasetError("Failed to fetch data") from cause
        except DatasetError as wrapped:
            return wrapped


@pytest.fixture()
def flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)


def _gitlab(tmp_path: Path, clock: _Clock, **kwargs: Any) -> VcsHostSeedDataset:
    scheduler = RateLimitedScheduler(rps=1000.0, bucket_capacity=1000, clock=clock, sleep=clock.sleep)
    return VcsHostSeedDataset(
        url=GITLAB,
        host="gitlab",
        filepath=str(tmp_path / "gitlab"),
        scheduler=scheduler,
        sleep=clock.sleep,
        clock=clock,
        **kwargs,
    )


def _projects(n: int) -> list[tuple[str, str]]:
    return [(f"pkg{i}", f"group/proj{i}") for i in range(n)]


# ------------------------------------------------------------------ the budget itself


def test_the_defaults_bound_a_failing_host_to_minutes() -> None:
    assert DEFAULT_FAILURE_BUDGET_SECONDS == 300.0 and DEFAULT_MAX_CONSECUTIVE_FAILURES == 5  # noqa: PLR2004
    assert DEFAULT_RUN_DEADLINE_SECONDS == 1800.0  # noqa: PLR2004


def test_the_seconds_limit_charges_a_request_that_failed_in_the_end() -> None:
    clock = _Clock()
    budget = FailureBudget(seconds=100.0, max_consecutive=99, clock=clock)
    started = budget.now()
    clock.t += 20.0
    budget.failed_attempt(started, wait=60.0)
    assert budget.spent == 0.0  # held against the request, not yet charged
    budget.exhausted("HTTP 429")  # 80 s: inside the budget
    assert budget.spent == 80.0  # noqa: PLR2004
    started = budget.now()
    clock.t += 20.0
    budget.failed_attempt(started)
    with pytest.raises(HostUnavailable, match=r"HTTP 429; 100 s spent on failed requests \(budget 100 s\)"):
        budget.exhausted("HTTP 429")


def test_a_request_that_answers_in_the_end_costs_nothing() -> None:
    clock = _Clock()
    budget = FailureBudget(seconds=100.0, max_consecutive=2, clock=clock)
    for _ in range(50):  # fifty requests that each wait out a 429 and then answer
        budget.failed_attempt(budget.now(), wait=60.0)
        budget.answered()
    assert budget.spent == 0.0 and budget.consecutive == 0


def test_the_count_limit_is_requests_in_a_row_and_an_answer_resets_it() -> None:
    budget = FailureBudget(seconds=1e9, max_consecutive=3)
    budget.exhausted("TimeoutError")
    budget.exhausted("TimeoutError")
    budget.answered()
    budget.exhausted("TimeoutError")
    budget.exhausted("TimeoutError")
    with pytest.raises(HostUnavailable, match="TimeoutError; 3 requests in a row failed after their retries"):
        budget.exhausted("TimeoutError")


def test_the_deadline_is_the_runs_wall_clock() -> None:
    clock = _Clock()
    budget = FailureBudget(deadline_seconds=50.0, clock=clock)
    clock.t += 49.0
    budget.check_deadline()
    clock.t += 1.0
    with pytest.raises(HostUnavailable, match="the run passed its 50 s deadline"):
        budget.check_deadline()


@pytest.mark.parametrize("limits", [{"seconds": 0}, {"max_consecutive": 0}, {"deadline_seconds": -1}])
def test_a_limit_that_is_not_positive_is_refused(tmp_path, limits) -> None:
    with pytest.raises(ValueError, match="limits are positive"):
        FailureBudget(**limits)
    with pytest.raises(ValueError, match="limits are positive"):
        _gitlab(tmp_path, _Clock(), failure_budget_seconds=0)


# ------------------------------------------------------------------ the live host path (the one that stalled)


def test_a_host_that_throttles_every_request_stops_inside_its_budget(tmp_path, flag_on, caplog) -> None:
    """The stall, replayed: every request answers 429 with ``Retry-After: 60``. Unbounded, 300 projects cost
    300 x 2 URLs x 4 attempts x 60 s = 40 hours; with the budget the run stops in about five minutes."""
    clock = _Clock()
    asked: list[str] = []

    def throttled(url: str) -> Any:
        asked.append(url)
        raise _http_error(429, "60")

    ds = _gitlab(tmp_path, clock, max_retries=3)
    with caplog.at_level(logging.INFO, logger=V.logger.name):
        frame = ds.load_many(_projects(300), fetcher=throttled)

    assert clock.t <= DEFAULT_FAILURE_BUDGET_SECONDS + 120.0, f"the run spent {clock.t} s on a host that never answered"
    assert len(asked) <= 8, asked  # noqa: PLR2004 -- the host is not asked again once the budget is used up
    assert frame.empty  # no project was finished
    marker = ds.staleness()
    assert marker is not None and marker.stale
    assert "gitlab unavailable this run: HTTP 429" in marker.reason and "finished 0 of 300" in marker.reason
    said = [r.getMessage() for r in caplog.records]
    assert "gitlab: asking for 300 identifier(s)" in said
    assert any("gitlab unavailable this run: HTTP 429" in line and "last-good" in line for line in said), said


def test_a_host_that_times_out_every_request_stops_on_the_count(tmp_path, flag_on) -> None:
    clock = _Clock()
    asked: list[str] = []

    def dropped(url: str) -> Any:
        asked.append(url)
        clock.t += 20.0  # the catalog's per-request timeout
        raise _timeout()

    ds = _gitlab(tmp_path, clock, max_retries=0, failure_budget_seconds=1e9, max_consecutive_failures=5)
    frame = ds.load_many(_projects(50), fetcher=dropped)

    assert len(asked) == 5  # noqa: PLR2004 -- five requests in a row failed, then no more
    assert len(frame) == 2  # noqa: PLR2004 -- two projects finished (release and tags both failed), the third stopped
    assert "5 requests in a row failed after their retries" in ds.staleness().reason


def test_a_stopped_run_keeps_what_it_got_and_the_last_good_rows_it_never_reached(tmp_path, flag_on) -> None:
    clock = _Clock()
    release = {p: V._live_host_paths("gitlab", GITLAB, p)[0] for _, p in _projects(4)}
    healthy = _gitlab(tmp_path, clock)
    healthy.load_many(_projects(4), fetcher=lambda url: [{"tag_name": "v1"}])
    assert healthy.load()["upstream_version"].tolist() == ["1", "1", "1", "1"]

    def first_then_throttled(url: str) -> Any:
        if url == release["group/proj0"]:
            return [{"tag_name": "v2"}]
        raise _http_error(429, "60")

    ds = _gitlab(tmp_path, clock, max_retries=3)
    frame = ds.load_many(_projects(4), fetcher=first_then_throttled)

    assert frame[["conda_name", "upstream_version"]].values.tolist() == [["pkg0", "2"]]
    stored = ds.load().set_index("conda_name")["upstream_version"].to_dict()
    assert stored == {"pkg0": "2", "pkg1": "1", "pkg2": "1", "pkg3": "1"}  # the rest keep last-good
    assert ds.staleness().stale and "finished 1 of 4" in ds.staleness().reason


def test_refusals_never_use_the_budget(tmp_path, flag_on, caplog) -> None:
    """A 404 is the host's answer (a project with no release, a renamed project), not a failure of the host."""
    clock = _Clock()

    def gone(url: str) -> Any:
        raise _http_error(404)

    ds = _gitlab(tmp_path, clock, max_retries=3, max_consecutive_failures=2, failure_budget_seconds=1.0)
    with caplog.at_level(logging.INFO, logger=V.logger.name):
        frame = ds.load_many(_projects(40), fetcher=gone)

    assert len(frame) == 40 and set(frame["last_error"]) == {"HTTP 404"}  # noqa: PLR2004
    assert not any("unavailable" in r.getMessage() for r in caplog.records)
    assert "gitlab: finished 40 in 0 s, 0 with a version, 40 without" in [r.getMessage() for r in caplog.records]


def test_a_host_that_recovers_is_asked_to_the_end(tmp_path, flag_on) -> None:
    clock = _Clock()
    calls = {"n": 0}

    def flaky(url: str) -> Any:
        calls["n"] += 1
        if calls["n"] % 3 == 0:
            raise _http_error(503)
        return [{"tag_name": "v3"}]

    ds = _gitlab(tmp_path, clock, max_retries=3)
    frame = ds.load_many(_projects(30), fetcher=flaky)

    assert frame["upstream_version"].tolist() == ["3"] * 30
    assert ds.staleness() is None


def test_each_run_starts_with_a_fresh_budget(tmp_path, flag_on) -> None:
    clock = _Clock()
    ds = _gitlab(tmp_path, clock, max_retries=0, max_consecutive_failures=2)

    def dropped(url: str) -> Any:
        raise _timeout()

    ds.load_many(_projects(5), fetcher=dropped)
    assert ds.staleness().stale
    frame = ds.load_many(_projects(5), fetcher=lambda url: [{"tag_name": "v9"}])
    assert frame["upstream_version"].tolist() == ["9"] * 5 and ds.staleness() is None


# ------------------------------------------------------------------ the path that retries in fetch_one_with_retry


def test_the_flag_off_host_path_stops_too(tmp_path) -> None:
    clock = _Clock()
    asked: list[str] = []

    def dropped(identifier: str) -> Any:
        asked.append(identifier)
        raise _timeout()

    ds = _gitlab(tmp_path, clock, max_retries=1, max_consecutive_failures=3)
    frame = ds.load_many(_projects(20), fetcher=dropped)

    assert len(frame) == 2 and len(asked) == 6  # noqa: PLR2004 -- two attempts each; the third project stops the run
    assert "gitlab unavailable this run: TimeoutError" in ds.staleness().reason


def test_a_registry_that_keeps_failing_stops_and_one_that_refuses_does_not(tmp_path) -> None:
    clock = _Clock()

    def registry(**kwargs: Any) -> RegistryUpstreamDataset:
        scheduler = RateLimitedScheduler(rps=1000.0, bucket_capacity=1000, clock=clock, sleep=clock.sleep)
        return RegistryUpstreamDataset(
            url="https://registry.npmjs.org",
            registry="npm",
            filepath=str(tmp_path / "npm"),
            scheduler=scheduler,
            sleep=clock.sleep,
            clock=clock,
            max_retries=0,
            **kwargs,
        )

    def failing(identifier: str) -> Any:
        raise _http_error(503)

    def refusing(identifier: str) -> Any:
        raise _http_error(404)

    stopped = registry(max_consecutive_failures=4)
    assert len(stopped.load_many(_projects(25), fetcher=failing)) == 3  # noqa: PLR2004 -- the fourth stops the run
    assert "npm unavailable this run: HTTP 503" in stopped.staleness().reason
    assert len(registry(max_consecutive_failures=4).load_many(_projects(25), fetcher=refusing)) == 25  # noqa: PLR2004


# ------------------------------------------------------------------ the review's cases (2026-11-22)


def test_a_refusal_in_the_middle_of_a_streak_starts_the_count_again(tmp_path, flag_on) -> None:
    """Fail, fail, a 404, fail, fail with a limit of three: the 404 is an answer, so the run is not stopped."""
    clock = _Clock()
    answers = iter([_timeout(), _timeout(), _http_error(404), _timeout(), _timeout(), _http_error(404)])

    def scripted(url: str) -> Any:
        raise next(answers)

    ds = _gitlab(tmp_path, clock, max_retries=0, max_consecutive_failures=3, failure_budget_seconds=1e9)
    frame = ds.load_many(_projects(3), fetcher=scripted)

    assert len(frame) == 3 and ds.staleness().reason.startswith("fetch returned no data")  # noqa: PLR2004 -- not stopped


def test_a_host_that_waits_out_a_429_now_and_then_is_asked_to_the_end(tmp_path, flag_on) -> None:
    """A 429 with ``Retry-After: 60`` on every 50th request, each retry answering: 12 waits of 60 s, more than the
    300 s budget in total, and none of it a failure of the host."""
    clock = _Clock()
    calls = {"n": 0, "throttled": False}

    def now_and_then(url: str) -> Any:
        calls["n"] += 1
        if calls["n"] % 50 == 0 and not calls["throttled"]:
            calls["throttled"] = True
            raise _http_error(429, "60")
        calls["throttled"] = False
        return [{"tag_name": "v3"}]

    ds = _gitlab(tmp_path, clock, max_retries=3)
    frame = ds.load_many(_projects(600), fetcher=now_and_then)

    assert len(frame) == 600 and frame["upstream_version"].notna().all() and ds.staleness() is None  # noqa: PLR2004
    assert sum(clock.slept) >= 600.0  # noqa: PLR2004 -- it waited longer than the budget, and was not stopped


def test_a_host_that_answers_slowly_is_stopped_by_the_runs_deadline(tmp_path, flag_on, caplog) -> None:
    """A tarpit: every answer takes 19 s and none fails. 300 projects would cost 3.2 hours."""
    clock = _Clock()

    def slow(url: str) -> Any:
        clock.t += 19.0
        return [{"tag_name": "v1"}]

    ds = _gitlab(tmp_path, clock)
    with caplog.at_level(logging.INFO, logger=V.logger.name):
        frame = ds.load_many(_projects(300), fetcher=slow)

    assert clock.t <= DEFAULT_RUN_DEADLINE_SECONDS + 19.0
    assert 0 < len(frame) < 300 and frame["upstream_version"].notna().all()  # noqa: PLR2004
    assert "the run passed its 1800 s deadline" in ds.staleness().reason
    said = [r.getMessage() for r in caplog.records]
    assert sum("finished after" in line for line in said) >= 20, "a slow run says where it is"  # noqa: PLR2004
    assert len(ds.load()) == len(frame)  # what it got is kept


def test_a_row_that_failed_for_the_cause_that_stopped_the_run_keeps_its_last_good_value(tmp_path, flag_on) -> None:
    clock = _Clock()
    release = {p: V._live_host_paths("gitlab", GITLAB, p)[0] for _, p in _projects(6)}
    _gitlab(tmp_path, clock).load_many(_projects(6), fetcher=lambda url: [{"tag_name": "v1"}])

    def one_then_timeouts(url: str) -> Any:
        if url == release["group/proj0"]:
            return [{"tag_name": "v2"}]
        raise _timeout()

    ds = _gitlab(tmp_path, clock, max_retries=0, max_consecutive_failures=4, failure_budget_seconds=1e9)
    frame = ds.load_many(_projects(6), fetcher=one_then_timeouts)

    assert frame["last_error"].tolist() == [None, "TimeoutError"]  # proj1 finished, with a transient error
    stored = ds.load().set_index("conda_name")
    assert stored["upstream_version"].to_dict() == {"pkg0": "2", **{f"pkg{i}": "1" for i in range(1, 6)}}
    assert stored["last_error"].isna().all()  # no null row and no error written over a good one


def test_the_run_after_a_stopped_run_asks_again_whatever_the_stores_age(tmp_path, flag_on, monkeypatch) -> None:
    """A stopped run that got some rows rewrites the store, which makes it look fresh; its marker says otherwise.
    ``save`` is watched through ``load_many``, so no request leaves the test."""
    clock = _Clock()
    release = {p: V._live_host_paths("gitlab", GITLAB, p)[0] for _, p in _projects(4)}

    def one_then_throttled(url: str) -> Any:
        if url == release["group/proj0"]:
            return [{"tag_name": "v2"}]
        raise _http_error(429, "60")

    ds = _gitlab(tmp_path, clock, max_retries=3)
    ds.load_many(_projects(4), fetcher=one_then_throttled)
    week = 604800
    assert ds.staleness().stale and not ds._refresh_due(week)  # fresh by age, stale by its marker

    runs: list[tuple] = []
    monkeypatch.setattr(ds, "load_many", lambda pairs: runs.append(tuple(pairs)))
    request = RefreshRequest(
        store="vcs_gitlab_api_raw", cadence_seconds=week, vcs_pairs=(), universe_pairs=tuple(_projects(4))
    )
    ds.save(request)
    assert runs == [tuple(_projects(4))], "the rows the stopped run never reached wait a whole cadence"
    assert ds.staleness().stale  # and the marker was not cleared unasked

    healthy = _gitlab(tmp_path, clock)
    healthy.load_many(_projects(4), fetcher=lambda url: [{"tag_name": "v3"}])
    assert healthy.staleness() is None
    asked: list[tuple] = []
    monkeypatch.setattr(healthy, "load_many", lambda pairs: asked.append(tuple(pairs)))
    healthy.save(request)
    assert asked == []  # fresh and not stale: not due, nothing asked


def test_the_seconds_limit_stops_the_path_that_retries_in_fetch_one_with_retry(tmp_path) -> None:
    clock = _Clock()
    asked: list[str] = []

    def hung(identifier: str) -> Any:
        asked.append(identifier)
        clock.t += 100.0  # a read that hangs to its timeout
        raise _timeout()

    ds = _gitlab(tmp_path, clock, max_retries=0, max_consecutive_failures=99, failure_budget_seconds=300.0)
    frame = ds.load_many(_projects(20), fetcher=hung)

    assert len(asked) == 3 and len(frame) == 2  # noqa: PLR2004 -- 300 s spent: the third stops the run
    assert "300 s spent on failed requests (budget 300 s)" in ds.staleness().reason


def test_a_stopped_registry_run_keeps_last_good_marks_stale_and_says_so(tmp_path, caplog) -> None:
    clock = _Clock()

    def registry(**kwargs: Any) -> RegistryUpstreamDataset:
        scheduler = RateLimitedScheduler(rps=1000.0, bucket_capacity=1000, clock=clock, sleep=clock.sleep)
        return RegistryUpstreamDataset(
            url="https://registry.npmjs.org",
            registry="npm",
            filepath=str(tmp_path / "npm"),
            scheduler=scheduler,
            sleep=clock.sleep,
            clock=clock,
            max_retries=0,
            **kwargs,
        )

    registry().load_many(_projects(5), fetcher=lambda name: {"dist-tags": {"latest": "1.0.0"}})

    def first_then_failing(identifier: str) -> Any:
        if identifier == "group/proj0":
            return {"dist-tags": {"latest": "2.0.0"}}
        raise _http_error(503)

    ds = registry(max_consecutive_failures=2)
    with caplog.at_level(logging.INFO, logger=V.logger.name):
        ds.load_many(_projects(5), fetcher=first_then_failing)

    stored = ds.load().set_index("conda_name")["upstream_version"].to_dict()
    assert stored == {"pkg0": "2.0.0", **{f"pkg{i}": "1.0.0" for i in range(1, 5)}}
    assert "npm unavailable this run: HTTP 503" in ds.staleness().reason
    assert any("npm unavailable this run" in r.getMessage() and r.levelno == logging.WARNING for r in caplog.records)


def test_the_limits_are_in_the_datasets_description(tmp_path) -> None:
    described = _gitlab(tmp_path, _Clock(), failure_budget_seconds=120.0)._describe()
    assert (described["failure_budget_seconds"], described["max_consecutive_failures"]) == (120.0, 5)
    assert described["run_deadline_seconds"] == DEFAULT_RUN_DEADLINE_SECONDS
