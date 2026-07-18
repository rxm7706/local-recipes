"""DuckDB ``vss`` RAG store — Story F3 (FR-5, AD-4, AD-13).

Semantic retrieval over embedded artifacts runs in the **same single engine** as the rest
of the migrated atlas (AD-4): the similarity RANKING is a DuckDB SQL query
(``ORDER BY array_distance(emb, ?) LIMIT k``) over a ``FLOAT[N]`` embedding column — NEVER a
numpy/pandas/faiss/hnswlib loop. Nothing here computes a distance in Python;
:meth:`DuckdbVssRagStore.similarity_search` returns the rows DuckDB already ranked. The
exact top-k is a DuckDB seq-scan + top-n; the ``vss`` **HNSW** index is the scale structure
over the embedding column whose *creation* (``index()``) requires the ``vss`` extension (so
provisioning is genuinely load-bearing) — approximate index-scan retrieval is the scale path,
the shipped query is exact.

**AD-13 — offline ``vss`` provisioning (RESOLVED, not ignored).** DuckDB's default
``INSTALL vss`` hits the network, which collides with AD-13 for the consumer profile. So the
consumer path only ever ``LOAD``s ``vss`` from the pre-provisioned local extension cache
(offline) via the injectable ``vss_loader`` (default :func:`load_vss_offline`). If ``vss`` is
NOT provisioned, the store **degrades gracefully**: :func:`load_vss_offline` raises a clear
:class:`VssNotProvisionedError` naming the one-time provisioning step — never a silent network
``INSTALL`` and never a silent wrong answer. The network ``INSTALL`` lives ONLY in the explicit,
attended :func:`provision_vss` (DW-F3-2), which the consumer path never calls.

The DuckDB connection is injectable (default a fresh in-memory connection) so the RAG surface
can ride the SAME consolidated F1 store (AD-4 single engine) rather than a second engine.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Sequence

import duckdb

from .embedding import Embedder, HashingEmbedder

# array_distance (L2) ↔ HNSW metric 'l2sq' — the matching pair the vss optimizer needs to use
# the index for a k-NN ``ORDER BY … LIMIT`` scan. L2 (not cosine) so a zero embedding vector
# stays a well-defined distance instead of NaN (AD-13: never a silent wrong answer).
_HNSW_METRIC = "l2sq"

# The offline LOAD step. The connection type used to gate the vss loader.
VssLoader = Callable[["duckdb.DuckDBPyConnection"], None]

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _valid_identifier(value: str, what: str) -> str:
    """A bare SQL identifier (interpolated into DDL by name — DuckDB has no identifier bind
    param). Rejects anything that could smuggle a second statement / drop a table."""
    if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
        raise ValueError(
            f"invalid {what} identifier {value!r}: must match {_IDENTIFIER_RE.pattern} "
            "(a bare SQL identifier — no spaces, quotes, or statement separators)"
        )
    return value


class VssNotProvisionedError(RuntimeError):
    """Raised when ``vss`` cannot be LOADed offline — the extension is not provisioned in the
    local cache and the consumer path must NOT reach for the network (AD-13). The message names
    the one-time provisioning step (:func:`provision_vss`, DW-F3-2)."""


def load_vss_offline(con: "duckdb.DuckDBPyConnection") -> None:
    """LOAD ``vss`` from the pre-provisioned local extension cache — OFFLINE (the consumer path).

    No ``INSTALL`` (that is the network step). If the extension is not present in the cache,
    DuckDB raises an IO/Catalog error; we translate it into a clear :class:`VssNotProvisionedError`
    so the caller degrades gracefully instead of silently falling back to a wrong answer or an
    unhandled network call (AD-13)."""
    try:
        con.execute("LOAD vss")
    except Exception as exc:  # duckdb.IOException / CatalogException / etc.
        raise VssNotProvisionedError(
            "the DuckDB 'vss' extension is not provisioned in the local extension cache, so it "
            "cannot be LOADed offline. The consumer path never runs a network INSTALL (AD-13). "
            "Run the one-time attended provisioning step first: "
            "pyforge.atlas.rag.provision_vss(connection)  (or `INSTALL vss;` in an attended "
            f"DuckDB session with network access). Underlying error: {type(exc).__name__}: {exc}"
        ) from exc


def provision_vss(con: "duckdb.DuckDBPyConnection") -> None:
    """One-time ATTENDED provisioning: ``INSTALL vss`` (network) then ``LOAD vss`` (DW-F3-2).

    This is the ONLY code path that may touch the network to obtain ``vss``. It is never called
    by the consumer/default store path — an operator runs it once to populate the local extension
    cache, after which :func:`load_vss_offline` works with no network."""
    con.execute("INSTALL vss")
    con.execute("LOAD vss")


def _as_artifacts(artifacts: Any) -> list[tuple[str, str]]:
    """Coerce the artifact input to a list of ``(id, text)`` pairs. Accepts an iterable of
    ``(id, text)`` pairs OR of mappings with ``id``/``text`` keys. Robust to ``None`` (→ empty).

    ``id`` and ``text`` are coerced to ``str`` — unicode passes through unchanged."""
    if artifacts is None:
        return []
    out: list[tuple[str, str]] = []
    for item in artifacts:
        if isinstance(item, dict):
            out.append((str(item["id"]), str(item["text"])))
        else:
            art_id, text = item
            out.append((str(art_id), str(text)))
    return out


class DuckdbVssRagStore:
    """RAG store whose similarity search runs IN DuckDB via ``vss`` (AD-4).

    Artifacts are embedded (via the injectable, deterministic-by-default :class:`Embedder`)
    into a ``FLOAT[dim]`` column; an HNSW index over that column makes the k-NN
    ``ORDER BY array_distance(...) LIMIT k`` query an index scan. The ranking is ALWAYS a
    DuckDB query — no Python-side distance math.
    """

    def __init__(
        self,
        *,
        embedder: Embedder | None = None,
        connection: "duckdb.DuckDBPyConnection | None" = None,
        vss_loader: VssLoader = load_vss_offline,
        table: str = "rag_artifacts",
        metric: str = _HNSW_METRIC,
    ) -> None:
        self.embedder: Embedder = embedder if embedder is not None else HashingEmbedder()
        self.dim = int(self.embedder.dim)
        # `table`/`metric` are interpolated into DDL/DML by name (DuckDB has no bind param for
        # an identifier), so validate them as bare SQL identifiers — a value like
        # "rag; DROP TABLE x" would otherwise execute (both are developer-controlled today, but
        # an unquoted-identifier injection is a real hole; F3 review).
        self._table = _valid_identifier(table, "table")
        self._metric = _valid_identifier(metric, "metric")
        # Injectable connection so the RAG surface can ride the SAME F1 consolidated store
        # (AD-4 single engine); default is a fresh in-memory DuckDB. Ownership is tracked so
        # close() never tears down an injected F1 connection.
        self._owns_con = connection is None
        self.con = connection if connection is not None else duckdb.connect()
        self._index = f"{self._table}_hnsw"
        # AD-13 gate: LOAD vss offline (or raise VssNotProvisionedError). No network INSTALL.
        vss_loader(self.con)
        # vss HNSW indexes are refused on a PERSISTENT (on-disk) DuckDB — the exact store F3 is
        # designed to share with F1 — unless this flag is set. The HNSW index is DERIVED,
        # rebuildable data (index() rebuilds it from the artifacts), so a crash-lost index is
        # recoverable by re-indexing; enabling experimental persistence is safe for it and is
        # what makes the documented "ride the F1 consolidated store" integration actually work
        # (F3 review — every test used in-memory, masking the on-disk BinderException).
        self.con.execute("SET hnsw_enable_experimental_persistence = true")
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.con.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} "
            f"(id VARCHAR, text VARCHAR, emb FLOAT[{self.dim}])"
        )

    def index(self, artifacts: Any) -> int:
        """(Re)build the store from ``artifacts`` — an iterable of ``(id, text)`` pairs or
        ``{id, text}`` mappings. Replaces existing contents, embeds every artifact, and builds
        the ``vss`` HNSW index. Returns the number of artifacts indexed.

        An empty artifact set is valid (leaves an empty, queryable store — F3 edge case)."""
        rows = _as_artifacts(artifacts)
        # Drop the index BEFORE mutating rows (HNSW does not support in-place row changes on a
        # persisted table); rebuild it after the bulk insert.
        self.con.execute(f"DROP INDEX IF EXISTS {self._index}")
        self.con.execute(f"DELETE FROM {self._table}")
        for art_id, text in rows:
            emb = self.embedder.embed(text)
            self._require_dim(emb)
            self.con.execute(
                f"INSERT INTO {self._table} VALUES (?, ?, ?::FLOAT[{self.dim}])",
                [art_id, text, emb],
            )
        # Build the HNSW index (requires vss — proves provisioning). Safe on an empty table.
        self.con.execute(
            f"CREATE INDEX {self._index} ON {self._table} "
            f"USING HNSW (emb) WITH (metric = '{self._metric}')"
        )
        return len(rows)

    def similarity_search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Return the ``k`` nearest artifacts to ``query``, RANKED nearest-first BY DuckDB.

        The query text is embedded with the SAME embedder, then the ranking is an **exact**
        DuckDB ``ORDER BY array_distance(emb, ?) LIMIT k`` — distance computed and sorted IN
        DuckDB, never in Python (AD-4, single engine). The result is exact and deterministic
        (ties broken by ``id``); the exact top-k does a DuckDB seq-scan + top-n, NOT an
        approximate HNSW scan (the ``id`` tiebreak keeps it exact, so it does not use the index).
        The ``vss`` extension is still load-bearing at the STORE level: the HNSW index is the
        vss-backed scale structure over the ``FLOAT[N]`` column, and BUILDING it (``index()``)
        requires ``vss`` — so provisioning is genuinely exercised. Each result is
        ``{"id", "text", "distance"}``, ascending by ``distance``."""
        return self._search_vector(self.embedder.embed(query), k)

    def _search_vector(self, query_vec: Sequence[float], k: int) -> list[dict[str, Any]]:
        """Rank by a raw query vector — the DuckDB-side k-NN. Validates the query dimension
        matches the index (a mismatch raises a CLEAR ValueError, never a silent wrong answer —
        AD-13). ``k <= 0`` returns an empty list; a very large ``k`` simply returns all rows."""
        self._require_dim(query_vec)
        if k <= 0:
            return []
        rows = self.con.execute(
            f"SELECT id, text, array_distance(emb, ?::FLOAT[{self.dim}]) AS distance "
            f"FROM {self._table} ORDER BY distance ASC, id ASC LIMIT ?",
            [list(query_vec), int(k)],
        ).fetchall()
        return [{"id": r[0], "text": r[1], "distance": r[2]} for r in rows]

    def _require_dim(self, vec: Sequence[float]) -> None:
        if len(vec) != self.dim:
            raise ValueError(
                f"embedding dimension mismatch: got {len(vec)}, store/index dim is {self.dim}. "
                "The query vector must match the indexed FLOAT[N] width (AD-13: a mismatch is a "
                "clear error, never a silent wrong answer)."
            )

    def count(self) -> int:
        return int(self.con.execute(f"SELECT count(*) FROM {self._table}").fetchone()[0])

    def close(self) -> None:
        """Close the connection ONLY if this store created it. An injected connection (the F1
        consolidated store) belongs to its owner — closing it here would tear down the shared
        single engine (AD-4)."""
        if self._owns_con:
            self.con.close()
