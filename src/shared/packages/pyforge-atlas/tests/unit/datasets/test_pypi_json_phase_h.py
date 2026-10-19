"""Story 34.10 (CAP-64): Phase H covers every mapped PyPI project, gated by its serial.

Network-free: every request goes to an injected fetcher or a stand-in ``APIDataset``; the
retry waits go to a recording ``retry_sleep``. Shapes as measured on 2026-10-18:
``/pypi/<name>/json`` carries ``info.version`` and a top-level ``last_serial``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests
from kedro.io import DatasetError
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import PyPIJsonFanOutDataset, RefreshRequest, public_sources
from pyforge.atlas.datasets import request_datasets as R
from pyforge.atlas.pipelines.pypi_intelligence.nodes import refresh_pypi_json_store

DAY = 86400
PAIRS = (("numpy", "numpy"), ("pandas", "pandas"), ("scipy", "scipy"), ("torch", "pytorch"))


def _ds(tmp_path: Path) -> PyPIJsonFanOutDataset:
    return PyPIJsonFanOutDataset(
        url="https://pypi.org", filepath=str(tmp_path / "store"), mapping_filepath=str(tmp_path / "absent.json")
    )


def _store(tmp_path: Path, rows: list[dict[str, Any]]) -> None:
    (tmp_path / "store").mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    for c in R._PYPI_JSON_FRAME_COLUMNS:
        if c not in frame.columns:
            frame[c] = pd.NA
    frame[R._PYPI_JSON_FRAME_COLUMNS].to_parquet(tmp_path / "store" / "store.parquet", index=False)


class _PyPI:
    def __init__(self, serials: dict[str, int] | None = None, fail: dict[str, list[int]] | None = None) -> None:
        self.serials = serials or {}
        self.fail = fail or {}  # name -> statuses to answer before succeeding
        self.requested: list[str] = []

    def __call__(self, key: str) -> dict[str, Any]:
        name = key.split("/pypi/")[1].split("/")[0]
        self.requested.append(name)
        queue = self.fail.get(name)
        if queue:
            status = queue.pop(0)
            response = requests.Response()
            response.status_code = status
            response.headers["Retry-After"] = "7"
            try:
                raise requests.HTTPError(f"{status} Error", response=response)
            except requests.HTTPError as exc:
                raise DatasetError("Failed to fetch data") from exc
        return {"info": {"version": "2.0"}, "last_serial": self.serials.get(name, 100)}


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(public_sources, "live", lambda: True)
    monkeypatch.delenv("PYPI_JSON_FANOUT_LIMIT", raising=False)


# -- the eligible set -------------------------------------------------------------------


def test_a_cold_live_run_fetches_every_candidate_uncapped_and_persists_in_chunks(tmp_path, live, monkeypatch):
    pairs = tuple((f"p{i:03d}", f"p{i:03d}") for i in range(250))  # past the old 200 cap
    monkeypatch.setattr(PyPIJsonFanOutDataset, "PERSIST_EVERY", 100)
    persisted: list[int] = []
    ds = _ds(tmp_path)
    ds.scheduler.acquire = lambda n=1: 0.0  # type: ignore[method-assign]  # no real token-bucket waits
    real = ds._persist
    ds._persist = lambda frame: persisted.append(len(frame)) or real(frame)  # type: ignore[method-assign]
    pypi = _PyPI()

    out = ds.fetch_candidates(fetcher=pypi, pairs=pairs)

    assert len(pypi.requested) == 250 and len(out) == 250 and persisted == [100, 100, 50]
    assert len(ds.load()) == 250


def test_the_eligible_set_is_never_fetched_then_serial_moved_then_the_30_day_recheck(tmp_path, live):
    now = time.time()
    _store(
        tmp_path,
        [
            {"pypi_name": "numpy", "fetched_at": now - DAY, "pypi_version_serial_at_fetch": 10},  # serial moved
            {"pypi_name": "pandas", "fetched_at": now - 31 * DAY, "pypi_version_serial_at_fetch": 20},  # old
            {"pypi_name": "scipy", "fetched_at": now - DAY, "pypi_version_serial_at_fetch": 30},  # current
            {"pypi_name": "old", "fetched_at": now - 60 * DAY, "pypi_version_serial_at_fetch": pd.NA},  # older
        ],
    )
    ds = _ds(tmp_path)

    eligible = ds._eligible(["numpy", "old", "pandas", "scipy", "torch"], {"numpy": 11, "scipy": 30}, now)

    assert eligible == ["torch", "numpy", "old", "pandas"]


def test_a_known_serial_against_a_missing_stamp_counts_as_moved(tmp_path, live):
    """Legacy's NULL-safe ``IS NOT``: a row fetched before serials were stamped is re-fetched once."""
    now = time.time()
    _store(tmp_path, [{"pypi_name": "numpy", "fetched_at": now - DAY}])

    assert _ds(tmp_path)._eligible(["numpy"], {"numpy": 5}, now) == ["numpy"]
    assert _ds(tmp_path)._eligible(["numpy"], {}, now) == []  # no serial known: only the 30-day check


