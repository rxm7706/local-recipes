"""Unit tests for `platform_breakdown` CLI (v8.19.0 Phase F+ Wave 3).

Coverage matrix per spec § Story 3:
  - Single-package mode renders all platforms ordered DESC by 90d.
  - Top-N mode ranks across packages on a single platform.
  - Feedstock-roundup mode groups by feedstock for a maintainer.
  - --format json shape per spec I/O matrix.
  - --format csv writes header + data rows.
  - FR-1 read-only contract: no urllib/requests in the script source.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
_SCRIPT = _SCRIPTS_DIR / "platform_breakdown.py"


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
def seeded_db(tmp_path, atlas_mod, monkeypatch):
    """Build a v28 atlas DB with platform breakdown data for two packages."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    # Three feedstocks owned by 'alice'; one by 'bob'.
    for conda, feedstock, maintainer in (
        ("numpy",  "numpy",  "alice"),
        ("pandas", "pandas", "alice"),
        ("scipy",  "scipy",  "bob"),
    ):
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, feedstock_name, relationship, match_source, "
            " match_confidence, latest_status, feedstock_archived) "
            "VALUES (?, ?, 'has_conda', 'test', 'high', 'active', 0)",
            (conda, feedstock),
        )
        conn.execute("INSERT OR IGNORE INTO maintainers(handle) VALUES (?)",
                     (maintainer,))
        mid = conn.execute(
            "SELECT id FROM maintainers WHERE handle = ?", (maintainer,)
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO package_maintainers(conda_name, maintainer_id) "
            "VALUES (?, ?)",
            (conda, mid),
        )
    # Platform breakdown data — fetched_at = 100 (arbitrary).
    plat_rows = [
        ("numpy",  "linux-64",    900, 9000),
        ("numpy",  "osx-arm64",   100, 1000),
        ("numpy",  "win-64",       50,  500),
        ("pandas", "linux-64",    400, 4000),
        ("pandas", "osx-arm64",   600, 6000),
        ("scipy",  "linux-64",    700, 7000),
        ("scipy",  "win-64",      300, 3000),
    ]
    for conda, plat, d90, total in plat_rows:
        conn.execute(
            "INSERT INTO package_platform_downloads "
            "(conda_name, pkg_platform, downloads_90d, downloads_total, "
            " fetched_at) VALUES (?, ?, ?, ?, 100)",
            (conda, plat, d90, total),
        )
    conn.commit()
    conn.close()
    # Point the CLI at our test DB.
    monkeypatch.setenv("HOME", str(tmp_path))
    return db_path


def _run(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke the CLI with the DB_PATH module-level constant overridden."""
    # The CLI computes DB_PATH from its own __file__; we patch by writing a
    # tiny wrapper that monkeypatches platform_breakdown.DB_PATH before
    # calling main().
    runner = (
        "import sys, importlib.util, pathlib; "
        f"sys.argv = ['platform-breakdown'] + {list(args)!r}; "
        f"spec = importlib.util.spec_from_file_location('pb', {str(_SCRIPT)!r}); "
        "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
        f"mod.DB_PATH = pathlib.Path({str(db_path)!r}); "
        "raise SystemExit(mod.main())"
    )
    return subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True, text=True,
    )


class TestPlatformBreakdown:
    def test_single_package_markdown(self, seeded_db):
        r = _run(seeded_db, "numpy")
        assert r.returncode == 0, r.stderr
        assert "numpy" in r.stdout
        assert "linux-64" in r.stdout
        assert "osx-arm64" in r.stdout
        # Total row exists.
        assert "Total" in r.stdout
        # Largest platform appears before smaller (ordered DESC).
        assert r.stdout.index("linux-64") < r.stdout.index("win-64")

    def test_single_package_json_shape(self, seeded_db):
        r = _run(seeded_db, "numpy", "--format", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) == 3  # numpy has 3 platforms
        # Each record has the documented schema.
        for row in data:
            assert {"conda_name", "feedstock_name", "pkg_platform",
                    "downloads_90d", "downloads_total", "share_pct"
                    }.issubset(row.keys())
        # Shares sum to ~100%.
        total = sum(r["share_pct"] for r in data)
        assert 99.5 <= total <= 100.5

    def test_top_n_by_platform(self, seeded_db):
        r = _run(seeded_db, "--top", "5", "--platform", "linux-64",
                 "--format", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        # 3 packages have linux-64 data.
        names = [d["conda_name"] for d in data]
        assert names == ["numpy", "scipy", "pandas"], (
            "should rank DESC by 90d downloads on the chosen platform"
        )

    def test_top_requires_platform(self, seeded_db):
        r = _run(seeded_db, "--top", "5")
        assert r.returncode == 2
        assert "--platform" in r.stderr

    def test_feedstock_roundup_maintainer(self, seeded_db):
        r = _run(seeded_db, "--feedstock-roundup", "--maintainer", "alice",
                 "--format", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        feedstocks = {d["feedstock_name"] for d in data}
        # alice owns numpy + pandas (3 + 2 = 5 platform rows).
        assert feedstocks == {"numpy", "pandas"}
        assert len(data) == 5

    def test_csv_format(self, seeded_db):
        r = _run(seeded_db, "numpy", "--format", "csv")
        assert r.returncode == 0, r.stderr
        reader = csv.reader(io.StringIO(r.stdout))
        rows = list(reader)
        # Header + 3 data rows.
        assert len(rows) == 4
        assert rows[0][0] == "conda_name"
        assert rows[0][2] == "pkg_platform"

    def test_read_only_no_network_imports(self):
        """FR-1: the script source must not import urllib or requests."""
        src = _SCRIPT.read_text()
        assert "import urllib" not in src
        assert "from urllib" not in src
        assert "import requests" not in src
        assert "from requests" not in src
