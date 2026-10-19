"""Story 35.3 (spec-pyforge-atlas CAP-65): upstream versions and feedstock health come from GitHub.

Legacy's three GitHub reads -- Phase K's releases and tags, Phase N's feedstock health, Phase E.5's
archived listing -- through an injected fetcher (no network), and the three consumers that pick
their rows by ``kind``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from pyforge.atlas.datasets.rate_limit import RateLimitedScheduler
from pyforge.atlas.datasets.request_datasets import GitHubRequestDataset, normalize_release_tag
from pyforge.atlas.pipelines.vcs_health.nodes import (
    detect_archived_feedstocks,
    fetch_live_health,
    track_upstream_versions,
)


def _dataset(tmp_path: Path, **kwargs: Any) -> GitHubRequestDataset:
    halve_min = kwargs.pop("halve_min", None)
    ds = GitHubRequestDataset(
        url="https://api.github.com/graphql",
        filepath=str(tmp_path / "store"),
        scheduler=RateLimitedScheduler(rps=1000.0, bucket_capacity=1000),
        sleep=kwargs.pop("sleep", lambda _s: None),
        **kwargs,
    )
    if halve_min is not None:
        ds.HALVE_MIN = halve_min  # the tests' batches are small; production halves above 12
    return ds


class _GitHub:
    """Answers each GraphQL body by what it asks for, as GitHub would."""

    def __init__(self, archived_pages: list[list[str]] | None = None) -> None:
        self.bodies: list[str] = []
        self.pages = archived_pages if archived_pages is not None else [["gone-feedstock", "not-a-feedstock-repo"]]

    def __call__(self, body: dict[str, Any]) -> dict[str, Any]:
        query = body["query"]
        self.bodies.append(query)
        if "organization" in query:
            page = 1 if "after:" in query else 0
            nodes = [{"name": n, "archivedAt": "2026-01-01T00:00:00Z"} for n in self.pages[page]]
            more = page + 1 < len(self.pages)
            listing = {"nodes": nodes, "pageInfo": {"hasNextPage": more, "endCursor": "c1" if more else None}}
            return {"data": {"organization": {"repositories": listing}}}
        if "releases" in query:
            return {
                "data": {
                    "r0": {"releases": {"nodes": []}, "refs": {"nodes": [{"name": "Release_1_6_15"}]}},  # tag only
                    "r1": {"releases": {"nodes": [{"tagName": "v3.0.44"}]}, "refs": {"nodes": [{"name": "v9"}]}},
                    "r2": None,
                    "r3": {"releases": {"nodes": []}, "refs": {"nodes": []}},
                    "rateLimit": {"cost": 1, "remaining": 4999},
                },
                "errors": [{"type": "NOT_FOUND", "path": ["r2"], "message": "Could not resolve to a Repository"}],
            }
        return {
            "data": {
                "r0": {
                    "pushedAt": "2026-10-17T00:00:00Z",
                    "isArchived": False,
                    "defaultBranchRef": {"target": {"statusCheckRollup": {"state": "SUCCESS"}}},
                    "issues": {"totalCount": 3},
                    "pullRequests": {"totalCount": 1},
                }
            }
        }


UPSTREAM = (
    ("a-pkg", "a", "a"),
    ("b-pkg", "b", "b"),
    ("b-extra", "b", "b"),  # two packages, one repo: one request, two rows
    ("gone-pkg", "c", "gone"),
    ("bare-pkg", "d", "bare"),
)


@pytest.mark.parametrize(
    ("tag", "version"),
    [
        ("v3.0.44", "3.0.44"),
        ("Release_1_6_15", "1_6_15"),
        ("rel-2.0", "2.0"),
        ("RELEASE-1", "1"),
        ("1.0", "1.0"),
        ("", None),
        (None, None),
        ("v", None),
    ],
)
def test_release_tags_normalize_as_legacy_does(tag, version):
    assert normalize_release_tag(tag) == version


def test_the_three_reads_land_as_rows_of_their_kind(tmp_path, monkeypatch):
    from pyforge.atlas.datasets import credentials as credential_switch

    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)  # load() shows every kind
    github = _GitHub()
    ds = _dataset(tmp_path)

    frame = ds.fetch_github(UPSTREAM, ["feedy"], fetcher=github)

    kinds = frame.groupby("kind").size().to_dict()
    assert kinds == {"upstream": 5, "feedstock": 1, "archived": 1}
    up = frame[frame["kind"] == "upstream"].set_index("key")
    assert up.loc["a-pkg", "upstream_version"] == "1_6_15"  # no release: the latest tag
    assert up.loc["b-pkg", "upstream_version"] == "3.0.44" and up.loc["b-extra", "upstream_version"] == "3.0.44"
    assert up.loc["gone-pkg", "last_error"].startswith("NOT_FOUND")
    assert up.loc["bare-pkg", "last_error"] == "no tags"
    assert sum("releases" in b for b in github.bodies) == 1 and "rateLimit" in github.bodies[0]
    fs = frame[frame["kind"] == "feedstock"].iloc[0]
    assert (fs["repo"], fs["ci_status"], fs["open_issues"], fs["open_prs"]) == (
        "conda-forge/feedy-feedstock",
        "success",
        3,
        1,
    )
    arch = frame[frame["kind"] == "archived"].iloc[0]
    assert (arch["feedstock_name"], bool(arch["archived"])) == ("gone", True)  # a non-feedstock repo is ignored
    assert ds.staleness() is None and len(ds.load()) == 7


def test_the_archived_listing_follows_its_pages(tmp_path):
    github = _GitHub(archived_pages=[["one-feedstock"], ["two-feedstock"]])

    frame = _dataset(tmp_path).fetch_github((), [], fetcher=github)

    assert sorted(frame["feedstock_name"]) == ["one", "two"] and sum("organization" in b for b in github.bodies) == 2


def test_the_feedstock_batches_are_legacys_25(tmp_path):
    github = _GitHub(archived_pages=[[]])

    _dataset(tmp_path).fetch_github((), [f"f{i}" for i in range(26)], fetcher=github)

    assert sum('owner: "conda-forge"' in b for b in github.bodies) == 2


def test_a_rate_limit_that_names_its_wait_is_waited_and_retried(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from kedro.io import DatasetError

    waits: list[float] = []
    calls = {"n": 0}

    def post(_body, _auth):  # noqa: ANN001, ANN202
        calls["n"] += 1
        if calls["n"] == 1:
            response = SimpleNamespace(status_code=403, headers={"Retry-After": "7"})
            raise DatasetError("Failed to send data", SimpleNamespace(response=response))
        return {"data": {"r0": {"releases": {"nodes": [{"tagName": "v1"}]}, "refs": {"nodes": []}}}}

    ds = _dataset(tmp_path, sleep=waits.append, max_retries=2)
    monkeypatch.setattr(ds, "_post", post)

    frame = ds.fetch_github((("p", "o", "r"),), [], auth=object())

    assert waits == [7.0] and frame.set_index("key").loc["p", "upstream_version"] == "1"


def test_a_store_written_before_this_story_keeps_its_rows(tmp_path, monkeypatch):
    from pyforge.atlas.datasets import credentials as credential_switch

    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)  # load() shows every kind
    ds = _dataset(tmp_path)
    Path(ds._filepath).mkdir(parents=True)
    pd.DataFrame({"feedstock_name": ["x", "y"], "stars": [1, 2]}).to_parquet(ds._store_path, index=False)

    ds.fetch_github((), ["feedy"], fetcher=_GitHub(archived_pages=[[]]))

    kinds = ds.load().groupby("kind")["key"].apply(sorted).to_dict()
    assert kinds == {"feedstock": ["feedy"], "health": ["x", "y"]}  # never collapsed onto one empty key


def _store() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "kind": ["upstream", "feedstock", "archived", "health"],
            "key": ["pkg", "fs", "old", "repo"],
            "conda_name": ["pkg", None, None, None],
            "feedstock_name": [None, "fs", "old", "repo"],
            "upstream_version": ["1.0", None, None, None],
            "last_error": [None, None, None, None],
            "archived": [None, False, True, True],
            "last_commit": [None, "2026-10-17", None, "2020"],
            "open_issues": [None, 3, None, 9],
            "open_prs": [None, 1, None, None],
            "ci_status": [None, "SUCCESS", None, None],
            "stars": [None, None, None, 5],
        }
    )


def test_each_consumer_reads_its_own_kind():
    store = _store()

    assert detect_archived_feedstocks(store)["feedstock_name"].tolist() == ["old"]  # not the health row's repo
    up = track_upstream_versions(store, pd.DataFrame(), pd.DataFrame())
    assert up[["conda_name", "host", "upstream_version"]].values.tolist() == [["pkg", "github", "1.0"]]
    health = fetch_live_health(store)
    assert health[["feedstock_name", "open_prs", "ci_status"]].values.tolist() == [["fs", 1, "SUCCESS"]]


def test_a_store_without_kinds_reads_as_before():
    store = _store().drop(columns=["kind", "key"])

    assert set(detect_archived_feedstocks(store)["feedstock_name"]) == {"old", "repo"}
    assert list(fetch_live_health(store).columns) == ["feedstock_name", "stars", "last_commit", "open_issues"]


def _timed_out(status: int = 502) -> Exception:
    from types import SimpleNamespace

    from kedro.io import DatasetError

    return DatasetError(
        "Failed to send data", SimpleNamespace(response=SimpleNamespace(status_code=status, headers={}))
    )


_NO_ARCHIVED = {"data": {"organization": {"repositories": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}}


def _upstream_only(fetch):  # noqa: ANN001, ANN202
    """``fetch`` for the upstream batches; Phase E.5's archived listing answers empty."""

    def answer(body: dict[str, Any]) -> dict[str, Any]:
        return _NO_ARCHIVED if "organization" in body["query"] else fetch(body)

    return answer


