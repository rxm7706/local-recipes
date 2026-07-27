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
    loaded = tools.read_dataset("demo_ds")
    assert loaded["dataset"] == "demo_ds"
    assert "build_stamp" in loaded and loaded["build_stamp"]
    # value is the exact sentinel object — load passthrough, AD-17 wraps the envelope
    assert loaded["value"] is SENTINEL
    assert loaded["value"] == {"rows": [{"package": "demo", "health": "green"}]}


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

    out = tools.read_dataset("df_ds")
    assert out["dataset"] == "df_ds"
    assert out["build_stamp"]
    # coerced to list[row-dict], not a raw DataFrame
    assert out["value"] == [
        {"package": "numpy", "downloads": 10},
        {"package": "pandas", "downloads": 20},
    ]
    # the whole point: it survives the MCP JSON boundary
    json.dumps(out)


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
        payload = tools.read_dataset(ds)
        assert payload["dataset"] == ds
        assert payload["build_stamp"]
        json.dumps(payload)
