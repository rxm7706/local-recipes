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
        return [{"conda_name": p.rsplit("/", 1)[-1].split("@")[0], "advisories": []} for p in chunk]

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
    sched = RateLimitedScheduler(rps=1000.0, bucket_capacity=100, clock=lambda: 0.0, sleep=lambda s: None)
    start_tokens = sched.tokens
    ds = _batch(tmp_path, fetcher=lambda chunk: [], scheduler=sched)
    ds.query_population([build_conda_purl(f"p{i}") for i in range(2500)])
    # 3 chunks -> exactly 3 tokens acquired
    assert sched.tokens == start_tokens - 3


def test_batch_query_population_1001_boundary(tmp_path):
    # the ≤1,000 discipline at the exact off-by-one boundary, at the DATASET (IO owner)
    seen: list[int] = []
    ds = _batch(tmp_path, fetcher=lambda chunk: seen.append(len(chunk)) or [])
    ds.query_population([build_conda_purl(f"p{i}") for i in range(1001)])
    assert seen == [1000, 1]  # never a 1001-query request


def test_batch_query_population_accepts_series_without_crash(tmp_path):
    # a pandas Series of purls must NOT raise "truth value ambiguous" (AD-13 never-crash)
    import pandas as pd

    seen: list[int] = []
    ds = _batch(tmp_path, fetcher=lambda chunk: seen.append(len(chunk)) or [])
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


def test_batch_nonserializable_payload_keeps_last_good_no_propagate(tmp_path):
    # AD-13 never-fail: a fetcher payload carrying a non-JSON scalar (datetime/set/numpy)
    # reaches json.dumps in the last-good write. That TypeError/ValueError is a WRITE
    # failure of the store -> degrade to keep-last-good + mark stale, never propagate.
    import datetime as _dt

    good = [{"conda_name": "libtiff", "advisories": []}]
    ds = _batch(tmp_path, fetcher=lambda chunk: good)
    ds.query_population([build_conda_purl("libtiff")])  # persist a good last-good first
    # now a payload with an un-serializable datetime must NOT raise out of query_population
    ds._fetcher = lambda chunk: [{"conda_name": "libtiff", "modified": _dt.datetime(2026, 1, 1)}]
    out = ds.query_population([build_conda_purl("libtiff")])  # must NOT raise
    assert out == [{"conda_name": "libtiff", "modified": _dt.datetime(2026, 1, 1)}]
    assert ds.is_stale() is True  # write failed -> marked stale
    assert ds._read_last_good() == good  # prior good store preserved (never clobbered)


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
    sched = RateLimitedScheduler(rps=1000.0, bucket_capacity=100, clock=lambda: 0.0, sleep=lambda s: None)
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
        fetcher=lambda aid: calls.append(aid) or {"advisory_id": aid, "affected": []},
    )
    out = ds.fetch_details(["BAS-1", "BAS-2", "BAS-1", "BAS-1"])
    assert calls == ["BAS-1", "BAS-2"]  # deduped, order preserved
    assert len(out) == 2


def test_detail_offline_marks_stale(tmp_path):
    ds = _detail(tmp_path, fetcher=None)
    out = ds.load()
    assert out == []
    assert ds.is_stale() is True


def test_detail_nonserializable_payload_keeps_last_good_no_propagate(tmp_path):
    # AD-13 never-fail (detail fan-out): a detail record whose field is a `set` (routine in
    # data payloads) is non-JSON -> the last-good write raises TypeError. It must degrade to
    # keep-last-good + mark stale, never propagate out of fetch_details.
    good = [{"advisory_id": "BAS-1", "affected": []}]
    ds = _detail(tmp_path, fetcher=lambda aid: {"advisory_id": aid, "affected": []})
    ds.fetch_details(["BAS-1"])  # persist a good last-good first
    ds._fetcher = lambda aid: {"advisory_id": aid, "aliases": {"CVE-1", "CVE-2"}}
    out = ds.fetch_details(["BAS-1"])  # must NOT raise
    assert out == [{"advisory_id": "BAS-1", "aliases": {"CVE-1", "CVE-2"}}]
    assert ds.is_stale() is True
    assert ds._read_last_good() == good  # prior good store preserved


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


