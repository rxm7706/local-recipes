"""The atlas reads the conda-forge bot's graph from its split repos (CFE v8.102.0).

In 2026-10 GitHub began redirecting ``regro/cf-graph-countyfair`` to
``conda-forge/conda-forge-bot-data``, whose archive holds no ``node_attrs/``,
``pr_info/`` or ``version_pr_info/``. Phase J then wiped ``dependencies`` and
wrote 0 edges, Phase M and Phase H's cf-graph mode read nothing, and nothing
said so. The graph now lives in four ``conda-forge-bot-data-*`` repos, one
record per file under a five-level sha1 shard.

These tests build archives in memory (no network): the split layout, the
pre-split combined layout, and the redirected bot-data archive that caused
the incident.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tarfile
import time
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
def src_mod():
    return _load("_cf_graph_source")


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


@pytest.fixture(scope="module")
def cfg_mod():
    return _load("_cf_graph_versions")


# ── archive builders ─────────────────────────────────────────────────────────

def _write_tar(target: Path, members: dict[str, object]) -> Path:
    """Write a gzip tarball whose files are `members` (path → JSON payload)."""
    with tarfile.open(target, "w:gz") as tf:
        for name, payload in members.items():
            data = json.dumps(payload).encode()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = int(time.time())
            tf.addfile(info, io.BytesIO(data))
    return target


def _split_members(kind: str, records: dict[str, object]) -> dict[str, object]:
    """`conda-forge-bot-data-<kind>-main/<5 shard dirs>/<key>.json` for each record."""
    out = {}
    for key, payload in records.items():
        *dirs, name = key.split("/")
        out["/".join([f"conda-forge-bot-data-{kind}-main", *dirs, "a", "b", "c", "d", "e",
                      f"{name}.json"])] = payload
    return out


def _write_split(data_dir: Path, kind: str, records: dict[str, object]) -> Path:
    return _write_tar(data_dir / f"cf-graph-{kind}.tar.gz", _split_members(kind, records))


# The archive GitHub serves for regro/cf-graph-countyfair since the redirect:
# plenty of JSON, none of it the graph.
_REDIRECTED_BOT_DATA = {
    "conda-forge-bot-data-main/all_feedstocks.json": {"active": ["numpy"]},
    "conda-forge-bot-data-main/status/version_status.json": {"numpy": "ok"},
    "conda-forge-bot-data-main/import_to_pkg_maps/a/numpy.json": {"numpy": ["numpy"]},
    "conda-forge-bot-data-main/mappings/pypi/name_mapping.json": [{"pypi_name": "numpy"}],
}


@pytest.fixture
def offline(atlas_mod, monkeypatch):
    """Any download attempt in a unit test fails, like an offline host."""
    def _raise(urls, target):
        raise RuntimeError("offline in unit tests")

    monkeypatch.setattr(atlas_mod, "_cfgraph_download", _raise)


@pytest.fixture
def atlas_db(tmp_path, atlas_mod, monkeypatch):
    monkeypatch.setattr(atlas_mod, "DATA_DIR", tmp_path)
    conn = atlas_mod.open_db(tmp_path / "cf_atlas.db")
    atlas_mod.init_schema(conn)
    for conda, fs in (("numpy", "numpy"), ("scipy", "scipy"), ("libmetaio", "metaio"),
                      ("metaio", "metaio")):
        conn.execute(
            "INSERT INTO packages (conda_name, feedstock_name, latest_status, "
            "feedstock_archived, relationship, match_source, match_confidence) "
            "VALUES (?, ?, 'active', 0, 'test', 'test', 'high')",
            (conda, fs),
        )
    conn.commit()
    yield conn
    conn.close()


# ── record keys ──────────────────────────────────────────────────────────────

class TestRecordKey:
    def test_split_layout_strips_the_five_shard_dirs(self, src_mod):
        name = "conda-forge-bot-data-node_attrs-main/1/2/3/4/5/numpy.json"
        assert src_mod.record_key(name, "node_attrs") == "numpy"

    def test_a_nested_node_keeps_its_prefix(self, src_mod):
        name = "conda-forge-bot-data-node_attrs-main/conda-forge/label/1/2/3/4/5/numpy.json"
        assert src_mod.record_key(name, "node_attrs") == "conda-forge/label/numpy"

    @pytest.mark.parametrize("name", [
        "cf-graph-countyfair-master/node_attrs/n/u/m/numpy.json",
        "cf-graph-countyfair-master/node_attrs/n/u/m/p/y/numpy.json",
    ])
    def test_legacy_layout_reads_any_shard_depth(self, src_mod, name):
        assert src_mod.record_key(name, "node_attrs") == "numpy"

    def test_pr_info_is_not_version_pr_info(self, src_mod):
        legacy = "cf-graph-countyfair-master/version_pr_info/n/u/m/numpy.json"
        split = "conda-forge-bot-data-version_pr_info-main/1/2/3/4/5/numpy.json"
        assert src_mod.record_key(legacy, "pr_info") is None
        assert src_mod.record_key(split, "pr_info") is None
        assert src_mod.record_key(split, "version_pr_info") == "numpy"

    @pytest.mark.parametrize("name", list(_REDIRECTED_BOT_DATA))
    def test_the_redirected_bot_data_archive_holds_no_record(self, src_mod, name):
        for kind in src_mod.KINDS:
            assert src_mod.record_key(name, kind) is None

    def test_lazy_pr_json_reference(self, src_mod):
        assert src_mod.lazy_pr_json_id({"__lazy_json__": "pr_json/4799436437.json"}) == "4799436437"
        assert src_mod.lazy_pr_json_id({"state": "closed"}) is None
        assert src_mod.lazy_pr_json_id(None) is None


# ── archive validation + fetch ───────────────────────────────────────────────

class TestFetch:
    def test_a_split_archive_validates(self, src_mod, tmp_path):
        tar = _write_tar(tmp_path / "x.tar.gz", _split_members("node_attrs", {"numpy": {}}))
        assert src_mod.validate_split_archive(tar, "node_attrs") is None

    def test_the_redirected_archive_is_rejected_by_its_top_directory(self, src_mod, tmp_path):
        tar = _write_tar(tmp_path / "x.tar.gz", _REDIRECTED_BOT_DATA)
        problem = src_mod.validate_split_archive(tar, "node_attrs")
        assert problem is not None and "conda-forge-bot-data-main" in problem

    def test_an_archive_of_another_kind_is_rejected(self, src_mod, tmp_path):
        tar = _write_tar(tmp_path / "x.tar.gz", _split_members("pr_info", {"numpy": {}}))
        assert src_mod.validate_split_archive(tar, "node_attrs") is not None

    def test_a_non_gzip_body_is_rejected(self, src_mod, tmp_path):
        bad = tmp_path / "x.tar.gz"
        bad.write_bytes(b"<html>rate limited</html>")
        assert "not a whole gzip stream" in src_mod.validate_split_archive(bad, "node_attrs")

    def test_a_truncated_archive_is_rejected(self, src_mod, tmp_path):
        """A cut-off download still opens and shows a valid head; the whole stream must check."""
        full = _write_tar(tmp_path / "full.tar.gz", _split_members(
            "node_attrs", {f"pkg{i}": {"meta_yaml": {"about": {"summary": "x" * 200}}}
                           for i in range(400)}))
        cut = tmp_path / "cut.tar.gz"
        cut.write_bytes(full.read_bytes()[: full.stat().st_size // 2])
        assert src_mod.validate_split_archive(full, "node_attrs") is None
        problem = src_mod.validate_split_archive(cut, "node_attrs")
        assert problem is not None and "whole gzip stream" in problem

    def test_a_member_outside_the_repo_directory_is_rejected(self, src_mod, tmp_path):
        members = _split_members("node_attrs", {"numpy": {}})
        members["elsewhere/a/b/c/d/e/numpy.json"] = {}
        tar = _write_tar(tmp_path / "x.tar.gz", members)
        assert "elsewhere" in src_mod.validate_split_archive(tar, "node_attrs")

    def test_the_downloader_restarts_from_byte_zero(self, atlas_mod, monkeypatch, tmp_path):
        """A retry never resumes (no Range header) and never appends to the first attempt."""
        seen_headers: list[dict] = []
        payload = b"x" * 5000

        class _Resp:
            def __init__(self, fail):
                self._fail, self._sent = fail, False

            def read(self, n=-1):
                if self._fail:
                    if not self._sent:
                        self._sent = True
                        return b"partial-bytes-from-attempt-one"
                    raise ConnectionResetError("dropped mid-body")
                if self._sent:
                    return b""
                self._sent = True
                return payload

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        calls = {"n": 0}

        def _request(url, extra_headers=None, user_agent="", skip_auth=False):
            seen_headers.append(dict(extra_headers or {}))
            return url

        def _open(req, timeout=0):
            calls["n"] += 1
            return _Resp(fail=calls["n"] == 1)

        monkeypatch.setattr(atlas_mod, "_HTTP_AVAILABLE", True)
        monkeypatch.setattr(atlas_mod, "_http_make_request", _request)
        monkeypatch.setattr(atlas_mod, "_http_open_url", _open)
        monkeypatch.setattr(atlas_mod.time, "sleep", lambda _s: None)
        target = tmp_path / "out.tar.gz.new"

        atlas_mod._cfgraph_download(["https://example.invalid/a.tar.gz"], target)

        assert calls["n"] == 2
        assert target.read_bytes() == payload
        assert all("Range" not in h for h in seen_headers)

    def test_a_fresh_cache_is_not_downloaded(self, src_mod, tmp_path):
        _write_split(tmp_path, "node_attrs", {"numpy": {}})

        def _never(urls, target):
            raise AssertionError("downloaded a fresh cache")

        res = src_mod.fetch(tmp_path, "node_attrs", ttl_days=1, urls=["u"], download=_never)
        assert res["cached"] is True

    def test_a_good_download_replaces_a_stale_cache(self, src_mod, tmp_path):
        cache = _write_split(tmp_path, "node_attrs", {"old": {}})
        os.utime(cache, (0, 0))
        stale_part = tmp_path / "cf-graph-node_attrs.tar.gz.new.part"
        stale_part.write_bytes(b"bytes from an earlier attempt")
        seen = {}

        def _download(urls, target):
            seen["part_existed"] = stale_part.exists()
            _write_tar(target, _split_members("node_attrs", {"numpy": {}}))

        res = src_mod.fetch(tmp_path, "node_attrs", ttl_days=1, urls=["u"], download=_download)
        assert res["downloaded"] is True
        assert seen["part_existed"] is False  # never resumed across attempts
        assert [k for k, _ in src_mod.iter_records(tmp_path, "node_attrs")] == ["numpy"]

    def test_a_redirected_download_keeps_the_previous_cache(self, src_mod, tmp_path):
        cache = _write_split(tmp_path, "node_attrs", {"numpy": {}})
        os.utime(cache, (0, 0))
        before = cache.read_bytes()

        def _download(urls, target):
            _write_tar(target, _REDIRECTED_BOT_DATA)

        res = src_mod.fetch(tmp_path, "node_attrs", ttl_days=1, urls=["u"], download=_download)
        assert "rejected download" in res["error"]
        assert res["kept_previous"] is True
        assert cache.read_bytes() == before
        assert not (tmp_path / "cf-graph-node_attrs.tar.gz.new").exists()

    def test_a_failed_download_keeps_the_previous_cache(self, src_mod, tmp_path):
        cache = _write_split(tmp_path, "node_attrs", {"numpy": {}})
        os.utime(cache, (0, 0))

        def _download(urls, target):
            raise RuntimeError("all sources exhausted")

        res = src_mod.fetch(tmp_path, "node_attrs", ttl_days=1, urls=["u"], download=_download)
        assert "download failed" in res["error"]
        assert res["kept_previous"] is True
        assert cache.exists()
        assert not list(tmp_path.glob("*.new*"))  # no staging or .part left behind

    def test_the_archive_urls_name_the_split_repo(self, atlas_mod, monkeypatch):
        monkeypatch.delenv("GITHUB_BASE_URL", raising=False)
        urls = atlas_mod._cfgraph_urls("node_attrs")
        assert urls[-1] == ("https://github.com/conda-forge/conda-forge-bot-data-node_attrs"
                            "/archive/refs/heads/main.tar.gz")


# ── Phase J ──────────────────────────────────────────────────────────────────

class TestPhaseJ:
    def test_split_node_attrs_fill_the_dependencies_table(self, atlas_mod, atlas_db, tmp_path):
        _write_split(tmp_path, "node_attrs", {
            "numpy": {"meta_yaml": {"requirements": {
                "host": ["python", "cython"], "run": ["python >=3.11", "libblas", "numpy"]}}},
            "metaio": {"meta_yaml": {"outputs": [
                {"name": "libmetaio", "requirements": {"run": ["libzlib"]}},
                {"name": "metaio", "requirements": {"run": ["libmetaio", "python"]}},
            ]}},
        })
        res = atlas_mod.phase_j_dependency_graph(atlas_db)
        assert res["node_attrs_records"] == 2
        edges = {tuple(r) for r in atlas_db.execute(
            "SELECT source_conda_name, target_conda_name, requirement_type, pin_spec "
            "FROM dependencies")}
        assert ("numpy", "python", "run", ">=3.11") in edges
        assert ("numpy", "cython", "host", None) in edges
        assert ("libmetaio", "libzlib", "run", None) in edges
        assert ("metaio", "libmetaio", "run", None) in edges
        assert not any(src == tgt for src, tgt, _, _ in edges)  # no self-reference

    def test_recipe_test_requires_become_test_edges(self, atlas_mod, atlas_db, tmp_path):
        """The bot keeps test requirements in `test.requires`, never `requirements.test`."""
        _write_split(tmp_path, "node_attrs", {
            "numpy": {"meta_yaml": {"requirements": {"run": ["python"]},
                                    "test": {"requires": ["pytest", "hypothesis >=6", "numpy"]}}},
            "metaio": {"meta_yaml": {"outputs": [
                {"name": "libmetaio", "test": {"requires": ["cmake"]}},
                {"name": "metaio", "requirements": {"run": ["libmetaio"]},
                 "test": {"requires": ["pytest"]}},
            ]}},
            "scipy": {"meta_yaml": {"requirements": {"test": ["explicit-wins"]},
                                    "test": {"requires": ["ignored"]}}},
        })
        atlas_mod.phase_j_dependency_graph(atlas_db)
        tests = {tuple(r) for r in atlas_db.execute(
            "SELECT source_conda_name, target_conda_name, pin_spec FROM dependencies "
            "WHERE requirement_type = 'test'")}
        assert tests == {
            ("numpy", "pytest", None), ("numpy", "hypothesis", ">=6"),
            ("libmetaio", "cmake", None), ("metaio", "pytest", None),
            ("scipy", "explicit-wins", None),
        }

    def test_v1_recipe_tests_become_test_edges(self, atlas_mod, atlas_db, tmp_path):
        """A v1 recipe keeps test deps in each `tests[]` element's `requirements`."""
        _write_split(tmp_path, "node_attrs", {
            "numpy": {"meta_yaml": {"schema_version": 1, "outputs": [{
                "name": "numpy",
                "requirements": {"run": ["python"]},
                "tests": [
                    {"python": {"imports": ["numpy"], "pip_check": True}},
                    {"script": ["pytest"], "requirements": {"run": ["pytest >=8", "numpy"],
                                                            "build": ["cmake"]}},
                    {"downstream": "scipy"},
                ],
            }]}},
        })
        atlas_mod.phase_j_dependency_graph(atlas_db)
        tests = {tuple(r) for r in atlas_db.execute(
            "SELECT target_conda_name, pin_spec FROM dependencies "
            "WHERE source_conda_name = 'numpy' AND requirement_type = 'test'")}
        assert tests == {("pytest", ">=8"), ("cmake", None)}

    def test_a_cache_with_no_node_attrs_keeps_the_existing_graph(
        self, atlas_mod, atlas_db, tmp_path
    ):
        """The incident: the redirected archive replaced the graph with nothing."""
        atlas_db.execute(
            "INSERT INTO dependencies VALUES ('scipy', 'numpy', 'run', '>=1.26')")
        atlas_db.commit()
        _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", _REDIRECTED_BOT_DATA)

        res = atlas_mod.phase_j_dependency_graph(atlas_db)

        assert res["skipped"] is True
        assert "holds no node_attrs record" in res["reason"]
        assert atlas_db.execute("SELECT COUNT(*) FROM dependencies").fetchone()[0] == 1

    def test_no_cache_at_all_skips(self, atlas_mod, atlas_db):
        res = atlas_mod.phase_j_dependency_graph(atlas_db)
        assert res["skipped"] is True
        assert "run Phase E first" in res["reason"]

    def test_the_split_cache_wins_over_a_legacy_one(self, atlas_mod, atlas_db, tmp_path):
        _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", {
            "cf-graph-countyfair-master/node_attrs/n/u/m/numpy.json":
                {"meta_yaml": {"requirements": {"run": ["legacy-dep"]}}},
        })
        _write_split(tmp_path, "node_attrs", {
            "numpy": {"meta_yaml": {"requirements": {"run": ["split-dep"]}}},
        })
        atlas_mod.phase_j_dependency_graph(atlas_db)
        targets = {r[0] for r in atlas_db.execute("SELECT target_conda_name FROM dependencies")}
        assert targets == {"split-dep"}


