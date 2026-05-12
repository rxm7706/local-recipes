"""hard_reset() preserves cache/parquet by default, nukes it with reset_cache."""
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


@pytest.fixture
def bootstrap_mod(tmp_path, monkeypatch):
    mod = _load("bootstrap_data")
    # Redirect DATA_DIR to a tempdir so the test cannot touch real data.
    fake = tmp_path / "conda-forge-expert"
    fake.mkdir()
    monkeypatch.setattr(mod, "DATA_DIR", fake)
    return mod


def _seed_data_dir(data_dir: Path) -> None:
    (data_dir / "cf_atlas.db").write_text("fake")
    parquet = data_dir / "cache" / "parquet"
    parquet.mkdir(parents=True)
    (parquet / "2026-04.parquet").write_text("p1")
    (parquet / "2026-03.parquet").write_text("p2")
    (data_dir / "vdb").mkdir()
    (data_dir / "vdb" / "huge.idx").write_text("v")


class TestHardReset:
    def test_default_preserves_parquet_cache(self, bootstrap_mod):
        _seed_data_dir(bootstrap_mod.DATA_DIR)
        bootstrap_mod.hard_reset(dry_run=False, reset_cache=False, assume_yes=True)
        d = bootstrap_mod.DATA_DIR
        assert d.exists()
        assert not (d / "cf_atlas.db").exists()
        assert not (d / "vdb" / "huge.idx").exists()
        assert (d / "cache" / "parquet" / "2026-04.parquet").exists()
        assert (d / "cache" / "parquet" / "2026-03.parquet").exists()

    def test_reset_cache_nukes_parquet(self, bootstrap_mod):
        _seed_data_dir(bootstrap_mod.DATA_DIR)
        bootstrap_mod.hard_reset(dry_run=False, reset_cache=True, assume_yes=True)
        d = bootstrap_mod.DATA_DIR
        assert d.exists()
        assert not (d / "cf_atlas.db").exists()
        assert not (d / "cache" / "parquet").exists()

    def test_dry_run_changes_nothing(self, bootstrap_mod):
        _seed_data_dir(bootstrap_mod.DATA_DIR)
        bootstrap_mod.hard_reset(dry_run=True, reset_cache=False, assume_yes=False)
        d = bootstrap_mod.DATA_DIR
        assert (d / "cf_atlas.db").exists()
        assert (d / "cache" / "parquet" / "2026-04.parquet").exists()
        assert (d / "vdb" / "huge.idx").exists()

    def test_aborted_confirmation_returns_false(self, bootstrap_mod, monkeypatch):
        _seed_data_dir(bootstrap_mod.DATA_DIR)
        monkeypatch.setattr(
            bootstrap_mod, "_confirm_destructive",
            lambda *_a, **_kw: False,
        )
        result = bootstrap_mod.hard_reset(
            dry_run=False, reset_cache=False, assume_yes=False,
        )
        assert result is False
        d = bootstrap_mod.DATA_DIR
        assert (d / "cf_atlas.db").exists()
        assert (d / "cache" / "parquet" / "2026-04.parquet").exists()
        assert (d / "vdb" / "huge.idx").exists()

    def test_dry_run_skips_confirmation(self, bootstrap_mod, monkeypatch):
        _seed_data_dir(bootstrap_mod.DATA_DIR)
        called = {"yes": False}
        def _spy(*_a, **_kw):
            called["yes"] = True
            return True
        monkeypatch.setattr(bootstrap_mod, "_confirm_destructive", _spy)
        result = bootstrap_mod.hard_reset(
            dry_run=True, reset_cache=False, assume_yes=False,
        )
        assert result is True
        assert called["yes"] is False
        # Nothing was actually deleted.
        d = bootstrap_mod.DATA_DIR
        assert (d / "cf_atlas.db").exists()

    def test_assume_yes_skips_countdown(self, bootstrap_mod):
        """With assume_yes=True, hard_reset returns quickly (no 5s sleep)."""
        import time
        _seed_data_dir(bootstrap_mod.DATA_DIR)
        t0 = time.monotonic()
        result = bootstrap_mod.hard_reset(
            dry_run=False, reset_cache=False, assume_yes=True,
        )
        elapsed = time.monotonic() - t0
        assert result is True
        assert elapsed < 1.0, f"expected <1s, took {elapsed:.2f}s"

    def test_missing_data_dir_is_noop(self, bootstrap_mod):
        # Remove the tempdir; hard_reset must not crash.
        d = bootstrap_mod.DATA_DIR
        d.rmdir()
        bootstrap_mod.hard_reset(dry_run=False, reset_cache=False, assume_yes=True)
        # Must not have recreated it on a no-op path.
        assert not d.exists()

    def test_no_parquet_to_preserve(self, bootstrap_mod):
        # DATA_DIR exists, has data, but no cache/parquet subdir.
        d = bootstrap_mod.DATA_DIR
        (d / "cf_atlas.db").write_text("fake")
        bootstrap_mod.hard_reset(dry_run=False, reset_cache=False, assume_yes=True)
        assert d.exists()
        assert not (d / "cf_atlas.db").exists()
        # No parquet to restore — still works without error.
