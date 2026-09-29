"""Story 28.2 — opt-in bag-of-concepts recall hits a no-overlap target; lexical misses it."""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.scribe.graph_store import FlatFileGraphStore
from pyforge.scribe.graph_store_pg import PostgresGraphStore
from pyforge.scribe.models import GraphNode
from pyforge.scribe.recall import _answer_semantic, answer

_SCRIBE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[6]


def _node(node_id: str, text: str, citation: str) -> GraphNode:
    return GraphNode(
        id=node_id,
        kind="memory",
        title=node_id.rsplit("/", 1)[-1],
        text=text,
        citation=citation,
        valid_from=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


@pytest.fixture()
def cited_repo(tmp_path: Path) -> Path:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "dog.md").write_text("the family dog", encoding="utf-8")
    (notes / "physics.md").write_text("unrelated", encoding="utf-8")
    return tmp_path


def _load_pair(store: PostgresGraphStore | FlatFileGraphStore, repo: Path) -> None:
    store.reset()
    store.upsert_node(_node("memory:project/dog", "dog", "notes/dog.md"))
    store.upsert_node(
        _node(
            "memory:project/physics",
            "quantum chromodynamics scattering amplitudes",
            "notes/physics.md",
        )
    )
    store.commit()


def test_semantic_recall_hits_no_lexical_overlap_target(tmp_path: Path, pg_dsn: str, cited_repo: Path) -> None:
    store = PostgresGraphStore(pg_dsn, tmp_path / "ignored")
    _load_pair(store, cited_repo)

    lexical = answer("canine", store, repo_root=cited_repo, mode="lexical")
    semantic = answer("canine", store, repo_root=cited_repo, mode="semantic")

    assert lexical.grounded is False
    assert lexical.citation is None
    assert semantic.grounded is True
    assert semantic.node_id == "memory:project/dog"
    assert semantic.citation == "notes/dog.md"
    assert semantic.text == "dog"


def test_flatfile_semantic_stays_lexical_only(cited_repo: Path) -> None:
    store = FlatFileGraphStore(cited_repo / "graph.json")
    _load_pair(store, cited_repo)
    semantic = answer("canine", store, repo_root=cited_repo, mode="semantic")
    lexical = answer("canine", store, repo_root=cited_repo, mode="lexical")
    assert semantic.grounded is False
    assert lexical.grounded is False
    assert store.query_similar("canine") == []


def test_semantic_skips_unresolvable_citation(tmp_path: Path, pg_dsn: str, cited_repo: Path) -> None:
    store = PostgresGraphStore(pg_dsn, tmp_path / "ignored")
    store.reset()
    store.upsert_node(_node("memory:project/dog", "dog", "notes/missing.md"))
    store.commit()
    result = answer("canine", store, repo_root=cited_repo, mode="semantic")
    assert result.grounded is False


def test_semantic_path_is_not_aliased_to_lexical() -> None:
    semantic_src = inspect.getsource(_answer_semantic)
    answer_src = inspect.getsource(answer)
    pg_src = inspect.getsource(PostgresGraphStore.query_similar)
    assert "query_similar" in semantic_src
    assert "query_similar" in answer_src
    assert "<=>" in pg_src
    assert "_tokenize" not in semantic_src
    assert "overlap" not in semantic_src
    assert "_tokenize" not in pg_src
    assert "iter_nodes" not in pg_src


def test_callers_still_do_not_import_postgres_adapter() -> None:
    forbidden = {"psycopg", "pgvector", "psycopg2"}
    for rel in ("compile.py", "recall.py", "cli.py", "graph_store_plugins.py", "embeddings.py"):
        path = _SCRIBE_ROOT / "src" / "pyforge" / "scribe" / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
                if "graph_store_pg" in node.module:
                    imported.add("graph_store_pg")
        assert forbidden.isdisjoint(imported), f"{rel} imports {imported & forbidden}"
        assert "graph_store_pg" not in imported, f"{rel} imports the PG adapter"


def test_no_pyforge_package_under_src_platform() -> None:
    platform = _REPO_ROOT / "src" / "platform"
    assert platform.is_dir()
    offenders: list[str] = []
    for path in platform.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "query_similar" in text or "embed_text" in text or "graph_store_pg" in text:
            offenders.append(str(path.relative_to(_REPO_ROOT)))
    assert offenders == []


def test_unknown_recall_mode_raises(cited_repo: Path) -> None:
    store = FlatFileGraphStore(cited_repo / "graph.json")
    with pytest.raises(ValueError, match="unknown recall mode"):
        answer("canine", store, repo_root=cited_repo, mode="fuzzy")
