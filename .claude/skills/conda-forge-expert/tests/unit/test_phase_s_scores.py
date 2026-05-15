"""Phase S — computed conda_forge_readiness + recommended_template.

Pure SQL UPDATE chain. Reads pypi_intelligence columns populated by
Phases O/P/Q/R and writes Tier-4 scores. The readiness formula is a
0-100 composite weighted across 6 components per the spec.
"""
from __future__ import annotations

import importlib.util
import sys
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


@pytest.fixture
def db(tmp_path, atlas_mod):
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    yield conn
    conn.close()


def _seed_intelligence(conn, pypi_name: str, **kwargs) -> None:
    """Insert a pypi_intelligence row with the given columns."""
    cols = ["pypi_name"]
    vals = [pypi_name]
    for k, v in kwargs.items():
        cols.append(k)
        vals.append(v)
    placeholders = ",".join(["?"] * len(vals))
    conn.execute(
        f"INSERT INTO pypi_intelligence ({','.join(cols)}) VALUES ({placeholders})",
        vals,
    )
    conn.commit()


class TestPhaseS_ReadinessFormula:
    """conda_forge_readiness = sum of 6 weighted components (max 100)."""

    def test_max_readiness_when_all_components_present(self, db, atlas_mod):
        now = int(time.time())
        _seed_intelligence(
            db, "max-pkg",
            json_fetched_at=now,
            license_spdx="MIT",
            requires_python=">=3.10",
            repo_url="https://github.com/example/max-pkg",
            latest_upload_at=now - 30 * 86400,  # 30 days ago
            has_sdist=1,
            packaging_shape="pure-python",
        )
        atlas_mod.phase_s_computed_scores(db)
        row = db.execute(
            "SELECT conda_forge_readiness, recommended_template FROM pypi_intelligence "
            "WHERE pypi_name='max-pkg'"
        ).fetchone()
        # 25 + 20 + 15 + 15 + 10 + 15 = 100
        assert row["conda_forge_readiness"] == 100
        assert row["recommended_template"] == "templates/python/recipe.yaml"

    def test_min_readiness_when_nothing_present(self, db, atlas_mod):
        now = int(time.time())
        _seed_intelligence(
            db, "min-pkg",
            json_fetched_at=now,
            # No license, no repo, no recent release, no sdist,
            # unknown packaging_shape, but requires_python=NULL → 20 pts
            requires_python=None,
            packaging_shape="unknown",
        )
        atlas_mod.phase_s_computed_scores(db)
        row = db.execute(
            "SELECT conda_forge_readiness, recommended_template FROM pypi_intelligence "
            "WHERE pypi_name='min-pkg'"
        ).fetchone()
        # 0 + 20 + 0 + 0 + 0 + 0 = 20 (only the "unspecified requires_python = ok" bonus)
        assert row["conda_forge_readiness"] == 20
        assert row["recommended_template"] is None

    def test_c_extension_gets_half_packaging_score(self, db, atlas_mod):
        now = int(time.time())
        _seed_intelligence(
            db, "cext-pkg",
            json_fetched_at=now,
            license_spdx="MIT",
            requires_python=">=3.10",
            repo_url="https://github.com/example/cext-pkg",
            latest_upload_at=now,
            has_sdist=1,
            packaging_shape="c-extension",
        )
        atlas_mod.phase_s_computed_scores(db)
        row = db.execute(
            "SELECT conda_forge_readiness, recommended_template FROM pypi_intelligence "
            "WHERE pypi_name='cext-pkg'"
        ).fetchone()
        # 25 + 20 + 15 + 15 + 10 + 7 = 92 (c-extension = half = 7)
        assert row["conda_forge_readiness"] == 92
        assert row["recommended_template"] == "templates/python/compiled-recipe.yaml"

    def test_skips_rows_with_no_phase_r_data(self, db, atlas_mod):
        # json_fetched_at IS NULL → score stays NULL (Phase R never ran on this row)
        _seed_intelligence(
            db, "unscored-pkg",
            license_spdx="MIT",
            packaging_shape="pure-python",
        )
        atlas_mod.phase_s_computed_scores(db)
        row = db.execute(
            "SELECT conda_forge_readiness FROM pypi_intelligence "
            "WHERE pypi_name='unscored-pkg'"
        ).fetchone()
        assert row["conda_forge_readiness"] is None

    def test_non_osi_license_scores_zero_for_license_component(self, db, atlas_mod):
        now = int(time.time())
        _seed_intelligence(
            db, "weird-license-pkg",
            json_fetched_at=now,
            license_spdx="WTFPL",   # not in OSI-approved subset
            requires_python=">=3.10",
            packaging_shape="pure-python",
        )
        atlas_mod.phase_s_computed_scores(db)
        row = db.execute(
            "SELECT conda_forge_readiness FROM pypi_intelligence "
            "WHERE pypi_name='weird-license-pkg'"
        ).fetchone()
        # 0 + 20 + 0 + 0 + 0 + 15 = 35
        assert row["conda_forge_readiness"] == 35


class TestPhaseS_RecommendedTemplate:
    """Template path mapping from packaging_shape."""

    @pytest.mark.parametrize("shape,expected", [
        ("pure-python",  "templates/python/recipe.yaml"),
        ("rust-pyo3",    "templates/python/maturin-recipe.yaml"),
        ("cython",       "templates/python/compiled-recipe.yaml"),
        ("c-extension",  "templates/python/compiled-recipe.yaml"),
        ("fortran",      None),
        ("multi-output", None),
        ("unknown",      None),
    ])
    def test_template_mapping(self, db, atlas_mod, shape, expected):
        now = int(time.time())
        _seed_intelligence(
            db, f"{shape}-pkg",
            json_fetched_at=now,
            packaging_shape=shape,
        )
        atlas_mod.phase_s_computed_scores(db)
        row = db.execute(
            "SELECT recommended_template FROM pypi_intelligence "
            "WHERE pypi_name=?", (f"{shape}-pkg",)
        ).fetchone()
        assert row["recommended_template"] == expected


class TestPhaseS_Idempotency:
    """Re-running Phase S overwrites with the same values; no double-counting."""

    def test_rerun_is_idempotent(self, db, atlas_mod):
        now = int(time.time())
        _seed_intelligence(
            db, "idem-pkg",
            json_fetched_at=now,
            license_spdx="MIT",
            requires_python=">=3.10",
            packaging_shape="pure-python",
        )
        atlas_mod.phase_s_computed_scores(db)
        score_a = db.execute(
            "SELECT conda_forge_readiness FROM pypi_intelligence WHERE pypi_name='idem-pkg'"
        ).fetchone()["conda_forge_readiness"]
        atlas_mod.phase_s_computed_scores(db)
        score_b = db.execute(
            "SELECT conda_forge_readiness FROM pypi_intelligence WHERE pypi_name='idem-pkg'"
        ).fetchone()["conda_forge_readiness"]
        assert score_a == score_b


class TestPhaseS_DisableEnv:
    def test_disabled_env_skips(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_S_DISABLED", "1")
        result = atlas_mod.phase_s_computed_scores(db)
        assert result.get("skipped") is True
