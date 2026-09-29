"""GraphStore driver on the CAP-19 plane (steward 34.5, FR-50).

Embeddings and nearest-neighbor live in ``atlas.duckdb``. DuckDB is imported
lazily so declaring the CAP-18 entry point does not require duckdb until
``around`` constructs a store.
"""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from datetime import datetime
from pathlib import Path
from typing import Any

from pyforge.core.hooks import PluginError

from pyforge.scribe.embeddings import EMBEDDING_DIM, embed_text
from pyforge.scribe.graph_store import GRAPHSTORE_HOOK_SPEC
from pyforge.scribe.models import GraphNode as GraphNodeModel

PLANE_GRAPHSTORE_OWNER = "atlas"
ATLAS_DUCKDB_NAME = "atlas.duckdb"


def _import_duckdb():
    try:
        import duckdb
    except ImportError as exc:
        raise PluginError("plane graph-store requires duckdb (query plane / CAP-19)") from exc
    return duckdb


class PlaneGraphStore:
    """Concrete ``GraphStore``: node snapshot + ``FLOAT[N]`` ranking on ``atlas.duckdb``."""

    def __init__(
        self,
        plane_path: Path,
        store_path: Path,
        *,
        write: bool = True,
    ) -> None:
        path = Path(plane_path)
        if path.name != ATLAS_DUCKDB_NAME:
            raise PluginError(f"plane store must be {ATLAS_DUCKDB_NAME}, got {path.name!r}")
        if str(path) in {":memory:", ""} or path.as_posix() == ":memory:":
            raise PluginError("in-memory DuckDB is not the query plane")
        self.plane_path = path
        self.store_path = Path(store_path)
        self._nodes: dict[str, GraphNodeModel] = {}
        self._write = write
        self._con = self._open_plane(path, write=write)
        if write:
            self._ensure_tables()
        self._load()

    def _open_plane(self, path: Path, *, write: bool):
        if write:
            try:
                from pyforge.atlas.duckdb_writer import connect_writer
            except ImportError as exc:
                raise PluginError(
                    "plane graph-store writes require pyforge-atlas (duckdb_writer.connect_writer)"
                ) from exc
            return connect_writer(path)
        duckdb = _import_duckdb()
        return duckdb.connect(str(path), read_only=True)

    def _ensure_tables(self) -> None:
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS scribe_nodes ("
            "id VARCHAR PRIMARY KEY, kind VARCHAR, title VARCHAR, text VARCHAR, "
            "citation VARCHAR, valid_from VARCHAR, valid_until VARCHAR, superseded_by VARCHAR, "
            "stale BOOLEAN)"
        )
        # Story 6.3: a table created by a pre-6.3 version of this module
        # already exists (the CREATE above is a no-op for it) -- add the
        # column so `stale` persists across a commit/reload for this
        # backend too, matching Story 2.3's `valid_until`/`superseded_by`
        # precedent.
        self._con.execute("ALTER TABLE scribe_nodes ADD COLUMN IF NOT EXISTS stale BOOLEAN")
        self._con.execute(
            f"CREATE TABLE IF NOT EXISTS scribe_embeddings (id VARCHAR PRIMARY KEY, emb FLOAT[{EMBEDDING_DIM}])"
        )

    def _load(self) -> None:
        rows = self._con.execute(
            "SELECT id, kind, title, text, citation, valid_from, valid_until, superseded_by, stale FROM scribe_nodes"
        ).fetchall()
        loaded: dict[str, GraphNodeModel] = {}
        for row in rows:
            until = datetime.fromisoformat(row[6]) if row[6] else None
            loaded[row[0]] = GraphNodeModel(
                id=row[0],
                kind=row[1],
                title=row[2],
                text=row[3],
                citation=row[4],
                valid_from=datetime.fromisoformat(row[5]),
                valid_until=until,
                superseded_by=row[7],
                stale=bool(row[8]),
            )
        self._nodes = loaded

    def reset(self) -> None:
        self._nodes = {}

    def upsert_node(self, node: GraphNodeModel) -> None:
        self._nodes[node.id] = node

    def invalidate_edge(self, node_id: str, *, ended_at: datetime, superseded_by: str) -> None:
        existing = self._nodes.get(node_id)
        if existing is None:
            raise ValueError(f"cannot invalidate unknown node id {node_id!r}")
        self._nodes[node_id] = existing.model_copy(update={"valid_until": ended_at, "superseded_by": superseded_by})

    def query_by_citation(self, citation: str) -> list[GraphNodeModel]:
        return [node for node in self._nodes.values() if node.citation == citation]

    def iter_nodes(self) -> Iterator[GraphNodeModel]:
        return iter(sorted(self._nodes.values(), key=lambda n: n.id))

    def query_similar(self, query: str, *, limit: int = 8) -> list[GraphNodeModel]:
        vector = embed_text(query)
        if vector is None or limit <= 0:
            return []
        rows = self._con.execute(
            f"SELECT n.id FROM scribe_embeddings e "
            f"JOIN scribe_nodes n ON n.id = e.id "
            f"WHERE n.valid_until IS NULL "
            f"AND (n.stale IS NULL OR NOT n.stale) "
            f"ORDER BY array_distance(e.emb, CAST(? AS FLOAT[{EMBEDDING_DIM}])) ASC, n.id ASC "
            f"LIMIT ?",
            [list(vector), int(limit)],
        ).fetchall()
        return [self._nodes[row[0]] for row in rows if row[0] in self._nodes]

    def commit(self) -> None:
        if not self._write:
            msg = "plane graph-store commit requires write=True (writer process only)"
            raise PluginError(msg)
        snapshot = list(self._nodes.values())
        self._con.execute("DELETE FROM scribe_nodes")
        self._con.execute("DELETE FROM scribe_embeddings")
        for node in snapshot:
            self._con.execute(
                "INSERT INTO scribe_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    node.id,
                    node.kind,
                    node.title,
                    node.text,
                    node.citation,
                    node.valid_from.isoformat(),
                    node.valid_until.isoformat() if node.valid_until else None,
                    node.superseded_by,
                    node.stale,
                ],
            )
            embedding = embed_text(f"{node.title} {node.text}")
            if embedding is None:
                continue
            self._con.execute(
                f"INSERT INTO scribe_embeddings VALUES (?, CAST(? AS FLOAT[{EMBEDDING_DIM}]))",
                [node.id, list(embedding)],
            )

    def close(self) -> None:
        self._con.close()


class PlaneGraphStorePlugin:
    """CAP-18 adapter: owner ``atlas`` — the plane, not a private Chroma."""

    hook_spec: str = GRAPHSTORE_HOOK_SPEC.name
    owner: str = PLANE_GRAPHSTORE_OWNER

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            store_path = context.get("store_path")
            plane_path = context.get("plane_path")
            if store_path is None or plane_path is None:
                raise PluginError("plane graph-store requires store_path and plane_path")
            if "chroma" in str(plane_path).lower():
                raise PluginError("Chroma is not the query plane")
            write = context.get("write", True) is True
            context["store"] = PlaneGraphStore(
                Path(plane_path),
                Path(store_path),
                write=write,
            )
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context
