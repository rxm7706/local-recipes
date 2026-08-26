"""Steward 34.2: named Kedro Parquet cache (FR-47, canopy AD-22)."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pandas as pd
import pytest
from kedro.framework.project import configure_project
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from kedro_datasets.pandas import ParquetDataset

from pyforge.atlas.pipeline_registry import register_pipelines
from pyforge.atlas.pipelines.query_plane_cache import create_pipeline
from pyforge.atlas.query_plane_cache import (
    ESTATE_CACHE_DATASET,
    PIPELINE_NAME,
    scan_estate_parquet,
)

ATLAS_ROOT = Path(__file__).resolve().parents[1]
CACHE_MODULE = ATLAS_ROOT / "src" / "pyforge" / "atlas" / "query_plane_cache.py"
PIPELINE_DIR = ATLAS_ROOT / "src" / "pyforge" / "atlas" / "pipelines" / "query_plane_cache"
CATALOG_YML = ATLAS_ROOT / "conf" / "base" / "catalog.yml"


def _estate_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sku": ["widget-a", "widget-b"],
            "units": [12, 7],
        }
    )


def test_named_pipeline_is_registered() -> None:
    configure_project("pyforge.atlas")
    pipelines = register_pipelines()
    assert PIPELINE_NAME in pipelines
    assert PIPELINE_NAME != "__default__"


def test_kedro_run_writes_compressed_parquet(tmp_path: Path) -> None:
    cache_path = tmp_path / "query_plane_estate.parquet"
    catalog = DataCatalog(
        {
            "query_plane_estate_source": MemoryDataset(_estate_frame()),
            "query_plane_estate": ParquetDataset(
                filepath=str(cache_path),
                save_args={"compression": "zstd"},
            ),
        }
    )
    SequentialRunner().run(create_pipeline(), catalog)
    assert cache_path.is_file()
    rows = scan_estate_parquet(cache_path)
    assert ("widget-a", 12) in rows
    assert ("widget-b", 7) in rows


def test_scan_does_not_use_oltp_writer_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_path = tmp_path / "estate.parquet"
    _estate_frame().to_parquet(cache_path, compression="zstd")
    writer_dsn = "postgresql://platform_writer:secret@oltp.example:5432/platform"
    monkeypatch.setenv("DATABASE_URL", writer_dsn)
    monkeypatch.setenv("OLTP_WRITER_DSN", writer_dsn)

    import duckdb

    real_connect = duckdb.connect

    def _memory_only(database: str = ":memory:", **kwargs: object):
        assert str(database) in {":memory:", ""}, database
        return real_connect(database)

    monkeypatch.setattr("pyforge.atlas.query_plane_cache.duckdb.connect", _memory_only)
    rows = scan_estate_parquet(cache_path)
    assert rows
    sig = inspect.signature(scan_estate_parquet)
    assert "dsn" not in sig.parameters
    assert "writer" not in sig.parameters
    source = inspect.getsource(scan_estate_parquet)
    assert "postgresql" not in source
    assert writer_dsn not in source


def test_refresh_is_not_airflow_or_01_raw() -> None:
    texts = [CATALOG_YML.read_text(encoding="utf-8")]
    for path in PIPELINE_DIR.glob("*.py"):
        texts.append(path.read_text(encoding="utf-8"))
    texts.append(CACHE_MODULE.read_text(encoding="utf-8"))
    blob = "\n".join(texts)
    assert "01_raw" not in blob
    assert "airflow" not in blob.lower()
    for path in [CACHE_MODULE, *PIPELINE_DIR.glob("*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            assert all("airflow" not in name for name in names)


def test_catalog_names_match_helper_constants() -> None:
    text = CATALOG_YML.read_text(encoding="utf-8")
    assert f"{ESTATE_CACHE_DATASET}:" in text
    assert "query_plane_estate_source:" in text
    assert "compression: zstd" in text