# ── Phase M ──────────────────────────────────────────────────────────────────

class TestPhaseM:
    def _health(self, conn, name):
        return dict(conn.execute(
            "SELECT bot_open_pr_count, bot_last_pr_state, bot_last_pr_version, "
            "bot_version_errors_count, feedstock_bad FROM packages WHERE conda_name = ?",
            (name,)).fetchone())

    def test_live_prs_resolve_through_pr_json(self, atlas_mod, atlas_db, tmp_path):
        _write_split(tmp_path, "pr_info", {
            "numpy": {"PRed": [
                {"PR": {"state": "closed"}, "data": {"version": "2.0"}},
                {"PR": {"__lazy_json__": "pr_json/101.json"}, "data": {"version": "2.1"}},
                {"PR": {"__lazy_json__": "pr_json/999.json"}, "data": {"version": "2.2"}},
            ]},
            "scipy": {"PRed": [
                {"PR": {"__lazy_json__": "pr_json/202.json"}, "data": {"version": "1.15"}},
            ], "bad": "solver error"},
        })
        _write_split(tmp_path, "version_pr_info", {
            "numpy": {"new_version_errors": {"2.2": "failed"}},
        })
        _write_split(tmp_path, "pr_json", {
            "101": {"state": "open", "title": "numpy v2.1"},
            "202": {"state": "open"},
            "303": {"state": "closed"},  # referenced by nobody: never decoded
        })

        res = atlas_mod.phase_m_feedstock_health(atlas_db)

        assert res["live_pr_references"] == 3
        assert res["live_pr_references_resolved"] == 2
        numpy = self._health(atlas_db, "numpy")
        assert numpy["bot_open_pr_count"] == 1          # 999 is unresolvable: unknown, not open
        assert numpy["bot_last_pr_state"] is None        # last entry is the unresolvable one
        assert numpy["bot_last_pr_version"] == "2.2"
        assert numpy["bot_version_errors_count"] == 1
        scipy = self._health(atlas_db, "scipy")
        assert scipy["bot_open_pr_count"] == 1
        assert scipy["bot_last_pr_state"] == "open"
        assert scipy["feedstock_bad"] == 1

    def test_caches_with_no_record_write_nothing(self, atlas_mod, atlas_db, tmp_path):
        atlas_db.execute("UPDATE packages SET bot_open_pr_count = 4, feedstock_bad = 1 "
                         "WHERE conda_name = 'numpy'")
        atlas_db.commit()
        _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", _REDIRECTED_BOT_DATA)

        res = atlas_mod.phase_m_feedstock_health(atlas_db)

        assert res["skipped"] is True and res["rows_updated"] == 0
        assert self._health(atlas_db, "numpy")["bot_open_pr_count"] == 4

    def test_missing_pr_json_writes_nothing(self, atlas_mod, atlas_db, tmp_path):
        """Without pr_json every live PR would read as not open: skip, keep the columns."""
        atlas_db.execute("UPDATE packages SET bot_open_pr_count = 3, bot_last_pr_state = 'open' "
                         "WHERE conda_name = 'numpy'")
        atlas_db.commit()
        _write_split(tmp_path, "pr_info", {"numpy": {"PRed": [
            {"PR": {"__lazy_json__": "pr_json/101.json"}, "data": {"version": "2.1"}}]}})
        _write_split(tmp_path, "version_pr_info", {"numpy": {"new_version_errors": {}}})

        res = atlas_mod.phase_m_feedstock_health(atlas_db)

        assert res["skipped"] is True and "live-PR references resolve" in res["reason"]
        assert self._health(atlas_db, "numpy")["bot_open_pr_count"] == 3
        assert self._health(atlas_db, "numpy")["bot_last_pr_state"] == "open"

    def test_missing_version_pr_info_writes_nothing(self, atlas_mod, atlas_db, tmp_path):
        atlas_db.execute("UPDATE packages SET bot_version_errors_count = 2 "
                         "WHERE conda_name = 'numpy'")
        atlas_db.commit()
        _write_split(tmp_path, "pr_info", {"numpy": {"PRed": [
            {"PR": {"state": "closed"}, "data": {"version": "2.0"}}]}})

        res = atlas_mod.phase_m_feedstock_health(atlas_db)

        assert res["skipped"] is True and "version_pr_info" in res["reason"]
        assert self._health(atlas_db, "numpy")["bot_version_errors_count"] == 2

    def test_the_legacy_combined_layout_still_reads(self, atlas_mod, atlas_db, tmp_path):
        _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", {
            "cf-graph-countyfair-master/pr_info/n/u/m/numpy.json":
                {"PRed": [{"PR": {"state": "open"}, "data": {"version": "2.1"}}]},
            "cf-graph-countyfair-master/version_pr_info/n/u/m/numpy.json":
                {"new_version_errors": {}},
        })
        atlas_mod.phase_m_feedstock_health(atlas_db)
        assert self._health(atlas_db, "numpy")["bot_open_pr_count"] == 1


