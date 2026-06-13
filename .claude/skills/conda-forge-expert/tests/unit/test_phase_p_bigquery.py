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


class TestPhaseP_CostGuardrails:
    """v8.14.3 hot-patch — partition pruning via _PARTITIONDATE literal
    dates, dry-run preflight, maximum_bytes_billed hard cap,
    job_timeout_ms wall-clock cap."""

    def test_uses_partition_date_not_timestamp(self, atlas_mod):
        """The v8.1.0 form used CURRENT_TIMESTAMP() against the `timestamp`
        column, which occasionally degraded planner pruning. The hot-patch
        switches to literal _PARTITIONDATE bounds."""
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "_PARTITIONDATE" in src, (
            "Phase P query must filter by _PARTITIONDATE for guaranteed pruning"
        )
        # The v8.1.0 SQL form had `TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ... DAY)`.
        # Reject only that specific SQL pattern so docstrings can still
        # mention the legacy form as historical context.
        assert "TIMESTAMP_SUB(CURRENT_TIMESTAMP()" not in src, (
            "v8.1.0's TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL ...) SQL must not survive"
        )

    def test_dry_run_preflight_present(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "dry_run=True" in src, (
            "Phase P must dry-run the query first to estimate cost"
        )
        assert "total_bytes_processed" in src, (
            "Dry-run preflight must read total_bytes_processed to compute cost"
        )

    def test_maximum_bytes_billed_set(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "maximum_bytes_billed" in src, (
            "Phase P real query must pass maximum_bytes_billed as a hard "
            "server-side cap to prevent runaway scans"
        )

    def test_job_timeout_ms_set(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "job_timeout_ms" in src, (
            "Phase P real query must pass job_timeout_ms to prevent zombie "
            "jobs charging slot time on flat-rate billing accounts"
        )

    def test_first_pull_and_refresh_caps_distinguished(self, atlas_mod):
        """First-pull (empty pypi_downloads_daily) uses a wider budget
        than a refresh — code must read both env vars."""
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "PHASE_P_MAX_COST_USD" in src
        assert "PHASE_P_MAX_COST_FIRST_PULL_USD" in src
        assert "MAX(download_date)" in src, (
            "First-pull detection must read pypi_downloads_daily's max date"
        )

    def test_dryrun_above_cap_aborts(self, db, atlas_mod, monkeypatch):
        """When the dry-run estimate exceeds the cap, Phase P returns
        skipped with cost in the reason — the real query is NOT submitted."""
        import types

        # Build a mock `google.cloud.bigquery` module surface that returns
        # a huge dry-run estimate so the cap aborts before the real query.
        fake_bigquery = types.SimpleNamespace()

        class _FakeJobConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        fake_bigquery.QueryJobConfig = _FakeJobConfig

        class _FakeDryJob:
            # 100 TB scanned → ~$625 at default $6.25/TB; blows past $0.01 cap
            total_bytes_processed = 100 * (10 ** 12)

        real_query_calls = []

        class _FakeClient:
            def __init__(self, project=None):
                self.project = project

            def query(self, query, job_config=None):
                if job_config and getattr(job_config, "kwargs", {}).get("dry_run"):
                    return _FakeDryJob()
                # Should NEVER reach here when dry-run aborts
                real_query_calls.append(query)
                raise AssertionError(
                    "real query was submitted after dry-run abort — "
                    "cap enforcement broken"
                )

        fake_bigquery.Client = _FakeClient

        fake_cloud = types.ModuleType("google.cloud")
        fake_cloud.bigquery = fake_bigquery  # type: ignore[attr-defined]
        fake_google = types.ModuleType("google")
        fake_google.cloud = fake_cloud  # type: ignore[attr-defined]

        monkeypatch.setitem(sys.modules, "google", fake_google)
        monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
        monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)

        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.setenv("PHASE_P_MAX_COST_USD", "0.01")
        monkeypatch.setenv("PHASE_P_MAX_COST_FIRST_PULL_USD", "0.01")

        result = atlas_mod.phase_p_pypi_downloads(db)

        assert result.get("skipped") is True
        assert "exceeds" in result.get("reason", "")
        assert result.get("estimated_usd") is not None
        assert result.get("estimated_usd") > 0.01
        assert real_query_calls == [], (
            "real query was submitted despite dry-run estimate exceeding cap"
        )


class TestPhaseP_IncrementalArchitecture:
    """v8.15.0 — per-day per-package storage in pypi_downloads_daily, mode
    selection (first-pull/incremental/gap-revert/no-op), GC pruning,
    force-first-pull recovery, deprecated tunable warning."""

    def test_query_groups_by_pypi_name_and_partition_date(self, atlas_mod):
        """v8.15.0 SQL emits per-day per-package rows instead of
        pre-aggregated 30d/90d sums."""
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "GROUP BY pypi_name, _PARTITIONDATE" in src, (
            "Phase P v8.15.0 must aggregate per (pypi_name, _PARTITIONDATE), "
            "not just pypi_name"
        )

    def test_inserts_into_pypi_downloads_daily(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "INSERT OR IGNORE INTO pypi_downloads_daily" in src, (
            "Phase P must INSERT OR IGNORE per-day rows into pypi_downloads_daily"
        )

    def test_recomputes_pypi_intelligence_from_local_table(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "FROM pypi_downloads_daily" in src and "downloads_30d" in src, (
            "Phase P must recompute pypi_intelligence.downloads_30d/90d "
            "from the local pypi_downloads_daily table via SQL aggregation"
        )
        assert "'bigquery-incremental'" in src, (
            "downloads_source must be tagged 'bigquery-incremental'"
        )

    def test_gc_prunes_retain_days(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert "PHASE_P_RETAIN_DAYS" in src
        assert "DELETE FROM pypi_downloads_daily WHERE download_date" in src, (
            "GC must DELETE pypi_downloads_daily rows older than the retain cutoff"
        )

    def test_no_new_partitions_short_circuits(self, db, atlas_mod, monkeypatch):
        """When pypi_downloads_daily.MAX(download_date) is today-1,
        no new BQ partitions to query → early skip with no client.query()."""
        import datetime
        import types

        # Populate pypi_downloads_daily with rows up to today-1 — so the
        # window is empty and Phase P must short-circuit before ever
        # building a BQ client.
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        db.execute(
            "INSERT INTO pypi_downloads_daily (pypi_name, download_date, downloads) "
            "VALUES (?, ?, ?)",
            ("numpy", yesterday, 1000),
        )
        db.commit()

        # If client.query is invoked we want to know — should never reach.
        client_init_called = []

        class _FakeClient:
            def __init__(self, project=None):
                client_init_called.append(project)

            def query(self, *args, **kwargs):
                raise AssertionError("client.query called despite no new partitions")

        fake_bigquery = types.SimpleNamespace(
            Client=_FakeClient,
            QueryJobConfig=lambda **kw: types.SimpleNamespace(**kw),
        )
        fake_cloud = types.ModuleType("google.cloud")
        fake_cloud.bigquery = fake_bigquery  # type: ignore[attr-defined]
        fake_google = types.ModuleType("google")
        fake_google.cloud = fake_cloud  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "google", fake_google)
        monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
        monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)

        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.delenv("PHASE_P_FORCE_FIRST_PULL", raising=False)

        result = atlas_mod.phase_p_pypi_downloads(db)

        assert result.get("skipped") is True
        assert "no new partitions" in result.get("reason", "")
        assert result.get("mode") == "incremental"

    def test_gap_above_90d_reverts_to_first_pull(self, db, atlas_mod, monkeypatch):
        """When MAX(download_date) is 120 days ago, mode flips to
        first-pull (uses the larger cap)."""
        import datetime
        import types

        old_date = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
        db.execute(
            "INSERT INTO pypi_downloads_daily (pypi_name, download_date, downloads) "
            "VALUES (?, ?, ?)",
            ("ancient", old_date, 5),
        )
        db.commit()

        # Dry-run estimate > $0.01 cap forces an abort that surfaces `mode`.
        class _FakeDryJob:
            total_bytes_processed = 5 * (10 ** 12)

        class _FakeClient:
            def __init__(self, project=None):
                pass

            def query(self, query, job_config=None):
                if job_config and job_config.dry_run:
                    return _FakeDryJob()
                raise AssertionError("real query submitted despite abort")

        fake_bigquery = types.SimpleNamespace(
            Client=_FakeClient,
            QueryJobConfig=lambda **kw: types.SimpleNamespace(**kw),
        )
        fake_cloud = types.ModuleType("google.cloud")
        fake_cloud.bigquery = fake_bigquery  # type: ignore[attr-defined]
        fake_google = types.ModuleType("google")
        fake_google.cloud = fake_cloud  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "google", fake_google)
        monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
        monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)

        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.delenv("PHASE_P_FORCE_FIRST_PULL", raising=False)
        # Both caps tiny so abort always fires, surfaces mode label.
        monkeypatch.setenv("PHASE_P_MAX_COST_USD", "0.01")
        monkeypatch.setenv("PHASE_P_MAX_COST_FIRST_PULL_USD", "0.01")

        result = atlas_mod.phase_p_pypi_downloads(db)

        # Gap > 90 → first-pull-after-gap; aborts via cap, mode label preserved.
        assert result.get("skipped") is True
        assert result.get("mode") == "first-pull-after-gap"

    def test_force_first_pull_wipes_daily_table(self, db, atlas_mod, monkeypatch):
        """PHASE_P_FORCE_FIRST_PULL=1 deletes existing pypi_downloads_daily
        rows before mode detection runs (which then sees an empty table)."""
        import datetime
        import types

        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        db.execute(
            "INSERT INTO pypi_downloads_daily (pypi_name, download_date, downloads) "
            "VALUES (?, ?, ?)",
            ("numpy", yesterday, 1000),
        )
        db.commit()
        assert db.execute(
            "SELECT COUNT(*) FROM pypi_downloads_daily"
        ).fetchone()[0] == 1

        class _FakeDryJob:
            total_bytes_processed = 5 * (10 ** 12)

        class _FakeClient:
            def __init__(self, project=None):
                pass

            def query(self, query, job_config=None):
                if job_config and job_config.dry_run:
                    return _FakeDryJob()
                raise AssertionError("real query submitted despite abort")

        fake_bigquery = types.SimpleNamespace(
            Client=_FakeClient,
            QueryJobConfig=lambda **kw: types.SimpleNamespace(**kw),
        )
        fake_cloud = types.ModuleType("google.cloud")
        fake_cloud.bigquery = fake_bigquery  # type: ignore[attr-defined]
        fake_google = types.ModuleType("google")
        fake_google.cloud = fake_cloud  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "google", fake_google)
        monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
        monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)

        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.setenv("PHASE_P_FORCE_FIRST_PULL", "1")
        monkeypatch.setenv("PHASE_P_MAX_COST_USD", "0.01")
        monkeypatch.setenv("PHASE_P_MAX_COST_FIRST_PULL_USD", "0.01")

        result = atlas_mod.phase_p_pypi_downloads(db)

        # FORCE_FIRST_PULL wiped the table; mode is now first-pull (not
        # first-pull-after-gap, because the table is empty).
        assert result.get("mode") == "first-pull"
        # Verify the wipe actually deleted the row.
        assert db.execute(
            "SELECT COUNT(*) FROM pypi_downloads_daily"
        ).fetchone()[0] == 0

    def test_deprecated_window_days_warns(self, db, atlas_mod, monkeypatch, capsys):
        """PHASE_P_BQ_WINDOW_DAYS was declared in v8.1.0 spec but never
        consumed; v8.15.0 logs a deprecation warning when set."""
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.setenv("PHASE_P_BQ_WINDOW_DAYS", "60")
        # No bigquery library installed → skips after the warning.
        result = atlas_mod.phase_p_pypi_downloads(db)
        captured = capsys.readouterr()
        assert "PHASE_P_BQ_WINDOW_DAYS is deprecated" in captured.out
        # Result still skips because bigquery isn't installed (or installed
        # but creds missing) — but the warning must print regardless.
        assert result.get("skipped") is True
