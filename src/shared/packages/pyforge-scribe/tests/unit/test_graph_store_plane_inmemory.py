"""`PlaneGraphStore` against an in-memory stand-in for the plane connection -- no duckdb, no atlas.

`-e pyforge-scribe` carries neither duckdb nor atlas's DuckDB writer, so the real-DuckDB tests of
`test_graph_store_plane.py` skip there. These tests drive the same store through the two seams it
opens its connection by (`pyforge.atlas.duckdb_writer.connect_writer` for a writer, `duckdb.connect`
for a reader), each replaced in `sys.modules` by a stand-in that answers the statements the store
issues, so load, commit, ranking, the reserved compile-time row and every refusal run here.
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest
from pyforge.core.hooks import PluginError

from pyforge.scribe import graph_store_plane
from pyforge.scribe.embeddings import EMBEDDING_DIM, embed_text
from pyforge.scribe.graph_store_plane import (
    ATLAS_DUCKDB_NAME,
    PLANE_GRAPHSTORE_OWNER,
    PlaneGraphStore,
    PlaneGraphStorePlugin,
)
from pyforge.scribe.models import COMPILED_AT_ROW_ID, GraphNode

_NODE_COLUMNS = "id, kind, title, text, citation, valid_from, valid_until, superseded_by, stale"
_FROM = datetime(2026, 8, 1, tzinfo=timezone.utc)
_STAMP = datetime(2026, 11, 25, 12, 30, 15, 123456, tzinfo=timezone.utc)


class _Cursor:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple]:
        return list(self._rows)


class _Plane:
    """What one `atlas.duckdb` file holds: the two relations by id, and every connection opened on it."""

    def __init__(self) -> None:
        self.nodes: dict[str, list] = {}
        self.embeddings: dict[str, list[float]] = {}
        self.tables: set[str] = set()
        self.connections: list[_Connection] = []

    def connect(self, path: object, *, read_only: bool) -> _Connection:
        con = _Connection(self, path, read_only=read_only)
        self.connections.append(con)
        return con


class _Connection:
    """The statements `PlaneGraphStore` issues; anything else, or a write on a read-only open, fails the test."""

    def __init__(self, plane: _Plane, path: object, *, read_only: bool) -> None:
        self._plane = plane
        self.path = path
        self.read_only = read_only
        self.closed = False
        self.statements: list[str] = []

    def execute(self, query: str, params: list | None = None) -> _Cursor:
        assert not self.closed, "statement on a closed connection"
        text = " ".join(query.split())
        self.statements.append(text)
        plane = self._plane
        if text == f"SELECT {_NODE_COLUMNS} FROM scribe_nodes":
            return _Cursor([tuple(row) for _id, row in sorted(plane.nodes.items())])
        if text.startswith("SELECT n.id FROM scribe_embeddings e JOIN scribe_nodes n ON n.id = e.id"):
            assert "WHERE n.valid_until IS NULL AND (n.stale IS NULL OR NOT n.stale)" in text
            assert f"ORDER BY array_distance(e.emb, CAST(? AS FLOAT[{EMBEDDING_DIM}])) ASC, n.id ASC LIMIT ?" in text
            assert params is not None
            vector, limit = params
            assert isinstance(vector, list) and len(vector) == EMBEDDING_DIM
            ranked = sorted(
                (math.dist(emb, vector), node_id)
                for node_id, emb in plane.embeddings.items()
                if node_id in plane.nodes and plane.nodes[node_id][6] is None and not plane.nodes[node_id][8]
            )
            return _Cursor([(node_id,) for _distance, node_id in ranked[:limit]])
        assert not self.read_only, f"a read-only open issued a write: {text}"
        for table in ("scribe_nodes", "scribe_embeddings"):
            if text.startswith(f"CREATE TABLE IF NOT EXISTS {table} ("):
                plane.tables.add(table)
                return _Cursor([])
        if text == "ALTER TABLE scribe_nodes ADD COLUMN IF NOT EXISTS stale BOOLEAN":
            return _Cursor([])
        if text == "DELETE FROM scribe_nodes":
            plane.nodes.clear()
            return _Cursor([])
        if text == "DELETE FROM scribe_embeddings":
            plane.embeddings.clear()
            return _Cursor([])
        assert params is not None, text
        if text == "INSERT INTO scribe_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)":
            assert len(params) == 9
            assert params[0] not in plane.nodes, f"primary key {params[0]!r} inserted twice"
            plane.nodes[params[0]] = list(params)
            return _Cursor([])
        assert text == f"INSERT INTO scribe_embeddings VALUES (?, CAST(? AS FLOAT[{EMBEDDING_DIM}]))", text
        assert len(params[1]) == EMBEDDING_DIM
        plane.embeddings[params[0]] = list(params[1])
        return _Cursor([])

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def plane(monkeypatch: pytest.MonkeyPatch) -> _Plane:
    """One plane behind both seams: atlas's `connect_writer` (writer) and `duckdb.connect` (read-only)."""
    held = _Plane()
    atlas = ModuleType("pyforge.atlas")
    atlas.__path__ = []  # a package, so the store's `from pyforge.atlas.duckdb_writer import ...` resolves
    writer = ModuleType("pyforge.atlas.duckdb_writer")
    writer.connect_writer = lambda path: held.connect(path, read_only=False)  # type: ignore[attr-defined]
    duckdb = ModuleType("duckdb")

    def _connect(database: str, *, read_only: bool = False) -> _Connection:
        assert read_only is True, "the store's own duckdb.connect is the read-only open"
        return held.connect(database, read_only=read_only)

    duckdb.connect = _connect  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyforge.atlas", atlas)
    monkeypatch.setitem(sys.modules, "pyforge.atlas.duckdb_writer", writer)
    monkeypatch.setitem(sys.modules, "duckdb", duckdb)
    return held


