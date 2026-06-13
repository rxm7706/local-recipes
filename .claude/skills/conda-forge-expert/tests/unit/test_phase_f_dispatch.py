"""Unit tests for Phase F PHASE_F_SOURCE dispatcher."""
from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

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
    conn.execute(
        "INSERT INTO packages (conda_name, relationship, match_source, "
        "match_confidence, latest_status, latest_conda_version, "
        "feedstock_archived, downloads_fetched_at) "
        "VALUES (?, 'has_conda', 'test', 'high', 'active', '2.31.0', 0, 0)",
        ("requests",),
    )
    conn.execute(
        "INSERT INTO packages (conda_name, relationship, match_source, "
        "match_confidence, latest_status, latest_conda_version, "
        "feedstock_archived, downloads_fetched_at) "
        "VALUES (?, 'has_conda', 'test', 'high', 'active', '5.0.0', 0, 0)",
        ("django",),
    )
    conn.commit()
    yield conn
    conn.close()


def _scrub_phase_f_env(monkeypatch):
    for var in ("PHASE_F_SOURCE", "PHASE_F_DISABLED", "PHASE_F_S3_MONTHS", "PHASE_F_LIMIT"):
        monkeypatch.delenv(var, raising=False)


class _FakeResp:
    def __init__(self, body):
        self._body = body if isinstance(body, bytes) else body.encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, *_a, **_kw):
        return self._body


class TestAnacondaApiPath:
    def test_writes_downloads_source_anaconda_api(self, monkeypatch, db, atlas_mod):
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "anaconda-api")

        payload = json.dumps({
            "files": [
                {"version": "2.31.0", "ndownloads": 1000, "upload_time": "2024-01-01T00:00:00+00:00"},
                {"version": "2.32.0", "ndownloads": 500, "upload_time": "2024-06-01T00:00:00+00:00"},
            ]
        })
        django_payload = json.dumps({
            "files": [
                {"version": "5.0.0", "ndownloads": 200, "upload_time": "2024-02-01T00:00:00+00:00"},
            ]
        })

        def fake_urlopen(req, timeout=120):
            if "requests" in req.full_url:
                return _FakeResp(payload)
            return _FakeResp(django_payload)

        monkeypatch.setattr(atlas_mod.urllib.request, "urlopen", fake_urlopen)

        atlas_mod.phase_f_downloads(db)

        rows = list(db.execute(
            "SELECT conda_name, total_downloads, downloads_source FROM packages "
            "ORDER BY conda_name"
        ))
        sources = {r["conda_name"]: r["downloads_source"] for r in rows}
        assert sources == {"django": "anaconda-api", "requests": "anaconda-api"}
        totals = {r["conda_name"]: r["total_downloads"] for r in rows}
        assert totals == {"django": 200, "requests": 1500}

        pvd_sources = set(r[0] for r in db.execute(
            "SELECT DISTINCT source FROM package_version_downloads"
        ))
        assert pvd_sources == {"anaconda-api"}


class TestS3ParquetPath:
    def test_writes_downloads_source_s3_parquet(self, monkeypatch, db, atlas_mod):
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")

        import pyarrow as pa
        agg_table = pa.table({
            "time": ["2026-03", "2026-04", "2026-03", "2026-04", "2026-04"],
            "data_source": ["conda-forge"] * 5,
            "pkg_name": ["requests", "requests", "django", "django", "requests"],
            "pkg_version": ["2.31.0", "2.31.0", "5.0.0", "5.0.0", "2.32.0"],
            "pkg_platform": ["noarch"] * 5,
            "pkg_python": ["3.12"] * 5,
            "counts": [600, 400, 100, 100, 200],
        })

        import _parquet_cache  # type: ignore[import-not-found]
        monkeypatch.setattr(_parquet_cache, "list_s3_parquet_months",
                            lambda: ["2026-03", "2026-04"])
        monkeypatch.setattr(_parquet_cache, "ensure_month",
                            lambda month, current_month=None: Path("/tmp/unused"))
        monkeypatch.setattr(_parquet_cache, "read_filtered",
                            lambda months, pkg_names=None, data_source="conda-forge": agg_table)

        atlas_mod.phase_f_downloads(db)

        rows = list(db.execute(
            "SELECT conda_name, total_downloads, latest_version_downloads, "
            "downloads_source FROM packages ORDER BY conda_name"
        ))
        per_pkg = {r["conda_name"]: r for r in rows}
        assert per_pkg["requests"]["downloads_source"] == "s3-parquet"
        assert per_pkg["requests"]["total_downloads"] == 1200
        assert per_pkg["requests"]["latest_version_downloads"] == 1000
        assert per_pkg["django"]["downloads_source"] == "s3-parquet"
        assert per_pkg["django"]["total_downloads"] == 200
        assert per_pkg["django"]["latest_version_downloads"] == 200

        pvd_sources = set(r[0] for r in db.execute(
            "SELECT DISTINCT source FROM package_version_downloads"
        ))
        assert pvd_sources == {"s3-parquet"}
        pvd_uploads = set(r[0] for r in db.execute(
            "SELECT upload_unix FROM package_version_downloads"
        ))
        assert pvd_uploads == {None}