# --- BasiliskPackagesDataset (Story 21.4: GET /v1/packages catalog, ExternalRefreshDataset)

import pandas as pd  # noqa: E402

from pyforge.atlas.datasets.basilisk import (  # noqa: E402
    BasiliskPackagesDataset,
    parse_basilisk_packages_response,
)
from pyforge.atlas.datasets.refresh import RefreshRequest  # noqa: E402

_PKG_URL = "https://api.basilisk.prefix.dev/v1/packages"


def _page(offset: int, size: int, total: int) -> str:
    items = [
        {
            "name": f"pkg-{i}",
            "browse_ecosystem": "conda-forge",
            "latest_version": f"{i}.0",
            "version_count": 3,
            "status": "affected",
            "mapping_state": "mapped",
            "coverage_status": "no_match",
            "highest_cvss": None,
        }
        for i in range(offset, min(offset + size, total))
    ]
    return json.dumps({"total": total, "offset": offset, "limit": size, "items": items})


def _paged_fetcher(total: int, size: int, calls: list[str] | None = None):
    def fetcher(url: str) -> str:
        if calls is not None:
            calls.append(url)
        offset = int(url.rsplit("offset=", 1)[-1])
        return _page(offset, size, total)

    return fetcher


def _no_sleep_scheduler() -> RateLimitedScheduler:
    """A frozen-clock, no-sleep scheduler so multi-page walks burn no wall-clock
    (the default RateLimitedScheduler is rps=3 with a real time.sleep)."""
    return RateLimitedScheduler(rps=1000.0, bucket_capacity=100, clock=lambda: 0.0, sleep=lambda s: None)


def _pkgs(tmp_path, **kw) -> BasiliskPackagesDataset:
    kw.setdefault("scheduler", _no_sleep_scheduler())
    return BasiliskPackagesDataset(url=_PKG_URL, filepath=str(tmp_path / "packages"), **kw)


def test_parse_basilisk_packages_response_projects_catalog_columns():
    frame = parse_basilisk_packages_response(_page(0, 2, 2))
    assert frame["conda_name"].tolist() == ["pkg-0", "pkg-1"]
    assert frame["ecosystem"].tolist() == ["conda-forge", "conda-forge"]
    assert (frame["source"] == "basilisk_packages").all()
    assert frame["fetched_at"].map(lambda v: isinstance(v, int)).all()


def test_parse_basilisk_packages_response_accepts_dict_bytes_and_bare_list():
    assert len(parse_basilisk_packages_response({"items": [{"name": "a"}]})) == 1
    assert len(parse_basilisk_packages_response(b'{"items": [{"name": "a"}]}')) == 1
    assert len(parse_basilisk_packages_response([{"name": "a"}, {"name": "b"}])) == 2


def test_parse_basilisk_packages_response_malformed_never_raises():
    for bad in (None, "", "not json", {}, {"items": "nope"}, {"items": [1, {"name": ""}, {"nope": 1}]}, 42):
        frame = parse_basilisk_packages_response(bad)
        assert isinstance(frame, pd.DataFrame) and frame.empty
        assert "conda_name" in frame.columns


def test_packages_constructs_offline_no_refresher(tmp_path):
    ds = _pkgs(tmp_path)
    desc = ds._describe()
    assert desc["refresher_wired"] is False and desc["fetcher_wired"] is False
    assert desc["url"] == _PKG_URL


def test_packages_page_url_is_dataset_built():
    ds = BasiliskPackagesDataset(url=_PKG_URL + "/", filepath="x", page_size=200)
    assert ds.page_url(400) == f"{_PKG_URL}?limit=200&offset=400"


def test_packages_page_url_extends_an_existing_query_string_with_ampersand():
    ds = BasiliskPackagesDataset(url=_PKG_URL + "?ecosystem=conda-forge", filepath="x", page_size=200)
    assert ds.page_url(0) == f"{_PKG_URL}?ecosystem=conda-forge&limit=200&offset=0"


