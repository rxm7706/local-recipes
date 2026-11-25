"""Steward 34.5: plane GraphStore refusals (FR-50) — no duckdb required.

Story 6.3 adds one exception: `test_stale_round_trips_against_live_duckdb`
below opens a real `PlaneGraphStore` against a tmp_path duckdb file and
skips (not fails) when the `duckdb` extra isn't installed -- unlike the
`postgres` durable-driver suite, duckdb is not a `pyforge-scribe` pixi
dependency, so a hard `pytest.fail` here would break the default
`pyforge-scribe-test` task.

Steward Story 136.6: the five tests below that open a real DuckDB file skip in
`-e pyforge-scribe` and run in `pixi run -e pyforge-foundry-full
scribe-plane-and-portal-test`, a step of the lint-types job, where a skip fails.
"""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.core.hooks import PluginError

from pyforge.scribe.graph_store_plane import ATLAS_DUCKDB_NAME, PlaneGraphStore, PlaneGraphStorePlugin
from pyforge.scribe.models import COMPILED_AT_ROW_ID, GraphNode
from pyforge.scribe.recall import _answer_semantic, answer

#: Where the DuckDB round trips run (steward Story 136.6); each importorskip below says so.
_RUNS_IN = "not in this environment; it runs in `pixi run -e pyforge-foundry-full scribe-plane-and-portal-test`"


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
    assert "query_similar" in answer.__code__.co_names or "query_similar" in (_answer_semantic.__code__.co_names)


def test_stale_round_trips_against_live_duckdb(tmp_path: Path) -> None:
    pytest.importorskip("duckdb", reason=_RUNS_IN)
    pytest.importorskip("pyforge.atlas.duckdb_writer", reason=_RUNS_IN)
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


def test_compile_stamp_round_trips_against_live_duckdb(tmp_path: Path) -> None:
    """Story 35.1: the stamp is one reserved row of `scribe_nodes`, never a node, and a stampless commit drops it."""
    duckdb = pytest.importorskip("duckdb", reason=_RUNS_IN)
    pytest.importorskip("pyforge.atlas.duckdb_writer", reason=_RUNS_IN)
    plane_path = tmp_path / ATLAS_DUCKDB_NAME
    store_path = tmp_path / "graph.json"
    stamp = datetime(2026, 11, 25, 12, 30, tzinfo=timezone.utc)
    node = GraphNode(
        id="memory:feedback/x",
        kind="memory",
        title="x",
        text="some captured text",
        citation=".claude/memory/feedback/x.md",
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    def _reserved_rows() -> tuple[int, int]:
        con = duckdb.connect(str(plane_path), read_only=True)
        try:
            counts = [
                con.execute(f"SELECT count(*) FROM {table} WHERE id = ?", [COMPILED_AT_ROW_ID]).fetchone()[0]
                for table in ("scribe_nodes", "scribe_embeddings")
            ]
        finally:
            con.close()
        return counts[0], counts[1]

    store = PlaneGraphStore(plane_path, store_path)
    try:
        store.reset()
        store.upsert_node(node)
        with pytest.raises(ValueError, match="reserved"):
            store.upsert_node(node.model_copy(update={"id": COMPILED_AT_ROW_ID}))
        store.compiled_at = stamp
        store.commit()
    finally:
        store.close()

    assert _reserved_rows() == (1, 0)
    reopened = PlaneGraphStore(plane_path, store_path, write=False)
    try:
        assert reopened.compiled_at == stamp
        assert [n.id for n in reopened.iter_nodes()] == [node.id]
        assert [n.id for n in reopened.query_similar("captured text", limit=8)] == [node.id]
    finally:
        reopened.close()

    writer = PlaneGraphStore(plane_path, store_path)
    try:
        assert writer.compiled_at == stamp
        writer.reset()
        assert writer.compiled_at is None
        writer.commit()
    finally:
        writer.close()

    assert _reserved_rows() == (0, 0)
    emptied = PlaneGraphStore(plane_path, store_path, write=False)
    try:
        assert emptied.compiled_at is None
        assert list(emptied.iter_nodes()) == []
    finally:
        emptied.close()


def test_read_only_open_never_calls_connect_writer(tmp_path: Path) -> None:
    pytest.importorskip("duckdb", reason=_RUNS_IN)
    pytest.importorskip("pyforge.atlas.duckdb_writer", reason=_RUNS_IN)
    from pyforge.atlas import duckdb_writer

    plane_path = tmp_path / ATLAS_DUCKDB_NAME
    writer = PlaneGraphStore(plane_path, tmp_path / "graph.json")
    try:
        writer.reset()
        writer.commit()
    finally:
        writer.close()

    def _forbidden_writer(*_args, **_kwargs):
        raise AssertionError("connect_writer must not run for write=False")

    original = duckdb_writer.connect_writer
    duckdb_writer.connect_writer = _forbidden_writer
    try:
        reopened = PlaneGraphStore(plane_path, tmp_path / "graph.json", write=False)
        try:
            assert list(reopened.iter_nodes()) == []
        finally:
            reopened.close()
    finally:
        duckdb_writer.connect_writer = original


def _seed_plane(plane_path: Path, store_path: Path) -> None:
    """A read-only open needs the plane file to exist: DuckDB refuses to create one read-only."""
    writer = PlaneGraphStore(plane_path, store_path)
    try:
        writer.reset()
        writer.commit()
    finally:
        writer.close()


def test_plugin_honors_write_false(tmp_path: Path) -> None:
    pytest.importorskip("duckdb", reason=_RUNS_IN)
    pytest.importorskip("pyforge.atlas.duckdb_writer", reason=_RUNS_IN)
    plane_path = tmp_path / ATLAS_DUCKDB_NAME
    _seed_plane(plane_path, tmp_path / "graph.json")
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


def test_plugin_write_string_false_is_not_writer(tmp_path: Path) -> None:
    pytest.importorskip("duckdb", reason=_RUNS_IN)
    pytest.importorskip("pyforge.atlas.duckdb_writer", reason=_RUNS_IN)
    plane_path = tmp_path / ATLAS_DUCKDB_NAME
    _seed_plane(plane_path, tmp_path / "graph.json")
    plugin = PlaneGraphStorePlugin()
    ctx: dict = {
        "store_path": tmp_path / "graph.json",
        "plane_path": plane_path,
        "write": "false",
    }
    plugin.call("around", ctx)
    store = ctx["store"]
    try:
        assert store._write is False
    finally:
        store.close()