class TestS3ParquetWave2Metrics:
    """Wave 2 (v8.18.0) extensions: rolling 30/90d, trend slope, lifetime
    months, per-platform + per-python breakdown tables.
    """

    def _fixture_table(
        self,
        *,
        months_count: int = 7,
        include_prev_window: bool = True,
    ):
        """Build a parquet-shaped pyarrow Table with `months_count` of data.

        Layout: months_count consecutive months (newest = '2026-04'),
        single package 'requests' with 100 downloads/month on linux-64
        py 3.12. Adds a second package 'django' with only 1 month of
        data (so it has <6mo history).
        """
        import pyarrow as pa
        # Build months ending at 2026-04 going back in time.
        base = ["2025-10", "2025-11", "2025-12",
                "2026-01", "2026-02", "2026-03", "2026-04"]
        months = base[-months_count:]
        # 'requests' present every month, 100/month
        rows = []
        for m in months:
            rows.append((m, "conda-forge", "requests", "2.31.0",
                         "linux-64", "3.12", 100))
        # 'django' in only the most recent month
        rows.append((months[-1], "conda-forge", "django", "5.0.0",
                     "noarch", "3.11", 50))
        return pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })

    def _patch_parquet(self, monkeypatch, table, months):
        import _parquet_cache  # type: ignore[import-not-found]
        monkeypatch.setattr(_parquet_cache, "list_s3_parquet_months",
                            lambda: months)
        monkeypatch.setattr(_parquet_cache, "ensure_month",
                            lambda month, current_month=None: Path("/tmp/unused"))
        monkeypatch.setattr(_parquet_cache, "read_filtered",
                            lambda months, pkg_names=None,
                            data_source="conda-forge": table)

    def test_populates_30_90_day_and_lifetime_months(
        self, monkeypatch, db, atlas_mod
    ):
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        table = self._fixture_table(months_count=7)
        months = ["2025-10", "2025-11", "2025-12",
                  "2026-01", "2026-02", "2026-03", "2026-04"]
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        row = db.execute(
            "SELECT downloads_30d, downloads_90d, downloads_trend_90d, "
            "first_nonzero_month, last_nonzero_month "
            "FROM packages WHERE conda_name = 'requests'"
        ).fetchone()
        assert row["downloads_30d"] == 100  # last month
        assert row["downloads_90d"] == 300  # last 3 months × 100
        # 7 months: prev = months [-6..-3] = 100×3 = 300, cur = 300 → 0.0
        assert row["downloads_trend_90d"] == 0.0
        assert row["first_nonzero_month"] == "2025-10"
        assert row["last_nonzero_month"] == "2026-04"

    def test_trend_slope_at_exactly_6_months_boundary(
        self, monkeypatch, db, atlas_mod
    ):
        """M6: 6 months of data exactly should NOT trip the < 6 NULL guard.

        Verifies the boundary condition: at exactly len(months_present)==6
        the trend-slope formula must compute (not return NULL). The current
        guard reads `if len(months_present) < 6 or ...`, so 6 must pass.
        This test catches an accidental off-by-one (`<= 6`) regression.
        """
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        # Exactly 6 months — boundary case. prev3 = months [-6:-3], cur3
        # = months [-3:] — both windows have 3 months of fixture data so
        # neither sum is zero and the slope is computable.
        import pyarrow as pa
        months = ["2025-11", "2025-12", "2026-01",
                  "2026-02", "2026-03", "2026-04"]
        rows = []
        for m in months:
            rows.append((m, "conda-forge", "requests", "2.31.0",
                         "linux-64", "3.12", 100))
        rows.append(("2026-04", "conda-forge", "django", "5.0.0",
                     "noarch", "3.11", 1))
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        row = db.execute(
            "SELECT downloads_trend_90d FROM packages "
            "WHERE conda_name = 'requests'"
        ).fetchone()
        # At exactly 6 months and both windows nonzero, slope is well-defined.
        # The < 6 strict-less-than guard must NOT NULL this out.
        assert row["downloads_trend_90d"] is not None, (
            "at exactly 6 months the < 6 NULL guard must not trip "
            "(boundary check against accidental <= 6 off-by-one regression)"
        )

    def test_trend_slope_null_under_6_months_data(
        self, monkeypatch, db, atlas_mod
    ):
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        # Only 4 months of data — under 6mo bar.
        table = self._fixture_table(months_count=4)
        months = ["2026-01", "2026-02", "2026-03", "2026-04"]
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        row = db.execute(
            "SELECT downloads_30d, downloads_90d, downloads_trend_90d "
            "FROM packages WHERE conda_name = 'requests'"
        ).fetchone()
        assert row["downloads_30d"] == 100
        assert row["downloads_90d"] == 300
        assert row["downloads_trend_90d"] is None  # <6 months

    def test_trend_slope_cap_at_plus_ten(self, monkeypatch, db, atlas_mod):
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        # Build a Table where prev_90d=10 and cur_90d=10000 → ratio 999 → cap 10.0
        import pyarrow as pa
        months = ["2025-10", "2025-11", "2025-12",
                  "2026-01", "2026-02", "2026-03", "2026-04"]
        rows = []
        # prev window (months [-6..-3] = 2025-11..2026-01): trickle (10 total)
        rows.append(("2025-11", "conda-forge", "requests", "2.31.0",
                     "linux-64", "3.12", 10))
        # cur window (months [-3:] = 2026-02..2026-04): big traffic
        for m in ("2026-02", "2026-03", "2026-04"):
            rows.append((m, "conda-forge", "requests", "2.31.0",
                         "linux-64", "3.12", 10000))
        # Add 'django' so the eligible_names cardinality matches the db
        rows.append(("2026-04", "conda-forge", "django", "5.0.0",
                     "noarch", "3.11", 1))
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        row = db.execute(
            "SELECT downloads_trend_90d FROM packages "
            "WHERE conda_name = 'requests'"
        ).fetchone()
        # (30000 - 10) / 10 = 2999 → capped at 10.0
        assert row["downloads_trend_90d"] == 10.0

    def test_trend_slope_null_on_prev_window_zero(
        self, monkeypatch, db, atlas_mod
    ):
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        import pyarrow as pa
        # 7 months — but only most-recent 3 have data; prev_90d=0 → NULL guard.
        months = ["2025-10", "2025-11", "2025-12",
                  "2026-01", "2026-02", "2026-03", "2026-04"]
        rows = [(m, "conda-forge", "requests", "2.31.0",
                 "linux-64", "3.12", 100)
                for m in ("2026-02", "2026-03", "2026-04")]
        rows.append(("2026-04", "conda-forge", "django", "5.0.0",
                     "noarch", "3.11", 1))
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        row = db.execute(
            "SELECT downloads_trend_90d FROM packages "
            "WHERE conda_name = 'requests'"
        ).fetchone()
        assert row["downloads_trend_90d"] is None  # prev_90d == 0

    def test_per_platform_breakdown_populated(self, monkeypatch, db, atlas_mod):
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        import pyarrow as pa
        months = ["2026-02", "2026-03", "2026-04"]
        rows = [
            ("2026-02", "conda-forge", "requests", "2.31.0",
             "linux-64",  "3.12", 100),
            ("2026-03", "conda-forge", "requests", "2.31.0",
             "linux-64",  "3.12", 100),
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64",  "3.12", 100),
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "osx-arm64", "3.12", 50),
            ("2026-04", "conda-forge", "django",   "5.0.0",
             "noarch",   "3.11", 1),
        ]
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        rows_out = list(db.execute(
            "SELECT pkg_platform, downloads_90d, downloads_total "
            "FROM package_platform_downloads "
            "WHERE conda_name = 'requests' ORDER BY pkg_platform"
        ))
        by_plat = {r["pkg_platform"]: r for r in rows_out}
        assert "linux-64" in by_plat
        assert by_plat["linux-64"]["downloads_90d"] == 300
        assert by_plat["linux-64"]["downloads_total"] == 300
        assert "osx-arm64" in by_plat
        assert by_plat["osx-arm64"]["downloads_90d"] == 50

    def test_noarch_platform_synthetic_remap(
        self, monkeypatch, db, atlas_mod
    ):
        """pkg_platform='' in the parquet must be remapped to 'noarch'."""
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        import pyarrow as pa
        months = ["2026-04"]
        rows = [
            # Empty-string platform — noarch in parquet
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "", "3.12", 100),
            # Second package keeps the schema happy
            ("2026-04", "conda-forge", "django", "5.0.0",
             "noarch", "3.11", 1),
        ]
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        row = db.execute(
            "SELECT pkg_platform, downloads_total "
            "FROM package_platform_downloads WHERE conda_name = 'requests'"
        ).fetchone()
        assert row is not None
        assert row["pkg_platform"] == "noarch"
        assert row["downloads_total"] == 100

        # And confirm '' never leaks through.
        empties = db.execute(
            "SELECT COUNT(*) FROM package_platform_downloads "
            "WHERE pkg_platform = ''"
        ).fetchone()[0]
        assert empties == 0

    def test_python_regex_filter_drops_dirty_values(
        self, monkeypatch, db, atlas_mod
    ):
        """Dirty pkg_python values that don't match ^(2\\.7|3\\.[0-9]{1,2})$
        must not write rows. Per the spec regex, '7.3' (wrong major) and
        '2.30' (wrong minor for py2) are dropped; '3.81' technically
        matches `3.[0-9]{1,2}` and is kept (regex limitation — spec wording
        mentions '3.81' as ambiguous; the documented regex is what gates).
        Empty string and NULL also dropped.
        """
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        import pyarrow as pa
        months = ["2026-04"]
        rows = [
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "3.12", 100),    # valid → kept
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "7.3",  999),    # dirty (wrong major) → dropped
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "2.30", 999),    # dirty (wrong py2 minor) → dropped
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "2.7", 50),      # valid (py2.7 special case) → kept
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "",  999),       # empty → dropped
            ("2026-04", "conda-forge", "django", "5.0.0",
             "noarch",   "3.11", 1),
        ]
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        # Fetch both columns so we can verify exact count + no cross-contamination.
        rows_out = list(db.execute(
            "SELECT conda_name, pkg_python FROM package_python_downloads"
        ))
        # L2 (a): exactly 2 'requests' rows survive (3.12 + 2.7); 0 'django'
        # python rows because 3.11 is valid AND django was in fixture but
        # we filter to conda_name='requests' below for the value set.
        requests_pythons = {p for (n, p) in rows_out if n == "requests"}
        EXPECTED_COUNT_REQUESTS = 2  # only 3.12 + 2.7 survive
        assert len([p for (n, p) in rows_out if n == "requests"]) == EXPECTED_COUNT_REQUESTS, (
            f"expected exactly {EXPECTED_COUNT_REQUESTS} requests rows, "
            f"got {len([p for (n, p) in rows_out if n == 'requests'])}"
        )
        # Valid values present
        assert "3.12" in requests_pythons
        assert "2.7" in requests_pythons
        # Dirty values dropped
        assert "7.3" not in requests_pythons
        assert "2.30" not in requests_pythons
        assert "" not in requests_pythons
        # L2 (b): no cross-contamination — verify django rows only ever
        # carry pkg_python values from django fixture rows ('3.11'), and
        # none of the 'requests' dirty values leak across.
        django_pythons = {p for (n, p) in rows_out if n == "django"}
        for forbidden in ("7.3", "2.30", "3.12", "2.7", ""):
            assert forbidden not in django_pythons, (
                f"cross-contamination: django row carries pkg_python={forbidden!r}"
            )

    def test_breakdown_tables_idempotent_on_rerun(
        self, monkeypatch, db, atlas_mod
    ):
        """Re-running Phase F replaces rows, doesn't accumulate (INSERT OR REPLACE)."""
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        monkeypatch.setenv("PHASE_F_FORCE_REFRESH", "1")  # bypass TTL on rerun
        import pyarrow as pa
        months = ["2026-04"]
        rows = [
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "3.12", 100),
            ("2026-04", "conda-forge", "django",   "5.0.0",
             "noarch",   "3.11", 1),
        ]
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)
        atlas_mod.phase_f_downloads(db)  # second run

        n_plat = db.execute(
            "SELECT COUNT(*) FROM package_platform_downloads "
            "WHERE conda_name = 'requests' AND pkg_platform = 'linux-64'"
        ).fetchone()[0]
        n_py = db.execute(
            "SELECT COUNT(*) FROM package_python_downloads "
            "WHERE conda_name = 'requests' AND pkg_python = '3.12'"
        ).fetchone()[0]
        # PK = (conda_name, pkg_platform/pkg_python) — must be 1, not 2.
        assert n_plat == 1
        assert n_py == 1

    def test_force_refresh_sentinel_bypasses_ttl(
        self, monkeypatch, db, atlas_mod
    ):
        """`phase_f_force_refresh_pending` meta sentinel bypasses TTL once + clears."""
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        # Set both rows as recently fetched (would normally skip via TTL).
        now = 9_999_999_999  # far-future to defeat any cutoff
        db.execute("UPDATE packages SET downloads_fetched_at = ?", (now,))
        # Stamp the sentinel that the v26 → v27 migration would set.
        db.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("phase_f_force_refresh_pending", "1"),
        )
        db.commit()

        import pyarrow as pa
        months = ["2026-04"]
        rows = [
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "3.12", 100),
            ("2026-04", "conda-forge", "django", "5.0.0",
             "noarch", "3.11", 1),
        ]
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        # The sentinel must have been consumed (deleted).
        leftover = db.execute(
            "SELECT value FROM meta WHERE key='phase_f_force_refresh_pending'"
        ).fetchone()
        assert leftover is None

        # Wave 2 columns populated despite TTL.
        row = db.execute(
            "SELECT downloads_30d FROM packages WHERE conda_name = 'requests'"
        ).fetchone()
        assert row["downloads_30d"] == 100

    def test_phase_f_force_refresh_env_var_alone_bypasses_ttl(
        self, monkeypatch, db, atlas_mod
    ):
        """PHASE_F_FORCE_REFRESH=1 alone (no meta sentinel) bypasses TTL."""
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        monkeypatch.setenv("PHASE_F_FORCE_REFRESH", "1")
        # Set rows as recently fetched so TTL would normally exclude them.
        db.execute("UPDATE packages SET downloads_fetched_at = ?",
                   (9_999_999_999,))
        db.commit()

        import pyarrow as pa
        months = ["2026-04"]
        rows = [
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "3.12", 100),
            ("2026-04", "conda-forge", "django", "5.0.0",
             "noarch",   "3.11", 1),
        ]
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        # env-var path doesn't touch the meta sentinel (which is also absent).
        sentinel = db.execute(
            "SELECT value FROM meta WHERE key='phase_f_force_refresh_pending'"
        ).fetchone()
        assert sentinel is None  # never set in the first place
        # Wave 2 columns populated.
        row = db.execute(
            "SELECT downloads_30d FROM packages WHERE conda_name = 'requests'"
        ).fetchone()
        assert row["downloads_30d"] == 100

    def test_package_with_no_parquet_rows_has_null_wave2_columns(
        self, monkeypatch, db, atlas_mod
    ):
        """Packages eligible but absent from parquet keep NULL Wave 2 cols."""
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "s3-parquet")
        import pyarrow as pa
        months = ["2026-04"]
        # 'requests' present in parquet; 'django' eligible but missing.
        rows = [
            ("2026-04", "conda-forge", "requests", "2.31.0",
             "linux-64", "3.12", 100),
        ]
        table = pa.table({
            "time":         [r[0] for r in rows],
            "data_source":  [r[1] for r in rows],
            "pkg_name":     [r[2] for r in rows],
            "pkg_version":  [r[3] for r in rows],
            "pkg_platform": [r[4] for r in rows],
            "pkg_python":   [r[5] for r in rows],
            "counts":       [r[6] for r in rows],
        })
        self._patch_parquet(monkeypatch, table, months)
        atlas_mod.phase_f_downloads(db)

        django_row = db.execute(
            "SELECT total_downloads, downloads_30d, downloads_90d, "
            "downloads_trend_90d, first_nonzero_month, last_nonzero_month, "
            "downloads_source "
            "FROM packages WHERE conda_name = 'django'"
        ).fetchone()
        # total_downloads collapses to 0 (existing behavior — no data).
        assert django_row["total_downloads"] == 0
        # downloads_source stamped 's3-parquet' (source-of-truth tag).
        assert django_row["downloads_source"] == "s3-parquet"
        # All Wave 2 columns NULL.
        assert django_row["downloads_30d"] is None
        assert django_row["downloads_90d"] is None
        assert django_row["downloads_trend_90d"] is None
        assert django_row["first_nonzero_month"] is None
        assert django_row["last_nonzero_month"] is None
        # No breakdown rows for the missing package.
        assert db.execute(
            "SELECT COUNT(*) FROM package_platform_downloads "
            "WHERE conda_name = 'django'"
        ).fetchone()[0] == 0

    def test_api_path_leaves_wave2_columns_null(self, monkeypatch, db, atlas_mod):
        """downloads_source='anaconda-api' rows must have NULL Wave 2 columns."""
        _scrub_phase_f_env(monkeypatch)
        monkeypatch.setenv("PHASE_F_SOURCE", "anaconda-api")

        import json as _json
        payload = _json.dumps({
            "files": [
                {"version": "2.31.0", "ndownloads": 100,
                 "upload_time": "2024-01-01T00:00:00+00:00"},
            ]
        })
        django_payload = _json.dumps({"files": []})

        def fake_urlopen(req, timeout=120):
            return _FakeResp(payload if "requests" in req.full_url
                             else django_payload)
        monkeypatch.setattr(atlas_mod.urllib.request, "urlopen", fake_urlopen)
        atlas_mod.phase_f_downloads(db)

        row = db.execute(
            "SELECT downloads_30d, downloads_90d, downloads_trend_90d, "
            "first_nonzero_month, last_nonzero_month, downloads_source "
            "FROM packages WHERE conda_name = 'requests'"
        ).fetchone()
        assert row["downloads_source"] == "anaconda-api"
        assert row["downloads_30d"] is None
        assert row["downloads_90d"] is None
        assert row["downloads_trend_90d"] is None
        assert row["first_nonzero_month"] is None
        assert row["last_nonzero_month"] is None

        # And no rows in the breakdown tables for API-path packages.
        n_plat = db.execute(
            "SELECT COUNT(*) FROM package_platform_downloads "
            "WHERE conda_name = 'requests'"
        ).fetchone()[0]
        n_py = db.execute(
            "SELECT COUNT(*) FROM package_python_downloads "
            "WHERE conda_name = 'requests'"
        ).fetchone()[0]
        assert n_plat == 0
        assert n_py == 0


