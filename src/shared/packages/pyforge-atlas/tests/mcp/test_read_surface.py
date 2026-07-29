"""AC-2 — the dataset-read surface is a REAL ``catalog.load`` passthrough.

Offline (AD-11): the session is faked, but the catalog is a genuine
``kedro.io.DataCatalog`` seeded with a ``MemoryDataset``, so the exercise
runs the real ``catalog.load`` path end-to-end.
"""

from __future__ import annotations

import contextlib

import pytest
from kedro.io import DataCatalog, MemoryDataset

from pyforge.atlas.mcp import session as _session_mod
from pyforge.atlas.mcp import tools

SENTINEL = {"rows": [{"package": "demo", "health": "green"}]}


class FakeContext:
    def __init__(self, catalog):
        self.catalog = catalog


class FakeSession:
    def __init__(self, catalog):
        self._context = FakeContext(catalog)

    def load_context(self):
        return self._context


@pytest.fixture()
def real_catalog_session(monkeypatch):
    # copy_mode="assign": MemoryDataset deep-copies dicts by default; the
    # passthrough proof wants the EXACT object identity back.
    catalog = DataCatalog(
        datasets={"demo_ds": MemoryDataset(SENTINEL, copy_mode="assign")}
    )
    fake = FakeSession(catalog)

    @contextlib.contextmanager
    def fake_bootstrapped_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_bootstrapped_session)
    return catalog


def test_read_dataset_is_a_catalog_load_passthrough(real_catalog_session):
    envelope = tools.read_dataset("demo_ds")
    loaded = envelope["value"]
    # identity: the exact sentinel object came back untouched — no transform
    assert loaded is SENTINEL
    assert loaded == {"rows": [{"package": "demo", "health": "green"}]}


def test_read_dataset_envelope_carries_schema_version_and_dataset_name(real_catalog_session):
    envelope = tools.read_dataset("demo_ds")
    assert envelope["schema_version"] == "1"
    assert envelope["dataset"] == "demo_ds"


def test_read_dataset_unknown_kind_reports_unavailable_with_reason(real_catalog_session):
    """A ``MemoryDataset`` (or any type outside the three known kinds) has no
    genuine provenance — ``unavailable`` + a non-empty reason is a REQUIRED,
    valid, non-error response (C4), never a fabricated value."""
    envelope = tools.read_dataset("demo_ds")
    assert envelope["provenance_kind"] == "unavailable"
    assert envelope["build_stamp"] is None
    assert envelope["build_stamp_newest"] is None
    assert isinstance(envelope["reason"], str) and envelope["reason"]


def test_read_dataset_unknown_name_raises_catalog_error(real_catalog_session):
    # a pure passthrough raises whatever catalog.load raises (AD-7: the
    # surface adds nothing — not even its own not-found translation)
    with pytest.raises(Exception, match="no_such_ds"):
        tools.read_dataset("no_such_ds")


def test_list_datasets_lists_the_catalog_keys(real_catalog_session):
    assert tools.list_datasets() == ["demo_ds"]


def test_read_dataset_coerces_a_dataframe_to_json_serializable(monkeypatch):
    """Gemini PR-76 (HIGH): a Parquet-backed dataset loads as a pandas
    DataFrame, which FastMCP cannot serialize — read_dataset must coerce it
    to a JSON-native shape (list[row-dict]) WITHOUT importing pandas in the
    tool body (AD-7). Proven end-to-end: real catalog.load of a real
    DataFrame, then json.dumps of the tool's return."""
    import json

    import contextlib

    import pandas as pd
    from kedro.io import DataCatalog, MemoryDataset

    df = pd.DataFrame({"package": ["numpy", "pandas"], "downloads": [10, 20]})
    catalog = DataCatalog(datasets={"df_ds": MemoryDataset(df, copy_mode="assign")})
    fake = FakeSession(catalog)

    @contextlib.contextmanager
    def fake_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_session)

    envelope = tools.read_dataset("df_ds")
    # coerced to list[row-dict], not a raw DataFrame
    assert envelope["value"] == [
        {"package": "numpy", "downloads": 10},
        {"package": "pandas", "downloads": 20},
    ]
    # the whole point: the whole envelope survives the MCP JSON boundary
    json.dumps(envelope)


