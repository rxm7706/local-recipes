"""B1 request-parameterized dataset tests (Story B1, AC-2 / G-2).

Covers the parameterization surface (``request_path`` / ``with_query``) that the
catalog FLIP delivers — the AC-2 boundary a NODE may never cross — and confirms both
datasets construct offline + carry the rate-limit scheduler (dataset-owned discipline).
"""

from __future__ import annotations

import pytest

from pyforge.atlas.datasets import AnacondaDownloadsDataset, GitHubRequestDataset
from pyforge.atlas.datasets.rate_limit import DEFAULT_RPS, RateLimitedScheduler
from pyforge.atlas.datasets.refresh import RefreshRequest


def test_anaconda_dataset_constructs_offline_and_owns_scheduler():
    ds = AnacondaDownloadsDataset(url="https://api.anaconda.org/package", metadata={"layer": "raw"})
    assert isinstance(ds.scheduler, RateLimitedScheduler)
    assert ds.scheduler.rps == DEFAULT_RPS == 3.0
    d = ds._describe()
    assert d["parameterization"] == "AnacondaDownloadsDataset"
    assert d["method"] == "GET"


def test_anaconda_request_path_is_per_package():
    ds = AnacondaDownloadsDataset(url="https://api.anaconda.org/package")
    assert ds.request_path("conda-forge", "numpy") == "https://api.anaconda.org/package/conda-forge/numpy"
    # owner defaults to conda-forge, slashes trimmed
    assert ds.request_path("", "pandas") == "https://api.anaconda.org/package/conda-forge/pandas"


def test_github_dataset_constructs_offline_with_credentials(tmp_path):
    ds = GitHubRequestDataset(
        url="https://api.github.com/graphql",
        filepath=str(tmp_path / "vcs_github_api_raw"),
        method="POST",
        load_args={"json": {"query": "q"}},
        credentials={"stub": "x"},
        metadata={"layer": "raw"},
    )
    assert ds.scheduler.rps == 3.0
    assert ds._describe()["method"] == "POST"


def test_github_with_query_builds_the_request_body(tmp_path):
    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    body = ds.with_query("query { rateLimit { remaining } }", {"owner": "conda-forge"})
    assert body["query"].startswith("query")
    assert body["variables"] == {"owner": "conda-forge"}
    # no variables -> no variables key
    assert "variables" not in ds.with_query("query {}")


def test_github_build_batch_query_aliases_every_repo(tmp_path):
    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    body = ds.build_batch_query([("conda-forge", "numpy-feedstock"), ("conda-forge", "pandas-feedstock")])
    assert "r0: repository" in body["query"]
    assert "r1: repository" in body["query"]
    # empty batch falls back to the harmless rate-limit probe (never an empty POST body)
    assert ds.build_batch_query([])["query"] == "query { rateLimit { remaining } }"


def test_github_fetch_repo_health_persists_and_reads_back(tmp_path):
    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    payload = {
        "data": {
            "r0": {
                "isArchived": False,
                "stargazerCount": 42,
                "pushedAt": "2026-01-01T00:00:00Z",
                "issues": {"totalCount": 3},
            }
        }
    }
    out = ds.fetch_repo_health([("conda-forge", "numpy-feedstock")], fetcher=lambda body: payload)
    assert out.loc[0, "feedstock_name"] == "numpy-feedstock"
    assert not out.loc[0, "archived"]
    assert out.loc[0, "stars"] == 42
    assert out.loc[0, "open_issues"] == 3
    # persisted -> load() (a read-only projection) sees the same row.
    loaded = ds.load()
    assert loaded.loc[0, "feedstock_name"] == "numpy-feedstock"


def test_github_fetch_repo_health_all_failed_keeps_last_good(tmp_path):
    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    good = {"data": {"r0": {"isArchived": False, "stargazerCount": 1, "pushedAt": None, "issues": {}}}}
    ds.fetch_repo_health([("conda-forge", "numpy-feedstock")], fetcher=lambda body: good)
    assert not ds.load().empty

    # a batch where the repo is missing from the response -> every row fails -> AD-13
    # must NOT clobber last-good with an all-error frame.
    ds.fetch_repo_health([("conda-forge", "missing-feedstock")], fetcher=lambda body: {"data": {}})
    still_good = ds.load()
    assert still_good.loc[0, "feedstock_name"] == "numpy-feedstock"
    assert ds.is_stale()


