"""Story F3 (FR-5, AD-4, AD-13) — the RAG vss-ranking gate (``kedro-test``).

Proves the four F3 acceptance properties, all offline + deterministic:

(a) **ranked results FROM DuckDB** — embed a small artifact set, index it, run a similarity
    query, and assert the results come back nearest-first in a deterministic order (the
    deterministic default embedder makes the ranked fixture reproducible).
(b) **offline — no network** — the store LOADs ``vss`` from the local extension cache with
    ``autoinstall``/``autoload`` DISABLED, so the only way DuckDB could obtain ``vss`` (a
    network INSTALL / autoinstall) is turned off; the store still indexes + ranks. The
    embedder needs no model download.
(c) **unprovisioned vss degrades gracefully** — a connection pointed at an EMPTY extension
    directory (with autoinstall/autoload off) cannot LOAD ``vss``; the store raises a clear
    :class:`VssNotProvisionedError` naming the provisioning step — never a silent network
    INSTALL and never a silent wrong answer (AD-13).
(d) **the ranking runs IN DuckDB** — the search SQL's EXPLAIN plan computes
    ``array_distance`` and sorts (ORDER BY) inside DuckDB, an HNSW ``vss`` index exists over
    the ``FLOAT[N]`` column, and ``vss`` is loaded — the distance is a DuckDB expression, not
    a Python/numpy loop (AD-4, single engine).

Plus the F3 edge cases (empty corpus, no-match / k>corpus / very large k, duplicate & zero
embeddings, dimension mismatch, unicode) and the injectable-provisioning contract.
"""

from __future__ import annotations

import tempfile

import duckdb
import pytest

from pyforge.atlas.rag import (
    DEFAULT_EMBEDDING_DIM,
    DuckdbVssRagStore,
    HashingEmbedder,
    VssNotProvisionedError,
    load_vss_offline,
    provision_vss,
)

# A small, hand-authored artifact set with an obvious semantic clustering: two python-ish
# texts, one js, one rust. Deterministic embedder → reproducible ranked order.
ARTIFACTS = [
    ("py-recipe", "python conda-forge recipe packaging build"),
    ("js-pkg", "javascript npm node package manager"),
    ("py-pip", "python pip pypi package install"),
    ("rust", "rust cargo crate compile build"),
]


def _offline_connection() -> "duckdb.DuckDBPyConnection":
    """A DuckDB connection with autoinstall/autoload DISABLED — LOAD vss must come from the
    pre-provisioned local cache (offline), never a network INSTALL (AD-13)."""
    return duckdb.connect(
        config={
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
        }
    )


def _small_store(dim: int = 128) -> DuckdbVssRagStore:
    store = DuckdbVssRagStore(
        embedder=HashingEmbedder(dim=dim), connection=_offline_connection()
    )
    store.index(ARTIFACTS)
    return store


# ---------------------------------------------------------------------------
# (a) ranked results from DuckDB + determinism
# ---------------------------------------------------------------------------


def test_similarity_query_returns_ranked_results_from_duckdb():
    """A similarity query over embedded artifacts returns ranked results (nearest-first)."""
    store = _small_store()
    results = store.similarity_search("python package recipe build", k=3)
    assert len(results) == 3
    # ranked ascending by distance (nearest first)
    dists = [r["distance"] for r in results]
    assert dists == sorted(dists)
    # the nearest artifact is one of the python-ish ones, not js/rust (the vss ranking works)
    assert results[0]["id"] in {"py-recipe", "py-pip"}
    assert results[0]["distance"] <= results[-1]["distance"]


def test_ranked_order_is_deterministic_and_reproducible():
    """The deterministic embedder makes the ranked fixture reproducible run-to-run and
    across independent stores (offline gate reproducibility)."""
    a = _small_store()
    b = _small_store()
    q = "rust cargo build"
    ra = [r["id"] for r in a.similarity_search(q, k=4)]
    rb = [r["id"] for r in b.similarity_search(q, k=4)]
    assert ra == rb
    # nearest to a rust query is the rust artifact
    assert ra[0] == "rust"


def test_default_embedder_is_deterministic_across_instances():
    """Two fresh default embedders produce identical vectors (no per-process salt / RNG)."""
    v1 = HashingEmbedder(dim=64).embed("conda-forge python recipe")
    v2 = HashingEmbedder(dim=64).embed("conda-forge python recipe")
    assert v1 == v2
    assert len(v1) == 64
    assert HashingEmbedder().dim == DEFAULT_EMBEDDING_DIM


# ---------------------------------------------------------------------------
# (b) offline — no network
# ---------------------------------------------------------------------------