def _node(node_id: str, title: str, text: str, **fields: object) -> GraphNode:
    values: dict[str, object] = {
        "id": node_id,
        "kind": "memory",
        "title": title,
        "text": text,
        "citation": f"notes/feedback/{title}.md",
        "valid_from": _FROM,
    }
    values.update(fields)
    return GraphNode(**values)  # type: ignore[arg-type]


def _paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / ATLAS_DUCKDB_NAME, tmp_path / "graph.json"


# --- construction -----------------------------------------------------------------------------------------------


def test_a_plane_path_that_is_not_atlas_duckdb_is_refused_before_any_connection(tmp_path: Path, plane: _Plane) -> None:
    for wrong in (tmp_path / "scribe.duckdb", Path(":memory:"), Path("")):
        with pytest.raises(PluginError, match=r"plane store must be atlas\.duckdb"):
            PlaneGraphStore(wrong, tmp_path / "graph.json")
    assert plane.connections == []


def test_a_writer_opens_through_connect_writer_and_creates_both_relations(tmp_path: Path, plane: _Plane) -> None:
    plane_path, store_path = _paths(tmp_path)

    store = PlaneGraphStore(plane_path, store_path)

    assert (store.plane_path, store.store_path) == (plane_path, store_path)
    assert [(con.path, con.read_only) for con in plane.connections] == [(plane_path, False)]
    assert plane.tables == {"scribe_nodes", "scribe_embeddings"}
    statements = plane.connections[0].statements
    assert statements[1] == "ALTER TABLE scribe_nodes ADD COLUMN IF NOT EXISTS stale BOOLEAN"
    assert f"emb FLOAT[{EMBEDDING_DIM}]" in statements[2]
    assert statements[3] == f"SELECT {_NODE_COLUMNS} FROM scribe_nodes"
    assert list(store.iter_nodes()) == []
    assert store.compiled_at is None


def test_a_reader_opens_duckdb_read_only_and_issues_no_ddl(tmp_path: Path, plane: _Plane) -> None:
    plane_path, store_path = _paths(tmp_path)

    store = PlaneGraphStore(plane_path, store_path, write=False)

    assert [(con.path, con.read_only) for con in plane.connections] == [(str(plane_path), True)]
    assert plane.connections[0].statements == [f"SELECT {_NODE_COLUMNS} FROM scribe_nodes"]
    assert plane.tables == set()
    assert list(store.iter_nodes()) == []


