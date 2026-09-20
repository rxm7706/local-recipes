"""PyPIJsonRequestDataset tests (Story B2, DW-B1-2 / AC-1).

Proves the pypi_json_raw FLIP: the per-project ``/pypi/<name>/json`` parameterization
(the AC-2 boundary a node may never cross) AND the DW-B1-2 wiring — ``acquire()`` now
gates the concrete per-project fan-out, with the fake-clock coupling documented + guarded.
"""

from __future__ import annotations

import json

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


def test_fanout_dataset_fetch_candidates_reads_names_from_mapping_store(tmp_path):
    """Story 21.2: PyPIJsonFanOutDataset sources its candidate ``pypi_name``
    universe from the already-populated ``pypi_conda_map_store`` flat cache — never
    ``cf_atlas.db``. Review fix #6: the live fan-out runs via
    :meth:`fetch_candidates` (``save()``'s IO), never a bare ``load()``."""
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    mapping_path = tmp_path / "pypi_conda_map.json"
    mapping_path.write_text(json.dumps({"numpy": "numpy", "pandas": "pandas"}))
    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org", filepath=str(tmp_path / "store"), mapping_filepath=str(mapping_path)
    )
    seen_names: list[str] = []

    def fake_load_many(names, *, fetcher=None):
        seen_names.extend(names)
        return {n: {"info": {"version": "1.0.0"}} for n in names}

    ds.load_many = fake_load_many
    out = ds.fetch_candidates()
    assert seen_names == ["numpy", "pandas"]
    assert set(out["pypi_name"]) == {"numpy", "pandas"}
    assert set(out["conda_name"]) == {"numpy", "pandas"}
    assert (out["version"] == "1.0.0").all()
    # persisted -> load() (a read-only projection) sees the same rows.
    loaded = ds.load()
    assert set(loaded["pypi_name"]) == {"numpy", "pandas"}
    assert not ds.is_stale()


def test_fanout_load_is_a_read_only_projection_never_fetches(tmp_path):
    """Review fix #6: ``load()`` must never do a live network fan-out (the AD-13
    pattern every other Story 21.2 dataset follows) — only ``save()`` (via
    :meth:`fetch_candidates`) does. An absent store degrades to empty + stale."""
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org",
        filepath=str(tmp_path / "store"),
        mapping_filepath=str(tmp_path / "map.json"),
    )
    out = ds.load()
    assert out.empty
    assert "pypi_name" in out.columns and "version" in out.columns
    assert ds.is_stale()


def test_fanout_dataset_empty_mapping_store_persists_empty_and_stale(tmp_path):
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    mapping_path = tmp_path / "pypi_conda_map.json"  # never written -> absent store
    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org", filepath=str(tmp_path / "store"), mapping_filepath=str(mapping_path)
    )
    out = ds.fetch_candidates()
    assert out.empty
    assert ds.is_stale()


def test_fanout_dataset_filters_non_string_conda_name(tmp_path):
    """Review fix #12: a malformed mapping entry (non-string conda_name, or an
    empty key) must be filtered out — matches ``ParselmouthMappingDataset``'s
    filter, never surfaced downstream or crashing the fan-out."""
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    mapping_path = tmp_path / "pypi_conda_map.json"
    mapping_path.write_text(json.dumps({"numpy": "numpy", "broken": 12345, "": "empty-key"}))
    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org", filepath=str(tmp_path / "store"), mapping_filepath=str(mapping_path)
    )
    seen_names: list[str] = []
    ds.load_many = lambda names, **kw: seen_names.extend(names) or {n: {} for n in names}
    ds.fetch_candidates()
    assert seen_names == ["numpy"]  # "broken" (non-string value) / "" (falsy key) dropped


def test_fanout_limit_truncates_candidate_names(tmp_path, monkeypatch):
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    mapping_path = tmp_path / "pypi_conda_map.json"
    mapping_path.write_text(json.dumps({"a": "a", "b": "b", "c": "c"}))
    monkeypatch.setenv("PYPI_JSON_FANOUT_LIMIT", "2")
    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org", filepath=str(tmp_path / "store"), mapping_filepath=str(mapping_path)
    )
    seen_names: list[str] = []
    ds.load_many = lambda names, **kw: seen_names.extend(names) or {n: None for n in names}
    ds.fetch_candidates()
    assert seen_names == ["a", "b"]  # sorted candidate order, truncated to the limit


