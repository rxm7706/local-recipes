"""Unit tests for Phase E `python_min` extraction (v8.19.0 Phase F+ Wave 3).

Covers:
  - `_extract_declared_python_min` regex helper across v0 + v1 syntaxes.
  - Phase E UPDATE writes the declared value when present.
  - Phase E leaves `python_min` NULL when neither override form matches.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tarfile
import time
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


class TestExtractDeclaredPythonMin:
    """Regex behavior across the v0 + v1 override forms verified against
    a 5,001-sample survey of cf-graph node_attrs (2026-06-13)."""

    def test_v1_context_override_double_quoted(self, atlas_mod):
        raw = (
            "schema_version: 1\n\n"
            "context:\n"
            "  name: pyiron_atomistics\n"
            "  python_min: \"3.11\"\n"
            "\n"
            "package:\n"
        )
        assert atlas_mod._extract_declared_python_min(raw) == "3.11"

    def test_v1_context_override_single_quoted(self, atlas_mod):
        raw = "context:\n  python_min: '3.10'\n"
        assert atlas_mod._extract_declared_python_min(raw) == "3.10"

    def test_v0_jinja_set_override(self, atlas_mod):
        raw = (
            "{% set name = 'brukerapi' %}\n"
            "{% set python_min = \"3.10\" %}\n\n"
            "package:\n"
        )
        assert atlas_mod._extract_declared_python_min(raw) == "3.10"

    def test_no_override_returns_none(self, atlas_mod):
        # The vast majority of recipes reference but don't declare python_min.
        raw = (
            "context:\n  name: requests\n\n"
            "requirements:\n  host:\n    - python ${{ python_min }}.*\n"
            "  run:\n    - python >=${{ python_min }}\n"
        )
        assert atlas_mod._extract_declared_python_min(raw) is None

    def test_empty_input_returns_none(self, atlas_mod):
        assert atlas_mod._extract_declared_python_min("") is None
        assert atlas_mod._extract_declared_python_min(None) is None  # type: ignore[arg-type]


class TestPhaseEPythonMinWrite:
    """Phase E populates `packages.python_min` from a mocked cf-graph tarball."""

    def _build_tarball(self, tmp_path: Path, node_attrs: dict[str, dict]) -> Path:
        """Build a tiny cf-graph-shaped tarball with the given node_attrs files."""
        cache = tmp_path / "cf-graph-countyfair.tar.gz"
        with tarfile.open(cache, "w:gz") as tf:
            for feedstock, payload in node_attrs.items():
                # Mirror cf-graph layout: node_attrs/<l>/<l>/<l>/<l>/<l>/<feedstock>.json
                # Path content is only matched by `/node_attrs/` substring +
                # `.json` suffix in Phase E so any nested layout works.
                bytes_payload = json.dumps(payload).encode()
                info = tarfile.TarInfo(
                    name=f"cf-graph-master/node_attrs/x/y/z/{feedstock}.json"
                )
                info.size = len(bytes_payload)
                info.mtime = int(time.time())
                tf.addfile(info, io.BytesIO(bytes_payload))
        return cache

    @pytest.fixture
    def populated_db(self, tmp_path, atlas_mod, monkeypatch):
        # Build tarball with two feedstocks, one declaring python_min, one not.
        node_attrs = {
            "with-override": {
                "meta_yaml": {
                    "about": {"summary": "test", "home": "http://x"},
                    "package": {"name": "with-override"},
                },
                "raw_meta_yaml": (
                    "schema_version: 1\n\n"
                    "context:\n"
                    "  name: with-override\n"
                    "  python_min: \"3.11\"\n"
                ),
            },
            "no-override": {
                "meta_yaml": {
                    "about": {"summary": "test", "home": "http://x"},
                    "package": {"name": "no-override"},
                },
                "raw_meta_yaml": (
                    "context:\n  name: no-override\n\n"
                    "requirements:\n  host:\n"
                    "    - python ${{ python_min }}.*\n"
                ),
            },
        }
        # Point Phase E's DATA_DIR at tmp_path so it finds our tarball.
        monkeypatch.setattr(atlas_mod, "DATA_DIR", tmp_path)
        self._build_tarball(tmp_path, node_attrs)

        db_path = tmp_path / "cf_atlas.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        # Two feedstocks with matching conda_name == feedstock_name.
        for conda in ("with-override", "no-override"):
            conn.execute(
                "INSERT INTO packages "
                "(conda_name, feedstock_name, relationship, match_source, "
                " match_confidence, latest_status, feedstock_archived) "
                "VALUES (?, ?, 'has_conda', 'test', 'high', 'active', 0)",
                (conda, conda),
            )
        conn.commit()

        # Enable Phase E and bypass network re-fetch (cache exists with TTL).
        monkeypatch.setenv("PHASE_E_ENABLED", "1")
        monkeypatch.setenv("ATLAS_CFGRAPH_TTL_DAYS", "365")  # always-fresh cache
        return conn

    def test_phase_e_writes_python_min_from_v1_override(self, populated_db, atlas_mod):
        atlas_mod.phase_e_enrichment(populated_db)
        row = populated_db.execute(
            "SELECT python_min FROM packages WHERE conda_name = 'with-override'"
        ).fetchone()
        assert row["python_min"] == "3.11"

    def test_phase_e_leaves_python_min_null_when_not_declared(
        self, populated_db, atlas_mod
    ):
        atlas_mod.phase_e_enrichment(populated_db)
        row = populated_db.execute(
            "SELECT python_min FROM packages WHERE conda_name = 'no-override'"
        ).fetchone()
        assert row["python_min"] is None
