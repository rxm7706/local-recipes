"""Phase Q — cross-channel presence (bioconda/pytorch/nvidia/robostack)."""
from __future__ import annotations

import importlib.util
import json
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
    """v22 atlas with a small pypi_universe + intelligence rows for matching."""
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    for name in ("biopython", "numpy", "pytorch", "tree-sitter"):
        conn.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES (?, ?, ?)",
            (name, 1, 0),
        )
    conn.commit()
    yield conn
    conn.close()


class TestPep503Canonical:
    """`_pep503_canonical` collapses `_-.` runs to single `-` and lowercases."""

    def test_underscore_to_hyphen(self, atlas_mod):
        assert atlas_mod._pep503_canonical("tree_sitter") == "tree-sitter"

    def test_dot_to_hyphen(self, atlas_mod):
        assert atlas_mod._pep503_canonical("zope.interface") == "zope-interface"

    def test_uppercase_lowered(self, atlas_mod):
        assert atlas_mod._pep503_canonical("PyJWT") == "pyjwt"

    def test_runs_collapsed(self, atlas_mod):
        assert atlas_mod._pep503_canonical("foo___bar") == "foo-bar"
        assert atlas_mod._pep503_canonical("foo--bar") == "foo-bar"


class TestPhaseQDisabled:
    """PHASE_Q_DISABLED=1 skips cleanly."""

    def test_disabled_env_skips(self, db, atlas_mod, monkeypatch):
        monkeypatch.setenv("PHASE_Q_DISABLED", "1")
        result = atlas_mod.phase_q_cross_channel(db)
        assert result.get("skipped") is True


class TestPhaseQEmptyUniverse:
    """Empty pypi_universe → graceful skip."""

    def test_empty_universe_skips(self, tmp_path, atlas_mod):
        db_path = tmp_path / "empty.db"
        conn = atlas_mod.open_db(db_path)
        atlas_mod.init_schema(conn)
        result = atlas_mod.phase_q_cross_channel(conn)
        assert result.get("skipped") is True
        conn.close()


class TestPhaseQNetworkPaths:
    """Mock the per-channel fetch helper to verify the matching + UPDATE
    pipeline without hitting actual repodata endpoints."""

    def test_mocked_match_writes_in_bioconda_column(
        self, db, atlas_mod, monkeypatch,
    ):
        # Mock the channel fetch to return a controlled set
        def _fake_fetch(channel, subdirs, timeout=60):
            if channel == "bioconda":
                # PEP 503 already-canonical — biopython matches one universe row
                return ({"biopython", "samtools"}, None)
            if channel == "pytorch":
                return ({"pytorch", "torchvision"}, None)
            return (set(), None)

        monkeypatch.setattr(atlas_mod, "_phase_q_fetch_channel_pypi_names", _fake_fetch)
        result = atlas_mod.phase_q_cross_channel(db)
        assert not result.get("skipped")

        # Check bioconda matches
        rows = list(db.execute(
            "SELECT pypi_name, in_bioconda, in_pytorch FROM pypi_intelligence "
            "ORDER BY pypi_name"
        ))
        d = {r["pypi_name"]: dict(r) for r in rows}
        # biopython in bioconda; pytorch in pytorch
        assert d["biopython"]["in_bioconda"] == 1
        assert d["pytorch"]["in_pytorch"] == 1
        # numpy not in any of the mocked sets — no row inserted, OR row
        # inserted with NULL columns (no flip)
        assert d.get("numpy", {}).get("in_bioconda") in (None, 0)

    def test_mocked_fetch_failure_logged_not_raised(
        self, db, atlas_mod, monkeypatch,
    ):
        def _broken_fetch(channel, subdirs, timeout=60):
            return (set(), f"HTTPError 503: {channel} backend down")

        monkeypatch.setattr(atlas_mod, "_phase_q_fetch_channel_pypi_names", _broken_fetch)
        result = atlas_mod.phase_q_cross_channel(db)
        # All channels failed → no exception raised, failures recorded
        assert not result.get("skipped")
        assert result["channels_failed"] == len(atlas_mod._PHASE_Q_CONDA_CHANNELS)
        assert result["total_matches"] == 0


class TestPhaseQNameNormalization:
    """Phase Q PEP 503-canonicalizes both the channel-side names AND the
    universe-side names before matching."""

    def test_underscored_universe_name_matches_hyphenated_channel(
        self, db, atlas_mod, monkeypatch,
    ):
        # Insert a universe row with underscored PyPI form
        db.execute(
            "INSERT INTO pypi_universe (pypi_name, last_serial, fetched_at) "
            "VALUES ('zope_interface', 1, 0)"
        )
        db.commit()

        def _fake_fetch(channel, subdirs, timeout=60):
            if channel == "bioconda":
                # Channel-side has hyphen form
                return ({"zope-interface"}, None)
            return (set(), None)

        monkeypatch.setattr(atlas_mod, "_phase_q_fetch_channel_pypi_names", _fake_fetch)
        atlas_mod.phase_q_cross_channel(db)
        # Match should succeed via canonicalization on both sides
        row = db.execute(
            "SELECT in_bioconda FROM pypi_intelligence WHERE pypi_name='zope-interface'"
        ).fetchone()
        assert row is not None
        assert row["in_bioconda"] == 1


class TestPhaseQResolverIntegration:
    """`_resolve_anaconda_channel_urls` returns a fallback chain with
    JFrog mirror first, then prefix.dev, then anaconda.org."""

    def test_default_fallback_chain(self, atlas_mod, monkeypatch):
        monkeypatch.delenv("BIOCONDA_BASE_URL", raising=False)
        urls = atlas_mod._resolve_anaconda_channel_urls(
            "bioconda", "noarch", "current_repodata.json"
        )
        assert any("repo.prefix.dev/bioconda" in u for u in urls)
        assert any("conda.anaconda.org/bioconda" in u for u in urls)

    def test_env_var_takes_priority(self, atlas_mod, monkeypatch):
        monkeypatch.setenv("BIOCONDA_BASE_URL", "https://artifactory.example.com/bioconda")
        urls = atlas_mod._resolve_anaconda_channel_urls(
            "bioconda", "noarch", "current_repodata.json"
        )
        assert urls[0].startswith("https://artifactory.example.com/bioconda")

    def test_robostack_staging_env_var_normalization(self, atlas_mod, monkeypatch):
        # Channel name has '-' → env var swaps to '_'
        monkeypatch.setenv("ROBOSTACK_STAGING_BASE_URL", "https://example.com/rs")
        urls = atlas_mod._resolve_anaconda_channel_urls(
            "robostack-staging", "noarch", "current_repodata.json"
        )
        assert urls[0].startswith("https://example.com/rs")
