"""Persona profile resolution for bootstrap_data.py (v8.0.0 Wave D).

`--profile {maintainer,admin,consumer}` injects a bundle of env-var
defaults into `os.environ` via setdefault so explicit user env vars and
CLI flags always win. `maintainer` additionally auto-detects the GitHub
login via `gh api user --jq .login` and auto-restricts `PHASE_L_SOURCES`
to populated registries in scope.

Tests cover:
  - profile resolution merges env correctly
  - --profile maintainer enables E + N and auto-scopes the maintainer
  - --profile maintainer without gh prints warning + proceeds channel-wide
  - --profile consumer pins to air-gap sources (s3-parquet + cf-graph)
  - --profile admin runs channel-wide N (no PHASE_N_MAINTAINER)
  - end-of-run advisory print fires when no --profile, silenced by
    BUILD_CF_ATLAS_QUIET=1
  - _auto_detect_phase_l_sources returns None when the DB is missing or
    the view is unavailable
"""
from __future__ import annotations

import importlib.util
import io
import sqlite3
import sys
from contextlib import redirect_stdout
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
def bootstrap_mod():
    return _load("bootstrap_data")


def _scrub(monkeypatch):
    """Clear every env var the profile resolver reads/writes."""
    for k in (
        "PHASE_E_ENABLED", "PHASE_N_ENABLED",
        "PHASE_F_SOURCE", "PHASE_H_SOURCE",
        "PHASE_N_MAINTAINER", "PHASE_L_SOURCES",
        "PHASE_D_UNIVERSE_DISABLED", "BUILD_CF_ATLAS_QUIET",
    ):
        monkeypatch.delenv(k, raising=False)


class TestProfileResolution:
    def test_no_profile_returns_empty(self, bootstrap_mod, monkeypatch):
        _scrub(monkeypatch)
        env, warns = bootstrap_mod._resolve_profile_env(None)
        assert env == {}
        assert warns == []

    def test_unknown_profile_raises(self, bootstrap_mod, monkeypatch):
        _scrub(monkeypatch)
        with pytest.raises(ValueError, match="unknown --profile"):
            bootstrap_mod._resolve_profile_env("ghost")

    def test_maintainer_enables_e_and_n(self, bootstrap_mod, monkeypatch):
        _scrub(monkeypatch)
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_gh_user",
                            lambda timeout=5: "rxm7706")  # noqa: ARG005
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_phase_l_sources",
                            lambda maintainer, db_path=None: None)  # noqa: ARG005
        env, warns = bootstrap_mod._resolve_profile_env("maintainer")
        assert env["PHASE_E_ENABLED"] == "1"
        assert env["PHASE_N_ENABLED"] == "1"
        assert env["PHASE_F_SOURCE"] == "auto"
        assert env["PHASE_H_SOURCE"] == "auto"
        assert env["PHASE_N_MAINTAINER"] == "rxm7706"
        assert warns == []

    def test_maintainer_honors_existing_phase_n_maintainer(
        self, bootstrap_mod, monkeypatch,
    ):
        _scrub(monkeypatch)
        monkeypatch.setenv("PHASE_N_MAINTAINER", "alice-from-env")
        # gh-auto-detect should not be consulted when env is set.
        def _boom(timeout=5):
            raise AssertionError("auto-detect should not run")
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_gh_user", _boom)
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_phase_l_sources",
                            lambda maintainer, db_path=None: None)
        env, warns = bootstrap_mod._resolve_profile_env("maintainer")
        assert env["PHASE_N_MAINTAINER"] == "alice-from-env"
        assert warns == []

    def test_maintainer_without_gh_warns_and_proceeds(
        self, bootstrap_mod, monkeypatch,
    ):
        _scrub(monkeypatch)
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_gh_user",
                            lambda timeout=5: None)
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_phase_l_sources",
                            lambda maintainer, db_path=None: None)
        env, warns = bootstrap_mod._resolve_profile_env("maintainer")
        # PHASE_N_ENABLED still set — runs channel-wide as fallback.
        assert env["PHASE_N_ENABLED"] == "1"
        assert "PHASE_N_MAINTAINER" not in env
        assert len(warns) == 1
        assert "gh api user" in warns[0]

    def test_maintainer_auto_detects_phase_l_sources(
        self, bootstrap_mod, monkeypatch,
    ):
        _scrub(monkeypatch)
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_gh_user",
                            lambda timeout=5: "rxm7706")
        monkeypatch.setattr(bootstrap_mod, "_auto_detect_phase_l_sources",
                            lambda maintainer, db_path=None: "npm,cran")
        env, _warns = bootstrap_mod._resolve_profile_env("maintainer")
        assert env["PHASE_L_SOURCES"] == "npm,cran"

    def test_admin_runs_channel_wide(self, bootstrap_mod, monkeypatch):
        _scrub(monkeypatch)
        env, warns = bootstrap_mod._resolve_profile_env("admin")
        assert env["PHASE_N_ENABLED"] == "1"
        assert env["PHASE_E_ENABLED"] == "1"
        # Admin profile never sets a maintainer scope.
        assert "PHASE_N_MAINTAINER" not in env
        assert warns == []

    def test_consumer_sets_air_gap_sources(self, bootstrap_mod, monkeypatch):
        _scrub(monkeypatch)
        env, warns = bootstrap_mod._resolve_profile_env("consumer")
        assert env["PHASE_F_SOURCE"] == "s3-parquet"
        assert env["PHASE_H_SOURCE"] == "cf-graph"
        assert env["PHASE_D_UNIVERSE_DISABLED"] == "1"
        assert env["PHASE_N_ENABLED"] == ""
        assert warns == []