def test_fanout_limit_zero_disables_fetch_this_cycle(tmp_path, monkeypatch):
    """Review fix #7: ``PYPI_JSON_FANOUT_LIMIT=0`` explicitly disables the live
    fetch THIS cycle — distinct from unset/non-numeric, which use the bounded
    default. ``load_many`` must not even be invoked."""
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    mapping_path = tmp_path / "pypi_conda_map.json"
    mapping_path.write_text(json.dumps({"a": "a", "b": "b"}))
    monkeypatch.setenv("PYPI_JSON_FANOUT_LIMIT", "0")
    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org", filepath=str(tmp_path / "store"), mapping_filepath=str(mapping_path)
    )
    called = []
    ds.load_many = lambda names, **kw: called.append(names) or {}
    out = ds.fetch_candidates()
    assert not called  # load_many never even invoked
    assert out.empty
    assert ds.is_stale()
    marker = ds.staleness()
    assert "disabled" in marker.reason


def test_fanout_limit_default_is_bounded_not_unlimited(tmp_path):
    """Review finding: dropping the PYPI_JSON_LIVE_FANOUT hard gate must NOT also
    make the fan-out unbounded by default."""
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset
    from pyforge.atlas.datasets.request_datasets import _DEFAULT_PYPI_JSON_FANOUT_LIMIT

    names = {f"pkg{i}": f"pkg{i}" for i in range(_DEFAULT_PYPI_JSON_FANOUT_LIMIT + 50)}
    mapping_path = tmp_path / "pypi_conda_map.json"
    mapping_path.write_text(json.dumps(names))
    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org", filepath=str(tmp_path / "store"), mapping_filepath=str(mapping_path)
    )
    seen_names: list[str] = []
    ds.load_many = lambda ns, **kw: seen_names.extend(ns) or {n: None for n in ns}
    ds.fetch_candidates()
    assert len(seen_names) == _DEFAULT_PYPI_JSON_FANOUT_LIMIT


def test_fanout_dataset_rejects_unexpected_kwargs(tmp_path):
    """Review fix #9: consistent with ``ParselmouthMappingDataset`` — an
    unrecognized catalog key raises loudly rather than being silently sunk."""
    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    with pytest.raises(TypeError):
        PyPIJsonFanOutDataset(
            url="https://pypi.org",
            filepath=str(tmp_path / "store"),
            mapping_filepath=str(tmp_path / "map.json"),
            bogus="nope",
        )


def test_fanout_save_only_accepts_refresh_request(tmp_path):
    from kedro.io.core import DatasetError

    from pyforge.atlas.datasets import PyPIJsonFanOutDataset

    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org",
        filepath=str(tmp_path / "store"),
        mapping_filepath=str(tmp_path / "map.json"),
    )
    with pytest.raises(DatasetError, match="RefreshRequest"):
        ds.save({"a": 1})


def test_fanout_save_rejects_a_refresh_request_for_a_different_store(tmp_path):
    """Review fix #8: there is exactly one pypi_json_raw catalog entry, so any
    other store name is unambiguously a pipeline-wiring drift."""
    from kedro.io.core import DatasetError

    from pyforge.atlas.datasets import PyPIJsonFanOutDataset
    from pyforge.atlas.datasets.refresh import RefreshRequest

    ds = PyPIJsonFanOutDataset(
        url="https://pypi.org",
        filepath=str(tmp_path / "store"),
        mapping_filepath=str(tmp_path / "map.json"),
    )
    with pytest.raises(DatasetError, match="drifted out of sync"):
        ds.save(RefreshRequest(store="vcs_github_api_raw"))


def test_fanout_limit_degrades_on_non_numeric_env(monkeypatch):
    from pyforge.atlas.datasets.request_datasets import (
        _DEFAULT_PYPI_JSON_FANOUT_LIMIT,
        _pypi_json_fanout_limit,
    )

    monkeypatch.setenv("PYPI_JSON_FANOUT_LIMIT", "not-a-number")
    assert _pypi_json_fanout_limit() == _DEFAULT_PYPI_JSON_FANOUT_LIMIT


def test_fanout_limit_unset_uses_bounded_default(monkeypatch):
    from pyforge.atlas.datasets.request_datasets import (
        _DEFAULT_PYPI_JSON_FANOUT_LIMIT,
        _pypi_json_fanout_limit,
    )

    monkeypatch.delenv("PYPI_JSON_FANOUT_LIMIT", raising=False)
    assert _pypi_json_fanout_limit() == _DEFAULT_PYPI_JSON_FANOUT_LIMIT > 0
