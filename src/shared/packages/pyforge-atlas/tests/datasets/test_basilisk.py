"""Basilisk source dataset tests (Story B8, AC-1 + AC-5).

Proves the DATASET-owned discipline against a STUB fetcher — NO live Basilisk call
(AD-11; Basilisk is pre-announcement): the ``POST /v1/querybatch`` ≤1,000-query chunking,
the bounded ``GET /v1/vulns/{id}`` rate-limit discipline (concurrency cap + Retry-After +
jittered backoff), and the AD-13 offline-skip + keep-last-good + staleness marker.
"""

from __future__ import annotations

import json

import pytest
from kedro.io.core import DatasetError

from pyforge.atlas.datasets.basilisk import (
    BASILISK_QUERYBATCH_MAX,
    BasiliskBatchDataset,
    BasiliskDetailDataset,
    build_conda_purl,
    chunk_queries,
)
from pyforge.atlas.datasets.rate_limit import FetchError, RateLimitedScheduler


# --- chunk_queries (the ≤1,000-query discipline, AC-1) ----------------------

def test_chunk_queries_splits_at_1000_no_drop_no_dupe():
    purls = [f"pkg:conda/conda-forge/p{i}" for i in range(2500)]
    chunks = chunk_queries(purls)
    assert [len(c) for c in chunks] == [1000, 1000, 500]
    assert all(len(c) <= BASILISK_QUERYBATCH_MAX for c in chunks)
    # nothing dropped or duplicated, order preserved
    flat = [p for c in chunks for p in c]
    assert flat == purls


def test_chunk_queries_drops_none_and_handles_empty():
    assert chunk_queries([]) == []
    assert chunk_queries(None) == []
    assert chunk_queries(["a", None, "b"]) == [["a", "b"]]


def test_chunk_queries_rejects_nonpositive_size():
    with pytest.raises(ValueError):
        chunk_queries(["a"], size=0)


def test_build_conda_purl_cep63_form():
    assert build_conda_purl("libtiff", "4.6.0") == "pkg:conda/conda-forge/libtiff@4.6.0"
    assert build_conda_purl("perl") == "pkg:conda/conda-forge/perl"


# --- BasiliskBatchDataset (querybatch chunking + AD-13) ---------------------

def _batch(tmp_path, **kw):
    return BasiliskBatchDataset(
        url="https://api.basilisk.prefix.dev/v1/querybatch",
        filepath=str(tmp_path / "batch"),
        **kw,
    )


def test_batch_query_population_chunks_and_concatenates(tmp_path):
    seen_chunk_sizes: list[int] = []

    def fetcher(chunk):
        seen_chunk_sizes.append(len(chunk))
        # one advisory record per queried package (conda_name derived from the purl)
        return [
            {"conda_name": p.rsplit("/", 1)[-1].split("@")[0], "advisories": []}
            for p in chunk
        ]

    ds = _batch(tmp_path, fetcher=fetcher)
    purls = [build_conda_purl(f"p{i}") for i in range(2300)]
    out = ds.query_population(purls)
    # the DATASET chunked at ≤1000 (2300 -> 1000,1000,300), never the node
    assert seen_chunk_sizes == [1000, 1000, 300]
    assert len(out) == 2300
    assert not ds.is_stale()  # a good fetch clears stale


def test_batch_query_population_uses_the_scheduler(tmp_path):
    # one rate-limit token per chunk-request. Frozen clock -> no time-based refill, so the
    # token count is deterministic; bucket >> chunks -> never throttles (no sleep).
    sched = RateLimitedScheduler(
        rps=1000.0, bucket_capacity=100, clock=lambda: 0.0, sleep=lambda s: None
    )
    start_tokens = sched.tokens
    ds = _batch(tmp_path, fetcher=lambda chunk: [], scheduler=sched)
    ds.query_population([build_conda_purl(f"p{i}") for i in range(2500)])
    # 3 chunks -> exactly 3 tokens acquired
    assert sched.tokens == start_tokens - 3


def test_batch_query_population_1001_boundary(tmp_path):
    # the ≤1,000 discipline at the exact off-by-one boundary, at the DATASET (IO owner)
    seen: list[int] = []
    ds = _batch(tmp_path, fetcher=lambda chunk: (seen.append(len(chunk)) or []))
    ds.query_population([build_conda_purl(f"p{i}") for i in range(1001)])
    assert seen == [1000, 1]  # never a 1001-query request


def test_batch_query_population_accepts_series_without_crash(tmp_path):
    # a pandas Series of purls must NOT raise "truth value ambiguous" (AD-13 never-crash)
    import pandas as pd

    seen: list[int] = []
    ds = _batch(tmp_path, fetcher=lambda chunk: (seen.append(len(chunk)) or []))
    ds.query_population(pd.Series([build_conda_purl(f"p{i}") for i in range(3)]))
    assert seen == [3]


def test_wired_fetcher_load_marks_stale_when_unpopulated(tmp_path):
    # a wired-but-never-run store must NOT present "zero advisories, healthy" — surface stale
    ds = _batch(tmp_path, fetcher=lambda chunk: [])
    out = ds.load()
    assert out == []
    assert ds.is_stale() is True


def test_batch_offline_marks_stale_keeps_last_good(tmp_path):
    # first: a good fetch persists last-good
    good = [{"conda_name": "libtiff", "advisories": [{"id": "BAS-1", "modified": "t"}]}]
    ds_live = _batch(tmp_path, fetcher=lambda chunk: good)
    ds_live.query_population([build_conda_purl("libtiff")])
    # then: OFFLINE (no fetcher) -> keep last-good + mark stale, never crash
    ds_off = _batch(tmp_path, fetcher=None)
    resolved = ds_off.load()
    assert resolved == good  # last-good preserved (never clobbered by empty)
    assert ds_off.is_stale() is True
    marker = ds_off.staleness()
    assert marker is not None and marker.last_good_exists is True


