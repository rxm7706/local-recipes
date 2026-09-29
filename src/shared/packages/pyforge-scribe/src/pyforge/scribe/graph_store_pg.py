"""PostgreSQL/pgvector GraphStore adapter (steward Story 28.1, CAP-14 / FR-35).

The first durable driver behind the existing ``GraphStore`` port. Engine
client imports stay in this module (parent AD-5). ``psycopg`` is imported
lazily so declaring the CAP-18 entry point does not require the extra until
``around`` constructs a store.

Schema isolation: relations live in ``scribe_schema`` only, on the same
PostgreSQL instance as the rest of the estate (parent AD-1 — not a fourth
kind). Story 28.2 fills ``embedding`` on commit and ranks with ``<=>``
(cosine distance).

DDL governance (Story 41.3, CAP-9 / red-team S-4): this module executes no
DDL. The pgvector extension, ``scribe_schema`` and ``graph_nodes`` are
Liquibase changesets ``pyforge-scribe:1``–``:4``, applied by the migration
role. The runtime role holds DML only, so construction *asserts* the
relation is present and raises :class:`GraphSchemaMissing` when it is not.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, MutableMapping
from datetime import datetime
from pathlib import Path
from typing import Any

from pyforge.core.hooks import PluginError

from pyforge.scribe.embeddings import embed_text, vector_literal
from pyforge.scribe.graph_store import GRAPHSTORE_HOOK_SPEC, PG_GRAPHSTORE_OWNER
from pyforge.scribe.models import GraphNode

SCRIBE_SCHEMA = "scribe_schema"
GRAPH_TABLE = "graph_nodes"
GRAPH_CHANGESET_ID = "pyforge-scribe:2"
GRANTS_CHANGESET_ID = "pyforge-scribe:3"
_GRAPH_LOCK_KEY = 0x53435242  # "SCRB"
_DSN_ENV = "SCRIBE_GRAPH_DSN"


class GraphSchemaMissing(PluginError):
    """Scribe's governed relations are absent — Liquibase has not run.

    The named failure Story 41.3 requires: the runtime role cannot create
    them (CAP-9), so the only honest response is to say which changeset is
    missing rather than to widen the role.
    """


def _import_psycopg():
    try:
        import psycopg
        from psycopg import sql
    except ImportError as exc:
        raise PluginError(
            "PostgreSQL graph-store requires psycopg (install the pyforge-scribe postgres extra)"
        ) from exc
    return psycopg, sql


def _normalize_dsn(dsn: str) -> str:
    return dsn.split("?", 1)[0]


def resolve_graph_dsn(context: MutableMapping[str, Any] | None = None) -> str | None:
    if context is not None:
        raw = context.get("dsn")
        if isinstance(raw, str) and raw.strip():
            return _normalize_dsn(raw)
    env = os.environ.get(_DSN_ENV) or os.environ.get("DATABASE_URL")
    if env and env.strip():
        return _normalize_dsn(env)
    return None


class PostgresGraphStore:
    """Concrete ``GraphStore``: PostgreSQL rows in ``scribe_schema.graph_nodes``.

    In-memory mutate + one transactional ``commit()`` matches FlatFile
    last-writer-wins: racing commits serialize on ``pg_advisory_xact_lock``
    and each replaces the full snapshot, never a torn mix of two writers.
    ``store_path`` is retained for ``compile_graph``'s ``getattr(store,
    "store_path")`` seam and must not become a JSON document.
    """

    def __init__(
        self,
        dsn: str,
        store_path: Path,
        *,
        schema: str = SCRIBE_SCHEMA,
    ) -> None:
        if not dsn or not str(dsn).strip():
            raise PluginError("PostgreSQL graph-store requires a DSN")
        self.store_path = Path(store_path)
        self.dsn = _normalize_dsn(dsn)
        self.schema = schema
        self._nodes: dict[str, GraphNode] = {}
        self._assert_provisioned()
        self._load()

    def _connect(self):
        psycopg, _sql = _import_psycopg()
        return psycopg.connect(self.dsn)

    def _ident(self, name: str):
        _psycopg, sql = _import_psycopg()
        return sql.Identifier(name)

    def _table(self):
        _psycopg, sql = _import_psycopg()
        return sql.SQL("{}.{}").format(self._ident(self.schema), sql.Identifier(GRAPH_TABLE))

    def _assert_provisioned(self) -> None:
        """Assert-only: the relation must already exist (Story 41.3).

        ``to_regclass`` returns NULL for a relation that does not exist, so
        one read answers the question without touching DDL. It does **not**
        mask a privilege gap: without ``USAGE`` on the schema it raises
        ``permission denied for schema <name>``. That case has its own
        remedy, because ``pyforge-scribe:3`` (the grants) is
        ``onFail:CONTINUE`` — on a database where the app role was created
        after the first ``liquibase update``, the grants were silently
        skipped — so name that changeset instead of leaking a raw driver
        error.
        """
        psycopg, _sql = _import_psycopg()
        qualified = f"{self.schema}.{GRAPH_TABLE}"
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT to_regclass(%s)", (qualified,)).fetchone()
        except psycopg.errors.InsufficientPrivilege as exc:
            raise GraphSchemaMissing(
                f"{qualified} is not readable by this role -- apply Liquibase "
                f"changeset {GRANTS_CHANGESET_ID} (src/platform/db/changelog) "
                "as the migration role; it is skipped when the app role does "
                "not yet exist, and the scribe runtime cannot grant itself "
                "access (CAP-9)"
            ) from exc
        if row is None or row[0] is None:
            raise GraphSchemaMissing(
                f"{qualified} is absent -- apply Liquibase changeset "
                f"{GRAPH_CHANGESET_ID} (src/platform/db/changelog) as the "
                "migration role; the scribe runtime holds DML only and never "
                "creates it (CAP-9)"
            )

    def _load(self) -> None:
        _psycopg, sql = _import_psycopg()
        with self._connect() as conn:
            rows = conn.execute(
                sql.SQL(
                    """
                    SELECT id, kind, title, text, citation,
                           valid_from, valid_until, superseded_by, stale
                    FROM {}
                    """
                ).format(self._table())
            ).fetchall()
        self._nodes = {
            row[0]: GraphNode(
                id=row[0],
                kind=row[1],
                title=row[2],
                text=row[3],
                citation=row[4],
                valid_from=row[5],
                valid_until=row[6],
                superseded_by=row[7],
                stale=row[8],
            )
            for row in rows
        }

    def reset(self) -> None:
        self._nodes = {}

    def upsert_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node

    def invalidate_edge(self, node_id: str, *, ended_at: datetime, superseded_by: str) -> None:
        existing = self._nodes.get(node_id)
        if existing is None:
            raise ValueError(f"cannot invalidate unknown node id {node_id!r} -- upsert it first")
        self._nodes[node_id] = existing.model_copy(update={"valid_until": ended_at, "superseded_by": superseded_by})

    def query_by_citation(self, citation: str) -> list[GraphNode]:
        return [node for node in self._nodes.values() if node.citation == citation]

    def iter_nodes(self) -> Iterator[GraphNode]:
        return iter(sorted(self._nodes.values(), key=lambda n: n.id))

    def query_similar(self, query: str, *, limit: int = 8) -> list[GraphNode]:
        vector = embed_text(query)
        if vector is None or limit <= 0:
            return []
        _psycopg, sql = _import_psycopg()
        literal = vector_literal(vector)
        with self._connect() as conn:
            rows = conn.execute(
                sql.SQL(
                    """
                    SELECT id, kind, title, text, citation,
                           valid_from, valid_until, superseded_by, stale
                    FROM {}
                    WHERE embedding IS NOT NULL
                      AND valid_until IS NULL
                      AND stale = false
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """
                ).format(self._table()),
                (literal, limit),
            ).fetchall()
        return [
            GraphNode(
                id=row[0],
                kind=row[1],
                title=row[2],
                text=row[3],
                citation=row[4],
                valid_from=row[5],
                valid_until=row[6],
                superseded_by=row[7],
                stale=row[8],
            )
            for row in rows
        ]

    def commit(self) -> None:
        _psycopg, sql = _import_psycopg()
        snapshot = list(self._nodes.values())
        with self._connect() as conn:
            with conn.transaction():
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (_GRAPH_LOCK_KEY,))
                conn.execute(sql.SQL("DELETE FROM {}").format(self._table()))
                for node in snapshot:
                    embedding = embed_text(f"{node.title} {node.text}")
                    embedding_literal = vector_literal(embedding) if embedding is not None else None
                    conn.execute(
                        sql.SQL(
                            """
                            INSERT INTO {} (
                                id, kind, title, text, citation,
                                valid_from, valid_until, superseded_by, embedding, stale
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                            """
                        ).format(self._table()),
                        (
                            node.id,
                            node.kind,
                            node.title,
                            node.text,
                            node.citation,
                            node.valid_from,
                            node.valid_until,
                            node.superseded_by,
                            embedding_literal,
                            node.stale,
                        ),
                    )


class PostgresGraphStorePlugin:
    """CAP-18 registration adapter for ``PostgresGraphStore`` (Story 28.1)."""

    hook_spec: str = GRAPHSTORE_HOOK_SPEC.name
    owner: str = PG_GRAPHSTORE_OWNER

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            store_path = context.get("store_path")
            if store_path is None:
                raise PluginError("graph-store plugin requires context['store_path']")
            dsn = resolve_graph_dsn(context)
            if dsn is None:
                raise PluginError(f"PostgreSQL graph-store requires context['dsn'] or {_DSN_ENV} (or DATABASE_URL)")
            context["store"] = PostgresGraphStore(dsn, Path(store_path))
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context
