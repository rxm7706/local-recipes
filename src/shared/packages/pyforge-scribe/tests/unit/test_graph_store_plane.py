"""Steward 34.5: plane GraphStore refusals (FR-50) — no duckdb required.

Story 6.3 adds one exception: `test_stale_round_trips_against_live_duckdb`
below opens a real `PlaneGraphStore` against a tmp_path duckdb file and
skips (not fails) when the `duckdb` extra isn't installed -- unlike the
`postgres` durable-driver suite, duckdb is not a `pyforge-scribe` pixi
dependency, so a hard `pytest.fail` here would break the default
`pyforge-scribe-test` task.
"""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.core.hooks import PluginError
from pyforge.scribe.graph_store_plane import ATLAS_DUCKDB_NAME
from pyforge.scribe.graph_store_plane import PlaneGraphStore
from pyforge.scribe.graph_store_plane import PlaneGraphStorePlugin
from pyforge.scribe.models import GraphNode
from pyforge.scribe.recall import _answer_semantic
from pyforge.scribe.recall import answer


def test_chroma_and_memory_paths_fail(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match="atlas.duckdb"):
        PlaneGraphStore(tmp_path / "chroma.sqlite3", tmp_path / "graph.json")
    plugin = PlaneGraphStorePlugin()
    with pytest.raises(PluginError, match="Chroma"):
        plugin.call(
            "around",
            {"store_path": tmp_path / "g.json", "plane_path": tmp_path / "chroma"},
        )


def test_recall_callers_do_not_isinstance_the_driver() -> None:
    recall = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "recall.py"
    tree = ast.parse(recall.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            assert name != "isinstance"
    assert "query_similar" in answer.__code__.co_names or "query_similar" in (
        _answer_semantic.__code__.co_names
    )


def test_stale_round_trips_against_live_duckdb(tmp_path: Path) -> None:
    pytest.importorskip("duckdb")
    pytest.importorskip("pyforge.atlas.duckdb_writer")
    plane_path = tmp_path / ATLAS_DUCKDB_NAME
    node = GraphNode(
        id="memory:feedback/x",
        kind="memory",
        title="x",
        text="some captured text",
        citation=".claude/memory/feedback/x.md",
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
        stale=True,
    )

    store = PlaneGraphStore(plane_path, tmp_path / "graph.json")
    try:
        store.reset()
        store.upsert_node(node)
        store.commit()
    finally:
        store.close()

    reopened = PlaneGraphStore(plane_path, tmp_path / "graph.json", write=False)
    try:
        nodes = list(reopened.iter_nodes())
        assert [n.id for n in nodes] == ["memory:feedback/x"]
        assert nodes[0].stale is True
    finally:
        reopened.close()


def test_plugin_honors_write_false(tmp_path: Path) -> None:
    pytest.importorskip("duckdb")
    pytest.importorskip("pyforge.atlas.duckdb_writer")
    plane_path = tmp_path / ATLAS_DUCKDB_NAME
    plugin = PlaneGraphStorePlugin()
    ctx: dict = {
        "store_path": tmp_path / "graph.json",
        "plane_path": plane_path,
        "write": False,
    }
    plugin.call("around", ctx)
    store = ctx["store"]
    try:
        assert store._write is False
        with pytest.raises(PluginError, match="write=True"):
            store.commit()
    finally:
        store.close()