def _answer_each(body: dict[str, Any]) -> dict[str, Any]:
    """Every repository a body names, at version ``v1.<n>`` where n is its alias."""
    n = body["query"].count("repository(")
    return {
        "data": {f"r{i}": {"releases": {"nodes": [{"tagName": f"v1.{i}"}]}, "refs": {"nodes": []}} for i in range(n)}
    }


@pytest.mark.parametrize("status", [502, 504])
def test_a_batch_github_cannot_answer_in_time_is_halved(tmp_path, status):
    sizes: list[int] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        n = body["query"].count("repository(")
        sizes.append(n)
        if n > 2:
            raise _timed_out(status)
        return _answer_each(body)

    upstream = tuple((f"p{i}", "o", f"r{i}") for i in range(5))
    frame = _dataset(tmp_path, max_retries=0, halve_min=1).fetch_github(upstream, [], fetcher=_upstream_only(fetch))

    got = frame.set_index("key")["upstream_version"].to_dict()
    # 5 -> 2 + 3 -> 2 + (1 + 2): each repository keeps its own row, renumbered back into the batch
    assert got == {"p0": "1.0", "p1": "1.1", "p2": "1.0", "p3": "1.0", "p4": "1.1"}
    assert sizes == [5, 2, 3, 1, 2]


