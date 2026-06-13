"""Unit tests for `channel_split` CLI (v8.19.0 Phase F+ Wave 3).

Coverage matrix per spec § Story 5:
  - Single-package mode renders per-channel breakdown + migration-opportunity
    footer when defaults share > 10%.
  - --defaults-share-min N --top M filter + ranking by absolute defaults 90d.
  - --migration-checklist emits markdown checkbox lines.
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
_SCRIPT = _SCRIPTS_DIR / "channel_split.py"


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
def seeded_db(tmp_path, atlas_mod):
    """v28 atlas DB with per-channel data for three packages.

    matplotlib: 80% conda-forge, 17.5% defaults (migration target), pypi_only
                (no conda-forge feedstock yet — EC-9b "open feedstock" branch).
    numpy: 95% conda-forge, 5% defaults (below 10% floor)
    pandas: 60% conda-forge, 25% defaults (migration target), both_same_name
            (already on conda-forge — EC-9b "rerender + outreach" branch).
    """
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    for conda, feedstock, maintainer, relationship in (
        ("matplotlib", "matplotlib", "alice", "pypi_only"),
        ("numpy",      "numpy",      "alice", "both_same_name"),
        ("pandas",     "pandas",     "alice", "both_same_name"),
    ):
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, feedstock_name, relationship, match_source, "
            " match_confidence, latest_status, feedstock_archived) "
            "VALUES (?, ?, ?, 'test', 'high', 'active', 0)",
            (conda, feedstock, relationship),
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
    chan_rows = [
        # (pkg, channel, d90, total)
        ("matplotlib", "conda-forge", 8000, 80000),
        ("matplotlib", "defaults",    1750, 17500),
        ("matplotlib", "bioconda",     250,  2500),
        ("numpy",      "conda-forge", 9500, 95000),
        ("numpy",      "defaults",     500,  5000),
        ("pandas",     "conda-forge", 6000, 60000),
        ("pandas",     "defaults",    2500, 25000),
        ("pandas",     "pytorch",     1500, 15000),
    ]
    for pkg, ch, d90, total in chan_rows:
        conn.execute(
            "INSERT INTO package_channel_downloads "
            "(conda_name, data_source, downloads_90d, downloads_total, "
            " fetched_at) VALUES (?, ?, ?, ?, 100)",
            (pkg, ch, d90, total),
        )
    conn.commit()
    conn.close()
    return db_path


def _run(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    runner = (
        "import sys, importlib.util, pathlib; "
        f"sys.argv = ['channel-split'] + {list(args)!r}; "
        f"spec = importlib.util.spec_from_file_location('cs', {str(_SCRIPT)!r}); "
        "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
        f"mod.DB_PATH = pathlib.Path({str(db_path)!r}); "
        "raise SystemExit(mod.main())"
    )
    return subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True, text=True,
    )


class TestChannelSplit:
    def test_single_package_markdown_with_migration_footer(self, seeded_db):
        r = _run(seeded_db, "matplotlib")
        assert r.returncode == 0, r.stderr
        assert "conda-forge" in r.stdout
        assert "defaults" in r.stdout
        # matplotlib has 17.5% defaults → migration opportunity footer.
        assert "Migration opportunity" in r.stdout

    def test_single_package_no_migration_footer_under_floor(self, seeded_db):
        r = _run(seeded_db, "numpy")
        assert r.returncode == 0, r.stderr
        # numpy's defaults share = 5% < 10% → no migration opportunity.
        assert "Migration opportunity" not in r.stdout
        assert "no migration signal" in r.stdout

    def test_single_package_json_shape(self, seeded_db):
        r = _run(seeded_db, "matplotlib", "--format", "json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        channels = {row["data_source"] for row in data}
        assert channels == {"conda-forge", "defaults", "bioconda"}

    def test_top_n_filter_by_defaults_share(self, seeded_db):
        r = _run(seeded_db, "--defaults-share-min", "10.0", "--top", "5",
                 "--format", "json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        # matplotlib + pandas pass the 10% floor; numpy doesn't.
        names = [d["conda_name"] for d in data]
        assert "matplotlib" in names
        assert "pandas" in names
        assert "numpy" not in names
        # Sorted DESC by absolute defaults_90d — pandas (2500) before matplotlib (1750).
        assert names.index("pandas") < names.index("matplotlib")

    def test_top_n_csv_format(self, seeded_db):
        r = _run(seeded_db, "--defaults-share-min", "10.0", "--top", "10",
                 "--format", "csv")
        assert r.returncode == 0
        reader = csv.reader(io.StringIO(r.stdout))
        rows = list(reader)
        assert len(rows) >= 2  # header + 2 (matplotlib + pandas)
        # Header carries the rank-mode field order.
        assert "defaults_90d" in rows[0]

    def test_migration_checklist_emits_checkbox_lines(self, seeded_db):
        r = _run(seeded_db, "--migration-checklist", "--maintainer", "alice")
        assert r.returncode == 0
        # matplotlib + pandas should both appear (both above default 10% floor).
        assert "matplotlib" in r.stdout
        assert "pandas" in r.stdout
        # numpy (5% defaults) should NOT appear.
        assert "numpy" not in r.stdout
        # EC-9b: matplotlib is `relationship='pypi_only'` — message is the
        # "open conda-forge feedstock" call to action.
        matplotlib_line = next(
            ln for ln in r.stdout.splitlines() if "matplotlib" in ln
        )
        assert "Open conda-forge feedstock for" in matplotlib_line
        # EC-9b: pandas is `relationship='both_same_name'` — feedstock
        # already exists; message is the "rerender + outreach" call to action.
        pandas_line = next(
            ln for ln in r.stdout.splitlines() if "pandas" in ln
        )
        assert "Bump rerender + outreach" in pandas_line
        assert "Open conda-forge feedstock for" not in pandas_line

    def test_migration_checklist_requires_maintainer(self, seeded_db):
        r = _run(seeded_db, "--migration-checklist")
        assert r.returncode == 2
        assert "--maintainer" in r.stderr

    def test_read_only_no_network_imports(self):
        src = _SCRIPT.read_text()
        assert "import urllib" not in src
        assert "from urllib" not in src
        assert "import requests" not in src
        assert "from requests" not in src