class TestAutoDetectPhaseLSources:
    """`_auto_detect_phase_l_sources` is a best-effort DB query; always
    returns None on a missing DB or pre-v21 schema."""

    def test_missing_db_returns_none(self, bootstrap_mod, tmp_path):
        db = tmp_path / "nope.db"
        assert bootstrap_mod._auto_detect_phase_l_sources(
            "rxm7706", db_path=db
        ) is None

    def test_view_missing_returns_none(self, bootstrap_mod, tmp_path):
        # Empty SQLite — no view → resolver returns None.
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE packages (conda_name TEXT)")
        conn.commit()
        conn.close()
        assert bootstrap_mod._auto_detect_phase_l_sources(
            "rxm7706", db_path=db
        ) is None

    def test_returns_populated_sources(self, bootstrap_mod, tmp_path):
        db = tmp_path / "atlas.db"
        conn = sqlite3.connect(db)
        # Minimal schema for the view+join the resolver issues.
        conn.executescript("""
            CREATE TABLE packages (
                conda_name TEXT PRIMARY KEY,
                latest_status TEXT,
                feedstock_archived INTEGER,
                npm_name TEXT,
                cran_name TEXT,
                cpan_name TEXT,
                luarocks_name TEXT,
                maven_coord TEXT
            );
            CREATE TABLE package_maintainers (
                conda_name TEXT,
                handle TEXT
            );
            CREATE VIEW v_actionable_packages AS
                SELECT * FROM packages
                WHERE conda_name IS NOT NULL
                  AND COALESCE(latest_status, 'active') = 'active'
                  AND COALESCE(feedstock_archived, 0) = 0;
            INSERT INTO packages
                (conda_name, latest_status, feedstock_archived,
                 npm_name, cran_name, cpan_name, luarocks_name, maven_coord)
            VALUES
                ('foo', 'active', 0, 'foo-pkg', NULL, NULL, NULL, NULL),
                ('bar', 'active', 0, NULL, 'barpkg', NULL, NULL, NULL),
                ('baz', 'active', 0, NULL, NULL, NULL, NULL, NULL);
            INSERT INTO package_maintainers (conda_name, handle) VALUES
                ('foo', 'rxm7706'),
                ('bar', 'rxm7706'),
                ('baz', 'rxm7706');
        """)
        conn.commit()
        conn.close()
        result = bootstrap_mod._auto_detect_phase_l_sources(
            "rxm7706", db_path=db
        )
        assert result is not None
        sources = result.split(",")
        # foo has npm_name, bar has cran_name; cpan/luarocks/maven all empty.
        assert "npm" in sources
        assert "cran" in sources
        assert "cpan" not in sources

    def test_channel_wide_when_no_maintainer(self, bootstrap_mod, tmp_path):
        db = tmp_path / "atlas.db"
        conn = sqlite3.connect(db)
        conn.executescript("""
            CREATE TABLE packages (
                conda_name TEXT PRIMARY KEY,
                latest_status TEXT,
                feedstock_archived INTEGER,
                npm_name TEXT,
                cran_name TEXT,
                cpan_name TEXT,
                luarocks_name TEXT,
                maven_coord TEXT
            );
            CREATE VIEW v_actionable_packages AS
                SELECT * FROM packages
                WHERE conda_name IS NOT NULL
                  AND COALESCE(latest_status, 'active') = 'active'
                  AND COALESCE(feedstock_archived, 0) = 0;
            INSERT INTO packages
                (conda_name, latest_status, feedstock_archived,
                 npm_name, cran_name, cpan_name, luarocks_name, maven_coord)
            VALUES
                ('only-luarocks', 'active', 0, NULL, NULL, NULL, 'rock', NULL);
        """)
        conn.commit()
        conn.close()
        result = bootstrap_mod._auto_detect_phase_l_sources(
            None, db_path=db
        )
        assert result == "luarocks"


