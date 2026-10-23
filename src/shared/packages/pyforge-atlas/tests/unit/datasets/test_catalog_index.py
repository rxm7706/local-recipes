"""Story 37.10 — every catalog entry's last write and row count on the data root."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.datasets import CatalogIndexDataset
from pyforge.atlas.datasets.catalog_index import COLUMNS, data_root_relpath

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
json_store:
  type: x.RefreshStore
  filepath: ${globals:paths.data_root}/raw/json_store
literal_root:
  type: partitions.PartitionedDataset
  path: data/derived/literal_root
elsewhere:
  type: x.Clones
  filepath: ${globals:paths.repo_cache}/clones
live_only:
  type: x.APIDataset
  url: https://example.invalid/api
a_seed:
  type: x.TrackedSeedDataset
  filepath: conf/base/seeds/a_seed.json
_anchor: &anchor
  type: pandas.ParquetDataset
"""
GLOBALS = """
paths:
  data_root: ${env_or:PYFORGE_ATLAS_DATA_ROOT,data}
  pypi_conda_map: ${paths.data_root}/stores/pypi_conda_map.json
  repo_cache: /elsewhere/cache
"""
STAMP = 1_700_000_000


def _write(path: Path, rows: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"a": range(rows)}).to_parquet(path, index=False)
    os.utime(path, (STAMP, STAMP))
    return path


def _index(tmp_path: Path, catalog: str = CATALOG) -> dict[str, dict]:
    conf = tmp_path / "conf"
    conf.mkdir(exist_ok=True)
    (conf / "catalog.yml").write_text(catalog, encoding="utf-8")
    (conf / "globals.yml").write_text(GLOBALS, encoding="utf-8")
    frame = CatalogIndexDataset(filepath=str(conf / "catalog.yml"), path=str(tmp_path / "data")).load()
    assert list(frame.columns) == COLUMNS
    return {row["catalog_entry"]: row for row in frame.to_dict("records")}


def test_every_entry_under_the_data_root_is_listed_by_any_path_key_or_global(tmp_path):
    got = _index(tmp_path)
    assert set(got) == {
        "core_packages_enumerated",
        "discovery_homebrew_packages_raw",
        "never_written",
        "degraded",
        "pypi_conda_map_store",
        "json_store",
        "literal_root",
    }
    assert got["pypi_conda_map_store"]["relpath"] == "stores/pypi_conda_map.json"
    assert got["literal_root"]["relpath"] == "derived/literal_root"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("${globals:paths.data_root}/primary/x.parquet", "primary/x.parquet"),
        ("${globals:paths.pypi_conda_map}", "stores/pypi_conda_map.json"),
        ("data/derived/y", "derived/y"),
        ("${globals:paths.repo_cache}/clones", None),
        ("${globals:paths.unknown}/z", None),
        ("conf/base/seeds/s.json", None),
    ],
)
def test_a_catalog_path_resolves_through_the_path_globals(value, expected):
    paths = {"pypi_conda_map": "${paths.data_root}/stores/pypi_conda_map.json", "repo_cache": "/elsewhere/cache"}
    assert data_root_relpath(value, paths) == expected


def test_a_parquet_file_gives_its_write_and_footer_count(tmp_path):
    _write(tmp_path / "data/intermediate/core_packages_enumerated/core_packages_enumerated.parquet", 7)
    row = _index(tmp_path)["core_packages_enumerated"]
    assert row["row_count"] == 7
    assert row["layer"] == "intermediate"
    assert int(row["regenerated_at"].timestamp()) == STAMP
    assert not bool(row["stale"])