def test_a_reader_never_reaches_for_the_atlas_writer(
    tmp_path: Path, plane: _Plane, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _forbidden(_path: object) -> None:
        raise AssertionError("connect_writer must not run for write=False")

    monkeypatch.setattr(sys.modules["pyforge.atlas.duckdb_writer"], "connect_writer", _forbidden)

    store = PlaneGraphStore(*_paths(tmp_path), write=False)

    assert plane.connections[0].read_only is True
    assert store._write is False


def test_a_writer_without_atlas_is_refused_naming_the_missing_writer(
    tmp_path: Path, plane: _Plane, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "pyforge.atlas", None)
    monkeypatch.setitem(sys.modules, "pyforge.atlas.duckdb_writer", None)

    with pytest.raises(PluginError, match=r"require pyforge-atlas \(duckdb_writer\.connect_writer\)") as refused:
        PlaneGraphStore(*_paths(tmp_path))

    assert isinstance(refused.value.__cause__, ImportError)
    assert plane.connections == []


def test_a_reader_without_duckdb_is_refused_naming_duckdb(
    tmp_path: Path, plane: _Plane, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "duckdb", None)

    with pytest.raises(PluginError, match="plane graph-store requires duckdb") as refused:
        PlaneGraphStore(*_paths(tmp_path), write=False)

    assert isinstance(refused.value.__cause__, ImportError)
    assert plane.connections == []
    with pytest.raises(PluginError, match="requires duckdb"):
        graph_store_plane._import_duckdb()


def test_import_duckdb_returns_the_module_when_it_is_installed(plane: _Plane) -> None:
    assert graph_store_plane._import_duckdb() is sys.modules["duckdb"]


# --- commit and load --------------------------------------------------------------------------------------------


def test_commit_writes_every_field_and_a_reader_loads_the_same_nodes(tmp_path: Path, plane: _Plane) -> None:
    ended = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    live = _node("memory:feedback/dog", "dog", "the dog chased a ball")
    retired = _node(
        "memory:feedback/old", "old", "an earlier ruling", valid_until=ended, superseded_by="memory:feedback/dog"
    )
    stale = _node("memory:feedback/stale", "stale", "a cat on a mat", stale=True)
    writer = PlaneGraphStore(*_paths(tmp_path))
    for node in (stale, live, retired):
        writer.upsert_node(node)

    writer.commit()
    writer.close()

    assert plane.connections[0].closed is True
    assert plane.nodes["memory:feedback/old"] == [
        "memory:feedback/old",
        "memory",
        "old",
        "an earlier ruling",
        "notes/feedback/old.md",
        _FROM.isoformat(),
        ended.isoformat(),
        "memory:feedback/dog",
        False,
    ]
    assert plane.nodes["memory:feedback/dog"][6:] == [None, None, False]
    assert plane.nodes["memory:feedback/stale"][8] is True
    assert set(plane.embeddings) == {live.id, retired.id, stale.id}
    assert plane.embeddings[live.id] == list(embed_text("dog the dog chased a ball") or ())

    reader = PlaneGraphStore(*_paths(tmp_path), write=False)
    assert list(reader.iter_nodes()) == [live, retired, stale]  # sorted by id, every field round-tripped
    assert reader.compiled_at is None


def test_commit_replaces_the_snapshot_rather_than_appending(tmp_path: Path, plane: _Plane) -> None:
    first = _node("memory:feedback/a", "a", "alpha ruling")
    second = _node("memory:feedback/b", "b", "beta ruling")
    writer = PlaneGraphStore(*_paths(tmp_path))
    writer.upsert_node(first)
    writer.upsert_node(second)
    writer.commit()

    writer.reset()
    assert list(writer.iter_nodes()) == []
    writer.upsert_node(second.model_copy(update={"text": "beta ruling, revised"}))
    writer.commit()  # a second commit on one connection: the fake refuses a duplicate primary key

    assert set(plane.nodes) == {second.id}
    assert set(plane.embeddings) == {second.id}
    assert plane.nodes[second.id][3] == "beta ruling, revised"
    reopened = PlaneGraphStore(*_paths(tmp_path))
    assert [n.text for n in reopened.iter_nodes()] == ["beta ruling, revised"]


def test_a_node_with_nothing_to_embed_is_stored_without_an_embedding_row(tmp_path: Path, plane: _Plane) -> None:
    wordless = _node("memory:feedback/blank", "", "the of and")
    assert embed_text(f"{wordless.title} {wordless.text}") is None
    writer = PlaneGraphStore(*_paths(tmp_path))
    writer.upsert_node(wordless)
    writer.upsert_node(_node("memory:feedback/dog", "dog", "a puppy"))

    writer.commit()

    assert set(plane.nodes) == {"memory:feedback/blank", "memory:feedback/dog"}
    assert set(plane.embeddings) == {"memory:feedback/dog"}
    reader = PlaneGraphStore(*_paths(tmp_path), write=False)
    assert [n.id for n in reader.iter_nodes()] == ["memory:feedback/blank", "memory:feedback/dog"]
    assert reader.query_similar("the of and") == []  # the query embeds to nothing either
    assert [n.id for n in reader.query_similar("dog")] == ["memory:feedback/dog"]


def test_commit_on_a_read_only_store_is_refused_and_writes_nothing(tmp_path: Path, plane: _Plane) -> None:
    writer = PlaneGraphStore(*_paths(tmp_path))
    kept = _node("memory:feedback/kept", "kept", "kept ruling")
    writer.upsert_node(kept)
    writer.commit()
    reader = PlaneGraphStore(*_paths(tmp_path), write=False)
    reader.reset()  # in-memory only: the plane keeps its row

    with pytest.raises(PluginError, match=r"commit requires write=True \(writer process only\)"):
        reader.commit()

    assert set(plane.nodes) == {kept.id}
    assert plane.connections[-1].statements == [f"SELECT {_NODE_COLUMNS} FROM scribe_nodes"]


def test_close_closes_the_connection_the_store_opened(tmp_path: Path, plane: _Plane) -> None:
    writer = PlaneGraphStore(*_paths(tmp_path))
    reader = PlaneGraphStore(*_paths(tmp_path), write=False)

    reader.close()

    assert [con.closed for con in plane.connections] == [False, True]
    writer.close()
    assert [con.closed for con in plane.connections] == [True, True]


# --- the reserved compile-time row (Story 35.1) -----------------------------------------------------------------


def test_the_compile_time_is_one_reserved_row_and_never_a_node(tmp_path: Path, plane: _Plane) -> None:
    node = _node("memory:feedback/dog", "dog", "the dog chased a ball")
    writer = PlaneGraphStore(*_paths(tmp_path))
    writer.upsert_node(node)
    writer.compiled_at = _STAMP

    writer.commit()

    stamp = _STAMP.isoformat()
    assert plane.nodes[COMPILED_AT_ROW_ID] == [COMPILED_AT_ROW_ID, "doc", "", "", "", stamp, stamp, None, True]
    assert COMPILED_AT_ROW_ID not in plane.embeddings
    for write in (False, True):
        reopened = PlaneGraphStore(*_paths(tmp_path), write=write)
        assert reopened.compiled_at == _STAMP
        assert list(reopened.iter_nodes()) == [node]
        assert reopened.query_by_citation("") == []
        assert [n.id for n in reopened.query_similar("dog ball", limit=8)] == [node.id]


def test_reset_drops_the_compile_time_and_the_next_commit_removes_its_row(tmp_path: Path, plane: _Plane) -> None:
    writer = PlaneGraphStore(*_paths(tmp_path))
    writer.upsert_node(_node("memory:feedback/dog", "dog", "the dog chased a ball"))
    writer.compiled_at = _STAMP
    writer.commit()
    assert COMPILED_AT_ROW_ID in plane.nodes

    reopened = PlaneGraphStore(*_paths(tmp_path))
    assert reopened.compiled_at == _STAMP
    reopened.reset()
    assert reopened.compiled_at is None
    reopened.commit()

    assert plane.nodes == {}
    assert plane.embeddings == {}
    emptied = PlaneGraphStore(*_paths(tmp_path), write=False)
    assert emptied.compiled_at is None
    assert list(emptied.iter_nodes()) == []


def test_a_reload_with_no_reserved_row_clears_a_compile_time_held_in_memory(tmp_path: Path, plane: _Plane) -> None:
    store = PlaneGraphStore(*_paths(tmp_path))
    store.compiled_at = _STAMP  # set, never committed

    store._load()

    assert store.compiled_at is None


def test_the_reserved_id_cannot_be_upserted_as_a_node(tmp_path: Path, plane: _Plane) -> None:
    store = PlaneGraphStore(*_paths(tmp_path))

    with pytest.raises(ValueError, match="reserved for the store's compile time"):
        store.upsert_node(_node(COMPILED_AT_ROW_ID, "x", "some text"))

    assert list(store.iter_nodes()) == []
    store.commit()
    assert plane.nodes == {}


# --- the in-memory snapshot -------------------------------------------------------------------------------------


def test_upsert_replaces_by_id_and_iter_nodes_orders_by_id(tmp_path: Path, plane: _Plane) -> None:
    store = PlaneGraphStore(*_paths(tmp_path))
    store.upsert_node(_node("memory:feedback/b", "b", "first text"))
    store.upsert_node(_node("memory:feedback/a", "a", "alpha"))
    store.upsert_node(_node("memory:feedback/b", "b", "second text"))

    assert [(n.id, n.text) for n in store.iter_nodes()] == [
        ("memory:feedback/a", "alpha"),
        ("memory:feedback/b", "second text"),
    ]
    assert plane.nodes == {}  # nothing reaches the plane before commit


def test_query_by_citation_returns_exactly_the_nodes_citing_it(tmp_path: Path, plane: _Plane) -> None:
    store = PlaneGraphStore(*_paths(tmp_path))
    shared = "notes/shared-source.md"
    one = _node("doc:one", "one", "first", citation=shared)
    two = _node("doc:two", "two", "second", citation=shared)
    other = _node("doc:other", "other", "third")
    for node in (one, other, two):
        store.upsert_node(node)

    assert store.query_by_citation(shared) == [one, two]
    assert store.query_by_citation(other.citation) == [other]
    assert store.query_by_citation("docs/missing.md") == []


def test_invalidate_edge_ends_validity_and_survives_a_commit(tmp_path: Path, plane: _Plane) -> None:
    ended = datetime(2026, 10, 2, 9, 30, tzinfo=timezone.utc)
    store = PlaneGraphStore(*_paths(tmp_path))
    old = _node("memory:feedback/old", "old", "the dog ruling")
    store.upsert_node(old)
    store.upsert_node(_node("memory:feedback/new", "new", "the cat ruling"))

    store.invalidate_edge(old.id, ended_at=ended, superseded_by="memory:feedback/new")
    store.commit()

    reader = PlaneGraphStore(*_paths(tmp_path), write=False)
    reloaded = {n.id: n for n in reader.iter_nodes()}
    assert reloaded[old.id] == old.model_copy(update={"valid_until": ended, "superseded_by": "memory:feedback/new"})
    assert reloaded["memory:feedback/new"].valid_until is None
    assert [n.id for n in reader.query_similar("dog")] == ["memory:feedback/new"]  # an ended node is never ranked


def test_invalidate_edge_on_an_unknown_node_is_refused(tmp_path: Path, plane: _Plane) -> None:
    store = PlaneGraphStore(*_paths(tmp_path))

    with pytest.raises(ValueError, match="cannot invalidate unknown node id 'memory:feedback/ghost'"):
        store.invalidate_edge("memory:feedback/ghost", ended_at=_FROM, superseded_by="memory:feedback/x")

    assert list(store.iter_nodes()) == []


# --- ranking ----------------------------------------------------------------------------------------------------


def _ranked_plane(tmp_path: Path) -> PlaneGraphStore:
    writer = PlaneGraphStore(*_paths(tmp_path))
    writer.upsert_node(_node("memory:feedback/dog", "dog", "a puppy and a hound"))
    writer.upsert_node(_node("memory:feedback/cat", "cat", "a kitten"))
    writer.upsert_node(_node("memory:feedback/mixed", "mixed", "a dog met a cat near a lighthouse"))
    writer.upsert_node(_node("memory:feedback/stale", "stale", "dog dog dog", stale=True))
    writer.upsert_node(
        _node("memory:feedback/ended", "ended", "dog dog dog", valid_until=_STAMP, superseded_by="memory:feedback/dog")
    )
    writer.commit()
    return PlaneGraphStore(*_paths(tmp_path), write=False)


def test_query_similar_ranks_by_distance_and_skips_stale_and_ended_nodes(tmp_path: Path, plane: _Plane) -> None:
    reader = _ranked_plane(tmp_path)

    canine = [n.id for n in reader.query_similar("canine")]
    feline = [n.id for n in reader.query_similar("feline")]

    assert canine[0] == "memory:feedback/dog"
    assert feline[0] == "memory:feedback/cat"
    assert set(canine) == set(feline) == {"memory:feedback/dog", "memory:feedback/cat", "memory:feedback/mixed"}
    assert canine.index("memory:feedback/mixed") < canine.index("memory:feedback/cat")


def test_query_similar_honours_the_limit_and_a_non_positive_limit_asks_nothing(tmp_path: Path, plane: _Plane) -> None:
    reader = _ranked_plane(tmp_path)
    connection = plane.connections[-1]
    issued = len(connection.statements)

    assert reader.query_similar("canine", limit=0) == []
    assert reader.query_similar("canine", limit=-3) == []
    assert reader.query_similar("the of and") == []
    assert len(connection.statements) == issued  # none of the three reached the plane

    assert [n.id for n in reader.query_similar("canine", limit=1)] == ["memory:feedback/dog"]
    assert len(reader.query_similar("canine", limit=2)) == 2
    assert len(connection.statements) == issued + 2


def test_query_similar_drops_a_plane_row_the_snapshot_no_longer_holds(tmp_path: Path, plane: _Plane) -> None:
    reader = _ranked_plane(tmp_path)
    reader.reset()  # the plane still ranks three rows; the in-memory snapshot holds none

    assert reader.query_similar("canine") == []


# --- the CAP-18 plugin ------------------------------------------------------------------------------------------


def test_plugin_declares_the_graph_store_hook_under_owner_atlas() -> None:
    plugin = PlaneGraphStorePlugin()

    assert plugin.owner == PLANE_GRAPHSTORE_OWNER == "atlas"
    assert plugin.hook_spec == graph_store_plane.GRAPHSTORE_HOOK_SPEC.name


def test_plugin_around_builds_a_writer_store_by_default(tmp_path: Path, plane: _Plane) -> None:
    plane_path, store_path = _paths(tmp_path)
    context: dict = {"store_path": str(store_path), "plane_path": str(plane_path)}

    returned = PlaneGraphStorePlugin().call("around", context)

    store = context["store"]
    assert returned is context
    assert isinstance(store, PlaneGraphStore)
    assert (store.plane_path, store.store_path, store._write) == (plane_path, store_path, True)
    assert plane.connections[0].read_only is False


@pytest.mark.parametrize("write", [False, "false", "true", 1, None])
def test_plugin_opens_a_writer_only_for_a_literal_true(tmp_path: Path, plane: _Plane, write: object) -> None:
    plane_path, store_path = _paths(tmp_path)
    context: dict = {"store_path": store_path, "plane_path": plane_path, "write": write}

    PlaneGraphStorePlugin().call("around", context)

    assert context["store"]._write is False
    assert [con.read_only for con in plane.connections] == [True]
    with pytest.raises(PluginError, match="write=True"):
        context["store"].commit()


def test_plugin_around_hands_the_context_to_the_next_link(tmp_path: Path, plane: _Plane) -> None:
    plane_path, store_path = _paths(tmp_path)
    seen: list[PlaneGraphStore] = []

    def _next(context: dict) -> str:
        seen.append(context["store"])
        return "ran"

    context: dict = {"store_path": store_path, "plane_path": plane_path, "next": _next}

    assert PlaneGraphStorePlugin().call("around", context) == "ran"
    assert seen == [context["store"]]

    context["next"] = "not callable"
    assert PlaneGraphStorePlugin().call("around", context) is context


@pytest.mark.parametrize("missing", ["store_path", "plane_path"])
def test_plugin_around_refuses_a_context_missing_either_path(tmp_path: Path, plane: _Plane, missing: str) -> None:
    plane_path, store_path = _paths(tmp_path)
    context: dict = {"store_path": store_path, "plane_path": plane_path}
    del context[missing]

    with pytest.raises(PluginError, match="requires store_path and plane_path"):
        PlaneGraphStorePlugin().call("around", context)

    assert "store" not in context
    assert plane.connections == []


def test_plugin_around_refuses_a_chroma_plane_whatever_its_case(tmp_path: Path, plane: _Plane) -> None:
    context: dict = {"store_path": tmp_path / "graph.json", "plane_path": tmp_path / "Chroma" / ATLAS_DUCKDB_NAME}

    with pytest.raises(PluginError, match="Chroma is not the query plane"):
        PlaneGraphStorePlugin().call("around", context)

    assert "store" not in context
    assert plane.connections == []


def test_plugin_ignores_every_point_but_around(plane: _Plane) -> None:
    context: dict = {"marker": 1}

    for point in ("before", "after", "on_error"):
        assert PlaneGraphStorePlugin().call(point, context) is context

    assert context == {"marker": 1}
    assert plane.connections == []