def test_a_half_that_still_fails_names_the_failure_on_its_rows(tmp_path):
    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if 'name: "r0"' in body["query"]:
            raise _timed_out()
        return _answer_each(body)

    upstream = (("p0", "o", "r0"), ("p1", "o", "r1"))
    frame = (
        _dataset(tmp_path, max_retries=0, halve_min=1)
        .fetch_github(upstream, [], fetcher=_upstream_only(fetch))
        .set_index("key")
    )

    assert frame.loc["p0", "last_error"] == "HTTP 502" and frame.loc["p0", "upstream_version"] is None
    assert frame.loc["p1", "upstream_version"] == "1.0"


def test_a_batch_that_fails_otherwise_is_not_halved(tmp_path):
    sizes: list[int] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        sizes.append(body["query"].count("repository("))
        raise _timed_out(500)

    _dataset(tmp_path, max_retries=0).fetch_github(
        tuple((f"p{i}", "o", f"r{i}") for i in range(4)), [], fetcher=_upstream_only(fetch)
    )

    assert sizes == [4]


def test_the_graphql_post_stops_waiting_after_a_minute(tmp_path, monkeypatch):
    from pyforge.atlas.datasets import request_datasets as R

    seen: dict[str, Any] = {}

    class _Recording:
        def __init__(self, **kwargs: Any) -> None:
            seen.update(kwargs)

        def save(self, _body: Any) -> None:
            pass

        def get_last_response(self) -> dict[str, Any]:
            return {"data": {}}

    monkeypatch.setattr(R, "APIDataset", _Recording)
    _dataset(tmp_path)._post({"query": "{}"}, auth=object())  # type: ignore[arg-type]

    assert seen["save_args"] == {"timeout": GitHubRequestDataset.GRAPHQL_TIMEOUT_SECONDS} == {"timeout": 60}