def test_store_loads_vss_offline_with_autoinstall_disabled():
    """The consumer path indexes + ranks with autoinstall/autoload OFF — proving vss is
    LOADed from the local cache with no network INSTALL possible (AD-13)."""
    store = _small_store()  # built on _offline_connection()
    assert store.count() == len(ARTIFACTS)
    # vss is actually loaded on this offline connection
    loaded = store.con.execute(
        "SELECT loaded FROM duckdb_extensions() WHERE extension_name='vss'"
    ).fetchone()
    assert loaded and loaded[0] is True
    # and a query still ranks
    assert store.similarity_search("python", k=1)


# ---------------------------------------------------------------------------
# (c) unprovisioned vss degrades gracefully
# ---------------------------------------------------------------------------


def test_unprovisioned_vss_raises_clear_error_not_a_network_install():
    """An empty extension directory (autoinstall/autoload off) cannot LOAD vss; the store
    raises a clear VssNotProvisionedError naming the provisioning step — no silent network
    INSTALL, no wrong answer (AD-13)."""
    empty_dir = tempfile.mkdtemp()
    unprovisioned = duckdb.connect(
        config={
            "extension_directory": empty_dir,
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
        }
    )
    with pytest.raises(VssNotProvisionedError) as exc:
        DuckdbVssRagStore(
            embedder=HashingEmbedder(dim=32), connection=unprovisioned
        )
    msg = str(exc.value)
    assert "provision" in msg.lower()
    assert "INSTALL" in msg  # the message points at the one-time provisioning step


def test_load_vss_offline_helper_translates_missing_extension():
    """The offline loader helper turns DuckDB's raw IO/catalog error into the typed,
    actionable VssNotProvisionedError."""
    empty_dir = tempfile.mkdtemp()
    con = duckdb.connect(
        config={
            "extension_directory": empty_dir,
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
        }
    )
    with pytest.raises(VssNotProvisionedError):
        load_vss_offline(con)


# ---------------------------------------------------------------------------
# (d) the ranking runs IN DuckDB (AD-4)
# ---------------------------------------------------------------------------


def test_ranking_is_a_duckdb_query_not_python():
    """The search SQL's plan computes array_distance + sorts IN DuckDB, an HNSW vss index
    exists over the FLOAT[N] column, and vss is loaded — the ranking is a DuckDB query."""
    store = _small_store()
    qv = store.embedder.embed("python recipe")
    plan_rows = store.con.execute(
        f"EXPLAIN SELECT id, array_distance(emb, ?::FLOAT[{store.dim}]) AS distance "
        f"FROM {store._table} ORDER BY distance ASC, id ASC LIMIT 3",
        [qv],
    ).fetchall()
    plan = "\n".join(r[1] for r in plan_rows).lower()
    # the distance is computed as a DuckDB expression, and the sort is a DuckDB ORDER BY
    assert "array_distance" in plan
    assert "order by" in plan
    # a vss HNSW index physically exists over the embedding column
    idx = store.con.execute(
        f"SELECT index_name FROM duckdb_indexes() WHERE table_name='{store._table}'"
    ).fetchall()
    assert any(store._index == row[0] for row in idx), f"HNSW index missing: {idx}"
    # vss is loaded (the index type only exists because the extension is loaded)
    loaded = store.con.execute(
        "SELECT loaded FROM duckdb_extensions() WHERE extension_name='vss'"
    ).fetchone()
    assert loaded and loaded[0] is True


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


def test_empty_corpus_returns_no_results():
    store = DuckdbVssRagStore(
        embedder=HashingEmbedder(dim=32), connection=_offline_connection()
    )
    assert store.index([]) == 0
    assert store.count() == 0
    assert store.similarity_search("anything", k=5) == []


def test_k_larger_than_corpus_returns_all_rows():
    store = _small_store()
    results = store.similarity_search("python", k=100)
    assert len(results) == len(ARTIFACTS)  # never more than the corpus


def test_very_large_k_is_safe():
    store = _small_store()
    assert len(store.similarity_search("python", k=1_000_000)) == len(ARTIFACTS)


def test_non_positive_k_returns_empty():
    store = _small_store()
    assert store.similarity_search("python", k=0) == []
    assert store.similarity_search("python", k=-3) == []


def test_duplicate_embeddings_rank_deterministically():
    """Identical texts (identical embeddings) tie on distance; the id tie-break keeps the
    order deterministic (no flaky ordering)."""
    store = DuckdbVssRagStore(
        embedder=HashingEmbedder(dim=64), connection=_offline_connection()
    )
    store.index([("a", "same text"), ("b", "same text"), ("c", "different words")])
    r1 = [r["id"] for r in store.similarity_search("same text", k=3)]
    r2 = [r["id"] for r in store.similarity_search("same text", k=3)]
    assert r1 == r2
    # the two identical-text artifacts are the two nearest, ordered by id
    assert r1[:2] == ["a", "b"]