class TestAutoModeProbeFails:
    def test_probe_failure_falls_through_to_s3(self, monkeypatch, db, atlas_mod):
        _scrub_phase_f_env(monkeypatch)

        def fake_urlopen(req, timeout=10):
            raise urllib.error.URLError("Network is unreachable")

        monkeypatch.setattr(atlas_mod.urllib.request, "urlopen", fake_urlopen)

        api_calls = MagicMock(side_effect=AssertionError("API path must not run on probe failure"))
        monkeypatch.setattr(atlas_mod, "_phase_f_fetch_one", api_calls)

        import pyarrow as pa
        empty_table = pa.table({
            "time": ["2026-04"],
            "data_source": ["conda-forge"],
            "pkg_name": ["requests"],
            "pkg_version": ["2.31.0"],
            "pkg_platform": ["noarch"],
            "pkg_python": ["3.12"],
            "counts": [42],
        })

        import _parquet_cache  # type: ignore[import-not-found]
        monkeypatch.setattr(_parquet_cache, "list_s3_parquet_months", lambda: ["2026-04"])
        monkeypatch.setattr(_parquet_cache, "ensure_month",
                            lambda month, current_month=None: Path("/tmp/unused"))
        monkeypatch.setattr(_parquet_cache, "read_filtered",
                            lambda months, pkg_names=None, data_source="conda-forge": empty_table)

        result = atlas_mod.phase_f_downloads(db)
        assert result["source"] == "s3-parquet"

        sources = set(r[0] for r in db.execute(
            "SELECT DISTINCT downloads_source FROM packages WHERE downloads_source IS NOT NULL"
        ))
        assert sources == {"s3-parquet"}