def test_batch_fetcher_raises_marks_stale_no_propagate(tmp_path):
    def boom(chunk):
        raise RuntimeError("basilisk unreachable")

    ds = _batch(tmp_path, fetcher=boom)
    out = ds.query_population([build_conda_purl("perl")])  # must NOT raise
    assert out == []  # no last-good yet -> empty
    assert ds.is_stale() is True


def test_batch_empty_fetch_never_clobbers_last_good(tmp_path):
    good = [{"conda_name": "libtiff", "advisories": []}]
    ds = _batch(tmp_path, fetcher=lambda chunk: good)
    ds.query_population([build_conda_purl("libtiff")])
    # a later EMPTY fetch keeps last-good + marks stale (never writes empty over good)
    ds._fetcher = lambda chunk: []
    ds.query_population([build_conda_purl("libtiff")])
    assert ds.is_stale() is True
    assert ds._read_last_good() == good


def test_batch_save_is_read_only(tmp_path):
    ds = _batch(tmp_path)
    with pytest.raises((NotImplementedError, DatasetError), match="read-only"):
        ds.save([{"x": 1}])


def test_batch_url_from_basilisk_base_url(tmp_path):
    ds = _batch(tmp_path)
    desc = ds._describe()
    assert desc["url"].endswith("/v1/querybatch")
    assert "basilisk" in desc["url"]
    assert desc["querybatch_max"] == 1000


# --- BasiliskDetailDataset (bounded rate-limit discipline + AD-13) ----------

def _detail(tmp_path, **kw):
    return BasiliskDetailDataset(
        url="https://api.basilisk.prefix.dev/v1/vulns",
        filepath=str(tmp_path / "detail"),
        **kw,
    )


def test_detail_fetch_acquires_token_per_request(tmp_path):
    calls: list[str] = []
    sched = RateLimitedScheduler(
        rps=1000.0, bucket_capacity=100, clock=lambda: 0.0, sleep=lambda s: None
    )
    start = sched.tokens

    def fetcher(aid):
        calls.append(aid)
        return {"advisory_id": aid, "affected": []}

    ds = _detail(tmp_path, fetcher=fetcher, scheduler=sched)
    out = ds.fetch_details(["BAS-1", "BAS-2", "BAS-3"])
    assert calls == ["BAS-1", "BAS-2", "BAS-3"]
    assert len(out) == 3
    assert sched.tokens == start - 3  # exactly one token per request


def test_detail_honors_retry_after_then_succeeds(tmp_path):
    slept: list[float] = []
    attempts = {"n": 0}

    def flaky(aid):
        attempts["n"] += 1
        if attempts["n"] == 1:
            err = FetchError(aid, 429)
            err.retry_after = "5"  # Retry-After: 5 seconds
            raise err
        return {"advisory_id": aid, "affected": []}

    # rng_seed fixes the ±25% jitter; injected sleep records the backoff (no real wait)
    ds = _detail(tmp_path, fetcher=flaky, sleep=slept.append, rng_seed=0)
    out = ds.fetch_details(["BAS-1"])
    assert len(out) == 1  # retried and resolved
    assert len(slept) == 1  # backed off exactly once
    assert 0 < slept[0] <= 5 * 1.25  # parse_retry_after(5) with ±25% jitter


def test_detail_gives_up_after_max_retries(tmp_path):
    def always_429(aid):
        err = FetchError(aid, 429)
        err.retry_after = "1"
        raise err

    ds = _detail(tmp_path, fetcher=always_429, sleep=lambda s: None, max_retries=2, rng_seed=0)
    # exceeds retries -> the AD-13 outer guard catches it -> stale, never propagates
    out = ds.fetch_details(["BAS-1"])
    assert out == []
    assert ds.is_stale() is True


def test_detail_fetch_dedupes_advisory_ids(tmp_path):
    # one advisory can affect many conda packages -> the id list carries duplicates; the
    # bounded fetch issues ONE GET per UNIQUE id (docstring contract; saves rate-limit tokens)
    calls: list[str] = []
    ds = _detail(
        tmp_path,
        fetcher=lambda aid: (calls.append(aid) or {"advisory_id": aid, "affected": []}),
    )
    out = ds.fetch_details(["BAS-1", "BAS-2", "BAS-1", "BAS-1"])
    assert calls == ["BAS-1", "BAS-2"]  # deduped, order preserved
    assert len(out) == 2


def test_detail_offline_marks_stale(tmp_path):
    ds = _detail(tmp_path, fetcher=None)
    out = ds.load()
    assert out == []
    assert ds.is_stale() is True


def test_detail_concurrency_cap_default_single_worker(tmp_path, monkeypatch):
    monkeypatch.delenv("PHASE_K_AGGRESSIVE", raising=False)
    ds = _detail(tmp_path, fetcher=lambda aid: None)
    assert ds._describe()["concurrency"] == 1  # single-worker default (Phase K contract)


def test_detail_staleness_sidecar_is_valid_json(tmp_path):
    ds = _detail(tmp_path, fetcher=None)
    ds.load()
    marker_file = tmp_path / "detail" / ".staleness.json"
    assert marker_file.is_file()
    raw = json.loads(marker_file.read_text())
    assert raw["stale"] is True and "reason" in raw
