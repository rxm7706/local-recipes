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
    return GitHubRequestDataset(
        url="https://api.github.com/graphql",
        filepath=str(tmp_path / "store"),
        scheduler=RateLimitedScheduler(rps=1000.0, bucket_capacity=1000),
        sleep=kwargs.pop("sleep", lambda _s: None),
        **kwargs,
    )


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


def test_the_three_reads_land_as_rows_of_their_kind(tmp_path):
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
        "SUCCESS",
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


def test_a_store_written_before_this_story_keeps_its_rows(tmp_path):
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