# ── _anaconda_api_base — env-var override chain ────────────────────────────

class TestAnacondaApiBase:
    def test_default_is_public_host(self, atlas_mod, monkeypatch):
        monkeypatch.delenv("ANACONDA_API_BASE_URL", raising=False)
        monkeypatch.delenv("ANACONDA_API_BASE", raising=False)
        assert atlas_mod._anaconda_api_base() == "https://api.anaconda.org"

    def test_url_env_var_takes_precedence(self, atlas_mod, monkeypatch):
        monkeypatch.setenv("ANACONDA_API_BASE_URL", "https://jfrog/api/anaconda")
        monkeypatch.setenv("ANACONDA_API_BASE", "https://legacy-host")
        assert atlas_mod._anaconda_api_base() == "https://jfrog/api/anaconda"

    def test_legacy_env_var_used_when_new_unset(self, atlas_mod, monkeypatch):
        monkeypatch.delenv("ANACONDA_API_BASE_URL", raising=False)
        monkeypatch.setenv("ANACONDA_API_BASE", "https://legacy-host")
        assert atlas_mod._anaconda_api_base() == "https://legacy-host"

    def test_trailing_slash_stripped(self, atlas_mod, monkeypatch):
        monkeypatch.setenv("ANACONDA_API_BASE_URL", "https://jfrog/api/anaconda/")
        assert atlas_mod._anaconda_api_base() == "https://jfrog/api/anaconda"


