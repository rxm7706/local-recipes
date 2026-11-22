"""Story 51.1 (spec-pyforge-atlas CAP-64, CAP-65; AD-13): a stopped refresh starts where the last one ended.

The first public data build with Story 50.1 stopped GitLab's refresh at 105 of 406 on HTTP 429. Every run asked the
same list in the same order, so the runs a host stops never reached the tail; and the log named the 429 without what
the host said about its limit. A refresh now asks the identifiers it never asked first, then the rest longest since
asked first; every identifier a run asks is marked as asked, whether or not the host answered, without writing over a
last-good value; and a 429's rate-limit headers reach the log and the stop's reason. No network: an injected fetcher,
sleep and clock.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import unquote

import pandas as pd
import pytest
from kedro.io import DatasetError

from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets import vcs_sources as V
from pyforge.atlas.datasets.rate_limit import FailureBudget, RateLimitedScheduler
from pyforge.atlas.datasets.vcs_sources import RegistryUpstreamDataset, VcsHostSeedDataset

GITLAB = "https://gitlab.com/api/v4"
GITLAB_429 = {
    "RateLimit-Name": "throttle_unauthenticated_api",
    "RateLimit-Limit": "500",
    "RateLimit-Observed": "612",
    "RateLimit-Remaining": "0",
    "RateLimit-Reset": "1795377900",
    "Retry-After": "37",
}
SAID = (
    "RateLimit-Name=throttle_unauthenticated_api RateLimit-Limit=500 RateLimit-Observed=612 "
    "RateLimit-Remaining=0 RateLimit-Reset=1795377900 Retry-After=37"
)


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def _http_error(status: int, headers: dict[str, str] | None = None) -> Exception:
    response = SimpleNamespace(status_code=status, headers=headers or {})
    return DatasetError("Failed to fetch data", SimpleNamespace(response=response))


@pytest.fixture()
def flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)


def _gitlab(tmp_path: Path, wall: list[float], **kwargs: Any) -> VcsHostSeedDataset:
    clock = _Clock()
    scheduler = RateLimitedScheduler(rps=1000.0, bucket_capacity=1000, clock=clock, sleep=clock.sleep)
    dataset = VcsHostSeedDataset(
        url=GITLAB,
        host="gitlab",
        filepath=str(tmp_path / "gitlab"),
        scheduler=scheduler,
        sleep=clock.sleep,
        clock=clock,
        max_retries=0,
        **kwargs,
    )
    dataset._now = lambda: wall[0]
    return dataset


def _projects(n: int) -> list[tuple[str, str]]:
    return [(f"pkg{i}", f"group/proj{i}") for i in range(n)]


def _package(url: str) -> str:
    """The conda name a request is for (``.../projects/group%2Fproj7/releases`` -> ``pkg7``)."""
    project = unquote(url.split("/projects/")[1].split("/")[0])
    return "pkg" + project.rsplit("proj", 1)[1]


class _Host:
    """Answers ``answers`` projects a run, then a 429 for every request after; records who was asked.
    A project in ``broken`` always answers 503 and one in ``missing`` always 404; neither uses up ``answers``."""

    def __init__(self, answers: int, broken: tuple[str, ...] = (), missing: tuple[str, ...] = ()) -> None:
        self.answers = answers
        self.broken = broken
        self.missing = missing
        self.asked: list[str] = []
        self._answered: list[str] = []

    def new_run(self, answers: int | None = None) -> None:
        self.asked = []
        self._answered = []
        if answers is not None:
            self.answers = answers

    def __call__(self, url: str) -> Any:
        name = _package(url)
        if name not in self.asked:
            self.asked.append(name)
        if name in self.broken:
            raise _http_error(503)
        if name in self.missing:
            raise _http_error(404)
        if name not in self._answered:
            if len(self._answered) >= self.answers:
                raise _http_error(429, GITLAB_429)
            self._answered.append(name)
        return [{"tag_name": "v1.0"}]


def _times(dataset: VcsHostSeedDataset) -> dict[str, float]:
    return dataset._asked_times(dataset._stored())


def _versions(dataset: VcsHostSeedDataset) -> dict[str, Any]:
    loaded = dataset.load()
    return {n: (v if pd.notna(v) else None) for n, v in zip(loaded["conda_name"], loaded["upstream_version"])}


# ------------------------------------------------------------------ the order


def test_a_first_run_asks_in_the_order_given(tmp_path, flag_on) -> None:
    host = _Host(answers=99)
    _gitlab(tmp_path, [1000.0]).load_many(_projects(6), fetcher=host)
    assert host.asked == [f"pkg{i}" for i in range(6)]


def test_stopped_runs_cover_the_whole_list_between_them(tmp_path, flag_on) -> None:
    wall = [1000.0]
    host = _Host(answers=4)
    projects = _projects(12)

    def run() -> VcsHostSeedDataset:
        dataset = _gitlab(tmp_path, wall, max_consecutive_failures=1)
        dataset.load_many(projects, fetcher=host)
        return dataset

    first = run()  # pkg0..pkg3 answer, pkg4 meets the 429 and stops the run
    assert host.asked == ["pkg0", "pkg1", "pkg2", "pkg3", "pkg4"]
    assert first.is_stale()
    assert _times(first) == dict.fromkeys(["pkg0", "pkg1", "pkg2", "pkg3", "pkg4"], 1000.0)  # pkg4 was asked too
    assert _versions(first)["pkg4"] is None and _versions(first)["pkg0"] == "1.0"

    wall[0] = 2000.0
    host.new_run()
    second = run()  # the seven never asked come first, in the order given
    assert host.asked == ["pkg5", "pkg6", "pkg7", "pkg8", "pkg9"]
    assert _times(second)["pkg0"] == 1000.0 and _times(second)["pkg9"] == 2000.0  # noqa: PLR2004

    wall[0] = 3000.0
    host.new_run()
    third = run()  # the last two never asked, then the longest since asked
    assert host.asked == ["pkg10", "pkg11", "pkg0", "pkg1", "pkg2"]
    assert set(_times(third)) == {f"pkg{i}" for i in range(12)}  # three stopped runs asked every identifier
    assert {n for n, v in _versions(third).items() if v is None} == {"pkg4", "pkg9"}  # the two the 429 refused

    wall[0] = 4000.0
    host.new_run(answers=99)
    fourth = run()  # a run the host does not stop: longest since asked first
    # pkg2 kept its version when the third run stopped on it, so its tie is a plain one
    assert host.asked == [f"pkg{i}" for i in (3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 10, 11)]
    assert not fourth.is_stale()
    assert set(_times(fourth).values()) == {4000.0}
    assert set(_versions(fourth).values()) == {"1.0"}


def test_identifiers_that_fail_every_time_do_not_stop_every_run_at_the_head(tmp_path, flag_on) -> None:
    """Three projects answer 503 every time. Marked as asked, they move behind the rest; left unmarked they
    would be first in every run and stop it (three requests in a row) before a healthy project is reached."""
    wall = [1000.0]
    host = _Host(answers=99, broken=("pkg0", "pkg1", "pkg2"))
    projects = _projects(9)

    def run() -> VcsHostSeedDataset:
        dataset = _gitlab(tmp_path, wall, max_consecutive_failures=3)
        dataset.load_many(projects, fetcher=host)
        return dataset

    first = run()  # pkg0 fails twice (release, tags), pkg1's release is the third in a row
    assert host.asked == ["pkg0", "pkg1"] and first.is_stale()
    assert set(_times(first)) == {"pkg0", "pkg1"}  # asked, with nothing to keep

    wall[0] = 2000.0
    host.new_run()
    second = run()  # pkg2 fails twice, then pkg3 answers and resets the count: the rest are reached
    assert host.asked == ["pkg2", *[f"pkg{i}" for i in range(3, 9)], "pkg0", "pkg1"]
    assert {n for n, v in _versions(second).items() if v == "1.0"} == {f"pkg{i}" for i in range(3, 9)}

    wall[0] = 3000.0
    host.new_run()
    run()
    assert host.asked[:6] == [f"pkg{i}" for i in range(3, 9)]  # the healthy six again, before the three that fail


def test_a_row_the_stopping_cause_failed_keeps_its_value_and_is_marked_asked(tmp_path, flag_on) -> None:
    wall = [5000.0]
    dataset = _gitlab(tmp_path, wall, max_consecutive_failures=2)
    store = Path(dataset._filepath)
    store.mkdir(parents=True)
    pd.DataFrame(
        {
            "conda_name": ["pkg0", "pkg1", "pkg2"],
            "upstream_version": ["0.7", "0.8", "0.9"],
            "last_error": [None, None, None],
            "asked_at": [100, 200, 300],
        }
    ).to_parquet(store / dataset.STORE_FILENAME, index=False)
    dataset.load_many(_projects(3), fetcher=_Host(answers=0))  # pkg0 fails twice: the run stops on its tags
    assert _versions(dataset) == {"pkg0": "0.7", "pkg1": "0.8", "pkg2": "0.9"}  # no last-good value is lost
    assert _times(dataset) == {"pkg0": 5000.0, "pkg1": 200.0, "pkg2": 300.0}  # pkg0 asked; the unreached keep theirs
    assert dataset.is_stale()


def test_a_refusal_is_marked_asked_with_its_error(tmp_path, flag_on) -> None:
    dataset = _gitlab(tmp_path, [700.0])
    dataset.load_many(_projects(3), fetcher=_Host(answers=99, missing=("pkg1",)))
    assert _times(dataset) == {"pkg0": 700.0, "pkg1": 700.0, "pkg2": 700.0}
    errors = dataset.load().set_index("conda_name")["last_error"].to_dict()
    assert errors["pkg1"] == "HTTP 404" and _versions(dataset)["pkg1"] is None


def test_a_stopped_run_with_nothing_to_keep_still_marks_what_it_asked(tmp_path, flag_on) -> None:
    dataset = _gitlab(tmp_path, [900.0], max_consecutive_failures=2)
    dataset.load_many(_projects(4), fetcher=_Host(answers=0))  # every request a 429
    assert set(_times(dataset)) == {"pkg0"} and _versions(dataset) == {"pkg0": None}
    assert dataset.load().loc[0, "last_error"] == "HTTP 429"
    assert dataset.is_stale()


def test_a_stop_that_is_not_a_429_does_not_quote_an_earlier_one(tmp_path, flag_on, caplog) -> None:
    host = _Host(answers=1, broken=("pkg2", "pkg3"))  # pkg0 answers, pkg1 meets a 429, then two 503s stop the run
    dataset = _gitlab(tmp_path, [1000.0], max_consecutive_failures=5)
    with caplog.at_level(logging.INFO, logger=V.__name__):
        dataset.load_many(_projects(6), fetcher=host)
    marker = dataset.staleness()
    assert marker is not None and "HTTP 503" in marker.reason and "the host said" not in marker.reason
    assert "the host limits requests" in caplog.text  # the earlier 429 is still logged once


def test_the_longest_since_asked_goes_first_and_ties_keep_the_order_given(tmp_path, flag_on) -> None:
    # a tie between rows that both hold a version; a row with none goes after them (the test above)
    dataset = _gitlab(tmp_path, [9000.0])
    store = Path(dataset._filepath)
    store.mkdir(parents=True)
    pd.DataFrame(
        {
            "conda_name": ["pkg0", "pkg1", "pkg2", "pkg3"],
            "upstream_version": ["1", "1", "1", "1"],
            "last_error": [None, None, None, None],
            "asked_at": [300, 100, 300, 200],
        }
    ).to_parquet(store / dataset.STORE_FILENAME, index=False)
    host = _Host(answers=99)
    dataset.load_many(_projects(6), fetcher=host)
    assert host.asked == ["pkg4", "pkg5", "pkg1", "pkg3", "pkg0", "pkg2"]


def test_a_store_written_before_the_story_orders_nothing_and_merges(tmp_path, flag_on) -> None:
    dataset = _gitlab(tmp_path, [5000.0])
    store = Path(dataset._filepath)
    store.mkdir(parents=True)
    pd.DataFrame(
        {"conda_name": ["pkg1", "old"], "upstream_version": ["0.9", "7"], "last_error": [None, None]}
    ).to_parquet(store / dataset.STORE_FILENAME, index=False)
    host = _Host(answers=99)
    dataset.load_many(_projects(3), fetcher=host)
    assert host.asked == ["pkg0", "pkg1", "pkg2"]
    loaded = dataset.load().set_index("conda_name")["upstream_version"].to_dict()
    assert loaded == {"old": "7", "pkg0": "1.0", "pkg1": "1.0", "pkg2": "1.0"}
    assert _times(dataset) == {"pkg0": 5000.0, "pkg1": 5000.0, "pkg2": 5000.0}  # the row never asked has none


def test_a_store_that_cannot_be_read_orders_nothing(tmp_path, flag_on, caplog) -> None:
    dataset = _gitlab(tmp_path, [5000.0])
    store = Path(dataset._filepath)
    store.mkdir(parents=True)
    (store / dataset.STORE_FILENAME).write_bytes(b"not parquet")
    host = _Host(answers=99)
    with caplog.at_level(logging.WARNING, logger=V.__name__):
        dataset.load_many(_projects(3), fetcher=host)
    assert host.asked == ["pkg0", "pkg1", "pkg2"]
    assert "asking in the order given" in caplog.text


def test_a_registry_orders_the_same_way(tmp_path) -> None:
    clock = _Clock()
    wall = [100.0]
    asked: list[str] = []

    def registry() -> RegistryUpstreamDataset:
        dataset = RegistryUpstreamDataset(
            url="https://registry.npmjs.org",
            registry="npm",
            filepath=str(tmp_path / "npm"),
            scheduler=RateLimitedScheduler(rps=1000.0, bucket_capacity=1000, clock=clock, sleep=clock.sleep),
            sleep=clock.sleep,
            clock=clock,
            max_retries=0,
        )
        dataset._now = lambda: wall[0]
        return dataset

    def fetcher(name: str) -> Any:
        asked.append(name)
        return {"dist-tags": {"latest": "1.0.0"}}

    registry().load_many([("a", "a"), ("b", "b")], fetcher=fetcher)
    wall[0] = 200.0
    asked.clear()
    registry().load_many([("a", "a"), ("b", "b"), ("c", "c")], fetcher=fetcher)
    assert asked == ["c", "a", "b"]


# ------------------------------------------------------------------ the column a reader never sees


def test_load_returns_the_three_columns_and_the_file_keeps_the_time(tmp_path, flag_on) -> None:
    dataset = _gitlab(tmp_path, [1234.9])
    returned = dataset.load_many(_projects(2), fetcher=_Host(answers=99))
    assert list(returned.columns) == list(V._VERSION_COLUMNS)
    assert list(dataset.load().columns) == list(V._VERSION_COLUMNS)
    stored = pd.read_parquet(Path(dataset._filepath) / dataset.STORE_FILENAME)
    assert list(stored.columns) == [*V._VERSION_COLUMNS, "asked_at"]
    assert stored["asked_at"].tolist() == [1234, 1234]


# ------------------------------------------------------------------ what the host said


def test_a_429s_limit_headers_are_read_by_name_in_a_fixed_order() -> None:
    assert V._limit_said(_http_error(429, dict(reversed(GITLAB_429.items())))) == SAID
    assert V._limit_said(_http_error(429, {"retry-after": "5"})) is None  # a plain dict is case-sensitive
    assert V._limit_said(_http_error(429, {"Retry-After": "5", "Server": "nginx"})) == "Retry-After=5"


def test_a_headers_value_never_reaches_the_log_as_sent() -> None:
    said = V._limit_said(
        _http_error(429, {"RateLimit-Name": "x\r\n[WARNING] forged line; rm -rf /", "RateLimit-Limit": "9" * 500})
    )
    assert said == "RateLimit-Name=xWARNINGforgedlinerm-rf RateLimit-Limit=" + "9" * 48
    assert V._limit_said(_http_error(429, {"RateLimit-Name": " \r\n "})) is None  # nothing plain left


@pytest.mark.parametrize("error", [_http_error(503, GITLAB_429), _http_error(404, GITLAB_429), TimeoutError("x")])
def test_only_a_429_says_anything(error) -> None:
    assert V._limit_said(error) is None
    assert V._limit_said(_http_error(429)) is None  # a 429 with no such header


def test_the_budget_keeps_the_last_thing_said() -> None:
    budget = FailureBudget()
    assert budget.host_said is None
    budget.heard("RateLimit-Limit=500")
    budget.heard(None)  # a 429 that says nothing keeps the last
    assert budget.host_said == "RateLimit-Limit=500"


def test_a_stopped_run_logs_what_the_host_said_once_and_records_it(tmp_path, flag_on, caplog) -> None:
    dataset = _gitlab(tmp_path, [1000.0], max_consecutive_failures=3)
    with caplog.at_level(logging.INFO, logger=V.__name__):
        dataset.load_many(_projects(8), fetcher=_Host(answers=2))
    lines = [r.getMessage() for r in caplog.records if "the host limits requests" in r.getMessage()]
    assert lines == [f"gitlab: the host limits requests: {SAID}"]  # pkg2 twice, pkg3: one line
    stop = [r.getMessage() for r in caplog.records if "unavailable this run" in r.getMessage()]
    assert len(stop) == 1 and f"finished 3 of 8; the host said {SAID}" in stop[0]
    marker = dataset.staleness()
    assert marker is not None and marker.reason.endswith(f"the host said {SAID}")


def test_a_registry_run_carries_what_the_host_said(tmp_path, caplog) -> None:
    clock = _Clock()
    dataset = RegistryUpstreamDataset(
        url="https://registry.npmjs.org",
        registry="npm",
        filepath=str(tmp_path / "npm"),
        scheduler=RateLimitedScheduler(rps=1000.0, bucket_capacity=1000, clock=clock, sleep=clock.sleep),
        sleep=clock.sleep,
        clock=clock,
        max_retries=0,
        max_consecutive_failures=1,
    )

    def throttled(name: str) -> Any:
        raise _http_error(429, {"Retry-After": "30"})

    with caplog.at_level(logging.INFO, logger=V.__name__):
        dataset.load_many([("a", "a"), ("b", "b")], fetcher=throttled)
    assert "npm: the host limits requests: Retry-After=30" in caplog.text
    assert "the host said Retry-After=30" in caplog.text


def test_a_run_the_host_never_throttles_says_nothing(tmp_path, flag_on, caplog) -> None:
    with caplog.at_level(logging.INFO, logger=V.__name__):
        _gitlab(tmp_path, [1000.0]).load_many(_projects(3), fetcher=_Host(answers=99))
    assert "the host limits requests" not in caplog.text and "the host said" not in caplog.text
