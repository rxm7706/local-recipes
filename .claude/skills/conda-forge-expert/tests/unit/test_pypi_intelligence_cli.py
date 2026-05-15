"""pypi-intelligence CLI — filter chain SQL composition + JSON output."""
from __future__ import annotations

import importlib.util
import json
import subprocess
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


@pytest.fixture(scope="module")
def pypi_intel_mod():
    return _load("pypi_intelligence")


@pytest.fixture
def populated_db(tmp_path, atlas_mod):
    """v22 atlas with a small set of candidates spanning the filter surface."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    now = int(time.time())
    # Seed pypi_universe + pypi_intelligence rows
    candidates = [
        # (pypi_name, last_serial, conda_name_or_None, activity_band, ds30, in_bioconda,
        #  license_spdx, requires_python, packaging_shape, readiness)
        ("high-score-pkg",    1000, None, "hot",     50_000, 0, "MIT",        ">=3.10", "pure-python", 100),
        ("medium-score-pkg",   900, None, "warm",    10_000, 1, "Apache-2.0", ">=3.10", "c-extension",  70),
        ("low-score-pkg",      800, None, "cold",     1_000, 0, None,         None,     "unknown",      20),
        ("already-on-cf",      700, "already-on-cf", "hot", 100_000, 0, "MIT", ">=3.10", "pure-python", 100),
        ("dormant-pkg",        600, None, "dormant",    100, 0, "MIT",        ">=3.10", "pure-python", 100),
    ]
    for (name, serial, conda_name, band, ds30, in_bio,
         license_spdx, req_py, shape, score) in candidates:
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) VALUES (?, ?, ?)",
            (name, serial, 0),
        )
        if conda_name is not None:
            conn.execute(
                "INSERT INTO packages (conda_name, pypi_name, latest_status, "
                "relationship, match_source, match_confidence) "
                "VALUES (?, ?, 'active', 'both_same_name', 'test', 'high')",
                (conda_name, name),
            )
        conn.execute(
            "INSERT INTO pypi_intelligence "
            "(pypi_name, activity_band, downloads_30d, in_bioconda, "
            " license_spdx, requires_python, packaging_shape, "
            " conda_forge_readiness, json_fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, band, ds30, in_bio, license_spdx, req_py, shape, score, now),
        )
    conn.commit()
    yield db_path
    conn.close()


def _run_cli(db_path: Path, *args: str) -> tuple[int, str, str]:
    cli = _SCRIPTS_DIR / "pypi_intelligence.py"
    cmd = [sys.executable, str(cli), "--db", str(db_path), "--json", *args]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return p.returncode, p.stdout, p.stderr


class TestCLIBasicQueries:
    def test_default_returns_pypi_only_sorted_by_score(self, populated_db):
        rc, out, err = _run_cli(populated_db, "--not-in-conda-forge", "--limit", "10")
        assert rc == 0, err
        rows = json.loads(out)
        # 4 pypi-only candidates (excluding 'already-on-cf')
        names = [r["pypi_name"] for r in rows]
        assert "already-on-cf" not in names
        # Default sort = score DESC
        scores = [r["conda_forge_readiness"] for r in rows]
        assert scores == sorted(scores, reverse=True)

    def test_score_min_filter(self, populated_db):
        rc, out, _err = _run_cli(populated_db, "--not-in-conda-forge", "--score-min", "80")
        assert rc == 0
        rows = json.loads(out)
        for r in rows:
            assert r["conda_forge_readiness"] >= 80

    def test_activity_filter(self, populated_db):
        rc, out, _err = _run_cli(populated_db, "--activity", "hot")
        assert rc == 0
        rows = json.loads(out)
        for r in rows:
            assert r["activity_band"] == "hot"

    def test_in_bioconda_filter(self, populated_db):
        rc, out, _err = _run_cli(populated_db, "--in-bioconda")
        assert rc == 0
        rows = json.loads(out)
        # Only medium-score-pkg has in_bioconda=1
        names = [r["pypi_name"] for r in rows]
        assert "medium-score-pkg" in names
        assert "high-score-pkg" not in names

    def test_min_downloads_filter(self, populated_db):
        rc, out, _err = _run_cli(populated_db, "--min-downloads", "20000")
        assert rc == 0
        rows = json.loads(out)
        for r in rows:
            assert r["downloads_30d"] >= 20000


class TestCLISortBy:
    def test_sort_by_downloads(self, populated_db):
        rc, out, _err = _run_cli(populated_db, "--sort-by", "downloads", "--limit", "10")
        assert rc == 0
        rows = json.loads(out)
        # Filter to rows with non-NULL downloads_30d
        with_dl = [r for r in rows if r.get("downloads_30d") is not None]
        scores = [r["downloads_30d"] for r in with_dl]
        assert scores == sorted(scores, reverse=True)

    def test_sort_by_serial(self, populated_db):
        rc, out, _err = _run_cli(populated_db, "--sort-by", "serial", "--limit", "10")
        assert rc == 0
        rows = json.loads(out)
        serials = [r["last_serial"] for r in rows]
        assert serials == sorted(serials, reverse=True)


class TestCLIComposedFilters:
    def test_high_readiness_pypi_only(self, populated_db):
        """The flagship admin query: pypi-only, score >=70, sorted by score."""
        rc, out, _err = _run_cli(
            populated_db,
            "--not-in-conda-forge", "--score-min", "70", "--limit", "10",
        )
        assert rc == 0
        rows = json.loads(out)
        names = [r["pypi_name"] for r in rows]
        assert "high-score-pkg" in names
        assert "medium-score-pkg" in names
        assert "low-score-pkg" not in names         # score 20 < 70
        assert "already-on-cf" not in names         # has conda_name


class TestCLIMissingDB:
    def test_missing_db_returns_nonzero(self, tmp_path):
        ghost = tmp_path / "nope.db"
        cli = _SCRIPTS_DIR / "pypi_intelligence.py"
        p = subprocess.run(
            [sys.executable, str(cli), "--db", str(ghost), "--limit", "1"],
            capture_output=True, text=True, timeout=5,
        )
        assert p.returncode == 2
        assert "DB not found" in p.stderr
