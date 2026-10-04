"""Story 27.2 — degraded seed / cross-pipeline parquet + VCS refresh batches."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from pyforge.atlas.datasets.degraded_json import DegradedJsonSeedDataset
from pyforge.atlas.datasets.degrading_parquet import DegradingParquetDataset
from pyforge.atlas.pipelines.vcs_health.vcs_refresh_identifiers import batches_from_identity


def test_degraded_json_absent_seed_marks_stale(tmp_path):
    path = tmp_path / "seed.json"
    ds = DegradedJsonSeedDataset(filepath=str(path))
    assert ds.load() == {}
    marker_path = path.with_name(path.name + DegradedJsonSeedDataset.STALENESS_SUFFIX)
    assert marker_path.is_file()
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker["stale"] is True


def test_degraded_json_corrupt_seed_returns_empty(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text("{not-json", encoding="utf-8")
    ds = DegradedJsonSeedDataset(filepath=str(path))
    assert ds.load() == {}


def test_degraded_json_valid_dict(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text('{"k": 1}', encoding="utf-8")
    ds = DegradedJsonSeedDataset(filepath=str(path))
    assert ds.load() == {"k": 1}


def test_degraded_json_non_dict_payload_returns_empty(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text("[1, 2]", encoding="utf-8")
    ds = DegradedJsonSeedDataset(filepath=str(path))
    assert ds.load() == {}


def test_degraded_json_read_only(tmp_path):
    from kedro.io.core import DatasetError

    ds = DegradedJsonSeedDataset(filepath=str(tmp_path / "x.json"))
    with pytest.raises(DatasetError, match="read-only"):
        ds.save({})


def test_degrading_parquet_missing_file(tmp_path):
    ds = DegradingParquetDataset(filepath=str(tmp_path / "missing.parquet"), columns=["a"])
    frame = ds.load()
    assert frame.empty and list(frame.columns) == ["a"]


def test_degrading_parquet_corrupt_file(tmp_path):
    path = tmp_path / "bad.parquet"
    path.write_bytes(b"not-parquet")
    ds = DegradingParquetDataset(filepath=str(path), columns=["x"])
    frame = ds.load()
    assert frame.empty


def test_degrading_parquet_round_trip(tmp_path):
    path = tmp_path / "ok.parquet"
    ds = DegradingParquetDataset(filepath=str(path), columns=["name"])
    df = pd.DataFrame({"name": ["a"]})
    ds.save(df)
    loaded = ds.load()
    assert loaded["name"].tolist() == ["a"]


def test_batches_from_identity_empty_inputs():
    out = batches_from_identity(None)
    assert out["github_repos"] == ()
    assert all(out["registries"][k] == () for k in out["registries"])


def test_batches_from_identity_missing_name_column():
    df = pd.DataFrame({"other": [1]})
    out = batches_from_identity(df)
    assert out["github_repos"] == ()


def test_batches_from_identity_extracts_hosts_and_registries():
    df = pd.DataFrame(
        {
            "Core_Python_Package_Name": ["NumPy", "requests_pkg"],
            "primary_purl": [
                "pkg:github/numpy/numpy; pkg:npm/lodash",
                "pkg:gitlab/org/repo",
            ],
            "alternative_purls": ["pkg:codeberg/acme/tool", ""],
            "source_repository_url": ["pkg:cran/ggplot2", ""],
        }
    )
    out = batches_from_identity(df)
    assert ("numpy", "numpy") in out["github_repos"]
    assert ("requests-pkg", "org/repo") in out["gitlab"]
    assert ("numpy", "acme/tool") in out["codeberg"]
    assert ("numpy", "lodash") in out["registries"]["npm"]
