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


def test_a_cold_live_run_fetches_every_candidate_uncapped(tmp_path, live):
    pypi = _PyPI()
    out = _ds(tmp_path).fetch_candidates(fetcher=pypi, pairs=PAIRS * 60)  # far past the old 200 cap

    assert sorted(pypi.requested) == ["numpy", "pandas", "scipy", "torch"] and len(out) == 4


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


def test_a_failed_project_stays_eligible_and_an_outage_keeps_last_good(tmp_path, live):
    pypi = _PyPI(fail={"pandas": [404]})
    ds = _ds(tmp_path)
    ds.fetch_candidates(fetcher=pypi, pairs=PAIRS[:2])
    assert set(ds.load()["pypi_name"]) == {"numpy"}
    assert ds._eligible(["numpy", "pandas"], {}, time.time()) == ["pandas"]

    down = _PyPI(fail={"pandas": [500]})
    assert ds.fetch_candidates(fetcher=down, pairs=PAIRS[1:2]).empty
    assert "every request in the batch failed" in ds.staleness().reason and set(ds.load()["pypi_name"]) == {"numpy"}


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

    assert request.pypi_serials == (("Flask_Login", 11), ("numpy", 22))
    assert refresh_pypi_json_store({}, mapping, None).pypi_serials == ()
    assert refresh_pypi_json_store({}, None, snapshot).pypi_serials == ()