def test_each_row_stamps_the_serial_it_was_fetched_at(tmp_path, live):
    pypi = _PyPI(serials={"numpy": 999, "pandas": 7})
    ds = _ds(tmp_path)

    ds.fetch_candidates(fetcher=pypi, pairs=PAIRS[:2], serials=(("numpy", 41),))

    stamped = ds.load().set_index("pypi_name")
    assert stamped.loc["numpy", "pypi_version_serial_at_fetch"] == 41  # the snapshot's, as legacy stamps Phase D's
    assert stamped.loc["pandas", "pypi_version_serial_at_fetch"] == 7  # no snapshot serial: the payload's own


def test_a_warm_run_with_no_serial_movement_fetches_only_the_30_day_rechecks(tmp_path, live):
    now = time.time()
    _store(
        tmp_path,
        [
            {"pypi_name": "numpy", "fetched_at": now - DAY, "pypi_version_serial_at_fetch": 1},
            {"pypi_name": "pandas", "fetched_at": now - 40 * DAY, "pypi_version_serial_at_fetch": 2},
        ],
    )
    pypi = _PyPI()
    ds = _ds(tmp_path)
    ds.load_many = lambda names, *, fetcher=None: R.PyPIJsonRequestDataset.load_many(ds, names, fetcher=pypi)  # type: ignore[method-assign]

    ds.save(RefreshRequest(store="pypi_json_raw", pypi_pairs=PAIRS[:2], pypi_serials=(("numpy", 1), ("pandas", 2))))

    assert pypi.requested == ["pandas"]
    loaded = ds.load().set_index("pypi_name")
    assert loaded.loc["numpy", "fetched_at"] == pytest.approx(now - DAY)  # untouched
    assert loaded.loc["pandas", "fetched_at"] > now - 60


def test_nothing_eligible_is_a_clean_run(tmp_path, live):
    now = time.time()
    _store(tmp_path, [{"pypi_name": "numpy", "fetched_at": now, "pypi_version_serial_at_fetch": 1}])
    ds = _ds(tmp_path)
    ds._mark_stale("an older marker")
    pypi = _PyPI()

    out = ds.fetch_candidates(fetcher=pypi, pairs=PAIRS[:1], serials=(("numpy", 1),))

    assert out.empty and pypi.requested == [] and ds.staleness() is None


def test_live_the_store_cadence_never_holds_back_a_moved_serial(tmp_path, live):
    _store(tmp_path, [{"pypi_name": "numpy", "fetched_at": time.time(), "pypi_version_serial_at_fetch": 1}])
    ds = _ds(tmp_path)
    seen: list[list[str]] = []
    ds.load_many = lambda names, *, fetcher=None: (
        seen.append(list(names)) or {n: {"info": {"version": "2"}} for n in names}
    )  # type: ignore[method-assign]

    ds.save(RefreshRequest(store="pypi_json_raw", pypi_pairs=PAIRS[:1], pypi_serials=(("numpy", 2),)))

    assert seen == [["numpy"]]  # a fresh store, yet the moved serial is fetched


def test_an_explicit_limit_caps_the_eligible_set_never_fetched_first(tmp_path, live, monkeypatch):
    now = time.time()
    _store(tmp_path, [{"pypi_name": "numpy", "fetched_at": now - 40 * DAY, "pypi_version_serial_at_fetch": 1}])
    monkeypatch.setenv("PYPI_JSON_FANOUT_LIMIT", "2")
    pypi = _PyPI()

    _ds(tmp_path).fetch_candidates(fetcher=pypi, pairs=PAIRS)

    assert pypi.requested == ["pandas", "scipy"]


