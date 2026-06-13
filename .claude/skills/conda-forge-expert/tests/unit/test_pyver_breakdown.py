"""Unit tests for `pyver_breakdown` CLI (v8.19.0 Phase F+ Wave 3).

Coverage matrix per spec § Story 4:
  - Single-package mode renders per-Python breakdown + empirical floor footer.
  - --policy-check correctly categorizes bump-safe / aligned / aggressive.
  - --policy-check honors --threshold-pct.
  - --policy-check sorts bump-safe → aligned → aggressive (spec Q1=A).
  - NULL `python_min` rows surface as `unknown` with stderr warning.
  - All packages unknown → non-zero exit (spec I/O matrix line 47).
  - --format markdown|json|csv.
  - FR-1 read-only contract.
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
_SCRIPT = _SCRIPTS_DIR / "pyver_breakdown.py"


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


def _now() -> int:
    """A 'now' value that's recent enough to count as fresh under the
    7-day TTL the CLI checks against."""
    import time as _t
    return int(_t.time())


@pytest.fixture
def seeded_db(tmp_path, atlas_mod):
    """v28 atlas DB with per-Python data + declared python_min."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    now = _now()

    # Four packages with distinct policy-check categories:
    #   numpy: declared 3.10, empirical 3.11 → BUMP-SAFE
    #   pandas: declared 3.10, empirical 3.10 → ALIGNED
    #   niche-pkg: declared 3.11, empirical 3.10 → AGGRESSIVE
    #   nopy-pkg: declared NULL → UNKNOWN
    seed = [
        # (conda_name, declared_python_min, [(py, d90, total), ...])
        ("numpy",     "3.10", [("3.12", 9000), ("3.11", 1000), ("3.10", 5)]),  # floor=3.11 at 10% / 5 < 2%
        ("pandas",    "3.10", [("3.12", 5000), ("3.11", 2000), ("3.10", 500)]),  # floor=3.10
        ("niche-pkg", "3.11", [("3.12", 8000), ("3.11", 2000), ("3.10", 500)]),  # floor=3.10
        ("nopy-pkg",  None,   [("3.12", 1000), ("3.11", 500)]),
    ]
    for conda, declared, pys in seed:
        conn.execute(
            "INSERT INTO packages (conda_name, feedstock_name, "
            " relationship, match_source, match_confidence, latest_status, "
            " feedstock_archived, python_min) "
            "VALUES (?, ?, 'has_conda', 'test', 'high', 'active', 0, ?)",
            (conda, conda, declared),
        )
        conn.execute("INSERT OR IGNORE INTO maintainers(handle) VALUES (?)",
                     ("alice",))
        mid = conn.execute(
            "SELECT id FROM maintainers WHERE handle = ?", ("alice",)
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO package_maintainers(conda_name, maintainer_id) "
            "VALUES (?, ?)",
            (conda, mid),
        )
        for py, d90 in pys:
            conn.execute(
                "INSERT INTO package_python_downloads "
                "(conda_name, pkg_python, downloads_90d, downloads_total, "
                " fetched_at) VALUES (?, ?, ?, ?, ?)",
                (conda, py, d90, d90 * 10, now),
            )
    conn.commit()
    conn.close()
    return db_path


def _run(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    runner = (
        "import sys, importlib.util, pathlib; "
        f"sys.argv = ['pyver-breakdown'] + {list(args)!r}; "
        f"spec = importlib.util.spec_from_file_location('pv', {str(_SCRIPT)!r}); "
        "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
        f"mod.DB_PATH = pathlib.Path({str(db_path)!r}); "
        "raise SystemExit(mod.main())"
    )
    return subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True, text=True,
    )


class TestPyverBreakdown:
    def test_single_package_markdown_with_floor_footer(self, seeded_db):
        r = _run(seeded_db, "numpy")
        assert r.returncode == 0, r.stderr
        assert "3.12" in r.stdout
        assert "3.10" in r.stdout
        # Empirical floor at 2% threshold: 3.10 is below 2% on numpy
        # (5 out of 10005 ≈ 0.05%); 3.11 at 1000/10005 = 10% is the floor.
        assert "Empirical python_min floor" in r.stdout

    def test_single_package_json_shape(self, seeded_db):
        r = _run(seeded_db, "numpy", "--format", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert all("pkg_python" in row for row in data)
        # 3 Python versions for numpy.
        assert len(data) == 3

    def test_policy_check_categorizes_correctly(self, seeded_db):
        r = _run(seeded_db, "--policy-check", "--maintainer", "alice",
                 "--format", "json")
        assert r.returncode == 0, r.stderr
        rows = json.loads(r.stdout)
        by_name = {r["conda_name"]: r for r in rows}

        # numpy: declared 3.10, empirical (>=2%) 3.11 → bump-safe
        assert by_name["numpy"]["status"] == "bump-safe"
        # pandas: declared 3.10, empirical 3.10 → aligned
        assert by_name["pandas"]["status"] == "aligned"
        # niche-pkg: declared 3.11, empirical 3.10 → aggressive
        assert by_name["niche-pkg"]["status"] == "aggressive"
        # nopy-pkg: no declared → unknown
        assert by_name["nopy-pkg"]["status"] == "unknown"

    def test_policy_check_sort_order_bump_safe_first(self, seeded_db):
        r = _run(seeded_db, "--policy-check", "--maintainer", "alice",
                 "--format", "json")
        assert r.returncode == 0
        rows = json.loads(r.stdout)
        names_in_order = [r["conda_name"] for r in rows]
        # Output order must be: bump-safe → aligned → aggressive → unknown.
        # numpy = bump-safe, pandas = aligned, niche-pkg = aggressive, nopy = unknown.
        assert names_in_order.index("numpy") < names_in_order.index("pandas")
        assert names_in_order.index("pandas") < names_in_order.index("niche-pkg")
        assert names_in_order.index("niche-pkg") < names_in_order.index("nopy-pkg")

    def test_policy_check_threshold_pct(self, seeded_db):
        """With threshold-pct=15.0, niche-pkg's 3.10 (500/10500 ≈ 4.8%) and
        3.11 (2000/10500 ≈ 19%) are filtered such that floor=3.11 (the
        smallest survivor). niche-pkg declared 3.11, so status flips to
        ALIGNED (was AGGRESSIVE at threshold 2%).
        """
        r = _run(seeded_db, "--policy-check", "niche-pkg",
                 "--threshold-pct", "15.0",
                 "--format", "json")
        assert r.returncode == 0
        rows = json.loads(r.stdout)
        assert rows[0]["status"] == "aligned"

    def test_policy_check_emits_unknown_warning_on_stderr(self, seeded_db):
        r = _run(seeded_db, "--policy-check", "nopy-pkg", "--format", "json")
        assert r.returncode == 1  # all unknown → non-zero exit
        # Stderr warning about packages missing declared python_min.
        assert "no declared python_min" in r.stderr.lower() or (
            "unknown" in r.stderr.lower()
        )

    def test_csv_format(self, seeded_db):
        r = _run(seeded_db, "numpy", "--format", "csv")
        assert r.returncode == 0, r.stderr
        reader = csv.reader(io.StringIO(r.stdout))
        rows = list(reader)
        # Header + 3 data rows.
        assert len(rows) == 4
        assert rows[0][0] == "conda_name"

    def test_read_only_no_network_imports(self):
        src = _SCRIPT.read_text()
        assert "import urllib" not in src
        assert "from urllib" not in src
        assert "import requests" not in src
        assert "from requests" not in src