def test_github_fetch_repo_health_fetcher_error_marks_stale_not_raise(tmp_path):
    ds = GitHubRequestDataset(
        url="https://api.github.com/graphql",
        filepath=str(tmp_path / "store"),
        method="POST",
        sleep=lambda secs: None,
    )

    def boom(body):
        raise RuntimeError("network down")

    out = ds.fetch_repo_health([("conda-forge", "numpy-feedstock")], fetcher=boom)
    # the RETURN value carries the per-repo error detail (mirrors
    # VcsHostSeedDataset/RegistryUpstreamDataset.load_many, which also return the
    # full attempted frame on total failure) — only the PERSISTED store is forced
    # empty (AD-13 clobber-safety).
    assert out.loc[0, "feedstock_name"] == "numpy-feedstock"
    assert out.loc[0, "last_error"] is not None
    assert ds.load().empty
    assert ds.is_stale()


def test_github_fetch_repo_health_retries_max_retries_times_with_backoff(tmp_path):
    """Review fix #4: max_retries (accepted in __init__) is actually wired into a
    retry loop, with a backoff between attempts (review fix #3's pattern applied to
    GitHub) — not silently discarded / single-attempt-only."""
    sleeps = []
    ds = GitHubRequestDataset(
        url="https://api.github.com/graphql",
        filepath=str(tmp_path / "store"),
        method="POST",
        max_retries=2,
        sleep=lambda secs: sleeps.append(secs),
    )
    attempts = {"n": 0}

    def flaky(body):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return {"data": {"r0": {"isArchived": False, "stargazerCount": 1, "pushedAt": None, "issues": {}}}}

    out = ds.fetch_repo_health([("conda-forge", "numpy-feedstock")], fetcher=flaky)
    assert attempts["n"] == 3  # 1 initial + 2 retries == max_retries
    assert out.loc[0, "last_error"] is None
    assert len(sleeps) == 2


def test_github_fetch_repo_health_exhausts_retries_and_degrades(tmp_path):
    ds = GitHubRequestDataset(
        url="https://api.github.com/graphql",
        filepath=str(tmp_path / "store"),
        method="POST",
        max_retries=1,
        sleep=lambda secs: None,
    )
    attempts = {"n": 0}

    def always_fails(body):
        attempts["n"] += 1
        raise RuntimeError("down")

    out = ds.fetch_repo_health([("conda-forge", "numpy-feedstock")], fetcher=always_fails)
    assert attempts["n"] == 2  # 1 initial + 1 retry == max_retries, then give up
    assert out.loc[0, "last_error"] is not None
    assert ds.is_stale()


def test_github_fetch_repo_health_empty_batch_makes_zero_network_calls(tmp_path):
    """Review fix #2: an EMPTY repos batch must short-circuit before ANY network
    call — including the harmless rate-limit probe the old code issued via a bare
    ``fetcher=None`` default path. Blocks the socket layer (mirrors
    ``tests/catalog/test_catalog_resolution.py``'s ``_network_blocked()``) so a
    regression here fails loudly instead of silently reaching a real endpoint."""
    import socket
    from contextlib import contextmanager

    @contextmanager
    def _network_blocked():
        def _blocked(*args, **kwargs):  # pragma: no cover - only on violation
            raise AssertionError("network access attempted for an empty repos batch")

        orig = (
            socket.socket.connect,
            socket.socket.connect_ex,
            socket.create_connection,
            socket.getaddrinfo,
        )
        socket.socket.connect = _blocked  # type: ignore[method-assign]
        socket.socket.connect_ex = _blocked  # type: ignore[method-assign]
        socket.create_connection = _blocked  # type: ignore[assignment]
        socket.getaddrinfo = _blocked  # type: ignore[assignment]
        try:
            yield
        finally:
            (
                socket.socket.connect,
                socket.socket.connect_ex,
                socket.create_connection,
                socket.getaddrinfo,
            ) = orig

    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    with _network_blocked():
        out = ds.fetch_repo_health(())  # no fetcher injected -> would hit APIDataset for real
    assert out.empty
    assert ds.is_stale()
    # and the same holds through save() -> the production default path.
    ds2 = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store2"), method="POST")
    with _network_blocked():
        ds2.save(RefreshRequest(store="vcs_github_api_raw", cadence_seconds=0))
    assert ds2.is_stale()