def _feedstock_answer(body: dict[str, Any]) -> dict[str, Any]:
    n = body["query"].count("repository(")
    node = {"pushedAt": "t", "isArchived": False, "issues": {"totalCount": 0}, "pullRequests": {"totalCount": 0}}
    return {"data": {f"r{i}": node for i in range(n)}}


def test_phase_n_runs_four_batches_side_by_side_and_keeps_their_order(tmp_path):
    import threading
    import time as _time

    lock, live, peak = threading.Lock(), [0], [0]

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if "organization" in body["query"]:
            return _NO_ARCHIVED
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        _time.sleep(0.02)
        with lock:
            live[0] -= 1
        return _feedstock_answer(body)

    feedstocks = [f"fs{i:03d}" for i in range(200)]  # 8 batches of 25
    frame = _dataset(tmp_path).fetch_github((), feedstocks[::-1], fetcher=fetch)

    assert frame["key"].tolist() == feedstocks and frame["last_error"].isna().all()
    assert 2 <= peak[0] <= GitHubRequestDataset.FEEDSTOCK_CONCURRENCY == 4


def test_each_failed_batch_names_its_own_failure(tmp_path):
    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        query = body["query"]
        if "organization" in query:
            return _NO_ARCHIVED
        if '"fs000-feedstock"' in query:
            raise _timed_out(500)
        if '"fs025-feedstock"' in query:
            raise _timed_out(503)
        return _feedstock_answer(body)

    feedstocks = [f"fs{i:03d}" for i in range(75)]
    frame = _dataset(tmp_path, max_retries=0).fetch_github((), feedstocks, fetcher=fetch).set_index("key")

    assert frame.loc["fs000", "last_error"] == "HTTP 500" and frame.loc["fs024", "last_error"] == "HTTP 500"
    assert frame.loc["fs025", "last_error"] == "HTTP 503" and frame.loc["fs050", "last_error"] is None


def test_a_refusal_stops_the_feedstock_batches_not_yet_sent(tmp_path):
    sent: list[str] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        query = body["query"]
        sent.append(query)
        if "organization" in query:
            return _NO_ARCHIVED
        raise _timed_out(401)

    feedstocks = [f"fs{i:03d}" for i in range(25 * 40)]
    frame = _dataset(tmp_path, max_retries=0).fetch_github((), feedstocks, fetcher=fetch)

    assert len(sent) <= GitHubRequestDataset.FEEDSTOCK_CONCURRENCY  # at most the batches already in flight
    assert set(frame["last_error"]) == {"HTTP 401"}


def test_a_batch_halved_and_answered_leaves_no_marker(tmp_path):
    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if body["query"].count("repository(") > 2:
            raise _timed_out(502)
        return _answer_each(body)

    ds = _dataset(tmp_path, max_retries=0, halve_min=1)
    ds.fetch_github(tuple((f"p{i}", "o", f"r{i}") for i in range(4)), [], fetcher=_upstream_only(fetch))

    assert ds.staleness() is None