def test_an_explicit_zero_skips_the_cycle_under_a_marker(tmp_path, live, monkeypatch):
    monkeypatch.setenv("PYPI_JSON_FANOUT_LIMIT", "0")
    pypi = _PyPI()
    ds = _ds(tmp_path)

    assert ds.fetch_candidates(fetcher=pypi, pairs=PAIRS).empty and pypi.requested == []
    assert "disabled this cycle" in ds.staleness().reason


def test_a_404_is_a_recorded_miss_and_other_failures_stay_eligible(tmp_path, live):
    pypi = _PyPI(fail={"pandas": [404], "scipy": [500]})
    ds = _ds(tmp_path)
    ds.fetch_candidates(fetcher=pypi, pairs=PAIRS[:3], serials=(("pandas", 7),))
    now = time.time()

    assert set(ds.load()["pypi_name"]) == {"numpy"}
    assert ds._read_misses()["pandas"]["serial"] == 7
    assert ds._eligible(["numpy", "pandas", "scipy"], {"pandas": 7}, now) == ["scipy"]
    # a miss comes back, last, once its serial moves or 30 days pass
    assert ds._eligible(["numpy", "pandas", "scipy"], {"pandas": 8}, now) == ["scipy", "pandas"]
    assert ds._eligible(["pandas"], {"pandas": 7}, now + 31 * DAY) == ["pandas"]


def test_a_run_of_only_known_misses_is_not_an_outage(tmp_path, live):
    ds = _ds(tmp_path)
    ds.fetch_candidates(fetcher=_PyPI(fail={"pandas": [404]}), pairs=PAIRS[1:2])
    ds._mark_stale("an older marker")

    out = ds.fetch_candidates(fetcher=_PyPI(fail={"pandas": [404]}), pairs=PAIRS[1:2], serials=(("pandas", 9),))

    assert out.empty and ds.staleness() is None


def test_an_outage_keeps_last_good_under_the_marker(tmp_path, live):
    ds = _ds(tmp_path)
    ds.fetch_candidates(fetcher=_PyPI(), pairs=PAIRS[:1])

    assert ds.fetch_candidates(fetcher=_PyPI(fail={"pandas": [500]}), pairs=PAIRS[1:2]).empty
    assert "every request in the batch failed" in ds.staleness().reason and set(ds.load()["pypi_name"]) == {"numpy"}


def test_a_cap_never_spends_itself_on_known_misses(tmp_path, live, monkeypatch):
    ds = _ds(tmp_path)
    ds.fetch_candidates(fetcher=_PyPI(fail={"pandas": [404], "scipy": [404]}), pairs=PAIRS[:3], serials=(("numpy", 1),))
    monkeypatch.setenv("PYPI_JSON_FANOUT_LIMIT", "2")
    pypi = _PyPI()

    ds.fetch_candidates(fetcher=pypi, pairs=PAIRS[:3], serials=(("numpy", 2),))

    assert pypi.requested == ["numpy"]  # the moved serial, not the two misses


def test_an_empty_candidate_universe_is_stale_not_clean(tmp_path, live):
    ds = _ds(tmp_path)

    assert ds.fetch_candidates(fetcher=_PyPI(), pairs=()).empty
    assert "the mapping names no PyPI project" in ds.staleness().reason


def test_the_store_keeps_one_row_per_pypi_project_even_when_two_map_to_one_conda_package(tmp_path, live):
    pypi = _PyPI()
    ds = _ds(tmp_path)

    ds.fetch_candidates(fetcher=pypi, pairs=(("torch", "pytorch"), ("pytorch", "pytorch")))
    ds.fetch_candidates(fetcher=_PyPI(), pairs=(("torch", "pytorch"),), serials=(("torch", 101),))

    assert sorted(ds.load()["pypi_name"]) == ["pytorch", "torch"]


# -- 429 / 503 --------------------------------------------------------------------------


@pytest.mark.parametrize("status", [429, 503])
def test_a_throttled_request_is_retried_after_retry_after(tmp_path, live, status):
    pypi = _PyPI(fail={"numpy": [status, status]})
    ds = _ds(tmp_path)
    waits: list[float] = []
    ds.retry_sleep = waits.append  # type: ignore[assignment]

    out = ds.load_many(["numpy"], fetcher=pypi)

    assert "numpy" in out and pypi.requested == ["numpy"] * 3 and waits == [7.0, 7.0]


