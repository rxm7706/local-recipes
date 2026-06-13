"""Phase P — ClickHouse clickpy backend (v8.16.0+).

The default Phase P source is `clickhouse` (free public mirror at
sql-clickhouse.clickhouse.com); BigQuery is opt-in via
`PHASE_P_SOURCE=bigquery`. Tests here exercise the ClickHouse path
with a mocked HTTP layer (no network during tests).
"""
from __future__ import annotations

import importlib.util
import sys
import urllib.request
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


class TestDispatcher:
    """v8.16.0 dispatcher — PHASE_P_SOURCE selects backend."""

    def test_default_source_is_clickhouse(self, atlas_mod):
        """When PHASE_P_SOURCE is unset, default routes to ClickHouse."""
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert 'os.environ.get("PHASE_P_SOURCE", "clickhouse")' in src, (
            "Dispatcher must default to clickhouse when PHASE_P_SOURCE unset"
        )
        assert "_phase_p_clickhouse(conn)" in src, (
            "Dispatcher must route clickhouse → _phase_p_clickhouse"
        )
        assert "_phase_p_bigquery(conn)" in src, (
            "Dispatcher must route bigquery → _phase_p_bigquery"
        )

    def test_disabled_takes_priority_over_source(self, db, atlas_mod, monkeypatch):
        """PHASE_P_DISABLED=1 short-circuits before reading PHASE_P_SOURCE."""
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.setenv("PHASE_P_SOURCE", "clickhouse")
        monkeypatch.setenv("PHASE_P_DISABLED", "1")
        result = atlas_mod.phase_p_pypi_downloads(db)
        assert result.get("skipped") is True
        assert "PHASE_P_DISABLED" in result.get("reason", "")

    def test_unknown_source_skips(self, db, atlas_mod, monkeypatch):
        """PHASE_P_SOURCE=foo (unrecognized) → skip with clear reason."""
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.setenv("PHASE_P_SOURCE", "redis")
        result = atlas_mod.phase_p_pypi_downloads(db)
        assert result.get("skipped") is True
        reason = result.get("reason", "")
        assert "PHASE_P_SOURCE" in reason
        assert "clickhouse" in reason
        assert "bigquery" in reason

    def test_source_is_case_insensitive(self, db, atlas_mod, monkeypatch):
        """PHASE_P_SOURCE=CLICKHOUSE routes the same as 'clickhouse'."""
        import inspect
        src = inspect.getsource(atlas_mod.phase_p_pypi_downloads)
        assert ".lower()" in src, (
            "Dispatcher must normalize PHASE_P_SOURCE case via .lower()"
        )


class TestClickHouseQueryShape:
    """The SQL the ClickHouse backend submits to clickpy."""

    def test_query_uses_top_n_with_order_by(self, atlas_mod):
        """v8.16.0 ships as a single top-N query (ORDER BY d90 DESC LIMIT)
        because ClickHouse Play's ~1,000-row cap + aggressive rate-limit on
        sustained bursts makes bucketed full-coverage refresh impractical."""
        import inspect
        src = inspect.getsource(atlas_mod._phase_p_clickhouse)
        assert "ORDER BY d90 DESC LIMIT" in src, (
            "ClickHouse query must use ORDER BY d90 DESC LIMIT N for top-N"
        )
        assert "PHASE_P_CH_LIMIT" in src, (
            "Top-N must be tunable via PHASE_P_CH_LIMIT"
        )

    def test_query_targets_pre_aggregated_table(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod._phase_p_clickhouse)
        assert "pypi.pypi_downloads_per_day" in src, (
            "ClickHouse query must hit the pre-aggregated per-day table, "
            "not the raw pypi.pypi (which is too big for the play user's cap)"
        )

    def test_query_emits_d30_and_d90(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod._phase_p_clickhouse)
        # sumIf for 30-day window; sum for 90-day window
        assert "sumIf(count, date >= today() - 30)" in src
        assert "sum(count)" in src
        assert "WHERE date >= today() - 90" in src

    def test_query_uses_jsoneachrow(self, atlas_mod):
        import inspect
        src = inspect.getsource(atlas_mod._phase_p_clickhouse)
        assert "FORMAT JSONEachRow" in src, (
            "Response must be JSONEachRow so we can stream-parse line-by-line"
        )


