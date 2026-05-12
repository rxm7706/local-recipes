"""Unit tests for Phase H PHASE_H_SOURCE dispatcher and cf-graph bulk path."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tarfile
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


@pytest.fixture(scope="module")
def cfg_mod():
    return _load("_cf_graph_versions")


@pytest.fixture
def db(tmp_path, atlas_mod):
    db_path = tmp_path / "cf_atlas.db"
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)
    rows = [
        ("requests",  "requests",  "requests"),
        ("numpy",     "numpy",     "numpy"),
        ("pip",       "pip",       "pip"),
        ("orphan",    "orphan",    "orphan-no-shard"),
    ]
    for conda, feedstock, pypi in rows:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, feedstock_name, pypi_name, relationship, "
            " match_source, match_confidence) "
            "VALUES (?, ?, ?, 'cf+pypi', 'test', 'high')",
            (conda, feedstock, pypi),
        )
    conn.commit()
    yield conn
    conn.close()


def _scrub_phase_h_env(monkeypatch):
    for var in (
        "PHASE_H_SOURCE", "PHASE_H_DISABLED", "PHASE_H_TTL_DAYS",
        "PHASE_H_CONCURRENCY", "PHASE_H_LIMIT",
    ):
        monkeypatch.delenv(var, raising=False)


def _build_fake_tarball(tmp_path: Path, version_by_feedstock: dict[str, object]) -> Path:
    """Build a minimal cf-graph tarball with only the version_pr_info shards
    we care about. `version_by_feedstock` value can be a str, None, False,
    or arbitrary JSON to exercise filter cases."""
    out = tmp_path / "cf-graph.tar.gz"
    with tarfile.open(out, "w:gz") as tf:
        for fs, new_version in version_by_feedstock.items():
            payload = json.dumps({"bad": False, "new_version": new_version})
            data = payload.encode()
            info = tarfile.TarInfo(
                name=f"cf-graph-countyfair-master/version_pr_info/x/y/z/0/0/{fs}.json"
            )
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return out


class TestDispatcher:
    def test_disabled_short_circuits(self, monkeypatch, db, atlas_mod):
        _scrub_phase_h_env(monkeypatch)
        monkeypatch.setenv("PHASE_H_DISABLED", "1")
        res = atlas_mod.phase_h_pypi_versions(db)
        assert res["skipped"] is True

    def test_unknown_source_raises(self, monkeypatch, db, atlas_mod):
        _scrub_phase_h_env(monkeypatch)
        monkeypatch.setenv("PHASE_H_SOURCE", "bogus")
        with pytest.raises(ValueError, match="PHASE_H_SOURCE"):
            atlas_mod.phase_h_pypi_versions(db)


class TestCfGraphPath:
    def test_writes_versions_and_source_tag(
        self, monkeypatch, tmp_path, db, atlas_mod, cfg_mod
    ):
        _scrub_phase_h_env(monkeypatch)
        tar = _build_fake_tarball(tmp_path, {
            "requests": "9.9.9",
            "numpy":    "2.0.0",
            "pip":      "30.0.0",
            # orphan feedstock NOT in the tarball → row stays without version
        })
        monkeypatch.setattr(cfg_mod, "default_tarball_path", lambda: tar)
        monkeypatch.setenv("PHASE_H_SOURCE", "cf-graph")

        res = atlas_mod.phase_h_pypi_versions(db)

        assert res["source"] == "cf-graph"
        assert res["fetched"] == 3
        assert res["not_found_404"] == 1

        rows = {
            r["pypi_name"]: r for r in db.execute(
                "SELECT pypi_name, pypi_current_version, "
                "pypi_current_version_yanked, pypi_version_source, "
                "pypi_version_fetched_at FROM packages"
            )
        }
        assert rows["requests"]["pypi_current_version"] == "9.9.9"
        assert rows["requests"]["pypi_version_source"] == "cf-graph"
        # cf-graph does not carry PEP 592; yanked must be NULL not 0/1.
        assert rows["requests"]["pypi_current_version_yanked"] is None
        assert rows["requests"]["pypi_version_fetched_at"] is not None

        # Orphan got a source tag but no version + no fetched_at → will be
        # re-tried by a future pypi-json pass without being TTL-skipped.
        assert rows["orphan-no-shard"]["pypi_current_version"] is None
        assert rows["orphan-no-shard"]["pypi_version_source"] == "cf-graph"
        assert rows["orphan-no-shard"]["pypi_version_fetched_at"] is None

    def test_missing_tarball_skips_cleanly(
        self, monkeypatch, tmp_path, db, atlas_mod, cfg_mod
    ):
        _scrub_phase_h_env(monkeypatch)
        nonexistent = tmp_path / "no-such-tarball.tar.gz"
        monkeypatch.setattr(cfg_mod, "default_tarball_path", lambda: nonexistent)
        monkeypatch.setenv("PHASE_H_SOURCE", "cf-graph")

        res = atlas_mod.phase_h_pypi_versions(db)

        assert res.get("skipped") is True
        assert "cf-graph cache missing" in res.get("reason", "")

    def test_skips_null_and_falsey_new_version(
        self, monkeypatch, tmp_path, db, atlas_mod, cfg_mod
    ):
        _scrub_phase_h_env(monkeypatch)
        tar = _build_fake_tarball(tmp_path, {
            "requests": "9.9.9",
            "numpy":    None,    # bot couldn't detect upstream
            "pip":      False,   # legacy sentinel
        })
        monkeypatch.setattr(cfg_mod, "default_tarball_path", lambda: tar)
        monkeypatch.setenv("PHASE_H_SOURCE", "cf-graph")

        res = atlas_mod.phase_h_pypi_versions(db)

        # only `requests` has a usable string version
        assert res["fetched"] == 1
        rows = {
            r["pypi_name"]: r["pypi_current_version"]
            for r in db.execute("SELECT pypi_name, pypi_current_version FROM packages")
        }
        assert rows["requests"] == "9.9.9"
        assert rows["numpy"] is None
        assert rows["pip"] is None


class TestCfGraphModule:
    def test_iter_skips_malformed_json(self, tmp_path, cfg_mod):
        out = tmp_path / "broken.tar.gz"
        with tarfile.open(out, "w:gz") as tf:
            good = json.dumps({"new_version": "1.2.3"}).encode()
            info = tarfile.TarInfo(name="x/version_pr_info/a/b/c/d/e/good.json")
            info.size = len(good)
            tf.addfile(info, io.BytesIO(good))
            bad = b"this is not json"
            info = tarfile.TarInfo(name="x/version_pr_info/a/b/c/d/e/bad.json")
            info.size = len(bad)
            tf.addfile(info, io.BytesIO(bad))
        results = list(cfg_mod.iter_feedstock_versions(path=out))
        assert results == [("good", "1.2.3")]

    def test_build_pypi_version_map_join(self, tmp_path, cfg_mod):
        out = tmp_path / "join.tar.gz"
        with tarfile.open(out, "w:gz") as tf:
            for fs, v in [("requests", "2.0"), ("numpy", "1.0"), ("orphan", "9.0")]:
                payload = json.dumps({"new_version": v}).encode()
                info = tarfile.TarInfo(name=f"x/version_pr_info/a/b/c/d/e/{fs}.json")
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))
        mapping = {"requests": "Requests", "numpy": "numpy"}  # orphan missing
        result = cfg_mod.build_pypi_version_map(mapping, path=out)
        assert result == {"Requests": "2.0", "numpy": "1.0"}