def test_a_store_directory_sums_its_parquet_at_any_depth_and_takes_its_newest_write(tmp_path):
    store = tmp_path / "data/stores/discovery_homebrew_packages_raw"
    _write(store / "a.parquet", 2)
    newest = _write(store / "months" / "2026-10.parquet", 5)
    os.utime(newest, (STAMP + 60, STAMP + 60))
    (store / ".staleness.json").write_text(json.dumps({"stale": True, "reason": "fetch failed"}), encoding="utf-8")
    os.utime(store / ".staleness.json", (STAMP + 999, STAMP + 999))  # a marker is not a write
    row = _index(tmp_path)["discovery_homebrew_packages_raw"]
    assert row["row_count"] == 7
    assert int(row["regenerated_at"].timestamp()) == STAMP + 60
    assert bool(row["stale"]) is True
    assert row["stale_reason"] == "fetch failed"


def test_a_store_of_json_files_has_a_write_and_no_count(tmp_path):
    store = tmp_path / "data/raw/json_store"
    store.mkdir(parents=True)
    (store / "last_good.json").write_text("{}", encoding="utf-8")
    row = _index(tmp_path)["json_store"]
    assert not pd.isna(row["regenerated_at"])
    assert pd.isna(row["row_count"])


def test_a_store_holding_only_a_marker_is_not_written(tmp_path):
    store = tmp_path / "data/raw/json_store"
    store.mkdir(parents=True)
    (store / ".staleness.json").write_text(json.dumps({"stale": True, "reason": "x"}), encoding="utf-8")
    row = _index(tmp_path)["json_store"]
    assert pd.isna(row["regenerated_at"]) and bool(row["stale"]) is True


def test_a_file_marker_inside_a_store_is_not_a_write(tmp_path):
    store = tmp_path / "data/raw/json_store"
    store.mkdir(parents=True)
    (store / "part.parquet.staleness.json").write_text(json.dumps({"stale": True, "reason": "x"}), encoding="utf-8")
    assert pd.isna(_index(tmp_path)["json_store"]["regenerated_at"])


def test_a_sibling_marker_marks_a_file_stale(tmp_path):
    path = _write(tmp_path / "data/primary/degraded/degraded.parquet", 3)
    path.with_name(path.name + ".staleness.json").write_text(json.dumps({"stale": True, "reason": "x"}), "utf-8")
    assert bool(_index(tmp_path)["degraded"]["stale"]) is True


def test_an_absent_file_has_no_write_and_no_count(tmp_path):
    row = _index(tmp_path)["never_written"]
    assert pd.isna(row["regenerated_at"])
    assert pd.isna(row["row_count"])


def test_a_file_that_is_not_parquet_has_a_write_and_no_count(tmp_path):
    path = tmp_path / "data/primary/degraded/degraded.parquet"
    path.parent.mkdir(parents=True)
    path.write_text("not parquet", encoding="utf-8")
    row = _index(tmp_path)["degraded"]
    assert not pd.isna(row["regenerated_at"])
    assert pd.isna(row["row_count"])


@pytest.mark.parametrize("catalog", ["", "[1, 2]", "{bad: ["])
def test_an_unreadable_catalog_gives_an_empty_frame(tmp_path, catalog):
    assert _index(tmp_path, catalog) == {}


def test_a_missing_catalog_gives_an_empty_frame(tmp_path):
    frame = CatalogIndexDataset(filepath=str(tmp_path / "missing.yml"), path=str(tmp_path)).load()
    assert frame.empty and list(frame.columns) == COLUMNS


def test_the_dataset_is_read_only(tmp_path):
    with pytest.raises(Exception, match="read-only"):
        CatalogIndexDataset(filepath="x", path=str(tmp_path)).save(pd.DataFrame())


def test_the_shipped_catalog_lists_every_data_root_entry(tmp_path):
    shipped = Path(__file__).resolve().parents[3] / "conf" / "base" / "catalog.yml"
    frame = CatalogIndexDataset(filepath=str(shipped), path=str(tmp_path)).load()
    names = set(frame["catalog_entry"])
    assert {"core_packages_enumerated", "pypi_universe", "pypi_conda_map_store", "vulnerability_vdb_store"} <= names
    assert "catalog_index_raw" not in names  # it persists nothing