def test_read_dataset_coerces_series_ndarray_set(monkeypatch):
    """The other non-JSON-native shapes coerce too (Series/ndarray/set)."""
    import json
    import contextlib

    import numpy as np
    import pandas as pd
    from kedro.io import DataCatalog, MemoryDataset

    catalog = DataCatalog(
        datasets={
            "series_ds": MemoryDataset(pd.Series([1, 2], index=["a", "b"]), copy_mode="assign"),
            "arr_ds": MemoryDataset(np.array([1, 2, 3]), copy_mode="assign"),
            "set_ds": MemoryDataset({"x", "y"}, copy_mode="assign"),
        }
    )
    fake = FakeSession(catalog)

    @contextlib.contextmanager
    def fake_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_session)

    assert tools.read_dataset("series_ds")["value"] == {"a": 1, "b": 2}
    assert tools.read_dataset("arr_ds")["value"] == [1, 2, 3]
    assert sorted(tools.read_dataset("set_ds")["value"]) == ["x", "y"]
    for ds in ("series_ds", "arr_ds", "set_ds"):
        json.dumps(tools.read_dataset(ds))


# --------------------------------------------------------------------------- #
# AD-17 (Story I4) — genuine build provenance, per dataset KIND
# --------------------------------------------------------------------------- #


def test_read_dataset_api_dataset_reports_live_fetch(monkeypatch):
    """``api.APIDataset`` -> ``live-fetch``: the read genuinely IS the fetch, so
    ``build_stamp`` is the current call time — the ONE kind where "now" is
    correct provenance, not a fabricated stand-in."""
    import contextlib
    import datetime

    from kedro.io import DataCatalog
    from kedro_datasets.api import APIDataset

    ds = APIDataset(url="http://example.invalid/x")
    # Never touch the network: stub the dataset's own load, the same object
    # DataCatalog.load() calls into (catalog[name] is dataset, by identity).
    monkeypatch.setattr(ds, "load", lambda: {"ok": True})
    catalog = DataCatalog(datasets={"api_ds": ds})
    fake = FakeSession(catalog)

    @contextlib.contextmanager
    def fake_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_session)

    before = datetime.datetime.now(tz=datetime.UTC)
    envelope = tools.read_dataset("api_ds")
    after = datetime.datetime.now(tz=datetime.UTC)

    assert envelope["provenance_kind"] == "live-fetch"
    assert envelope["build_stamp_newest"] is None
    assert envelope["reason"] is None
    stamp = datetime.datetime.fromisoformat(envelope["build_stamp"])
    assert before <= stamp <= after
    assert envelope["value"] == {"ok": True}


def test_read_dataset_incremental_parquet_reports_fetched_at_not_read_time(
    tmp_path, monkeypatch
):
    """``IncrementalParquetDataset`` -> ``row-fetched-at``: ``build_stamp`` is the
    OLDEST recorded ``fetched_at``, ``build_stamp_newest`` the newest — the
    dataset's OWN recorded time, proven by a deliberately-old fixture value, not
    merely "a stamp is present" (equality, not presence)."""
    import contextlib
    import datetime

    import pandas as pd
    from kedro.io import DataCatalog
    from pyforge.atlas.datasets import IncrementalParquetDataset

    path = tmp_path / "core_downloads" / "core_downloads.parquet"
    ds = IncrementalParquetDataset(filepath=str(path))
    # 111 / 222 are deliberately ancient epoch-seconds stamps (1970), far from
    # "now" — save() preserves a caller-supplied, already-numeric fetched_at
    # column verbatim (no fill, no ms-fix needed).
    ds.save(pd.DataFrame({"conda_name": ["a", "b"], "fetched_at": [222, 111]}))
    catalog = DataCatalog(datasets={"incr_ds": ds})
    fake = FakeSession(catalog)

    @contextlib.contextmanager
    def fake_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_session)

    envelope = tools.read_dataset("incr_ds")
    assert envelope["provenance_kind"] == "row-fetched-at"
    assert envelope["build_stamp"] == datetime.datetime.fromtimestamp(
        111, tz=datetime.UTC
    ).isoformat()
    assert envelope["build_stamp_newest"] == datetime.datetime.fromtimestamp(
        222, tz=datetime.UTC
    ).isoformat()