def test_repositories_that_still_fail_are_counted_in_the_marker(tmp_path):
    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if 'name: "r0"' in body["query"]:
            raise _timed_out(500)
        return _answer_each(body)

    ds = _dataset(tmp_path, max_retries=0)
    ds.UPSTREAM_BATCH = 1  # one repository a batch: r0's fails, r1's is answered

    ds.fetch_github((("p0", "o", "r0"), ("p1", "o", "r1")), [], fetcher=_upstream_only(fetch))

    assert ds.staleness().reason == "repositories that failed: 1 (HTTP 500) -- they keep last-good"


# -- review round 1 ------------------------------------------------------------------------------


def _seed(ds: GitHubRequestDataset, rows: list[dict[str, Any]]) -> None:
    Path(ds._filepath).mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(ds._store_path, index=False)


def _stored(ds: GitHubRequestDataset) -> pd.DataFrame:
    return pd.read_parquet(ds._store_path).set_index(["kind", "key"])


_GOOD_FS = {"kind": "feedstock", "feedstock_name": "fs000", "open_prs": 7.0, "ci_status": "success", "last_error": None}


def test_a_feedstock_the_run_could_not_read_keeps_its_last_good_values(tmp_path):
    ds = _dataset(tmp_path, max_retries=0)
    _seed(ds, [{**_GOOD_FS, "key": "fs000"}])

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if "organization" in body["query"]:
            return _NO_ARCHIVED
        if '"fs000-feedstock"' in body["query"]:
            raise _timed_out(500)
        return _feedstock_answer(body)

    ds.fetch_github((), [f"fs{i:03d}" for i in range(50)], fetcher=fetch)  # two batches: the first fails

    row = _stored(ds).loc[("feedstock", "fs000")]
    assert (row["open_prs"], row["ci_status"], row["last_error"]) == (7.0, "success", "HTTP 500")
    assert "repositories that failed: 25 (HTTP 500)" in ds.staleness().reason


def test_a_refusal_writes_no_row_for_what_it_never_asked(tmp_path):
    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        query = body["query"]
        if "releases" in query:
            return _answer_each(body)
        if "organization" in query:
            return _NO_ARCHIVED
        raise _timed_out(401)

    ds = _dataset(tmp_path, max_retries=0)
    ds.FEEDSTOCK_CONCURRENCY = 1  # one batch at a time: the refused one, then one never sent
    _seed(ds, [{**_GOOD_FS, "key": f"fs{i:03d}", "feedstock_name": f"fs{i:03d}"} for i in range(50)])
    ds.fetch_github((("p", "o", "r"),), [f"fs{i:03d}" for i in range(50)], fetcher=fetch)

    stored = _stored(ds)
    assert set(stored.xs("feedstock")["open_prs"]) == {7.0}  # every last-good value kept
    assert stored.loc[("feedstock", "fs000"), "last_error"] == "HTTP 401"  # the refused batch: its error
    assert stored.loc[("feedstock", "fs025"), "last_error"] is None  # never asked: untouched
    assert (
        stored.loc[("upstream", "p"), "upstream_version"] == "1.0" and "stopped after HTTP 401" in ds.staleness().reason
    )


def test_the_archived_listing_alone_is_no_success(tmp_path):
    ds = _dataset(tmp_path, max_retries=0)
    _seed(ds, [{**_GOOD_FS, "key": "fs000"}])

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if "organization" in body["query"]:
            return {"data": {"organization": {"repositories": {"nodes": [{"name": "x-feedstock"}], "pageInfo": {}}}}}
        raise _timed_out(500)

    ds.fetch_github((("p", "o", "r"),), ["fs000"], fetcher=fetch)

    assert _stored(ds).loc[("feedstock", "fs000"), "open_prs"] == 7.0 and len(_stored(ds)) == 1
    assert ds.staleness().reason.startswith("every GitHub batch failed (HTTP 500)")