class TestClickHouseHTTPMock:
    """End-to-end behavioural test against a mocked ClickHouse HTTP layer."""

    def _install_fake_urlopen(self, monkeypatch, response_body: str):
        """Patch urllib.request.urlopen to return the given body for every call."""
        calls = []

        class _FakeResp:
            def __init__(self, body: bytes):
                self._body = body
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return self._body

        def fake_urlopen(req, timeout=None):
            calls.append({
                "url": req.full_url,
                "data": req.data.decode("utf-8") if req.data else "",
                "timeout": timeout,
            })
            return _FakeResp(response_body.encode("utf-8"))

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        return calls

    def test_clickhouse_default_path_upserts_rows(self, db, atlas_mod, monkeypatch):
        """Single top-N query; verify upsert behavior + PEP 503 canonicalization."""
        body = (
            '{"project":"numpy","d30":"100","d90":"300"}\n'
            '{"project":"pandas","d30":"50","d90":"150"}\n'
            '{"project":"Tree_Sitter","d30":"10","d90":"30"}\n'
        )
        calls = self._install_fake_urlopen(monkeypatch, body)
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.setenv("PHASE_P_CH_LIMIT", "100")

        result = atlas_mod.phase_p_pypi_downloads(db)

        # Single top-N query (not bucketed).
        assert len(calls) == 1
        c = calls[0]
        assert c["url"] == "https://sql-clickhouse.clickhouse.com/?user=play"
        assert "pypi.pypi_downloads_per_day" in c["data"]
        assert "ORDER BY d90 DESC LIMIT 100" in c["data"]

        # Result accounting.
        assert result.get("source") == "clickhouse-clickpy"
        assert result.get("rows_upserted") == 3
        assert result.get("top_n") == 100
        # Single fetch — no row aggregation across calls; values match sample.
        row = db.execute(
            "SELECT pypi_name, downloads_30d, downloads_90d, downloads_source "
            "FROM pypi_intelligence WHERE pypi_name='numpy'"
        ).fetchone()
        assert row is not None
        assert row[1] == 100
        assert row[2] == 300
        assert row[3] == "clickhouse-clickpy"
        # PEP 503 collapse: 'Tree_Sitter' → 'tree-sitter'
        row_ts = db.execute(
            "SELECT pypi_name, downloads_30d FROM pypi_intelligence "
            "WHERE pypi_name='tree-sitter'"
        ).fetchone()
        assert row_ts is not None
        assert row_ts[1] == 10, "PEP 503 canonicalization to 'tree-sitter' must work"

    def test_clickhouse_url_overridable(self, db, atlas_mod, monkeypatch):
        """PHASE_P_CH_BASE_URL replaces the default endpoint."""
        body = '{"project":"numpy","d30":"1","d90":"1"}\n'
        calls = self._install_fake_urlopen(monkeypatch, body)
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.setenv("PHASE_P_CH_BASE_URL", "https://internal-mirror.example.com/?u=play")

        atlas_mod.phase_p_pypi_downloads(db)

        assert len(calls) == 1
        assert calls[0]["url"] == "https://internal-mirror.example.com/?u=play"

    def test_clickhouse_http_error_skips_cleanly(self, db, atlas_mod, monkeypatch):
        """When urlopen raises, Phase P returns skipped with the error in reason."""
        import urllib.error

        def boom(req, timeout=None):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)

        result = atlas_mod.phase_p_pypi_downloads(db)

        assert result.get("skipped") is True
        reason = result.get("reason", "")
        assert "ClickHouse query failed" in reason

    def test_clickhouse_cap_warning_above_1000_limit(self, db, atlas_mod, monkeypatch, capsys):
        """Setting PHASE_P_CH_LIMIT > 1000 is a no-op (ClickHouse Play caps at
        ~1,000 aggregated-result rows); WARN log must call this out."""
        # Build only 1000 rows even though limit is 5000 — simulating cap.
        rows = "\n".join(
            f'{{"project":"pkg{i}","d30":"1","d90":"1"}}' for i in range(1000)
        )
        self._install_fake_urlopen(monkeypatch, rows)
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.setenv("PHASE_P_CH_LIMIT", "5000")

        atlas_mod.phase_p_pypi_downloads(db)
        out = capsys.readouterr().out
        assert "WARN" in out and "1,000 rows" in out, (
            "When operator asks for >1000 but server caps at 1000, must warn"
        )

    def test_clickhouse_ignores_non_json_lines(self, db, atlas_mod, monkeypatch):
        """ClickHouse error responses come back as plain text — skip non-JSON lines."""
        body = (
            'Code: 241. DB::Exception: Memory limit exceeded\n'
            '{"project":"numpy","d30":"1","d90":"1"}\n'
            ''  # blank line
        )
        self._install_fake_urlopen(monkeypatch, body)
        monkeypatch.setenv("PHASE_P_ENABLED", "1")
        monkeypatch.delenv("PHASE_P_DISABLED", raising=False)
        monkeypatch.setenv("PHASE_P_CH_BUCKETS", "1")

        result = atlas_mod.phase_p_pypi_downloads(db)

        assert result.get("rows_upserted") == 1, (
            "Only the valid JSON line counts; the error message and blank are skipped"
        )