def test_read_dataset_incremental_parquet_normalizes_millisecond_fetched_at(
    tmp_path, monkeypatch
):
    """Review pass 1 regression: a ``fetched_at`` column that reached the
    Parquet file at MILLISECOND magnitude (bypassing ``save()``'s own ms-guard —
    e.g. a future writer, or a frame constructed directly) must NOT crash
    ``read_dataset``; it must normalize to seconds like
    ``IncrementalParquetDataset`` itself already does (DW-A3-P10)."""
    import contextlib
    import datetime

    import pandas as pd
    from kedro.io import DataCatalog
    from pyforge.atlas.datasets import IncrementalParquetDataset

    # Write the Parquet DIRECTLY (bypassing IncrementalParquetDataset.save(),
    # which would normalize ms values at write time) so the persisted file
    # genuinely holds a raw ms-magnitude fetched_at, exactly as `.load()` (a
    # thin `self._inner.load()` passthrough) would hand it back unmodified.
    ms_value = 1_700_000_000_000  # ms-magnitude (>= 1e12)
    path = tmp_path / "ms_ds" / "ms_ds.parquet"
    path.parent.mkdir(parents=True)
    pd.DataFrame({"conda_name": ["a"], "fetched_at": [ms_value]}).to_parquet(path)

    ds = IncrementalParquetDataset(filepath=str(path))
    catalog = DataCatalog(datasets={"ms_ds": ds})
    fake = FakeSession(catalog)

    @contextlib.contextmanager
    def fake_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_session)

    envelope = tools.read_dataset("ms_ds")  # must NOT raise ValueError
    assert envelope["provenance_kind"] == "row-fetched-at"
    expected = datetime.datetime.fromtimestamp(ms_value / 1000, tz=datetime.UTC).isoformat()
    assert envelope["build_stamp"] == expected
    assert envelope["build_stamp_newest"] == expected


def test_read_dataset_pandas_parquet_reports_file_mtime_not_read_time(
    tmp_path, monkeypatch
):
    """``pandas.ParquetDataset`` -> ``file-mtime``: ``build_stamp`` is the
    materialized file's own mtime, proven via ``os.utime`` to a deliberately-old
    value — equality against that value, not merely "a stamp is present"."""
    import contextlib
    import datetime
    import os

    import pandas as pd
    from kedro.io import DataCatalog
    from kedro_datasets.pandas import ParquetDataset

    path = tmp_path / "core_feedstock_health" / "core_feedstock_health.parquet"
    path.parent.mkdir(parents=True)
    pd.DataFrame({"feedstock_name": ["a"]}).to_parquet(path)
    old_ts = 1_600_000_000  # 2020-09-13, deliberately far from "now"
    os.utime(path, (old_ts, old_ts))

    ds = ParquetDataset(filepath=str(path))
    catalog = DataCatalog(datasets={"pq_ds": ds})
    fake = FakeSession(catalog)

    @contextlib.contextmanager
    def fake_session(project_path=None, extra_params=None, env=None):
        yield fake

    monkeypatch.setattr(_session_mod, "bootstrapped_session", fake_session)

    envelope = tools.read_dataset("pq_ds")
    assert envelope["provenance_kind"] == "file-mtime"
    assert envelope["build_stamp"] == datetime.datetime.fromtimestamp(
        old_ts, tz=datetime.UTC
    ).isoformat()
    assert envelope["build_stamp_newest"] is None