def test_with_the_flag_off_the_store_reads_as_before_this_story(tmp_path, monkeypatch):
    from pyforge.atlas.datasets import credentials as credential_switch

    ds = _dataset(tmp_path)
    _seed(
        ds,
        [
            {"kind": "health", "key": "h", "feedstock_name": "h", "stars": 3.0},
            {**_GOOD_FS, "key": "fs000"},
            {"kind": "upstream", "key": "p", "conda_name": "p", "upstream_version": "1.0"},
        ],
    )

    off = ds.load()
    monkeypatch.setattr(credential_switch, "live_vcs_universe", lambda: True)
    on = ds.load()

    assert off["kind"].tolist() == ["health"]
    assert sorted(on["kind"]) == ["feedstock", "health", "upstream"]
    assert fetch_live_health(off)["feedstock_name"].tolist() == ["h"]


def test_halving_stops_at_a_dozen_repositories(tmp_path):
    sizes: list[int] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        sizes.append(body["query"].count("repository("))
        raise _timed_out(502)

    upstream = tuple((f"p{i:03d}", "o", f"r{i:03d}") for i in range(100))
    _dataset(tmp_path, max_retries=0).fetch_github(upstream, [], fetcher=_upstream_only(fetch))

    assert min(sizes) == 6 and len(sizes) == 23  # 100, 50x2, 25x4, 12/13x8, then each 13 as 6/7


def test_ten_batches_failing_whole_in_a_row_stop_the_run(tmp_path):
    sent: list[str] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        sent.append(body["query"])
        raise _timed_out(500)

    ds = _dataset(tmp_path, max_retries=0)
    ds.UPSTREAM_BATCH = 1
    ds.fetch_github(tuple((f"p{i}", "o", f"r{i}") for i in range(15)), [], fetcher=_upstream_only(fetch))

    assert len(sent) == 10 and "10 batches failed in a row (HTTP 500)" in ds.staleness().reason


def test_a_refusal_in_one_thread_stops_a_retry_in_another(tmp_path):
    import threading
    import time as _time

    refused, started = threading.Event(), threading.Event()
    calls: dict[str, int] = {}

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        query = body["query"]
        if "organization" in query:
            return _NO_ARCHIVED
        first = query.split('name: "', 1)[1].split('"', 1)[0]
        calls[first] = calls.get(first, 0) + 1
        if first == "fs000-feedstock":
            started.wait(1)  # the other batch is in flight before this one is refused
            refused.set()
            raise _timed_out(401)
        started.set()
        refused.wait(1)
        _time.sleep(0.05)  # the refusal is recorded before this batch retries
        raise _timed_out(502)

    ds = _dataset(tmp_path, max_retries=3, halve_min=100)
    ds.fetch_github((), [f"fs{i:03d}" for i in range(50)], fetcher=fetch)

    assert calls["fs025-feedstock"] == 1  # never sent again after the other thread's 401


def test_a_rate_limited_answer_stops_the_run(tmp_path):
    sent: list[str] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        sent.append(body["query"])
        return {"errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}]}

    ds = _dataset(tmp_path, max_retries=0)
    ds.UPSTREAM_BATCH = 1
    ds.fetch_github(tuple((f"p{i}", "o", f"r{i}") for i in range(5)), [], fetcher=fetch)

    assert len(sent) == 1 and "RATE_LIMITED" in ds.staleness().reason


def test_a_failed_archived_page_is_in_the_marker(tmp_path):
    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if "organization" in body["query"]:
            raise _timed_out(500)
        return _answer_each(body)

    ds = _dataset(tmp_path, max_retries=0)
    ds.fetch_github((("p", "o", "r"),), [], fetcher=fetch)

    assert ds.staleness().reason == "archived listing stopped at page 1: HTTP 500"


def test_the_queries_ask_what_legacy_asks():
    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath="/tmp/unused")
    k = ds.build_upstream_query([("o", "r")])["query"]
    n = ds.build_feedstock_query(["fs"])["query"]
    e = ds.build_archived_query(None)["query"]

    assert "releases(first: 1, orderBy: {field: CREATED_AT, direction: DESC}) { nodes { tagName } }" in k
    assert 'refs(refPrefix: "refs/tags/", first: 1, orderBy: {field: TAG_COMMIT_DATE, direction: DESC})' in k
    assert (
        "pushedAt isArchived defaultBranchRef { target { ... on Commit { statusCheckRollup { state } } } } "
        "issues(states: OPEN) { totalCount } pullRequests(states: OPEN) { totalCount }"
    ) in n
    assert 'organization(login: "conda-forge")' in e and "repositories(first: 100, isArchived: true" in e


