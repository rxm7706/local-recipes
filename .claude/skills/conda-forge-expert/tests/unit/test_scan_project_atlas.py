"""Unit tests for scan_project's cf_atlas readers — AUD-CFE-007.

`enrich_with_atlas` issued one SELECT per dependency and never closed its
connection; `fetch_atlas_vuln_summary` batched but also leaked the connection
and could exceed SQLite's host-parameter limit on a large lock file. Both now go
through `_atlas_connect_ro` + `_atlas_select_in`.
"""
from __future__ import annotations

import sqlite3

import pytest

COLUMNS = """
    conda_name TEXT, pypi_name TEXT, latest_conda_version TEXT,
    conda_license TEXT, feedstock_archived INT, latest_status TEXT,
    vuln_total INT, vuln_critical_affecting_current INT,
    vuln_high_affecting_current INT, vuln_kev_affecting_current INT,
    vdb_scanned_at INT
"""

ROWS = [
    # conda_name, pypi_name, version, license, archived, status,
    # total, crit, high, kev, scanned_at
    ("numpy", "numpy", "2.5.1", "BSD-3-Clause", 0, "active", 3, 1, 2, 0, 1700000000),
    ("python-dateutil", "python-dateutil", "2.9.0", "Apache-2.0", 0, "active",
     0, 0, 0, 0, 1700000001),
    ("langfuse-python", "langfuse", "4.7.1", "MIT", 0, "active", 1, 0, 1, 1,
     1700000002),
    ("oldpkg", "oldpkg", "0.1", "MIT", 1, "archived", 0, 0, 0, 0, None),
]


@pytest.fixture(scope="module")
def scan(load_module):
    return load_module("scan_project.py")


