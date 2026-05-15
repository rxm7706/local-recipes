"""Phase P — PyPI downloads via BigQuery.

Phase P is opt-in (`PHASE_P_ENABLED=1`) AND requires `google-cloud-bigquery`
(not in the local-recipes env by default — operators add via
`pixi add google-cloud-bigquery`). These tests exercise the skip paths
without requiring the actual library or BQ credentials.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


@pytest.fixture
def db(tmp_path, atlas_mod):
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


class TestPhaseP_OptInGate:
    """Phase P only runs when PHASE_P_ENABLED=1 is set."""

    def test_disabled_takes_priority(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.setenv("PHASE_P_DISABLED", "1")
        result = atlas_mod.phase_p_pypi_downloads(db)
        assert result.get("skipped") is True
        assert "PHASE_P_DISABLED" in result.get("reason", "")

    def test_default_no_env_is_skipped(self, db, atlas_mod, monkeypatch):
        monkeypatch.delenv("PHASE_P_ENABLED", raising=False)
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        result = atlas_mod.phase_p_pypi_downloads(db)
        assert result.get("skipped") is True
        assert "opt-in" in result.get("reason", "")


class TestPhaseP_MissingLibrary:
    """When google-cloud-bigquery is not importable, Phase P skips gracefully."""

    def test_missing_library_skips(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        # google-cloud-bigquery is not in the local-recipes env by default;
        # the lazy `from google.cloud import bigquery` will raise ImportError.
        result = atlas_mod.phase_p_pypi_downloads(db)
        # Either the library is installed OR not — test the not-installed case
        # which matches the default local-recipes env. If a future env
        # update adds it, this test will need to mock the import instead.
        try:
            from google.cloud import bigquery  # type: ignore[import-untyped]  # noqa: F401
            installed = True
        except ImportError:
            installed = False
        if not installed:
            assert result.get("skipped") is True
            assert "google-cloud-bigquery" in result.get("reason", "")


class TestPhaseP_QueryShape:
    """When the library is mocked-available, the query string follows the
    documented shape (project-level aggregate, 30d + 90d windows)."""

    def test_query_string_aggregates_per_project(self, atlas_mod):
        # Source check on the canonical phase_p_pypi_downloads function:
        # the query string is embedded in the function body. Verify the
        # documented shape via source-level grep.
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "bigquery-public-data.pypi.file_downloads" in src
        assert "downloads_30d" in src
        assert "downloads_90d" in src
        assert "GROUP BY pypi_name" in src
        # PEP 503-canonical pypi_name on the BQ side too
        assert "REGEXP_REPLACE(LOWER(file.project)" in src
