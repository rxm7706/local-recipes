"""Phase R — per-project JSON enrichment for top-N candidate slice.

Covers `_classify_packaging_shape`, `_normalize_license_to_spdx`, and the
Phase R orchestration (candidate slice + TTL gate + skip paths).
"""
from __future__ import annotations

import importlib.util
import json
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


# ─── _classify_packaging_shape ─────────────────────────────────────────

class TestClassifyPackagingShape:
    def test_pure_python_classification(self, atlas_mod):
        """All wheels are *-none-any.whl → pure-python."""
        doc = {
            "info": {"requires_dist": [], "classifiers": []},
            "urls": [
                {"packagetype": "sdist",       "filename": "foo-1.0.tar.gz"},
                {"packagetype": "bdist_wheel", "filename": "foo-1.0-py3-none-any.whl"},
                {"packagetype": "bdist_wheel", "filename": "foo-1.0-py2.py3-none-any.whl"},
            ],
        }
        assert atlas_mod._classify_packaging_shape(doc) == "pure-python"

    def test_rust_pyo3_via_maturin_requires(self, atlas_mod):
        doc = {
            "info": {
                "requires_dist": ["maturin >=1.0"],
                "classifiers": [],
            },
            "urls": [],
        }
        assert atlas_mod._classify_packaging_shape(doc) == "rust-pyo3"

    def test_rust_pyo3_via_classifier(self, atlas_mod):
        doc = {
            "info": {
                "requires_dist": [],
                "classifiers": ["Programming Language :: Rust"],
            },
            "urls": [],
        }
        assert atlas_mod._classify_packaging_shape(doc) == "rust-pyo3"

    def test_cython_classification(self, atlas_mod):
        doc = {
            "info": {
                "requires_dist": ["Cython >=3.0"],
                "classifiers": [],
            },
            "urls": [
                {"packagetype": "bdist_wheel",
                 "filename": "foo-1.0-cp310-cp310-linux_x86_64.whl"},
            ],
        }
        # Cython wins over c-extension when build-system declares cython
        assert atlas_mod._classify_packaging_shape(doc) == "cython"

    def test_c_extension_via_cp_abi(self, atlas_mod):
        doc = {
            "info": {"requires_dist": [], "classifiers": []},
            "urls": [
                {"packagetype": "bdist_wheel",
                 "filename": "foo-1.0-cp311-cp311-linux_x86_64.whl"},
                {"packagetype": "bdist_wheel",
                 "filename": "foo-1.0-cp312-cp312-manylinux_2_17_x86_64.whl"},
            ],
        }
        assert atlas_mod._classify_packaging_shape(doc) == "c-extension"

    def test_unknown_when_no_wheels_and_no_classifiers(self, atlas_mod):
        doc = {
            "info": {"requires_dist": [], "classifiers": []},
            "urls": [{"packagetype": "sdist", "filename": "foo-1.0.tar.gz"}],
        }
        assert atlas_mod._classify_packaging_shape(doc) == "unknown"

    def test_malformed_input_returns_unknown(self, atlas_mod):
        assert atlas_mod._classify_packaging_shape(None) == "unknown"
        assert atlas_mod._classify_packaging_shape("not a dict") == "unknown"


# ─── _normalize_license_to_spdx ─────────────────────────────────────────

class TestNormalizeLicense:
    def test_canonical_mit(self, atlas_mod):
        assert atlas_mod._normalize_license_to_spdx("MIT") == "MIT"
        assert atlas_mod._normalize_license_to_spdx("MIT License") == "MIT"
        assert atlas_mod._normalize_license_to_spdx("mit license") == "MIT"

    def test_apache_variants(self, atlas_mod):
        assert atlas_mod._normalize_license_to_spdx("Apache 2.0") == "Apache-2.0"
        assert atlas_mod._normalize_license_to_spdx("Apache-2.0") == "Apache-2.0"
        assert atlas_mod._normalize_license_to_spdx("Apache License, Version 2.0") == "Apache-2.0"

    def test_gpl_variants(self, atlas_mod):
        assert atlas_mod._normalize_license_to_spdx("GPL v2") == "GPL-2.0-only"
        assert atlas_mod._normalize_license_to_spdx("GPL v3") == "GPL-3.0-only"

    def test_classifier_style(self, atlas_mod):
        assert atlas_mod._normalize_license_to_spdx(
            "License :: OSI Approved :: MIT License"
        ) == "MIT"

    def test_unknown_returns_none(self, atlas_mod):
        assert atlas_mod._normalize_license_to_spdx("Some Custom License") is None
        assert atlas_mod._normalize_license_to_spdx("") is None
        assert atlas_mod._normalize_license_to_spdx(None) is None
        assert atlas_mod._normalize_license_to_spdx("UNKNOWN") is None


# ─── Phase R orchestration ─────────────────────────────────────────────