# ── _parse_retry_after — RFC 9110 Retry-After parsing ──────────────────────

class TestParseRetryAfter:
    def test_empty_returns_fallback(self, atlas_mod):
        assert atlas_mod._parse_retry_after(None, fallback=2.5) == 2.5
        assert atlas_mod._parse_retry_after("", fallback=2.5) == 2.5

    def test_integer_seconds(self, atlas_mod):
        assert atlas_mod._parse_retry_after("30", fallback=999.0) == 30.0

    def test_integer_seconds_whitespace_tolerant(self, atlas_mod):
        assert atlas_mod._parse_retry_after("  15  ", fallback=999.0) == 15.0

    def test_negative_seconds_clamped_to_zero(self, atlas_mod):
        # A server that says "-5" is buggy; clamp to 0 rather than retry in the past.
        assert atlas_mod._parse_retry_after("-5", fallback=999.0) == 0.0

    def test_unparseable_falls_back(self, atlas_mod):
        assert atlas_mod._parse_retry_after("not-a-number", fallback=4.0) == 4.0

    def test_capped_at_60_seconds(self, atlas_mod):
        # A 3600s Retry-After would stall a worker for an hour. We bail and
        # let TTL re-pick the row next run.
        assert atlas_mod._parse_retry_after("3600", fallback=999.0) == 60.0

    def test_http_date_form_far_future_caps(self, atlas_mod):
        # HTTP-date form: a far-future date computes to a delta > 60, so it caps.
        out = atlas_mod._parse_retry_after("Wed, 12 Nov 2099 14:00:00 GMT", fallback=999.0)
        assert out == 60.0

    def test_fallback_negative_also_clamped(self, atlas_mod):
        assert atlas_mod._parse_retry_after(None, fallback=-1.0) == 0.0
