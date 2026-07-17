"""PyPIJsonRequestDataset tests (Story B2, DW-B1-2 / AC-1).

Proves the pypi_json_raw FLIP: the per-project ``/pypi/<name>/json`` parameterization
(the AC-2 boundary a node may never cross) AND the DW-B1-2 wiring — ``acquire()`` now
gates the concrete per-project fan-out, with the fake-clock coupling documented + guarded.
"""

from __future__ import annotations

import pytest

from pyforge.atlas.datasets import PyPIJsonRequestDataset, RateLimitedScheduler


class _AdvancingClock:
    """A fake clock whose ``sleep`` ADVANCES ``now`` — the safe fixture form (a frozen
    clock + no-op sleep would make acquire() infinite-spin; DW-B1-2 coupling note)."""

    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, secs: float) -> None:
        self.t += secs


def test_request_path_is_per_project():
    ds = PyPIJsonRequestDataset(url="https://pypi.org")
    assert ds.request_path("numpy") == "https://pypi.org/pypi/numpy/json"
    assert ds.request_path("/pandas/") == "https://pypi.org/pypi/pandas/json"


def test_constructs_offline_and_owns_scheduler():
    ds = PyPIJsonRequestDataset(url="https://pypi.org", metadata={"layer": "raw"})
    assert isinstance(ds.scheduler, RateLimitedScheduler)
    assert ds._describe()["parameterization"] == "PyPIJsonRequestDataset"


def test_load_many_acquires_a_token_per_project_request():
    # DW-B1-2: the scheduler now GATES the live fetch path. Small bucket + advancing
    # clock so throttling is observable and acquire() never spins.
    clk = _AdvancingClock()
    sched = RateLimitedScheduler(rps=3.0, bucket_capacity=2, clock=clk.now, sleep=clk.sleep)
    ds = PyPIJsonRequestDataset(url="https://pypi.org", scheduler=sched)

    fetched = []
    result = ds.load_many(["a", "b", "c"], fetcher=lambda key: fetched.append(key) or {"url": key})

    # 3 requests issued, each through the scheduler (bucket started at 2 -> 3rd waits)
    assert list(result.keys()) == ["a", "b", "c"]
    assert fetched == [
        "https://pypi.org/pypi/a/json",
        "https://pypi.org/pypi/b/json",
        "https://pypi.org/pypi/c/json",
    ]
    assert clk.t > 0.0  # the 3rd acquire had to wait for a refill -> time advanced


def test_bucket_ge_n_never_spins_even_with_frozen_clock():
    # DW-B1-2 coupling guard: bucket_capacity >= n means no acquire ever needs to wait,
    # so a frozen clock (no advance) is safe. This asserts the documented escape hatch.
    frozen = RateLimitedScheduler(rps=3.0, bucket_capacity=5, clock=lambda: 0.0, sleep=lambda s: None)
    ds = PyPIJsonRequestDataset(url="https://pypi.org", scheduler=frozen)
    result = ds.load_many(["a", "b", "c"], fetcher=lambda key: key)  # would spin if bucket < 3
    assert len(result) == 3


def test_fetch_one_acquires_before_delegating():
    clk = _AdvancingClock()
    sched = RateLimitedScheduler(rps=3.0, bucket_capacity=1, clock=clk.now, sleep=clk.sleep)
    ds = PyPIJsonRequestDataset(url="https://pypi.org", scheduler=sched)
    ds.fetch_one("k1", fetcher=lambda k: k)  # free (bucket=1)
    ds.fetch_one("k2", fetcher=lambda k: k)  # throttled -> advances clock
    assert clk.t > 0.0


def test_save_is_read_only():
    from kedro.io.core import DatasetError

    ds = PyPIJsonRequestDataset(url="https://pypi.org")
    with pytest.raises(DatasetError, match="read-only"):
        ds.save({"a": 1})


def test_single_load_directs_to_load_many():
    # B2 review-hardening (F-B): the per-project fan-out is NOT a single-URL load — a
    # bare load() must raise (directing to load_many) rather than silently fetch the
    # invalid bare base URL.
    from kedro.io.core import DatasetError

    ds = PyPIJsonRequestDataset(url="https://pypi.org")
    with pytest.raises(DatasetError, match="load_many"):
        ds.load()


def test_load_many_skips_missing_names():
    frozen = RateLimitedScheduler(rps=3.0, bucket_capacity=5, clock=lambda: 0.0, sleep=lambda s: None)
    ds = PyPIJsonRequestDataset(url="https://pypi.org", scheduler=frozen)
    result = ds.load_many(["a", None, float("nan"), "b"], fetcher=lambda k: k)
    assert set(result.keys()) == {"a", "b"}  # None / NaN skipped, no crash