class TestAdvisoryPrint:
    """End-of-run advisory only fires when --profile is unset and
    BUILD_CF_ATLAS_QUIET is empty."""

    def test_advisory_prints_when_no_profile(self, bootstrap_mod, monkeypatch):
        monkeypatch.delenv("BUILD_CF_ATLAS_QUIET", raising=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            bootstrap_mod._print_no_profile_advisory(None)
        out = buf.getvalue()
        assert "No --profile specified" in out
        assert "--profile maintainer" in out

    def test_advisory_silent_with_profile(self, bootstrap_mod, monkeypatch):
        monkeypatch.delenv("BUILD_CF_ATLAS_QUIET", raising=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            bootstrap_mod._print_no_profile_advisory("maintainer")
        assert buf.getvalue() == ""

    def test_advisory_silenced_by_quiet_env(self, bootstrap_mod, monkeypatch):
        monkeypatch.setenv("BUILD_CF_ATLAS_QUIET", "1")
        buf = io.StringIO()
        with redirect_stdout(buf):
            bootstrap_mod._print_no_profile_advisory(None)
        assert buf.getvalue() == ""


class TestAutoDetectGhUser:
    """Helper handles missing-gh / unauth / timeout without raising."""

    def test_missing_gh_returns_none(self, bootstrap_mod, monkeypatch):
        def _fnf(*a, **kw):
            raise FileNotFoundError("gh not installed")
        monkeypatch.setattr(bootstrap_mod.subprocess, "run", _fnf)
        assert bootstrap_mod._auto_detect_gh_user() is None

    def test_timeout_returns_none(self, bootstrap_mod, monkeypatch):
        import subprocess as _sp
        def _to(*a, **kw):
            raise _sp.TimeoutExpired(cmd="gh", timeout=5)
        monkeypatch.setattr(bootstrap_mod.subprocess, "run", _to)
        assert bootstrap_mod._auto_detect_gh_user() is None

    def test_unauth_returns_none(self, bootstrap_mod, monkeypatch):
        class _R:
            returncode = 4
            stdout = ""
            stderr = "auth required"
        monkeypatch.setattr(bootstrap_mod.subprocess, "run",
                            lambda *a, **kw: _R())
        assert bootstrap_mod._auto_detect_gh_user() is None

    def test_success_returns_login(self, bootstrap_mod, monkeypatch):
        class _R:
            returncode = 0
            stdout = "rxm7706\n"
            stderr = ""
        monkeypatch.setattr(bootstrap_mod.subprocess, "run",
                            lambda *a, **kw: _R())
        assert bootstrap_mod._auto_detect_gh_user() == "rxm7706"