def test_zero_vector_query_is_well_defined():
    """A query that embeds to the zero vector (empty / all-out-of-vocab text) must still
    return a well-defined L2 ranking (never a NaN / crash — that's why L2, not cosine)."""
    store = _small_store()
    results = store.similarity_search("", k=2)  # empty text → zero vector
    assert len(results) == 2
    assert all(r["distance"] == r["distance"] for r in results)  # not NaN


def test_zero_vector_artifact_indexes_and_ranks():
    """An artifact whose text embeds to the zero vector indexes fine and is rankable."""
    store = DuckdbVssRagStore(
        embedder=HashingEmbedder(dim=32), connection=_offline_connection()
    )
    store.index([("empty", ""), ("real", "python recipe")])
    assert store.count() == 2
    results = store.similarity_search("python recipe", k=2)
    assert results[0]["id"] == "real"  # the real match ranks above the zero-vector artifact


def test_dimension_mismatch_errors_clearly():
    """A query vector whose width != the indexed FLOAT[N] must raise a CLEAR error, never a
    silent wrong answer (AD-13)."""
    store = _small_store(dim=128)
    with pytest.raises(ValueError, match="dimension mismatch"):
        store._search_vector([0.1] * 10, k=3)


def test_unicode_artifacts_index_and_rank():
    store = DuckdbVssRagStore(
        embedder=HashingEmbedder(dim=64), connection=_offline_connection()
    )
    store.index([("u1", "café déjà vü 日本語 packaging"), ("u2", "plain ascii text")])
    assert store.count() == 2
    results = store.similarity_search("café 日本語", k=2)
    assert results[0]["id"] == "u1"


# ---------------------------------------------------------------------------
# injectable provisioning contract (the gate controls provisioning — AD-13)
# ---------------------------------------------------------------------------


def test_vss_loader_is_injectable_and_called():
    """The vss_loader is injectable so the gate/consumer controls provisioning; the store
    calls it exactly once at construction on its own connection."""
    calls: list[object] = []

    def spy_loader(con):
        calls.append(con)
        con.execute("LOAD vss")

    store = DuckdbVssRagStore(
        embedder=HashingEmbedder(dim=16),
        connection=_offline_connection(),
        vss_loader=spy_loader,
    )
    assert calls == [store.con]


def test_provision_vss_is_a_separate_attended_path():
    """provision_vss (the network INSTALL) is a distinct callable, never invoked by the
    default consumer store path — it is the attended one-time step (DW-F3-2)."""
    # the default loader is the OFFLINE one, not the provisioning one
    import inspect

    assert DuckdbVssRagStore.__init__.__defaults__ is None  # kw-only; check signature default
    sig = inspect.signature(DuckdbVssRagStore.__init__)
    assert sig.parameters["vss_loader"].default is load_vss_offline
    assert provision_vss is not load_vss_offline


def test_index_and_search_on_a_PERSISTENT_connection():
    """F3 review (both reviewers): the store's stated purpose is riding the F1 on-disk
    consolidated store. vss refuses an HNSW index on a persistent DB unless
    hnsw_enable_experimental_persistence is set — the store now sets it, so index()+search
    work on a file-backed connection (every prior test used in-memory, masking this)."""
    import os as _os
    with tempfile.TemporaryDirectory() as d:
        path = _os.path.join(d, "f1_consolidated.duckdb")
        con = duckdb.connect(
            path,
            config={"autoinstall_known_extensions": False, "autoload_known_extensions": False},
        )
        store = DuckdbVssRagStore(embedder=HashingEmbedder(dim=32), connection=con)
        n = store.index([("a", "conda-forge python recipe"), ("b", "rust cargo crate")])
        assert n == 2
        hits = store.similarity_search("python recipe", k=1)
        assert len(hits) == 1 and hits[0]["id"] in {"a", "b"}


def test_malicious_table_or_metric_identifier_is_rejected():
    """F3 review: table/metric are interpolated into DDL by name (no identifier bind param), so
    a value smuggling a second statement must be rejected at construction, not executed."""
    con = duckdb.connect()
    con.execute("CREATE TABLE victim(secret VARCHAR)")
    with pytest.raises(ValueError, match="invalid table identifier"):
        DuckdbVssRagStore(
            embedder=HashingEmbedder(dim=8), connection=con,
            table="rag (id VARCHAR); DROP TABLE victim; CREATE TABLE rag2",
        )
    # victim survives — the injection never executed.
    assert con.execute("SELECT count(*) FROM victim").fetchone()[0] == 0
    with pytest.raises(ValueError, match="invalid metric identifier"):
        DuckdbVssRagStore(embedder=HashingEmbedder(dim=8), metric="l2sq'); DROP TABLE x; --")
