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
