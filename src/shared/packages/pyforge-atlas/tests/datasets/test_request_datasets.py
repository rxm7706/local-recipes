"""B1 request-parameterized dataset tests (Story B1, AC-2 / G-2).

Covers the parameterization surface (``request_path`` / ``with_query``) that the
catalog FLIP delivers — the AC-2 boundary a NODE may never cross — and confirms both
datasets construct offline + carry the rate-limit scheduler (dataset-owned discipline).
"""

from __future__ import annotations

import pytest

from pyforge.atlas.datasets import AnacondaDownloadsDataset, GitHubRequestDataset
from pyforge.atlas.datasets.rate_limit import DEFAULT_RPS, RateLimitedScheduler


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


def test_github_dataset_constructs_offline_with_credentials():
    ds = GitHubRequestDataset(
        url="https://api.github.com/graphql",
        method="POST",
        load_args={"json": {"query": "q"}},
        credentials={"stub": "x"},
        metadata={"layer": "raw"},
    )
    assert ds.scheduler.rps == 3.0
    assert ds._describe()["method"] == "POST"


def test_github_with_query_builds_the_request_body():
    ds = GitHubRequestDataset(url="https://api.github.com/graphql", method="POST")
    body = ds.with_query("query { rateLimit { remaining } }", {"owner": "conda-forge"})
    assert body["query"].startswith("query")
    assert body["variables"] == {"owner": "conda-forge"}
    # no variables -> no variables key
    assert "variables" not in ds.with_query("query {}")


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