def test_github_batch_query_chunks_large_repo_lists(tmp_path):
    """Review fix #5: a repos sequence larger than GITHUB_BATCH_QUERY_MAX is split
    into multiple batched requests (mirrors the Basilisk chunk_queries precedent) —
    never one unbounded query."""
    from pyforge.atlas.datasets.request_datasets import GITHUB_BATCH_QUERY_MAX

    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    n = GITHUB_BATCH_QUERY_MAX + 5
    repos = [("conda-forge", f"pkg{i}-feedstock") for i in range(n)]
    call_sizes = []

    def fetcher(body):
        # count aliases in this one request's query to recover the chunk size
        chunk_size = body["query"].count("repository(owner:")
        call_sizes.append(chunk_size)
        data = {
            f"r{i}": {"isArchived": False, "stargazerCount": 0, "pushedAt": None, "issues": {}}
            for i in range(chunk_size)
        }
        return {"data": data}

    out = ds.fetch_repo_health(repos, fetcher=fetcher)
    assert len(call_sizes) == 2  # 100 + 5 -> two chunks, never one unbounded request
    assert sum(call_sizes) == n
    assert all(size <= GITHUB_BATCH_QUERY_MAX for size in call_sizes)
    assert len(out) == n


def test_github_save_only_accepts_refresh_request(tmp_path):
    from kedro.io.core import DatasetError

    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    with pytest.raises(DatasetError, match="RefreshRequest"):
        ds.save({"a": 1})
    # a RefreshRequest is accepted -> drives fetch_repo_health() with no crash (empty
    # batch by default -> AD-13 marks stale, never raises).
    ds.save(RefreshRequest(store="vcs_github_api_raw", cadence_seconds=0))
    assert ds.is_stale()


def test_github_save_rejects_a_refresh_request_for_a_different_store(tmp_path):
    """Review fix #8: there is exactly one GitHub catalog entry, so any other
    store name is unambiguously a pipeline-wiring drift."""
    from kedro.io.core import DatasetError

    ds = GitHubRequestDataset(url="https://api.github.com/graphql", filepath=str(tmp_path / "store"), method="POST")
    with pytest.raises(DatasetError, match="drifted out of sync"):
        ds.save(RefreshRequest(store="vcs_gitlab_api_raw"))


def test_anaconda_load_returns_empty_stub_not_base_url():
    ds = AnacondaDownloadsDataset(url="https://api.anaconda.org/package")
    frame = ds.load()
    assert list(frame.columns) == ["conda_name", "version", "downloads"]
    assert frame.empty


def test_anaconda_load_many_uses_injected_fetcher():
    ds = AnacondaDownloadsDataset(url="https://api.anaconda.org/package")

    def fake_fetch(path: str) -> dict:
        assert path.endswith("/conda-forge/numpy")
        return {
            "files": [
                {"version": "1.26.0", "ndownloads": 100},
                {"version": "1.25.0", "ndownloads": 50},
            ]
        }

    out = ds.load_many(["numpy"], fetcher=fake_fetch)
    assert len(out) == 2
    assert out["downloads"].sum() == 150


def test_request_datasets_are_read_only_sources():
    from kedro.io.core import DatasetError

    ds = AnacondaDownloadsDataset(url="https://api.anaconda.org/package")
    # kedro's AbstractDataset.save wraps our NotImplementedError in a DatasetError
    with pytest.raises(DatasetError, match="read-only"):
        ds.save({"a": 1})
