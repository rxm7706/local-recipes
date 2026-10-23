"""Story 37.10 — every catalog entry's last write and row count on the data root."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.datasets import CatalogIndexDataset
from pyforge.atlas.datasets.catalog_index import COLUMNS

CATALOG = """
core_packages_enumerated:
  type: pandas.ParquetDataset
  filepath: ${globals:paths.data_root}/intermediate/core_packages_enumerated/core_packages_enumerated.parquet
  metadata:
    layer: intermediate
discovery_homebrew_packages_raw:
  type: x.HomebrewPackagesDataset
  url: https://example.invalid/formula.json
  filepath: ${globals:paths.data_root}/stores/discovery_homebrew_packages_raw
never_written:
  type: pandas.ParquetDataset
  filepath: ${globals:paths.data_root}/primary/never_written/never_written.parquet
degraded:
  type: x.DegradingParquetDataset
  filepath: ${globals:paths.data_root}/primary/degraded/degraded.parquet
pypi_conda_map_store:
  type: x.MappingCacheDataset
  filepath: ${globals:paths.pypi_conda_map}
live_only:
  type: x.APIDataset
  url: https://example.invalid/api
a_seed:
  type: x.TrackedSeedDataset
  filepath: conf/base/seeds/a_seed.json
_anchor: &anchor
  type: pandas.ParquetDataset
"""
STAMP = 1_700_000_000


def _write(path: Path, rows: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"a": range(rows)}).to_parquet(path, index=False)
    os.utime(path, (STAMP, STAMP))
    return path


def _index(tmp_path: Path, catalog: str = CATALOG) -> dict[str, dict]:
    catalog_path = tmp_path / "catalog.yml"
    catalog_path.write_text(catalog, encoding="utf-8")
    frame = CatalogIndexDataset(catalog_path=str(catalog_path), data_root=str(tmp_path / "data")).load()
    assert list(frame.columns) == COLUMNS
    return {row["catalog_entry"]: row for row in frame.to_dict("records")}


def test_only_entries_under_the_data_root_are_listed(tmp_path):
    got = _index(tmp_path)
    assert set(got) == {"core_packages_enumerated", "discovery_homebrew_packages_raw", "never_written", "degraded"}


def test_a_parquet_file_gives_its_write_and_footer_count(tmp_path):
    _write(tmp_path / "data/intermediate/core_packages_enumerated/core_packages_enumerated.parquet", 7)
    row = _index(tmp_path)["core_packages_enumerated"]
    assert row["row_count"] == 7
    assert row["layer"] == "intermediate"
    assert int(row["regenerated_at"].timestamp()) == STAMP
    assert row["stale"] is False or row["stale"] == False  # noqa: E712 -- numpy bool


def test_a_store_directory_gives_its_newest_parquet_and_its_marker(tmp_path):
    store = tmp_path / "data/stores/discovery_homebrew_packages_raw"
    _write(store / "old.parquet", 2)
    newest = _write(store / "packages.parquet", 5)
    os.utime(newest, (STAMP + 60, STAMP + 60))
    (store / ".staleness.json").write_text(json.dumps({"stale": True, "reason": "fetch failed"}), encoding="utf-8")
    row = _index(tmp_path)["discovery_homebrew_packages_raw"]
    assert row["row_count"] == 5
    assert int(row["regenerated_at"].timestamp()) == STAMP + 60
    assert bool(row["stale"]) is True
    assert row["stale_reason"] == "fetch failed"


def test_a_sibling_marker_marks_a_file_stale(tmp_path):
    path = _write(tmp_path / "data/primary/degraded/degraded.parquet", 3)
    path.with_name(path.name + ".staleness.json").write_text(json.dumps({"stale": True, "reason": "x"}), "utf-8")
    assert bool(_index(tmp_path)["degraded"]["stale"]) is True


def test_an_absent_file_has_no_write_and_no_count(tmp_path):
    row = _index(tmp_path)["never_written"]
    assert row["regenerated_at"] is None or pd.isna(row["regenerated_at"])
    assert pd.isna(row["row_count"])


def test_a_file_that_is_not_parquet_has_a_write_and_no_count(tmp_path):
    path = tmp_path / "data/primary/degraded/degraded.parquet"
    path.parent.mkdir(parents=True)
    path.write_text("not parquet", encoding="utf-8")
    row = _index(tmp_path)["degraded"]
    assert not pd.isna(row["regenerated_at"])
    assert pd.isna(row["row_count"])


@pytest.mark.parametrize("catalog", ["", "[1, 2]", "{bad: [", None])
def test_an_unreadable_catalog_gives_an_empty_frame(tmp_path, catalog):
    if catalog is None:
        frame = CatalogIndexDataset(catalog_path=str(tmp_path / "missing.yml"), data_root=str(tmp_path)).load()
        assert frame.empty and list(frame.columns) == COLUMNS
        return
    assert _index(tmp_path, catalog) == {}


def test_the_dataset_is_read_only(tmp_path):
    with pytest.raises(Exception, match="read-only"):
        CatalogIndexDataset(catalog_path="x", data_root=str(tmp_path)).save(pd.DataFrame())


def test_the_shipped_catalog_lists_every_data_root_entry(tmp_path):
    shipped = Path(__file__).resolve().parents[3] / "conf" / "base" / "catalog.yml"
    frame = CatalogIndexDataset(catalog_path=str(shipped), data_root=str(tmp_path)).load()
    names = set(frame["catalog_entry"])
    assert {"core_packages_enumerated", "pypi_universe", "catalog_index_health"} <= names
    assert "catalog_index_raw" not in names  # it persists nothing