@pytest.fixture
def atlas(scan, monkeypatch, tmp_path):
    """A synthetic cf_atlas.db wired into the module + a statement counter."""
    db = tmp_path / "cf_atlas.db"
    conn = sqlite3.connect(db)
    conn.execute(f"CREATE TABLE packages ({COLUMNS})")
    conn.executemany(
        "INSERT INTO packages VALUES (?,?,?,?,?,?,?,?,?,?,?)", ROWS
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(scan, "ATLAS_DB", db)

    statements: list[str] = []
    opened: list[sqlite3.Connection] = []
    real_connect = scan._atlas_connect_ro

    def _counting_connect():
        c = real_connect()
        c.set_trace_callback(statements.append)
        opened.append(c)
        return c

    monkeypatch.setattr(scan, "_atlas_connect_ro", _counting_connect)
    return {"db": db, "statements": statements, "opened": opened}


def dep(scan, name, ecosystem="conda"):
    return scan.Dep(name=name, version=None, ecosystem=ecosystem,
                    manifest="test.yml")


class TestEnrichWithAtlas:
    def test_returns_records_keyed_by_ecosystem_and_name(self, scan, atlas):
        deps = [dep(scan, "numpy"), dep(scan, "langfuse", "pypi")]
        out = scan.enrich_with_atlas(deps)
        assert set(out) == {"conda:numpy", "pypi:langfuse"}
        assert out["conda:numpy"]["latest_conda_version"] == "2.5.1"
        # The G10 divergence: pypi `langfuse` -> conda `langfuse-python`.
        assert out["pypi:langfuse"]["conda_name"] == "langfuse-python"

    def test_unknown_names_are_absent_not_error(self, scan, atlas):
        out = scan.enrich_with_atlas([dep(scan, "definitely-not-a-package")])
        assert out == {}

    def test_non_conda_pypi_ecosystems_ignored(self, scan, atlas):
        deps = [dep(scan, "left-pad", "npm"), dep(scan, "curl", "apt")]
        assert scan.enrich_with_atlas(deps) == {}
        # No ecosystem to query for -> no connection opened at all.
        assert atlas["opened"] == []

    def test_one_query_per_ecosystem_not_per_dependency(self, scan, atlas):
        """The finding: 4 conda deps used to mean 4 SELECTs."""
        deps = [dep(scan, n) for n in
                ("numpy", "python-dateutil", "langfuse-python", "oldpkg")]
        out = scan.enrich_with_atlas(deps)
        assert len(out) == 4
        selects = [s for s in atlas["statements"] if "SELECT" in s.upper()]
        assert len(selects) == 1, selects

    def test_two_queries_when_both_ecosystems_present(self, scan, atlas):
        deps = [dep(scan, "numpy"), dep(scan, "langfuse", "pypi")]
        scan.enrich_with_atlas(deps)
        selects = [s for s in atlas["statements"] if "SELECT" in s.upper()]
        assert len(selects) == 2, selects

    def test_duplicate_deps_are_deduped(self, scan, atlas):
        deps = [dep(scan, "numpy")] * 5
        out = scan.enrich_with_atlas(deps)
        assert list(out) == ["conda:numpy"]
        selects = [s for s in atlas["statements"] if "SELECT" in s.upper()]
        assert len(selects) == 1

    def test_connection_is_closed(self, scan, atlas):
        scan.enrich_with_atlas([dep(scan, "numpy")])
        assert len(atlas["opened"]) == 1
        with pytest.raises(sqlite3.ProgrammingError):
            atlas["opened"][0].execute("SELECT 1")

    def test_connection_is_read_only(self, scan, atlas):
        """A read path should not be able to mutate the atlas."""
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn = scan._atlas_connect_ro()
            try:
                conn.execute("DELETE FROM packages")
            finally:
                conn.close()

    def test_chunks_past_the_host_parameter_limit(self, scan, atlas):
        """A big lock file must not blow SQLITE_MAX_VARIABLE_NUMBER."""
        many = [dep(scan, f"pkg-{i}") for i in range(scan._ATLAS_IN_CHUNK * 2 + 7)]
        many.append(dep(scan, "numpy"))
        out = scan.enrich_with_atlas(many)  # must not raise
        assert list(out) == ["conda:numpy"]
        selects = [s for s in atlas["statements"] if "SELECT" in s.upper()]
        assert len(selects) == 3, f"expected 3 chunks, got {len(selects)}"

    def test_missing_db_returns_empty(self, scan, monkeypatch, tmp_path):
        monkeypatch.setattr(scan, "ATLAS_DB", tmp_path / "nope.db")
        assert scan.enrich_with_atlas([dep(scan, "numpy")]) == {}

    def test_corrupt_db_degrades_instead_of_crashing_the_scan(
        self, scan, monkeypatch, tmp_path
    ):
        bad = tmp_path / "cf_atlas.db"
        bad.write_bytes(b"not a database")
        monkeypatch.setattr(scan, "ATLAS_DB", bad)
        assert scan.enrich_with_atlas([dep(scan, "numpy")]) == {}


class TestFetchAtlasVulnSummary:
    def test_returns_counts_keyed_by_conda_name(self, scan, atlas):
        deps = [dep(scan, "numpy"), dep(scan, "langfuse-python")]
        out = scan.fetch_atlas_vuln_summary(deps, {})
        assert out["numpy"] == {
            "total": 3, "critical_affecting_current": 1,
            "high_affecting_current": 2, "kev_affecting_current": 0,
            "scanned_at": 1700000000,
        }
        assert out["langfuse-python"]["kev_affecting_current"] == 1

    def test_never_scanned_rows_are_skipped(self, scan, atlas):
        """A NULL vdb_scanned_at means Phase G has no cached answer."""
        out = scan.fetch_atlas_vuln_summary([dep(scan, "oldpkg")], {})
        assert out == {}

    def test_connection_is_closed(self, scan, atlas):
        scan.fetch_atlas_vuln_summary([dep(scan, "numpy")], {})
        assert len(atlas["opened"]) == 1
        with pytest.raises(sqlite3.ProgrammingError):
            atlas["opened"][0].execute("SELECT 1")

    def test_chunks_past_the_host_parameter_limit(self, scan, atlas):
        many = [dep(scan, f"pkg-{i}") for i in range(scan._ATLAS_IN_CHUNK + 1)]
        many.append(dep(scan, "numpy"))
        out = scan.fetch_atlas_vuln_summary(many, {})  # must not raise
        assert list(out) == ["numpy"]

    def test_no_relevant_deps_opens_nothing(self, scan, atlas):
        assert scan.fetch_atlas_vuln_summary([dep(scan, "left-pad", "npm")], {}) == {}
        assert atlas["opened"] == []

    def test_missing_db_returns_empty(self, scan, monkeypatch, tmp_path):
        monkeypatch.setattr(scan, "ATLAS_DB", tmp_path / "nope.db")
        assert scan.fetch_atlas_vuln_summary([dep(scan, "numpy")], {}) == {}
