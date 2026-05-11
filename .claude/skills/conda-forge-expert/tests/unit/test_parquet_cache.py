"""Unit tests for `_parquet_cache.ensure_month` and `read_filtered`.

Builds a tiny synthetic parquet in-test via pyarrow; never touches the network.
"""
from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    """Load an underscore-private module from scripts/ via importlib."""
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def http_mod():
    return _load("_http")


@pytest.fixture
def parquet_cache_mod(http_mod):
    return _load("_parquet_cache")


@pytest.fixture
def synthetic_parquet_bytes():
    """A 4-row parquet matching the bucket schema."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.table({
        "time": ["2026-04", "2026-04", "2026-04", "2026-04"],
        "data_source": ["conda-forge", "conda-forge", "bioconda", "conda-forge"],
        "pkg_name": ["requests", "django", "samtools", "requests"],
        "pkg_version": ["2.31.0", "5.0.0", "1.20", "2.32.0"],
        "pkg_platform": ["noarch", "noarch", "linux-64", "noarch"],
        "pkg_python": ["3.12", "3.12", "", "3.13"],
        "counts": [1000, 500, 9999, 200],
    })
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


@pytest.fixture
def cache_root(tmp_path, parquet_cache_mod):
    parquet_cache_mod.set_cache_dir(tmp_path / "parquet-cache")
    yield tmp_path / "parquet-cache"
    parquet_cache_mod.set_cache_dir(None)


class TestEnsureMonth:
    def test_downloads_when_missing(
        self, monkeypatch, http_mod, parquet_cache_mod, cache_root, synthetic_parquet_bytes,
    ):
        called: list[str] = []

        class _FakeResp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *_): return None

        def fake_open_url(req, timeout):
            called.append(req.full_url)
            return _FakeResp(synthetic_parquet_bytes)

        monkeypatch.setattr(http_mod, "open_url", fake_open_url)
        monkeypatch.setattr(parquet_cache_mod, "open_url", fake_open_url)

        path = parquet_cache_mod.ensure_month("2026-03", current_month="2026-04")
        assert path.exists()
        assert path.read_bytes() == synthetic_parquet_bytes
        assert len(called) == 1

    def test_idempotent_on_cache_hit(
        self, monkeypatch, parquet_cache_mod, cache_root, synthetic_parquet_bytes,
    ):
        target = cache_root / "2026-03.parquet"
        cache_root.mkdir(parents=True, exist_ok=True)
        target.write_bytes(synthetic_parquet_bytes)
        called: list[str] = []

        def fake_open_url(req, timeout):
            called.append(req.full_url)
            raise AssertionError("ensure_month should not download a cached non-current month")

        monkeypatch.setattr(parquet_cache_mod, "open_url", fake_open_url)
        path = parquet_cache_mod.ensure_month("2026-03", current_month="2026-04")
        assert path == target
        assert called == []

    def test_truncated_download_rejected(
        self, monkeypatch, parquet_cache_mod, cache_root,
    ):
        target = cache_root / "2026-04.parquet"

        class _FakeResp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *_): return None

        def fake_open_url(req, timeout):
            return _FakeResp(b"x" * 32)  # well under 1024-byte floor

        monkeypatch.setattr(parquet_cache_mod, "open_url", fake_open_url)
        with pytest.raises(RuntimeError, match="truncated or empty"):
            parquet_cache_mod.ensure_month("2026-04", current_month="2026-04")
        assert not target.exists()  # tmp cleaned up; no garbage cached

    def test_listing_failure_with_cache_returns_cache(
        self, monkeypatch, parquet_cache_mod, cache_root, synthetic_parquet_bytes,
    ):
        target = cache_root / "2026-03.parquet"
        cache_root.mkdir(parents=True, exist_ok=True)
        target.write_bytes(synthetic_parquet_bytes)

        def fake_list():
            raise RuntimeError("S3 listing unreachable")

        monkeypatch.setattr(parquet_cache_mod, "list_s3_parquet_months", fake_list)

        def fake_open_url(req, timeout):
            raise AssertionError("must not download when listing fails and cache exists")

        monkeypatch.setattr(parquet_cache_mod, "open_url", fake_open_url)
        path = parquet_cache_mod.ensure_month("2026-03")
        assert path == target

    def test_current_month_always_refetched(
        self, monkeypatch, parquet_cache_mod, cache_root, synthetic_parquet_bytes,
    ):
        target = cache_root / "2026-04.parquet"
        cache_root.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"stale-contents")
        called: list[str] = []

        class _FakeResp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *_): return None

        def fake_open_url(req, timeout):
            called.append(req.full_url)
            return _FakeResp(synthetic_parquet_bytes)

        monkeypatch.setattr(parquet_cache_mod, "open_url", fake_open_url)
        path = parquet_cache_mod.ensure_month("2026-04", current_month="2026-04")
        assert path.read_bytes() == synthetic_parquet_bytes
        assert len(called) == 1


class TestReadFiltered:
    def test_data_source_filter_applied(
        self, parquet_cache_mod, cache_root, synthetic_parquet_bytes,
    ):
        cache_root.mkdir(parents=True, exist_ok=True)
        (cache_root / "2026-04.parquet").write_bytes(synthetic_parquet_bytes)

        table = parquet_cache_mod.read_filtered(["2026-04"], data_source="conda-forge")
        sources = set(table["data_source"].to_pylist())
        assert sources == {"conda-forge"}
        assert table.num_rows == 3

    def test_pkg_name_filter(
        self, parquet_cache_mod, cache_root, synthetic_parquet_bytes,
    ):
        cache_root.mkdir(parents=True, exist_ok=True)
        (cache_root / "2026-04.parquet").write_bytes(synthetic_parquet_bytes)

        table = parquet_cache_mod.read_filtered(
            ["2026-04"], pkg_names={"requests"}, data_source="conda-forge"
        )
        assert set(table["pkg_name"].to_pylist()) == {"requests"}
        assert table.num_rows == 2

    def test_returns_expected_columns(
        self, parquet_cache_mod, cache_root, synthetic_parquet_bytes,
    ):
        cache_root.mkdir(parents=True, exist_ok=True)
        (cache_root / "2026-04.parquet").write_bytes(synthetic_parquet_bytes)

        table = parquet_cache_mod.read_filtered(["2026-04"])
        assert set(table.column_names) == {
            "time", "data_source", "pkg_name", "pkg_version",
            "pkg_platform", "pkg_python", "counts",
        }