def test_a_throttle_that_outlasts_the_attempts_is_a_miss(tmp_path, live):
    pypi = _PyPI(fail={"numpy": [429, 429, 429]})
    ds = _ds(tmp_path)
    waits: list[float] = []
    ds.retry_sleep = waits.append  # type: ignore[assignment]

    assert ds.load_many(["numpy"], fetcher=pypi) == {}
    assert ds.last_failures["numpy"].startswith("HTTP 429") and len(waits) == 2


def test_with_no_retry_after_the_wait_backs_off(tmp_path, live):
    ds = _ds(tmp_path)
    waits: list[float] = []
    ds.retry_sleep = waits.append  # type: ignore[assignment]
    calls = {"n": 0}

    def throttled(key: str) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] < 3:
            response = requests.Response()
            response.status_code = 503
            try:
                raise requests.HTTPError("503", response=response)
            except requests.HTTPError as exc:
                raise DatasetError("Failed to fetch data") from exc
        return {"info": {"version": "1"}}

    assert "numpy" in ds.load_many(["numpy"], fetcher=throttled) and waits == [1.0, 2.0]


def test_a_404_is_never_retried(tmp_path, live):
    pypi = _PyPI(fail={"ghost": [404]})
    ds = _ds(tmp_path)
    ds.retry_sleep = lambda s: pytest.fail("a 404 is not retried")  # type: ignore[assignment]

    ds.load_many(["ghost"], fetcher=pypi)

    assert pypi.requested == ["ghost"] and ds.last_failures["ghost"].startswith("HTTP 404")


def test_the_live_get_sends_a_timeout_and_no_credential(tmp_path, monkeypatch):
    captured: list[dict[str, Any]] = []

    class _Api:
        def __init__(self, *, url: str, load_args: dict[str, Any], **_kw: Any):
            captured.append({"url": url, **load_args})

        def load(self) -> Any:
            return {"info": {"version": "1"}}

    ds = _ds(tmp_path)  # built first: the base composes its own APIDataset at construction
    monkeypatch.setattr(R, "APIDataset", _Api)
    ds.scheduler.acquire = lambda n=1: 0.0  # type: ignore[method-assign]

    ds.load_many(["numpy", "scipy"])

    assert [c["url"] for c in captured] == ["https://pypi.org/pypi/numpy/json", "https://pypi.org/pypi/scipy/json"]
    for c in captured:
        assert c["timeout"] == 30 and callable(c["auth"]) and c["auth"]("r") == "r"
    assert captured[0] is not captured[1]


# -- the flag -----------------------------------------------------------------------------


@flag_states("pyforge.atlas.live_public_sources")  # spelled out: the flag gate reads this file for the key
def test_the_flag_chooses_the_eligible_set_or_the_bounded_rotation(tmp_path, flag_provider, monkeypatch):
    flag_on = flag_provider[public_sources.FLAG_KEY]
    monkeypatch.setattr(public_sources, "live", lambda: flag_on)
    monkeypatch.delenv("PYPI_JSON_FANOUT_LIMIT", raising=False)
    monkeypatch.setattr(R, "_DEFAULT_PYPI_JSON_FANOUT_LIMIT", 2)  # the bounded rotation, scaled down
    pypi = _PyPI()
    ds = _ds(tmp_path)

    ds.fetch_candidates(fetcher=pypi, pairs=PAIRS)

    if flag_on:
        assert sorted(pypi.requested) == ["numpy", "pandas", "scipy", "torch"]
        assert not (tmp_path / "store" / ".fanout_offset").exists()
    else:
        assert pypi.requested == ["numpy", "pandas"]  # today's 200-name rotation, at 2
        assert (tmp_path / "store" / ".fanout_offset").read_text() == "2"


# -- the trigger --------------------------------------------------------------------------


def test_the_trigger_carries_each_candidates_serial_matched_under_pep_503():
    mapping = pd.DataFrame(
        {"pypi_name": ["Flask_Login", "numpy", "absent"], "conda_name": ["flask-login", "numpy", "x"]}
    )
    snapshot = pd.DataFrame(
        {"pypi_name": ["flask-login", "NumPy", "unrelated"], "last_serial": [11, "22", 33], "serial_delta": [None] * 3}
    )

    request = refresh_pypi_json_store({}, mapping, snapshot)

    assert request.pypi_serials == (("flask-login", 11), ("numpy", 22))  # keyed by PEP 503, as the fan-out
    assert refresh_pypi_json_store({}, mapping, None).pypi_serials == ()
    assert refresh_pypi_json_store({}, None, snapshot).pypi_serials == ()


