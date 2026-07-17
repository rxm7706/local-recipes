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
    # identity: the exact sentinel object came back untouched — no transform
    assert loaded is SENTINEL
    assert loaded == {"rows": [{"package": "demo", "health": "green"}]}


def test_read_dataset_unknown_name_raises_catalog_error(real_catalog_session):
    # a pure passthrough raises whatever catalog.load raises (AD-7: the
    # surface adds nothing — not even its own not-found translation)
    with pytest.raises(Exception, match="no_such_ds"):
        tools.read_dataset("no_such_ds")


def test_list_datasets_lists_the_catalog_keys(real_catalog_session):
    assert tools.list_datasets() == ["demo_ds"]