class _StubResponse:
    """A Response-like object (the shape an injected requests/httpx fetcher returns)."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.mark.parametrize(
    ("payload", "expected_rows"),
    [
        (_StubResponse({"items": [{"name": "a"}, {"name": "b"}]}), 2),
        (_StubResponse([{"name": "a"}]), 1),
        (_StubResponse(ValueError("not json")), 0),  # .json() raising -> empty, never a crash
    ],
)
def test_parse_basilisk_packages_response_accepts_response_like_objects(payload, expected_rows):
    assert len(parse_basilisk_packages_response(payload)) == expected_rows


def test_packages_fetch_success_walks_every_page_and_persists(tmp_path):
    calls: list[str] = []
    ds = _pkgs(tmp_path, fetcher=_paged_fetcher(total=450, size=200, calls=calls), page_size=200)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert ds.is_stale() is False
    out = ds.load()
    assert len(out) == 450
    assert out["conda_name"].is_unique
    # exactly 3 pages (200 + 200 + 50); the short last page stops the walk
    assert [u.rsplit("offset=", 1)[-1] for u in calls] == ["0", "200", "400"]


def test_packages_stops_at_total_when_pages_are_exact_multiples(tmp_path):
    calls: list[str] = []
    ds = _pkgs(tmp_path, fetcher=_paged_fetcher(total=400, size=200, calls=calls), page_size=200)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert len(ds.load()) == 400
    assert len(calls) == 2  # offset 400 >= total -> never requested


def test_packages_server_clamp_below_requested_page_size_still_walks_everything(tmp_path):
    """The live server clamps `limit` to 200 whatever is requested: a dataset built with
    page_size=1000 must still collect all 450 rows over 3 calls (offset advances by the
    rows actually served; "short page" is judged against the served limit)."""
    calls: list[str] = []

    def clamped(url: str) -> str:
        calls.append(url)
        offset = int(url.rsplit("offset=", 1)[-1])
        assert "limit=1000" in url  # the dataset asked for 1000...
        return _page(offset, 200, 450)  # ...the server served 200 (envelope limit=200)

    ds = _pkgs(tmp_path, fetcher=clamped, page_size=1000)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert len(ds.load()) == 450
    assert [u.rsplit("offset=", 1)[-1] for u in calls] == ["0", "200", "400"]
    assert ds.is_stale() is False


def test_packages_acquires_one_scheduler_token_per_page(tmp_path):
    sched = RateLimitedScheduler(rps=1000.0, bucket_capacity=100, clock=lambda: 0.0, sleep=lambda s: None)
    start = sched.tokens
    ds = _pkgs(tmp_path, fetcher=_paged_fetcher(total=450, size=200), page_size=200, scheduler=sched)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert sched.tokens == start - 3


def test_packages_page_cap_never_hangs_and_keeps_collected(tmp_path):
    # a server that keeps returning full pages regardless of offset, and reports no total
    def endless(url: str) -> str:
        return json.dumps({"items": [{"name": f"p-{url.rsplit('offset=', 1)[-1]}-{i}"} for i in range(5)]})

    ds = _pkgs(tmp_path, fetcher=endless, page_size=5, max_pages=4)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert len(ds.load()) == 20  # 4 pages x 5 rows, then the cap trips (no last-good -> persisted)
    # ...but a cap-terminated walk is PARTIAL and must not read as fresh
    assert ds.is_stale() is True
    assert "partial catalog walk: 20/?" in ds.staleness().reason
    assert "page cap" in ds.staleness().reason


def test_packages_first_run_no_last_good_fetch_failure_marks_stale_empty(tmp_path):
    def boom(url: str):
        raise ConnectionError("endpoint down")

    ds = _pkgs(tmp_path, fetcher=boom)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))  # never raises
    assert ds.is_stale() is True
    marker = ds.staleness()
    assert marker is not None and marker.last_good_exists is False
    out = ds.load()
    assert out.empty and "conda_name" in out.columns


def test_packages_fetch_failure_keeps_last_good_and_marks_stale(tmp_path):
    p = tmp_path / "packages"
    _pkgs(tmp_path, fetcher=_paged_fetcher(total=10, size=200)).save(
        RefreshRequest(store="discovery_basilisk_packages_raw", force=True)
    )
    assert p.is_dir()

    def boom(url: str):
        raise ConnectionError("endpoint down")

    ds = _pkgs(tmp_path, fetcher=boom)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert ds.is_stale() is True
    assert ds.staleness().last_good_exists is True
    assert len(ds.load()) == 10  # prior catalog untouched


def test_packages_mid_walk_failure_persists_pages_collected_so_far(tmp_path):
    def flaky(url: str) -> str:
        offset = int(url.rsplit("offset=", 1)[-1])
        if offset >= 200:
            raise ConnectionError("page 2 down")
        return _page(offset, 200, 450)

    ds = _pkgs(tmp_path, fetcher=flaky, page_size=200)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert len(ds.load()) == 200  # first run, no last-good: the partial is persisted (better than nothing)
    # ...but it is visibly STALE with the partial reason, never "fresh"
    assert ds.is_stale() is True
    marker = ds.staleness()
    assert marker.last_good_exists is True
    assert marker.reason.startswith("partial catalog walk: 200/450")


def test_packages_partial_walk_never_overwrites_a_fuller_last_good(tmp_path):
    """A full 450-row last-good exists; a later flaky walk fails at offset 200 -> the
    200-row partial must NOT replace it: load() still returns 450 rows, store stale."""
    _pkgs(tmp_path, fetcher=_paged_fetcher(total=450, size=200), page_size=200).save(
        RefreshRequest(store="discovery_basilisk_packages_raw", force=True)
    )
    assert len(_pkgs(tmp_path).load()) == 450

    def flaky(url: str) -> str:
        offset = int(url.rsplit("offset=", 1)[-1])
        if offset >= 200:
            raise ConnectionError("page 2 down")
        return _page(offset, 200, 450)

    ds = _pkgs(tmp_path, fetcher=flaky, page_size=200)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert len(ds.load()) == 450  # the fuller catalog survived
    assert ds.is_stale() is True
    assert ds.staleness().reason.startswith("partial catalog walk: 200/450")


def test_packages_complete_walk_after_a_partial_clears_stale(tmp_path):
    def flaky(url: str) -> str:
        offset = int(url.rsplit("offset=", 1)[-1])
        if offset >= 200:
            raise ConnectionError("page 2 down")
        return _page(offset, 200, 450)

    _pkgs(tmp_path, fetcher=flaky, page_size=200).save(
        RefreshRequest(store="discovery_basilisk_packages_raw", force=True)
    )
    ds = _pkgs(tmp_path, fetcher=_paged_fetcher(total=450, size=200), page_size=200)
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert len(ds.load()) == 450
    assert ds.is_stale() is False


def test_packages_offline_no_fetcher_marks_stale_and_keeps_last_good(tmp_path):
    _pkgs(tmp_path, fetcher=_paged_fetcher(total=10, size=200)).save(
        RefreshRequest(store="discovery_basilisk_packages_raw", force=True)
    )
    offline = _pkgs(tmp_path)
    offline.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert offline.is_stale() is True
    assert len(offline.load()) == 10


def test_packages_empty_payload_keeps_last_good(tmp_path):
    _pkgs(tmp_path, fetcher=_paged_fetcher(total=10, size=200)).save(
        RefreshRequest(store="discovery_basilisk_packages_raw", force=True)
    )
    ds = _pkgs(tmp_path, fetcher=lambda url: json.dumps({"total": 0, "items": []}))
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    assert ds.is_stale() is True
    assert len(ds.load()) == 10


def test_packages_unreadable_store_degrades_to_empty(tmp_path):
    ds = _pkgs(tmp_path, fetcher=_paged_fetcher(total=10, size=200))
    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))
    ds._store_path.write_bytes(b"not a parquet")
    out = _pkgs(tmp_path).load()
    assert out.empty and ds.is_stale() is True


def test_packages_write_rejects_frame_missing_required_columns(tmp_path):
    with pytest.raises(ValueError):
        _pkgs(tmp_path)._write(pd.DataFrame({"nonsense": [1]}))