# -- review round 1: the boundaries and branches the first tests left open --------------------


def test_the_30_day_recheck_is_strictly_older_and_oldest_first(tmp_path, live):
    now = 1_800_000_000.0
    _store(
        tmp_path,
        [
            {"pypi_name": "edge", "fetched_at": now - 30 * DAY, "pypi_version_serial_at_fetch": 1},
            {"pypi_name": "newer", "fetched_at": now - 30 * DAY - 10, "pypi_version_serial_at_fetch": 1},
            {"pypi_name": "older", "fetched_at": now - 45 * DAY, "pypi_version_serial_at_fetch": 1},
            {"pypi_name": "unstamped", "fetched_at": pd.NA, "pypi_version_serial_at_fetch": 1},
        ],
    )

    # exactly 30 days is not yet due (legacy: fetched_at < now - 30d); a missing stamp is due
    assert _ds(tmp_path)._eligible(["newer", "edge", "older", "unstamped"], {}, now) == ["unstamped", "older", "newer"]


def test_retry_after_is_capped_at_60_seconds(tmp_path, live):
    pypi = _PyPI(fail={"numpy": [429]})
    original = pypi.__call__

    def long_wait(key: str) -> dict[str, Any]:
        try:
            return original(key)
        except DatasetError as exc:
            exc.__cause__.response.headers["Retry-After"] = "999"  # type: ignore[union-attr]
            raise

    ds = _ds(tmp_path)
    waits: list[float] = []
    ds.retry_sleep = waits.append  # type: ignore[assignment]

    ds.load_many(["numpy"], fetcher=long_wait)

    assert waits == [60.0]


def test_a_failure_with_no_http_status_is_never_retried(tmp_path, live):
    calls = {"n": 0}

    def unreachable(key: str) -> dict[str, Any]:
        calls["n"] += 1
        try:
            raise requests.ConnectionError("dns")
        except requests.ConnectionError as exc:
            raise DatasetError("Failed to connect to the remote server") from exc

    ds = _ds(tmp_path)
    ds.retry_sleep = lambda s: pytest.fail("not retried")  # type: ignore[assignment]

    assert ds.load_many(["numpy"], fetcher=unreachable) == {} and calls["n"] == 1


def test_a_credentialed_config_gets_no_public_args(tmp_path, monkeypatch):
    captured: list[dict[str, Any]] = []

    class _Api:
        def __init__(self, *, url: str, load_args: dict[str, Any], credentials: Any = None, **_kw: Any):
            captured.append({"load_args": load_args, "credentials": credentials})

        def load(self) -> Any:
            return {"info": {"version": "1"}}

    ds = PyPIJsonFanOutDataset(
        url="https://pypi.example.invalid",
        filepath=str(tmp_path / "store"),
        mapping_filepath=str(tmp_path / "absent.json"),
        credentials=("user", "token"),
    )
    monkeypatch.setattr(R, "APIDataset", _Api)
    ds.scheduler.acquire = lambda n=1: 0.0  # type: ignore[method-assign]

    ds.load_many(["numpy"])

    assert "auth" not in captured[0]["load_args"] and captured[0]["credentials"] == ("user", "token")


def test_the_live_store_writes_the_serials_and_the_request_carries_them():
    request = RefreshRequest(store="pypi_json_raw", pypi_serials=(("numpy", 3),))
    assert request.to_dict()["pypi_serials"] == [("numpy", 3)]


def test_a_stored_row_carries_its_current_serial(tmp_path, live):
    ds = _ds(tmp_path)
    ds.fetch_candidates(fetcher=_PyPI(serials={"numpy": 55}), pairs=PAIRS[:1])

    assert ds.load().set_index("pypi_name").loc["numpy", "pypi_last_serial"] == 55


@pytest.mark.parametrize(("raw", "cap"), [("abc", None), ("-5", None), ("3", 3), ("0", 0)])
def test_an_unusable_limit_leaves_the_live_run_uncapped(monkeypatch, raw, cap):
    monkeypatch.setenv("PYPI_JSON_FANOUT_LIMIT", raw)
    assert R._pypi_json_fanout_cap() == cap


def test_the_trigger_skips_a_snapshot_row_with_no_serial():
    mapping = pd.DataFrame({"pypi_name": ["numpy", "scipy"], "conda_name": ["numpy", "scipy"]})
    snapshot = pd.DataFrame({"pypi_name": ["numpy", "scipy"], "last_serial": [pd.NA, 4]})

    assert refresh_pypi_json_store({}, mapping, snapshot).pypi_serials == (("scipy", 4),)