# ── Phase H, cf-graph mode ───────────────────────────────────────────────────

class TestPhaseHCfGraph:
    @pytest.fixture
    def h_db(self, atlas_db):
        atlas_db.execute("UPDATE packages SET pypi_name = conda_name")
        atlas_db.commit()
        return atlas_db

    @pytest.fixture
    def cf_graph_env(self, monkeypatch, cfg_mod, tmp_path):
        for var in ("PHASE_H_DISABLED", "PHASE_H_TTL_DAYS", "PHASE_H_CONCURRENCY",
                    "PHASE_H_LIMIT"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("PHASE_H_SOURCE", "cf-graph")
        monkeypatch.setattr(cfg_mod, "_data_dir", lambda: tmp_path)

    def test_split_version_pr_info_feeds_phase_h(
        self, atlas_mod, cfg_mod, h_db, cf_graph_env, tmp_path
    ):
        _write_split(tmp_path, "version_pr_info", {"numpy": {"new_version": "2.3.0"}})
        assert cfg_mod.default_tarball_path().name == "cf-graph-version_pr_info.tar.gz"

        res = atlas_mod.phase_h_pypi_versions(h_db)

        assert res["fetched"] == 1
        row = h_db.execute("SELECT pypi_current_version FROM packages "
                           "WHERE conda_name = 'numpy'").fetchone()
        assert row["pypi_current_version"] == "2.3.0"

    def test_a_cache_with_no_version_pr_info_skips(
        self, atlas_mod, h_db, cf_graph_env, tmp_path
    ):
        _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", _REDIRECTED_BOT_DATA)

        res = atlas_mod.phase_h_pypi_versions(h_db)

        assert res["skipped"] is True
        assert "holds no version_pr_info record" in res["reason"]
        tagged = h_db.execute("SELECT COUNT(*) FROM packages "
                              "WHERE pypi_version_source IS NOT NULL").fetchone()[0]
        assert tagged == 0


# ── Phase E ──────────────────────────────────────────────────────────────────

class TestPhaseE:
    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch):
        monkeypatch.setenv("PHASE_E_ENABLED", "1")
        monkeypatch.setenv("ATLAS_CFGRAPH_TTL_DAYS", "1")

    def test_an_offline_host_reads_a_legacy_cache(
        self, atlas_mod, atlas_db, offline, tmp_path
    ):
        _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", {
            "cf-graph-countyfair-master/node_attrs/n/u/m/numpy.json":
                {"meta_yaml": {"about": {"summary": "arrays"}}},
        })
        res = atlas_mod.phase_e_enrichment(atlas_db)
        assert res["node_attrs_records"] == 1
        assert res["fetch"]["node_attrs"]["error"].startswith("download failed")
        row = atlas_db.execute("SELECT conda_summary FROM packages "
                               "WHERE conda_name = 'numpy'").fetchone()
        assert row["conda_summary"] == "arrays"

    def test_no_record_is_an_error_and_keeps_the_force_refresh_trigger(
        self, atlas_mod, atlas_db, offline, tmp_path
    ):
        atlas_db.execute("INSERT OR REPLACE INTO meta(key, value) "
                         "VALUES ('phase_e_force_refresh_pending', '1')")
        atlas_db.commit()
        _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", _REDIRECTED_BOT_DATA)

        res = atlas_mod.phase_e_enrichment(atlas_db)

        assert res["node_attrs_records"] == 0
        assert "holds no node_attrs record" in res["error"]
        pending = atlas_db.execute("SELECT value FROM meta "
                                   "WHERE key = 'phase_e_force_refresh_pending'").fetchone()
        assert pending is not None

    def test_the_split_caches_retire_a_legacy_cache(self, atlas_mod, atlas_db, offline, tmp_path):
        legacy = _write_tar(tmp_path / "cf-graph-countyfair.tar.gz", _REDIRECTED_BOT_DATA)
        for kind in ("node_attrs", "pr_info", "version_pr_info", "pr_json"):
            _write_split(tmp_path, kind, {"numpy": {}})

        res = atlas_mod.phase_e_enrichment(atlas_db)

        assert not legacy.exists()
        assert res["node_attrs_records"] == 1

    def test_no_archive_at_all_skips(self, atlas_mod, atlas_db, offline):
        res = atlas_mod.phase_e_enrichment(atlas_db)
        assert res["skipped"] is True
        assert "no cf-graph node_attrs archive" in res["reason"]