@pytest.fixture
def db(tmp_path, atlas_mod):
    """v22 atlas with pypi_universe seeded but no conda-forge matches."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    # Seed candidates (pypi-only — no `packages` rows)
    for name, serial in [("alpha", 10), ("beta", 9), ("gamma", 8)]:
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, ?, ?)",
            (name, serial, 0),
        )
    conn.commit()
    yield conn
    conn.close()


class TestPhaseR_OptInGate:
    def test_disabled_skips(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_R_ENABLED", "1")
        monkeypatch.setenv("PHASE_R_DISABLED", "1")
        result = atlas_mod.phase_r_pypi_json_enrich(db)
        assert result.get("skipped") is True
        assert "PHASE_R_DISABLED" in result.get("reason", "")

    def test_default_no_env_is_skipped(self, db, atlas_mod, monkeypatch):
        monkeypatch.delenv("PHASE_R_ENABLED", raising=False)
        monkeypatch.delenv("PHASE_R_DISABLED", raising=False)
        result = atlas_mod.phase_r_pypi_json_enrich(db)
        assert result.get("skipped") is True
        assert "opt-in" in result.get("reason", "")


class TestPhaseR_CandidateSlice:
    """Phase R's candidate query orders by last_serial DESC and excludes
    rows with fresh json_fetched_at."""

    def test_candidate_limit_respected(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_R_ENABLED", "1")
        monkeypatch.setenv("PHASE_R_CANDIDATE_LIMIT", "2")

        # Mock the worker to avoid real HTTP
        def _fake_fetch(pypi_name):
            return (pypi_name, {"info": {"version": "1.0"}, "urls": []}, None)
        monkeypatch.setattr(atlas_mod, "_phase_r_fetch_one", _fake_fetch)

        result = atlas_mod.phase_r_pypi_json_enrich(db)
        # Only top-2 by serial (alpha=10, beta=9)
        assert result.get("candidates_processed") == 2
        assert result.get("fetched") == 2

    def test_ttl_gate_excludes_fresh_rows(self, db, atlas_mod, monkeypatch):
        import time
        # Pre-seed pypi_intelligence with a fresh json_fetched_at on alpha
        now = int(time.time())
        db.execute(
            "INSERT INTO pypi_intelligence (pypi_name, json_fetched_at) "
            "VALUES (?, ?)",
            ("alpha", now),
        )
        db.commit()

        monkeypatch.setenv("PHASE_R_ENABLED", "1")
        monkeypatch.setenv("PHASE_R_TTL_DAYS", "7")

        def _fake_fetch(pypi_name):
            return (pypi_name, {"info": {"version": "1.0"}, "urls": []}, None)
        monkeypatch.setattr(atlas_mod, "_phase_r_fetch_one", _fake_fetch)

        result = atlas_mod.phase_r_pypi_json_enrich(db)
        # alpha excluded by TTL; beta + gamma processed
        assert result.get("candidates_processed") == 2

    def test_404_response_records_error_and_advances_ttl(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_R_ENABLED", "1")

        def _fake_fetch(pypi_name):
            if pypi_name == "alpha":
                return ("alpha", None, "HTTP 404")
            return (pypi_name, {"info": {"version": "1.0"}, "urls": []}, None)
        monkeypatch.setattr(atlas_mod, "_phase_r_fetch_one", _fake_fetch)

        result = atlas_mod.phase_r_pypi_json_enrich(db)
        assert result.get("not_found") == 1
        # 404 advances json_fetched_at so the row won't be re-fetched immediately
        row = db.execute(
            "SELECT json_last_error, json_fetched_at FROM pypi_intelligence "
            "WHERE pypi_name='alpha'"
        ).fetchone()
        assert row["json_last_error"] == "HTTP 404"
        assert row["json_fetched_at"] is not None


class TestPhaseR_Enrichment:
    """End-to-end: a mocked fetcher returns a realistic JSON doc; verify
    Phase R parses license/classifiers/wheels and writes to pypi_intelligence."""

    def test_full_enrichment_pipeline(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_R_ENABLED", "1")

        def _fake_fetch(pypi_name):
            if pypi_name == "alpha":
                return (pypi_name, {
                    "info": {
                        "version": "2.5.0",
                        "license": "MIT License",
                        "requires_python": ">=3.10",
                        "summary": "A test package",
                        "home_page": "https://example.com/alpha",
                        "project_urls": {
                            "Repository": "https://github.com/example/alpha",
                            "Documentation": "https://docs.example.com/alpha",
                        },
                        "classifiers": [
                            "License :: OSI Approved :: MIT License",
                            "Programming Language :: Python :: 3",
                        ],
                        "requires_dist": [],
                    },
                    "urls": [
                        {"packagetype": "sdist",       "filename": "alpha-2.5.0.tar.gz",
                         "upload_time_iso_8601": "2026-04-01T12:00:00Z"},
                        {"packagetype": "bdist_wheel", "filename": "alpha-2.5.0-py3-none-any.whl",
                         "upload_time_iso_8601": "2026-04-01T12:01:00Z"},
                    ],
                    "releases": {
                        "2.5.0": [
                            {"yanked": False, "upload_time_iso_8601": "2026-04-01T12:00:00Z"},
                            {"yanked": False, "upload_time_iso_8601": "2026-04-01T12:01:00Z"},
                        ],
                    },
                }, None)
            return (pypi_name, {"info": {"version": "1.0"}, "urls": []}, None)
        monkeypatch.setattr(atlas_mod, "_phase_r_fetch_one", _fake_fetch)

        result = atlas_mod.phase_r_pypi_json_enrich(db)
        assert result.get("fetched") == 3

        row = db.execute(
            "SELECT latest_version, license_raw, license_spdx, "
            "requires_python, repo_url, has_wheel, has_sdist, packaging_shape, "
            "classifiers, wheel_platforms FROM pypi_intelligence "
            "WHERE pypi_name='alpha'"
        ).fetchone()
        assert row["latest_version"] == "2.5.0"
        assert row["license_raw"] == "MIT License"
        assert row["license_spdx"] == "MIT"
        assert row["requires_python"] == ">=3.10"
        assert row["repo_url"] == "https://github.com/example/alpha"
        assert row["has_wheel"] == 1
        assert row["has_sdist"] == 1
        assert row["packaging_shape"] == "pure-python"
        # Classifiers stored as JSON
        assert "License :: OSI Approved :: MIT License" in json.loads(row["classifiers"])
        # Wheel platforms include 'any'
        assert "any" in json.loads(row["wheel_platforms"])