def test_the_catalog_runs_the_fan_out_at_10_requests_a_second():
    import yaml

    catalog = yaml.safe_load((Path(R.__file__).parents[4] / "conf" / "base" / "catalog.yml").read_text())
    assert catalog["pypi_json_raw"]["rps"] == 10


# -- review round 2 ---------------------------------------------------------------------------


def test_the_default_chunk_is_legacys_commit_interval():
    assert PyPIJsonFanOutDataset.PERSIST_EVERY == 500


def test_two_spellings_of_one_project_are_one_candidate_and_one_row(tmp_path, live):
    pypi = _PyPI()
    ds = _ds(tmp_path)

    ds.fetch_candidates(fetcher=pypi, pairs=(("dagster_aws", "dagster-aws"), ("dagster-aws", "dagster-aws")))

    assert pypi.requested == ["dagster-aws"] and list(ds.load()["pypi_name"]) == ["dagster-aws"]


def test_a_project_stored_then_gone_waits_like_any_miss(tmp_path, live):
    now = time.time()
    _store(tmp_path, [{"pypi_name": "numpy", "fetched_at": now - 40 * DAY, "pypi_version_serial_at_fetch": 1}])
    ds = _ds(tmp_path)

    ds.fetch_candidates(fetcher=_PyPI(fail={"numpy": [404]}), pairs=PAIRS[:1], serials=(("numpy", 1),))

    assert ds._eligible(["numpy"], {"numpy": 1}, time.time()) == []  # not a 30-day re-check every run
    assert ds._eligible(["numpy"], {"numpy": 2}, time.time()) == ["numpy"]


def test_a_later_success_clears_the_miss(tmp_path, live):
    ds = _ds(tmp_path)
    ds.fetch_candidates(fetcher=_PyPI(fail={"pandas": [404]}), pairs=PAIRS[1:2], serials=(("pandas", 1),))
    assert "pandas" in ds._read_misses()

    ds.fetch_candidates(fetcher=_PyPI(), pairs=PAIRS[1:2], serials=(("pandas", 2),))

    assert "pandas" not in ds._read_misses() and list(ds.load()["pypi_name"]) == ["pandas"]


def test_a_malformed_miss_is_simply_due(tmp_path, live):
    ds = _ds(tmp_path)
    ds._write_misses({"pandas": {"fetched_at": "soon", "serial": None}})

    assert ds._eligible(["pandas"], {}, time.time()) == ["pandas"]


def test_the_node_keeps_the_universe_serial_under_pep_503_never_below_the_stamp():
    from pyforge.atlas.pipelines.pypi_intelligence.nodes import fetch_pypi_current_versions

    store = pd.DataFrame(
        {
            "pypi_name": ["dagster-aws", "numpy", "scipy"],
            "version": ["1", "2", "3"],
            "pypi_last_serial": [10, 20, 30],
            "pypi_version_serial_at_fetch": [10, 20, 30],
            "fetched_at": [1, 1, 1],
        }
    )
    universe = pd.DataFrame({"pypi_name": ["Dagster_AWS", "numpy", "unrelated"], "last_serial": [15, 18, 1]})

    out = fetch_pypi_current_versions(store, universe).set_index("pypi_name")

    assert out.loc["dagster-aws", "pypi_last_serial"] == 15  # the universe's, matched under PEP 503
    assert out.loc["numpy", "pypi_last_serial"] == 20  # a lagging universe never lowers the stamp
    assert out.loc["scipy", "pypi_last_serial"] == 30  # no universe row: its own


def test_the_stats_30_day_boundary_is_strict():
    from pyforge.atlas.pipelines.pypi_intelligence.nodes import (
        _PHASE_H_SAFETY_RECHECK_SECONDS,
        phase_h_eligibility_stats,
    )

    now = 1_800_000_000
    frame = pd.DataFrame(
        {
            "pypi_name": ["edge", "older"],
            "pypi_last_serial": [1, 1],
            "pypi_version_serial_at_fetch": [1, 1],
            "fetched_at": [now - _PHASE_H_SAFETY_RECHECK_SECONDS, now - _PHASE_H_SAFETY_RECHECK_SECONDS - 1],
        }
    )
    assert phase_h_eligibility_stats(frame, now=now)["eligible_safety_recheck"] == 1