def test_a_retry_is_logged_by_its_status_never_its_text(tmp_path, caplog):
    import logging
    from types import SimpleNamespace

    caplog.set_level(logging.INFO, logger="pyforge.atlas.datasets.request_datasets")

    from kedro.io import DatasetError

    answers = iter(
        [DatasetError("SECRET-TEXT", SimpleNamespace(response=SimpleNamespace(status_code=502, headers={}))), None]
    )

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if "organization" in body["query"]:
            return _NO_ARCHIVED
        exc = next(answers)
        if exc is not None:
            raise exc
        return _answer_each(body)

    _dataset(tmp_path, max_retries=1).fetch_github((("p", "o", "r"),), [], fetcher=fetch)

    assert "HTTP 502, retry 1/1" in caplog.text and "SECRET-TEXT" not in caplog.text


def test_a_read_timeout_is_halved_too(tmp_path):
    import requests
    from kedro.io import DatasetError

    sizes: list[int] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        n = body["query"].count("repository(")
        sizes.append(n)
        if n > 2:
            try:
                raise requests.exceptions.ReadTimeout("slow")
            except requests.exceptions.ReadTimeout as cause:
                raise DatasetError("Failed to connect to the remote server") from cause
        return _answer_each(body)

    _dataset(tmp_path, max_retries=0, halve_min=1).fetch_github(
        tuple((f"p{i}", "o", f"r{i}") for i in range(4)), [], fetcher=_upstream_only(fetch)
    )

    assert sizes == [4, 2, 2]


def test_a_feedstock_github_could_not_resolve_names_its_error(tmp_path):
    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        if "organization" in body["query"]:
            return _NO_ARCHIVED
        answer = _feedstock_answer(body)
        answer["data"]["r1"] = None
        answer["errors"] = [{"type": "NOT_FOUND", "path": ["r1"], "message": "Could not resolve"}]
        return answer

    frame = _dataset(tmp_path).fetch_github((), ["a", "b"], fetcher=fetch).set_index("key")

    assert frame.loc["b", "last_error"] == "NOT_FOUND: Could not resolve" and frame.loc["a", "last_error"] is None


def test_the_live_health_keeps_one_row_per_feedstock_with_its_error():
    store = pd.DataFrame(
        [
            {"kind": "feedstock", "key": "a", "feedstock_name": "a", "open_prs": 1, "last_error": None},
            {"kind": "feedstock", "key": "a", "feedstock_name": "a", "open_prs": 2, "last_error": None},
            {"kind": "feedstock", "key": "b", "feedstock_name": "b", "open_prs": None, "last_error": "HTTP 500"},
        ]
    )

    out = fetch_live_health(store)

    assert out["feedstock_name"].tolist() == ["a", "b"] and out["last_error"].tolist()[1] == "HTTP 500"


def test_a_repo_named_in_two_cases_is_asked_once(tmp_path):
    asked: list[int] = []

    def fetch(body: dict[str, Any]) -> dict[str, Any]:
        asked.append(body["query"].count("repository("))
        return _answer_each(body)

    frame = _dataset(tmp_path).fetch_github(
        (("a", "Owner", "Repo"), ("b", "owner", "repo")), [], fetcher=_upstream_only(fetch)
    )

    assert asked == [1] and frame.set_index("key").loc[["a", "b"], "upstream_version"].tolist() == ["1.0", "1.0"]
