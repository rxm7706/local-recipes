"""Steward 34.3: vectors persist on the plane writer (FR-48, canopy AD-22)."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import duckdb
import pytest

from pyforge.atlas.duckdb_writer import ATLAS_DUCKDB_NAME
from pyforge.atlas.query_plane_vectors import extract_real_arrays_onto_plane, nearest_neighbor, open_plane_rag_store
from pyforge.atlas.rag import HashingEmbedder
from pyforge.atlas.rag.store import load_vss_offline

ATLAS_ROOT = Path(__file__).resolve().parents[2]
VECTORS_MODULE = ATLAS_ROOT / "src" / "pyforge" / "atlas" / "query_plane_vectors.py"
STORE_MODULE = ATLAS_ROOT / "src" / "pyforge" / "atlas" / "rag" / "store.py"


def _has_vss() -> bool:
    try:
        con = duckdb.connect(
            config={
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
            }
        )
        try:
            load_vss_offline(con)
            return True
        finally:
            con.close()
    except Exception:
        return False


requires_vss = pytest.mark.skipif(
    not _has_vss(),
    reason="vss DuckDB extension is not provisioned in local cache",
)


@requires_vss
def test_extract_plants_float_n_and_vss_returns_row(tmp_path: Path) -> None:
    plane = tmp_path / ATLAS_DUCKDB_NAME
    planted = [1.0, 0.0, 0.0, 0.0]
    other = [0.0, 1.0, 0.0, 0.0]
    writer = extract_real_arrays_onto_plane(
        plane,
        [("planted", planted), ("other", other)],
        dim=4,
    )
    try:
        hits = nearest_neighbor(writer, planted, dim=4, k=1)
        assert hits[0][0] == "planted"
        assert hits[0][1] == pytest.approx(0.0)
        extras = list(tmp_path.glob("*.duckdb"))
        assert extras == [plane]
    finally:
        writer.close()


@requires_vss
def test_open_plane_rag_store_uses_writer_not_memory(tmp_path: Path) -> None:
    plane = tmp_path / ATLAS_DUCKDB_NAME
    store = open_plane_rag_store(plane, embedder=HashingEmbedder(dim=32))
    try:
        store.index([("a", "alpha token cluster"), ("b", "unrelated rust crate")])
        hits = store.similarity_search("alpha token", k=1)
        assert hits[0]["id"] == "a"
        assert Path(store.con.execute("PRAGMA database_list").fetchone()[2]).name == ATLAS_DUCKDB_NAME
    finally:
        store.close()


def test_open_plane_rag_store_rejects_second_duckdb(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="atlas.duckdb"):
        open_plane_rag_store(tmp_path / "other.duckdb")


def test_consumer_path_does_not_install() -> None:
    text = VECTORS_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(VECTORS_MODULE))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert "INSTALL" not in node.value
    source = inspect.getsource(extract_real_arrays_onto_plane)
    assert "LOAD" in source or "load_vss_offline" in source
    store_src = STORE_MODULE.read_text(encoding="utf-8")
    assert "def load_vss_offline" in store_src
    assert 'con.execute("INSTALL vss")' in store_src  # attended only
    assert store_src.index("def load_vss_offline") < store_src.index("def provision_vss")
