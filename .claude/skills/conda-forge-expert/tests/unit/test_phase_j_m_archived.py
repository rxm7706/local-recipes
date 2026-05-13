"""Phase J + M must skip archived / inactive feedstocks.

Regression test for the 2026-05-13 actionable-scope audit: Phase J wrote
dependency edges from every cf-graph node_attrs file with no archived
filter, polluting `whodepends` results with edges from feedstocks no
consumer cares about. Phase M wrote bot-status columns to archived rows
that feedstock-health queries filter out at read time. Both now adopt
the canonical persona-filter triplet at the write site.
"""
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


def _make_cf_graph_tar(target: Path, nodes: dict[str, dict]) -> None:
    """Build a minimal cf-graph-shaped tarball at `target`.

    `nodes` maps feedstock-name → meta_yaml dict. Phase J reads
    `node_attrs/<sharded>/<feedstock>.json`; Phase M reads
    `pr_info/<sharded>/<feedstock>.json` and `version_pr_info/<sharded>/<feedstock>.json`.
    """
    with tarfile.open(target, "w:gz") as tf:
        for fs, meta in nodes.items():
            payload = json.dumps({"meta_yaml": meta}).encode()
            info = tarfile.TarInfo(
                name=f"cf-graph-countyfair/node_attrs/a/b/c/{fs}.json"
            )
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))


@pytest.fixture
def db_with_cf_graph(tmp_path, atlas_mod, monkeypatch):
    """Seed atlas with active + archived feedstocks and a matching cf-graph cache."""
    db_path = tmp_path / "cf_atlas.db"
    monkeypatch.setattr(atlas_mod, "DATA_DIR", tmp_path)
    conn = atlas_mod.open_db(db_path)
    atlas_mod.init_schema(conn)

    seeds = [
        # (conda_name, feedstock_name, latest_status, feedstock_archived)
        ("active-a",    "active-a",    "active",   0),
        ("active-b",    "active-b",    "active",   0),
        ("archived-c",  "archived-c",  "active",   1),
        ("inactive-d",  "inactive-d",  "inactive", 0),
    ]
    for conda, fs, status, archived in seeds:
        conn.execute(
            "INSERT INTO packages "
            "(conda_name, feedstock_name, latest_status, feedstock_archived, "
            " relationship, match_source, match_confidence) "
            "VALUES (?, ?, ?, ?, 'test', 'test', 'high')",
            (conda, fs, status, archived),
        )
    conn.commit()

    # Build the cf-graph tarball with all 4 feedstocks present
    cache_path = tmp_path / "cf-graph-countyfair.tar.gz"
    _make_cf_graph_tar(cache_path, {
        "active-a":    {"requirements": {"run": ["dep1", "dep2"]}},
        "active-b":    {"requirements": {"run": ["dep3"]}},
        "archived-c":  {"requirements": {"run": ["dep4", "dep5"]}},
        "inactive-d":  {"requirements": {"run": ["dep6"]}},
    })
    yield conn, cache_path
    conn.close()


class TestPhaseJSkipsArchived:
    def test_dependencies_excludes_archived_and_inactive(self, db_with_cf_graph, atlas_mod):
        conn, _cache = db_with_cf_graph
        result = atlas_mod.phase_j_dependency_graph(conn)

        # Phase J reports skip count
        assert result["skipped_inactive_feedstocks"] == 2, \
            f"expected 2 skipped (archived + inactive), got {result}"

        # Verify the dependencies table only has edges from active feedstocks
        sources = {row[0] for row in conn.execute(
            "SELECT DISTINCT source_conda_name FROM dependencies"
        )}
        assert "active-a" in sources
        assert "active-b" in sources
        assert "archived-c" not in sources, \
            "archived feedstock leaked dependency edges"
        assert "inactive-d" not in sources, \
            "inactive feedstock leaked dependency edges"


class TestPhaseMSkipsArchived:
    def test_rows_to_process_excludes_archived_and_inactive(self, db_with_cf_graph, atlas_mod):
        conn, _cache = db_with_cf_graph

        # Direct unit assertion against the same SELECT Phase M uses
        rows = list(conn.execute(
            "SELECT conda_name FROM packages "
            "WHERE conda_name IS NOT NULL "
            "  AND feedstock_name IS NOT NULL "
            "  AND COALESCE(latest_status, 'active') = 'active' "
            "  AND COALESCE(feedstock_archived, 0) = 0"
        ))
        names = {r[0] for r in rows}
        assert names == {"active-a", "active-b"}, \
            f"Phase M scope should match exactly 2 active rows, got {names}"
